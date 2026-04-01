import sys
import os
from pathlib import Path
import logging
import pytest

# Setup mocking/paths
sys.path.append(os.getcwd())

# Config Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Test_RAGED")


@pytest.mark.skipif(not Path("rag_cache/rag.db").exists(), reason="Requires existing RAG cache with data")
def test_rag_retrieval_content():
    """
    Diagnose RAG Quality:
    1. Loads the existing RAG index from 'rag_cache'.
    2. Searches for 'news' (or generic query).
    3. Prints the EXACT text chunks the LLM would see.
    """
    print("\nXXX DIAGNOSTIC START XXX")
    try:
        from zena_mode import LocalRAG
    except ImportError:
        pytest.skip("Could not import zena_mode")

    rag_cache = Path("rag_cache")
    if not rag_cache.exists():
        pytest.skip(f"No rag_cache found at {rag_cache.absolute()}")

    rag = LocalRAG(cache_dir=rag_cache)
    rag.load(rag_cache)

    if rag.index is None or rag.index.ntotal == 0:
        pytest.skip("RAG index is empty - no data to test")

    print(f"SUCCESS: Loaded RAG Index. Total vectors: {rag.index.ntotal}")
    # Simulate User Query
    query = "what are the news on thet site"
    print(f"\nQUERY: '{query}'")
    results = rag.search(query, k=5)

    if not results:
        print("RESULT: No chunks found.")
    else:
        print(f"RESULT: Found {len(results)} chunks.\n")
        for i, chunk in enumerate(results, 1):
            title = chunk.get("title", "No Title")
            text = chunk.get("text", "[EMPTY TEXT]")
            url = chunk.get("url", "No URL")

            print(f"--- Chunk {i} ---")
            print(f"Title: {title}")
            print(f"URL:   {url}")
            print(f"Text Length: {len(text)} chars")
            print(f"PREVIEW: {text[:500].replace(chr(10), ' ')}...")
            print("----------------")
            sys.stdout.flush()


if __name__ == "__main__":
    test_rag_retrieval_content()
