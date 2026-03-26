"""
RAG-grounded chat endpoint for the Zena widget.

Endpoint:
  POST /v1/rag/chat  — query → RAG search → context inject → LLM generate → respond

This is the backend that powers the embedded Zena chatbot widget.
It retrieves relevant context from the RAG pipeline before generating a response.
"""

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger("api_server")

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────


class RAGChatMessage(BaseModel):
    role: str = "user"
    content: str = ""


class RAGChatRequest(BaseModel):
    """Request body for /v1/rag/chat."""

    messages: List[RAGChatMessage] = []
    temperature: float = 0.7
    max_tokens: Optional[int] = 512
    top_k: int = 5  # RAG retrieval depth
    score_threshold: float = 0.3  # minimum relevance
    system_prompt: Optional[str] = None  # override system prompt
    focus_mode: Optional[str] = None  # prompt focus mode (e.g. "data_extraction")


class RAGChatResponse(BaseModel):
    id: str
    object: str = "rag.chat.completion"
    created: int
    model: str = "rag-pipeline"
    choices: List[Dict[str, Any]]
    usage: Dict[str, Any] = {}
    rag_sources: List[Dict[str, Any]] = []  # sources used for context


# ── Singleton accessor for the RAG integration ────────────────────────


def _get_rag_integration():
    """Try to import and return the global RAG integration instance."""
    try:
        from rag_integration import RAGIntegration

        return RAGIntegration()
    except Exception:
        return None


def _get_llm_state():
    """Get the API server state (LLM adapter) if available."""
    try:
        from server.helpers import get_state

        return get_state()
    except Exception:
        return None


# ── The endpoint ──────────────────────────────────────────────────────


@router.post("/v1/rag/chat")
async def rag_chat(req: RAGChatRequest):
    """
    RAG-augmented chat completion.

    1. Extract the user query from the last message
    2. Search the RAG knowledge base for relevant context
    3. Inject context into the system prompt
    4. Generate a response via the LLM (or return context-only if no LLM)
    """
    if not req.messages:
        raise HTTPException(400, detail="messages required")

    # Extract the latest user message as the query
    user_query = ""
    for msg in reversed(req.messages):
        if msg.role == "user" and msg.content.strip():
            user_query = msg.content.strip()
            break
    if not user_query:
        raise HTTPException(400, detail="No user message found")

    request_id = f"ragchat-{uuid.uuid4().hex[:12]}"
    created = int(time.time())

    # ── Step 1: RAG retrieval ─────────────────────────────────────────
    rag = _get_rag_integration()
    context_text = ""
    rag_sources: List[Dict[str, Any]] = []

    if rag and rag.initialized:
        try:
            context_text, raw_results = await rag.query_context(
                query=user_query,
                top_k=req.top_k,
                score_threshold=req.score_threshold,
            )
            rag_sources = [
                {
                    "text": r.get("text", "")[:300],
                    "score": round(r.get("score", 0), 3),
                    "source": r.get("source", "unknown"),
                }
                for r in raw_results
            ]
        except Exception as e:
            logger.warning(f"[rag-chat] RAG retrieval failed: {e}")
            context_text = ""
            rag_sources = []

    # ── Step 2: Build messages with context ──────────────────────────
    # Apply focus mode if specified (prompt injection for data tasks)
    focused_query = user_query
    try:
        from Core.prompt_focus import FocusMode, apply_focus

        if req.focus_mode:
            _mode = FocusMode.from_string(req.focus_mode)
            if _mode != FocusMode.GENERAL:
                _focus_sys, focused_query = apply_focus(_mode, user_query, req.system_prompt)
                if not req.system_prompt:
                    req.system_prompt = _focus_sys
    except ImportError as exc:
        logger.debug("%s", exc)

    system_prompt = req.system_prompt or (
        "You are Zena, a helpful virtual assistant. "
        "Answer the user's question using ONLY the provided context. "
        "If the context doesn't contain the answer, say so honestly. "
        "Respond in the same language the user uses."
    )

    if context_text:
        system_prompt += f"\n\n--- KNOWLEDGE BASE CONTEXT ---\n{context_text}\n--- END CONTEXT ---"

    messages_for_llm = [{"role": "system", "content": system_prompt}]
    for msg in req.messages:
        # Replace the last user message with the focused version
        if msg.role == "user" and msg.content.strip() == user_query:
            messages_for_llm.append({"role": msg.role, "content": focused_query})
        else:
            messages_for_llm.append({"role": msg.role, "content": msg.content})

    # ── Step 3: Try LLM generation ───────────────────────────────────
    state = _get_llm_state()
    response_text = ""

    if state and state.ready and state.adapter:
        try:
            from server.helpers import build_inference_request, estimate_tokens
            from server.schemas import ChatCompletionRequest, ChatMessage

            # Build a ChatCompletionRequest for the existing infrastructure
            chat_req = ChatCompletionRequest(
                messages=[ChatMessage(role=m["role"], content=m["content"]) for m in messages_for_llm],
                temperature=req.temperature,
                max_tokens=req.max_tokens or 512,
                stream=False,
            )
            llm_req = build_inference_request(messages_for_llm, chat_req)

            async with state.inference_semaphore:
                result = await asyncio.to_thread(state.adapter.generate, llm_req)
            response_text = result if isinstance(result, str) else str(result)

            # Cache the result
            try:
                state.cache.put(
                    messages_for_llm,
                    req.temperature,
                    req.max_tokens or 512,
                    response_text,
                )
            except Exception as exc:
                logger.debug("%s", exc)

            prompt_tokens = estimate_tokens(messages_for_llm)
            completion_tokens = estimate_tokens(response_text)
            state.record_request(completion_tokens)

            return JSONResponse(
                content={
                    "id": request_id,
                    "object": "rag.chat.completion",
                    "created": created,
                    "model": getattr(state, "model_id", "rag-pipeline"),
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": response_text,
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": prompt_tokens + completion_tokens,
                    },
                    "rag_sources": rag_sources,
                }
            )

        except Exception as e:
            logger.warning(f"[rag-chat] LLM generation failed: {e}, falling back to context-only")

    # ── Fallback: return RAG context without LLM ─────────────────────
    if context_text:
        # Format context as a readable answer
        response_text = "Based on the knowledge base, here is what I found:\n\n" + context_text[:2000]
    else:
        response_text = (
            "I don't have enough information to answer that question yet. "
            "Please make sure data has been loaded into the RAG pipeline."
        )

    return JSONResponse(
        content={
            "id": request_id,
            "object": "rag.chat.completion",
            "created": created,
            "model": "rag-context-only",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {},
            "rag_sources": rag_sources,
        }
    )
