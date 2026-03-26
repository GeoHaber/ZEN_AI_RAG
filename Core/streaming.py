"""
Core/streaming.py — Streaming answer generation utilities for ZEN_RAG.

Phase 2.3: Real-time streaming answers via Streamlit's st.write_stream().

Supports:
  - Token-by-token streaming (for LLMs with streaming API)
  - Chunk-by-chunk simulation (for LLMs without native streaming)
  - Background hallucination checking after full answer is generated

Usage (in Streamlit):
    from Core.streaming import stream_answer_to_streamlit

    stream_answer_to_streamlit(
        query="What is X?",
        context_chunks=retrieved_chunks,
        llm=my_llm,
        rag=my_rag,
    )
"""

import logging
import time
from typing import Any, Dict, Generator, List

logger = logging.getLogger(__name__)

# =============================================================================
# Context builder
# =============================================================================


def build_context_string(chunks: List[Dict], max_chars: int = 8000) -> str:
    """Build numbered context string from retrieved chunks."""
    parts = []
    total = 0
    for i, chunk in enumerate(chunks, 1):
        text = chunk.get("text", "")
        source = chunk.get("title") or chunk.get("url") or ""
        if source:
            block = f"[{i}] ({source})\n{text}"
        else:
            block = f"[{i}] {text}"
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block)
    return "\n\n".join(parts) or "No context available."


# =============================================================================
# Streaming generators
# =============================================================================


def _char_stream(text: str, delay: float = 0.01) -> Generator[str, None, None]:
    """Simulate streaming by yielding characters with delay."""
    for char in text:
        yield char
        if delay > 0:
            time.sleep(delay)


def _word_stream(text: str, delay: float = 0.03) -> Generator[str, None, None]:
    """Simulate streaming by yielding words with delay."""
    words = text.split()
    for i, word in enumerate(words):
        yield word + (" " if i < len(words) - 1 else "")
        if delay > 0:
            time.sleep(delay)


def _ollama_stream(llm: Any, prompt: str) -> Generator[str, None, None]:
    """Stream from Ollama adapter if available."""
    try:
        import ollama

        model = getattr(llm, "model_name", None) or getattr(llm, "_model", "llama3")
        stream = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        for chunk in stream:
            content = chunk.get("message", {}).get("content", "")
            if content:
                yield content
    except Exception as e:
        logger.debug(f"[Streaming] Ollama stream failed: {e}")
        raise


def _llama_cpp_stream(llm: Any, prompt: str, max_tokens: int = 500) -> Generator[str, None, None]:
    """Stream from llama-cpp-python if available."""
    try:
        model = getattr(llm, "_model", None) or getattr(llm, "llm", None)
        if model is None:
            raise ValueError("No llama_cpp model found")
        output = model(
            prompt,
            max_tokens=max_tokens,
            stream=True,
            temperature=0.1,
        )
        for token in output:
            text = token.get("choices", [{}])[0].get("text", "")
            if text:
                yield text
    except Exception as e:
        logger.debug(f"[Streaming] llama-cpp stream failed: {e}")
        raise


def get_answer_stream(
    llm: Any,
    prompt: str,
    max_tokens: int = 500,
    fallback_delay: float = 0.02,
) -> Generator[str, None, None]:
    """
    Get a streaming generator for an LLM response.

    Tries native streaming adapters first, falls back to simulated word streaming.
    """
    # Try Ollama streaming
    try:
        llm_type = type(llm).__name__.lower()
        if "ollama" in llm_type:
            yield from _ollama_stream(llm, prompt)
            return
    except Exception as exc:
        logger.debug("%s", exc)

    # Try llama-cpp streaming
    try:
        if hasattr(llm, "_model") or hasattr(llm, "llm"):
            yield from _llama_cpp_stream(llm, prompt, max_tokens)
            return
    except Exception as exc:
        logger.debug("%s", exc)

    # Fallback: synchronous call + word-by-word simulation
    try:
        if hasattr(llm, "query_sync"):
            full_text = llm.query_sync(prompt, max_tokens=max_tokens)
        elif hasattr(llm, "generate"):
            full_text = llm.generate(prompt)
        elif callable(llm):
            full_text = llm(prompt)
        else:
            full_text = ""
        yield from _word_stream(full_text, delay=fallback_delay)
    except Exception as e:
        logger.error(f"[Streaming] All streaming methods failed: {e}")
        yield "Error generating answer. Please try again."


# =============================================================================
# Streamlit integration
# =============================================================================

RAG_ANSWER_PROMPT = """You are a helpful assistant. Answer the question using ONLY the provided context.
Be concise and factual. If the answer is not in the context, say "I don't have enough information."

Context:
{context}

Question: {question}

Answer:"""


def stream_answer_to_streamlit(
    query: str,
    context_chunks: List[Dict],
    llm: Any,
    rag: Any = None,
    show_sources: bool = True,
    check_hallucination_after: bool = True,
) -> str:
    """
    Stream an LLM answer to the current Streamlit chat message container.

    Args:
        query: User query.
        context_chunks: Retrieved chunks from RAG.
        llm: LLM adapter.
        rag: LocalRAG instance (used for hallucination check if available).
        show_sources: Show source attribution after the answer.
        check_hallucination_after: Run hallucination check in background after streaming.

    Returns:
        The complete generated answer text.
    """
    try:
        import streamlit as st
    except ImportError:
        logger.error("[Streaming] Streamlit not available")
        return ""

    context_str = build_context_string(context_chunks)
    prompt = RAG_ANSWER_PROMPT.format(context=context_str, question=query)

    # Stream the answer
    full_answer = ""
    with st.chat_message("assistant"):
        placeholder = st.empty()
        accumulated = ""
        try:
            for token in get_answer_stream(llm, prompt):
                accumulated += token
                placeholder.markdown(accumulated + "\u258c")  # Blinking cursor
            placeholder.markdown(accumulated)  # Final answer (no cursor)
            full_answer = accumulated
        except Exception as e:
            placeholder.markdown("Error generating answer. Please try again.")
            logger.error(f"[Streaming] Answer generation failed: {e}")
            return ""

        # Show sources
        if show_sources and context_chunks:
            with st.expander("Sources", expanded=False):
                seen_sources = set()
                for chunk in context_chunks:
                    src = chunk.get("title") or chunk.get("url") or "Unknown"
                    if src not in seen_sources:
                        seen_sources.add(src)
                        st.caption(f"- {src}")

        # Background hallucination check
        if check_hallucination_after and rag is not None:
            try:
                from Core.hallucination_detector_v2 import HallucinationDetector

                detector = HallucinationDetector()
                context_texts = [c.get("text", "") for c in context_chunks]
                result = detector.check(full_answer, context_texts)
                if result.get("hallucination_detected"):
                    st.warning(
                        "Potential hallucination detected. Please verify this answer.",
                        icon="warning",
                    )
                    # Record in metrics
                    try:
                        from Core.metrics_tracker import MetricsTracker

                        MetricsTracker.get_instance().record_query(
                            query=query, latency_s=0.0, hallucination_detected=True
                        )
                    except Exception as exc:
                        logger.debug("%s", exc)
            except Exception as e:
                logger.debug(f"[Streaming] Hallucination check failed: {e}")

    return full_answer
