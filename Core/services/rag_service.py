"""
RAG Service — Retrieval Augmented Generation Pipeline.

Responsibility: Orchestrate the full RAG workflow:
  1. Retrieve relevant documents from the vector store
  2. Augment the query with document context
  3. Generate a response using the LLM

This service is pure Python, async, and fully testable.
Adapted from RAG_RAT/Core/services/rag_service.py.
"""

from __future__ import annotations

import asyncio
import logging
import time as _time
from typing import Any, AsyncGenerator, Dict, List, Optional

from Core.exceptions import (
    DocumentError,
    LLMError,
    RAGError,
    ValidationError,
)

logger = logging.getLogger(__name__)

_DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant. Use the provided context to answer "
    "the user's question accurately.  If the context does not contain "
    "enough information, say so honestly."
)


class RAGService:
    """
    Orchestrate the RAG pipeline.

    Pure business logic — no UI dependencies.
    Combines retrieval + augmentation + generation.
    """

    def __init__(self):
        self.llm_service = None
        self.doc_service = None

    # ─── Full Pipeline ───────────────────────────────────

    async def full_rag_pipeline(
        self,
        query: str,
        provider: str,
        model: str,
        api_key: Optional[str] = None,
        top_k: int = 5,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """
        Execute the full RAG pipeline: retrieve → augment → generate.

        Returns:
            Generated response with context.

        Raises:
            ValidationError, RAGError, LLMError
        """
        self._validate_query(query)

        try:
            # Step 1: Retrieve
            logger.info(f"RAG: Retrieving for '{query[:50]}…'")
            documents = await self._retrieve_documents(query, top_k)
            if not documents:
                logger.warning("RAG: No documents found; proceeding without context")
            else:
                logger.info(f"RAG: Retrieved {len(documents)} documents")

            # Step 2: Augment
            messages = self._augment_query(query, documents, system_prompt)

            # Step 3: Generate
            logger.info("RAG: Generating response")
            response = await self._generate_response(
                messages, provider, model, api_key, temperature, max_tokens, **kwargs
            )
            logger.info(f"✓ RAG pipeline complete: {len(response)} chars")
            return response

        except (ValidationError, RAGError, LLMError):
            raise
        except Exception as exc:
            raise RAGError(f"RAG pipeline failed: {exc}", stage="full_pipeline")

    async def stream_rag_pipeline(
        self,
        query: str,
        provider: str,
        model: str,
        api_key: Optional[str] = None,
        top_k: int = 5,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Stream RAG response tokens."""
        self._validate_query(query)
        try:
            documents = await self._retrieve_documents(query, top_k)
            messages = self._augment_query(query, documents, system_prompt)
            async for chunk in self._stream_response(
                messages, provider, model, api_key, temperature, max_tokens, **kwargs
            ):
                yield chunk
        except (ValidationError, RAGError, LLMError):
            raise
        except Exception as exc:
            raise RAGError(f"RAG stream failed: {exc}", stage="stream_pipeline")

    async def retrieve_documents(
        self, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Public method — retrieve documents matching *query*."""
        self._validate_query(query)
        return await self._retrieve_documents(query, top_k)

    # ─── Private Helpers ─────────────────────────────────

    async def _retrieve_documents(
        self, query: str, top_k: int
    ) -> List[Dict[str, Any]]:
        """Retrieve from RAGIntegration or return empty list."""
        try:
            try:
                from rag_integration import get_rag

                rag = await get_rag()
                if rag and rag.initialized:
                    results = await rag.search_context(
                        query, top_k=top_k, score_threshold=0.25
                    )
                    return [
                        {
                            "name": r.get("source", "unknown"),
                            "content": r.get("text", ""),
                            "score": r.get("score", 0),
                        }
                        for r in results
                    ]
            except ImportError:
                logger.debug("RAGIntegration not available")
            except Exception as exc:
                logger.warning(f"RAGIntegration search failed: {exc}")
            return []
        except Exception as exc:
            raise RAGError(f"Retrieval error: {exc}", stage="retrieval")

    def _augment_query(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Augment query with document context → OpenAI-format messages."""
        try:
            sys_msg = system_prompt or _DEFAULT_SYSTEM_PROMPT
            if not documents:
                return [
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": query},
                ]

            context = "\n\n".join(
                f"Document: {doc.get('name', 'Unknown')}\n"
                f"Content: {doc.get('content', '')[:500]}…"
                for doc in documents[:3]
            )
            augmented = (
                f"Use the following documents to answer the query:\n\n"
                f"{context}\n\nQuery: {query}"
            )
            return [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": augmented},
            ]
        except Exception as exc:
            raise RAGError(f"Augmentation failed: {exc}", stage="augmentation")

    async def _generate_response(
        self,
        messages: List[Dict[str, str]],
        provider: str,
        model: str,
        api_key: Optional[str],
        temperature: float,
        max_tokens: int,
        **kwargs: Any,
    ) -> str:
        if self.llm_service is None:
            from Core.services.llm_service import LLMService

            self.llm_service = LLMService()
        try:
            return await self.llm_service.call_llm(
                provider=provider,
                model=model,
                messages=messages,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
        except LLMError:
            raise
        except Exception as exc:
            raise RAGError(f"Generation failed: {exc}", stage="generation")

    async def _stream_response(
        self,
        messages: List[Dict[str, str]],
        provider: str,
        model: str,
        api_key: Optional[str],
        temperature: float,
        max_tokens: int,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        if self.llm_service is None:
            from Core.services.llm_service import LLMService

            self.llm_service = LLMService()
        try:
            async for chunk in self.llm_service.stream_llm(
                provider=provider,
                model=model,
                messages=messages,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            ):
                yield chunk
        except LLMError:
            raise
        except Exception as exc:
            raise RAGError(f"Stream generation failed: {exc}", stage="generation")

    @staticmethod
    def _validate_query(query: str) -> None:
        if not query or not query.strip():
            raise ValidationError("Query cannot be empty", field="query")
        if len(query) > 100_000:
            raise ValidationError("Query too long (max 100 000 chars)", field="query")
