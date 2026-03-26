"""
Chat completions & legacy completions router.

Endpoints:
  POST /v1/chat/completions
  POST /v1/completions
  POST /v1/infill
"""

import asyncio
import json
import sys
import time
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from server.schemas import (
    ChatCompletionRequest,
    ChatMessage,
    CompletionRequest,
    InferenceRequest,
    InfillRequest,
)
from server.helpers import (
    get_state,
    get_llm,
    get_token_streamer,
    estimate_tokens,
    build_completion_json,
    build_inference_request,
    tokenize_for_stream,
)

from inference_guard import InferenceGuard
from compact_tokens import compact_for_inference

router = APIRouter()

_AUTO_COMPACT_THRESHOLD = 2048


@router.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    """OpenAI-compatible chat completions — TRUE token streaming."""
    state = get_state()
    if not state:
        raise HTTPException(503, detail="Server not initialized")
    if not state.ready:
        state.initialize()
    if not state.ready:
        raise HTTPException(503, detail="Model not loaded — check logs")
    if not req.messages:
        raise HTTPException(400, detail="messages required")

    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    # Auto-compact long conversations
    est_tokens = estimate_tokens(messages)
    if est_tokens > _AUTO_COMPACT_THRESHOLD and len(messages) > 4:
        import logging

        logger = logging.getLogger("api_server")
        messages = compact_for_inference(
            messages,
            keep_last_n=4,
            target_tokens=req.max_tokens or 2048,
        )
        new_est = estimate_tokens(messages)
        logger.info(
            f"[compact] Auto-compacted: {est_tokens} -> {new_est} tokens ({len(req.messages)} -> {len(messages)} msgs)"
        )

    # Cache check (non-streaming only)
    if not req.stream:
        cached = state.cache.get(messages, req.temperature, req.max_tokens or 2048)
        if cached is not None:
            request_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
            token_est = estimate_tokens(cached)
            state.cache_served += 1
            state.record_request(token_est)
            return JSONResponse(
                content=build_completion_json(
                    request_id,
                    cached,
                    token_est,
                    estimate_tokens(messages),
                ),
                headers={"X-Cache": "HIT", "X-Inference-Time-Ms": "0"},
            )

    llm_req = build_inference_request(messages, req)
    request_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())

    if req.stream:
        return StreamingResponse(
            _stream_response(
                llm_req,
                request_id,
                created,
                messages,
                req.temperature,
                req.max_tokens or 2048,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        return await _complete_response(
            llm_req,
            request_id,
            created,
            messages,
            req.temperature,
            req.max_tokens or 2048,
        )


@router.post("/v1/completions")
async def completions(req: CompletionRequest):
    """OpenAI-compatible completions — supports suffix (FIM/infill)."""
    state = get_state()
    prompt = req.prompt if isinstance(req.prompt, str) else "\n".join(req.prompt)

    if req.suffix is not None:
        llm = get_llm()
        if not llm:
            raise HTTPException(503, detail="Model not loaded")

        request_id = f"cmpl-{uuid.uuid4().hex[:12]}"
        try:
            async with state.inference_semaphore:
                call_kwargs = dict(
                    prompt=prompt,
                    suffix=req.suffix,
                    max_tokens=req.max_tokens or 2048,
                    temperature=req.temperature,
                    top_p=req.top_p,
                    echo=req.echo,
                    stream=False,
                )
                if req.seed is not None:
                    call_kwargs["seed"] = req.seed
                if req.logit_bias:
                    call_kwargs["logit_bias"] = req.logit_bias
                if req.stop:
                    call_kwargs["stop"] = req.stop

                result = llm.create_completion(**call_kwargs)

            text = result["choices"][0]["text"] if result.get("choices") else ""
            token_est = estimate_tokens(text)
            state.record_request(token_est)
            return {
                "id": request_id,
                "object": "text_completion",
                "created": int(time.time()),
                "model": state.model_id,
                "choices": result.get("choices", [{"text": text, "index": 0, "finish_reason": "stop"}]),
                "usage": result.get(
                    "usage",
                    {
                        "prompt_tokens": estimate_tokens(prompt),
                        "completion_tokens": token_est,
                        "total_tokens": estimate_tokens(prompt) + token_est,
                    },
                ),
            }
        except Exception as e:
            raise HTTPException(500, detail=f"Completion (FIM) failed: {e}")

    chat_req = ChatCompletionRequest(
        model=req.model,
        messages=[ChatMessage(role="user", content=prompt)],
        temperature=req.temperature,
        top_p=req.top_p,
        max_tokens=req.max_tokens,
        stream=req.stream,
        seed=req.seed,
        logprobs=req.logprobs,
        top_logprobs=req.top_logprobs,
        logit_bias=req.logit_bias,
        stop=req.stop,
    )
    return await chat_completions(chat_req)


@router.post("/v1/infill")
async def infill(req: InfillRequest):
    """Dedicated fill-in-the-middle endpoint using native FIM tokens."""
    state = get_state()
    llm = get_llm()
    if not llm:
        raise HTTPException(503, detail="Model not loaded")

    request_id = f"infill-{uuid.uuid4().hex[:12]}"

    try:
        async with state.inference_semaphore:
            call_kwargs = dict(
                prompt=req.prompt,
                suffix=req.suffix if req.suffix else None,
                max_tokens=req.max_tokens or 256,
                temperature=req.temperature,
                top_p=req.top_p,
                stream=False,
            )
            if req.stop:
                call_kwargs["stop"] = req.stop

            result = llm.create_completion(**call_kwargs)

        text = result["choices"][0]["text"] if result.get("choices") else ""
        token_est = estimate_tokens(text)
        state.record_request(token_est)

        return {
            "id": request_id,
            "object": "infill",
            "created": int(time.time()),
            "model": state.model_id,
            "choices": [
                {
                    "text": text,
                    "index": 0,
                    "finish_reason": result["choices"][0].get("finish_reason", "stop")
                    if result.get("choices")
                    else "stop",
                }
            ],
            "usage": result.get(
                "usage",
                {
                    "prompt_tokens": estimate_tokens(req.prompt),
                    "completion_tokens": token_est,
                    "total_tokens": estimate_tokens(req.prompt) + token_est,
                },
            ),
        }
    except Exception as e:
        raise HTTPException(500, detail=f"Infill failed: {e}")


# ── Response builders ─────────────────────────────────────────────────


async def _complete_response(
    req: InferenceRequest,
    request_id: str,
    created: int,
    messages: list,
    temperature: float,
    max_tokens: int,
) -> JSONResponse:
    """Non-streaming: collect full response, return as JSON."""
    state = get_state()
    start = time.time()
    text = ""
    ttft_ms = None

    async with InferenceGuard(
        "non_streaming",
        adapter=state.adapter,
        request_info={
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
    ) as guard:
        async with state.inference_semaphore:
            guard.phase("inference")
            streamer = get_token_streamer()
            if streamer:
                async for token in streamer.query_stream_tokens(req):
                    if ttft_ms is None:
                        ttft_ms = (time.time() - start) * 1000
                        guard.mark("first_token")
                    text += token
            else:
                async for chunk in state.adapter.query(req):
                    if ttft_ms is None:
                        ttft_ms = (time.time() - start) * 1000
                        guard.mark("first_token")
                    text += chunk
            guard.mark("inference_done")

    elapsed_ms = (time.time() - start) * 1000
    token_est = estimate_tokens(text)
    prompt_tokens = estimate_tokens(messages)
    state.record_request(token_est)

    state.cache.put(messages, temperature, max_tokens, text)

    headers = {
        "X-Cache": "MISS",
        "X-Inference-Time-Ms": f"{elapsed_ms:.0f}",
    }
    if ttft_ms is not None:
        headers["X-Time-To-First-Token-Ms"] = f"{ttft_ms:.0f}"

    body = build_completion_json(request_id, text, token_est, prompt_tokens)
    body["timings"] = {
        "prompt_eval_duration_ms": round(ttft_ms, 1) if ttft_ms else 0,
        "eval_duration_ms": round(elapsed_ms - (ttft_ms or 0), 1),
        "total_duration_ms": round(elapsed_ms, 1),
        "tokens_per_second": round(token_est / (elapsed_ms / 1000), 1) if elapsed_ms > 0 else 0,
    }

    return JSONResponse(content=body, headers=headers)


async def _stream_response(
    req: InferenceRequest,
    request_id: str,
    created: int,
    messages: list,
    temperature: float,
    max_tokens: int,
):
    """TRUE token-level SSE streaming with InferenceGuard wrapping."""
    state = get_state()
    guard = InferenceGuard(
        "streaming",
        adapter=state.adapter,
        request_info={
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        },
    )
    await guard.__aenter__()

    try:
        first = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": state.model_id,
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": ""},
                    "finish_reason": None,
                }
            ],
        }
        yield f"data: {json.dumps(first)}\n\n"

        collected = []
        time.time()

        async with state.inference_semaphore:
            guard.phase("inference")
            streamer = get_token_streamer()
            if streamer:
                async for token in streamer.query_stream_tokens(req):
                    if not token:
                        continue
                    if not collected:
                        guard.mark("first_token")
                    collected.append(token)
                    chunk = {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": state.model_id,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": token},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
            else:
                async for chunk_text in state.adapter.query(req):
                    if not chunk_text:
                        continue
                    collected.append(chunk_text)
                    for word in tokenize_for_stream(chunk_text):
                        chunk = {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": state.model_id,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": word},
                                    "finish_reason": None,
                                }
                            ],
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
                        await asyncio.sleep(0)
            guard.mark("inference_done")

        stop_chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": state.model_id,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop",
                }
            ],
        }
        yield f"data: {json.dumps(stop_chunk)}\n\n"
        yield "data: [DONE]\n\n"

        full_text = "".join(collected)
        token_est = estimate_tokens(full_text)
        state.record_request(token_est)
        state.cache.put(messages, temperature, max_tokens, full_text)

        await guard.__aexit__(None, None, None)

    except BaseException:
        await guard.__aexit__(*sys.exc_info())
        raise
