"""
Helper utilities shared across routers.

Extracted from api_server.py.
"""

import time
from typing import Dict, List, Optional

from server.schemas import (
    ChatCompletionRequest,
    InferenceRequest,
)


def get_state():
    """Get the global ServerState — imported lazily to avoid circular deps."""
    import api_server

    return api_server.state


def get_swap_tracker():
    """Get the global SwapTracker."""
    import api_server

    return api_server._swap_tracker


def get_llm():
    """Get the raw Llama object (or None) — delegates to api_server._get_llm for patchability."""
    import api_server

    return api_server._get_llm()


def get_token_streamer():
    """Get the adapter that supports token streaming — delegates to api_server._get_token_streamer."""
    import api_server

    return api_server._get_token_streamer()


def estimate_tokens(content) -> int:
    """Estimate token count (~4 chars per token for English)."""
    if isinstance(content, str):
        return max(1, len(content) // 4)
    if isinstance(content, list):
        total = sum(len(m.get("content", "")) for m in content)
        return max(1, total // 4)
    return 1


def build_completion_json(
    request_id: str,
    text: str,
    completion_tokens: int,
    prompt_tokens: int,
    tool_calls: Optional[List[Dict]] = None,
) -> dict:
    """Build a standard chat.completion JSON response."""
    state = get_state()
    message = {"role": "assistant", "content": text}
    finish_reason = "stop"
    if tool_calls:
        message["tool_calls"] = tool_calls
        finish_reason = "tool_calls"

    return {
        "id": request_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": state.model_id if state else "unknown",
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def build_inference_request(messages: List[dict], req: ChatCompletionRequest) -> InferenceRequest:
    """Build a proper InferenceRequest from the HTTP request + messages."""
    return InferenceRequest(
        prompt=next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"),
            "",
        ),
        system_prompt=next(
            (m["content"] for m in messages if m["role"] == "system"),
            None,
        ),
        temperature=req.temperature,
        top_p=req.top_p,
        max_tokens=req.max_tokens or 2048,
        stream=req.stream,
        messages=messages,
        grammar=req.grammar,
        response_format=req.response_format,
        tools=getattr(req, "tools", None),
        tool_choice=getattr(req, "tool_choice", None),
        seed=req.seed,
        logprobs=req.logprobs,
        top_logprobs=req.top_logprobs,
        logit_bias=req.logit_bias,
        top_k=getattr(req, "top_k", None),
        min_p=getattr(req, "min_p", None),
        repeat_penalty=getattr(req, "repeat_penalty", None),
        frequency_penalty=req.frequency_penalty,
        presence_penalty=req.presence_penalty,
    )


def tokenize_for_stream(text: str) -> List[str]:
    """Fallback: split text into token-like chunks for fake streaming."""
    tokens = []
    current = []
    for ch in text:
        current.append(ch)
        if ch in (" ", "\n", ".", ",", ";", "!", "?", ":", ")", "]", "}"):
            tokens.append("".join(current))
            current = []
        elif len(current) >= 5:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tokens
