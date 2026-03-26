#!/usr/bin/env python3
"""
Run predefined medical prompts: RAG retrieval + optional Llama server (or Ollama)
for answers; write a simple report to medical_scenarios/report.txt.
Run from project root: python -m medical_scenarios.run_queries_report
"""

import asyncio
import os
import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SCRIPT_DIR = Path(__file__).resolve().parent
REPORT_PATH = SCRIPT_DIR / "report.txt"

# LLM endpoint: Llama server (OpenAI-compatible) or Ollama
# Set MEDICAL_LLM_ENDPOINT=http://localhost:8001 or http://localhost:11434
# Set MEDICAL_LLM_PROVIDER=Ollama or Local (llama-cpp)
LLM_ENDPOINT = os.environ.get("MEDICAL_LLM_ENDPOINT", "http://localhost:8001")
LLM_PROVIDER = os.environ.get("MEDICAL_LLM_PROVIDER", "Local (llama-cpp)")
LLM_MODEL = os.environ.get("MEDICAL_LLM_MODEL", "llama3.2")


def get_rag():
    """Return LocalRAG instance using project rag_storage."""
    from zena_mode.rag_pipeline import LocalRAG

    storage = PROJECT_ROOT / "rag_storage"
    rag = LocalRAG(cache_dir=storage)
    if not rag.chunks:
        rag._load_metadata()
    return rag


async def call_llm(prompt: str, context: str, provider: str, model: str, endpoint: str) -> str:
    """Call LLM with system context and user prompt. Returns answer or error message."""
    try:
        from adapter_factory import create_adapter
        from llm_adapters import LLMRequest
    except ImportError as e:
        return f"(adapters not available: {e})"
    try:
        adapter = create_adapter(provider, endpoint=endpoint)
    except Exception as e:
        return f"(LLM unavailable: {e})"
    system = f"Answer based only on the following context.\n\nContext:\n{context[:4000]}"
    request = LLMRequest(
        provider=provider,
        model=model,
        prompt=prompt,
        system_prompt=system,
        temperature=0.3,
        max_tokens=512,
        stream=True,
        endpoint=endpoint,
    )
    try:
        chunks = []
        gen = adapter.query(request)
        async for token in gen:
            chunks.append(token)
        return "".join(chunks).strip() or "(no output)"
    except Exception as e:
        return f"(LLM error: {e})"


def run_queries_and_report():
    """Run predefined prompts, optional LLM, build report_lines and write file."""
    from medical_scenarios.prompts import MEDICAL_PROMPTS, PROMPT_IDS

    report_lines = []
    report_lines.append("=" * 70)
    report_lines.append("  MEDICAL SCENARIOS — QUERY REPORT")
    report_lines.append("=" * 70)
    report_lines.append("")

    try:
        rag = get_rag()
    except Exception as e:
        report_lines.append(f"RAG unavailable: {e}")
        REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")
        print(f"Report written (RAG failed): {REPORT_PATH}")
        return

    n_chunks = len(getattr(rag, "chunks", []))
    report_lines.append(f"Vector DB: {n_chunks} chunks loaded.")
    report_lines.append(f"LLM: {LLM_PROVIDER} @ {LLM_ENDPOINT} (model: {LLM_MODEL})")
    report_lines.append("")

    use_llm = os.environ.get("MEDICAL_USE_LLM", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )

    for i, (prompt_id, prompt) in enumerate(zip(PROMPT_IDS, MEDICAL_PROMPTS)):
        report_lines.append("-" * 70)
        report_lines.append(f"  [{prompt_id}]")
        report_lines.append(f"  Q: {prompt}")
        try:
            results = rag.hybrid_search(prompt, k=3, alpha=0.5, rerank=True)
        except Exception as e:
            report_lines.append(f"  RAG error: {e}")
            report_lines.append("")
            continue
        if not results:
            report_lines.append("  RAG: no results.")
            report_lines.append("")
            continue
        context = "\n\n".join(r.get("text", "")[:800] for r in results)
        report_lines.append(f"  RAG: {len(results)} chunk(s) retrieved.")
        report_lines.append(f"  Top source: {results[0].get('url', results[0].get('title', 'N/A'))}")
        report_lines.append("")

        if use_llm:
            answer = asyncio.run(call_llm(prompt, context, LLM_PROVIDER, LLM_MODEL, LLM_ENDPOINT))
            report_lines.append(f"  A: {answer[:500]}{'…' if len(answer) > 500 else ''}")
        else:
            report_lines.append("  A: (LLM disabled; top chunk preview below)")
            report_lines.append(f"  {results[0].get('text', '')[:400]}…")
        report_lines.append("")

    report_lines.append("=" * 70)
    report_lines.append("  END REPORT")
    report_lines.append("=" * 70)

    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Report written: {REPORT_PATH}")


if __name__ == "__main__":
    run_queries_and_report()
