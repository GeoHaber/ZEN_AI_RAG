#!/usr/bin/env python3
"""
Index medical scenario documents into the RAG vector database, verify success,
and expose one vector DB entry as an example (structure + sample content).
Run from project root: python -m medical_scenarios.index_and_verify
"""

import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"


def load_scenario_documents():
    """Load generated scenario files into document list for RAG."""
    documents = []
    if not DATA_DIR.exists():
        print(f"Error: {DATA_DIR} not found. Run generate_scenarios.py first.")
        return documents
    for f in sorted(DATA_DIR.glob("*.txt")):
        text = f.read_text(encoding="utf-8").strip()
        if not text:
            continue
        title = text.split("\n")[0][:80] if "\n" in text else text[:80]
        documents.append(
            {
                "content": text,
                "url": f"medical_scenarios/data/{f.name}",
                "title": title,
            }
        )
    return documents


def index_and_verify():
    """Index documents with LocalRAG, verify count, print one entry structure."""
    documents = load_scenario_documents()
    if not documents:
        print("No documents to index.")
        return False

    # [X-Ray auto-fix] print(f"Loaded {len(documents)} scenario documents.")
    storage = PROJECT_ROOT / "rag_storage"
    # [X-Ray auto-fix] print(f"Vector DB path: {storage}")
    try:
        from zena_mode.rag_pipeline import LocalRAG
    except ImportError:
        # [X-Ray auto-fix] print(f"LocalRAG unavailable: {e}")
        print("Install RAG dependencies: pip install sentence-transformers qdrant-client")
        return False

    rag = LocalRAG(cache_dir=storage)
    rag.warmup()
    rag.build_index(documents, dedup_threshold=0.9, filter_junk=True)

    # Verify
    n_chunks = len(rag.chunks)
    # [X-Ray auto-fix] print(f"\nIndexing result: {n_chunks} chunks in vector DB.")
    if n_chunks == 0:
        print("WARNING: No chunks were added. Check chunker/filter or document content.")
        return False
    print("Indexing verified: chunks added successfully.")

    # Expose one entry as example (structure from in-memory chunk mirror)
    print("\n" + "=" * 60)
    print("  ONE VECTOR DB ENTRY (structure example)")
    print("  (from LocalRAG in-memory chunk mirror; Qdrant payload is similar)")
    print("=" * 60)
    example = rag.chunks[0]
    for key in sorted(example.keys()):
        val = example[key]
        if key == "text":
            preview = (val[:200] + "…") if len(val) > 200 else val
            preview = preview.replace("\n", " ")
            # [X-Ray auto-fix] print(f"  {key}: {preview!r}")
        else:
            # [X-Ray auto-fix] print(f"  {key}: {val!r}")
            pass
    print("=" * 60)

    try:
        rag.close()
    except Exception as exc:
        _ = exc  # suppressed intentionally
    return True


if __name__ == "__main__":
    ok = index_and_verify()
    sys.exit(0 if ok else 1)
