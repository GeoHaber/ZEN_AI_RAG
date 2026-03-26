"""
Inference router — embeddings, tokenize, detokenize, count_tokens.

Endpoints:
  POST /v1/embeddings
  POST /tokenize
  POST /detokenize
  POST /v1/count_tokens
"""

from fastapi import APIRouter, HTTPException

from server.schemas import (
    EmbeddingRequest,
    TokenizeRequest,
    DetokenizeRequest,
    TokenCountRequest,
)
from server.helpers import get_state, get_llm

router = APIRouter()


@router.post("/v1/embeddings")
async def embeddings(req: EmbeddingRequest):
    """OpenAI-compatible embeddings."""
    state = get_state()
    llm = get_llm()
    if not llm:
        raise HTTPException(503, detail="Model not loaded")

    inputs = req.input if isinstance(req.input, list) else [req.input]

    try:
        async with state.inference_semaphore:
            result = llm.create_embedding(inputs)
    except Exception as e:
        raise HTTPException(500, detail=f"Embedding failed: {e}")

    data = result.get("data", result) if isinstance(result, dict) else result
    usage = result.get("usage", {}) if isinstance(result, dict) else {}

    return {
        "object": "list",
        "data": data if isinstance(data, list) else [{"object": "embedding", "embedding": data, "index": 0}],
        "model": state.model_id,
        "usage": usage
        or {
            "prompt_tokens": sum(len(t.split()) for t in inputs),
            "total_tokens": sum(len(t.split()) for t in inputs),
        },
    }


@router.post("/tokenize")
async def tokenize(req: TokenizeRequest):
    """Tokenize text using the loaded model's tokenizer."""
    llm = get_llm()
    if not llm:
        raise HTTPException(503, detail="Model not loaded")
    try:
        tokens = llm.tokenize(
            req.content.encode("utf-8"),
            add_bos=req.add_special,
        )
        result = {"tokens": tokens}
        if getattr(req, "with_pieces", False):
            pieces = []
            for tid in tokens:
                try:
                    piece = llm.detokenize([tid]).decode("utf-8", errors="replace")
                except Exception:
                    piece = f"<token_{tid}>"
                pieces.append({"id": tid, "piece": piece})
            result["tokens"] = pieces
        return result
    except Exception as e:
        raise HTTPException(500, detail=f"Tokenize failed: {e}")


@router.post("/detokenize")
async def detokenize(req: DetokenizeRequest):
    """Convert tokens back to text."""
    llm = get_llm()
    if not llm:
        raise HTTPException(503, detail="Model not loaded")
    try:
        text = llm.detokenize(req.tokens).decode("utf-8", errors="replace")
        return {"content": text}
    except Exception as e:
        raise HTTPException(500, detail=f"Detokenize failed: {e}")


@router.post("/v1/count_tokens")
async def count_tokens(req: TokenCountRequest):
    """Count tokens in text without returning the full token list."""
    state = get_state()
    llm = get_llm()
    if not llm:
        raise HTTPException(503, detail="Model not loaded")
    try:
        tokens = llm.tokenize(req.content.encode("utf-8"), add_bos=False)
        return {"count": len(tokens), "model": state.model_id}
    except Exception as e:
        raise HTTPException(500, detail=f"Token count failed: {e}")
