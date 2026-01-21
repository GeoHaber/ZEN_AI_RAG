import sys
import os
from pathlib import Path
import logging

# Setup mocking/paths
sys.path.append(os.getcwd())

# Config Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Test_RAGED")

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
        print("FAILED: Could not import zena_mode. Are you in the project root?")
        return

    rag_cache = Path("rag_cache")
    if not rag_cache.exists():
        print(f"FAILED: No rag_cache found at {rag_cache.absolute()}")
        return

    rag = LocalRAG(cache_dir=rag_cache)
    if rag.load(rag_cache):
        print(f"SUCCESS: Loaded RAG Index. Total vectors: {rag.index.ntotal}")
    else:
        print("FAILED: Could not load index.")
        return

    # Simulate User Query
    query = "what are the news on thet site"
    print(f"\nQUERY: '{query}'")
    
    results = rag.search(query, k=5)
    
    if not results:
        print("RESULT: No chunks found.")
    else:
        print(f"RESULT: Found {len(results)} chunks.\n")
        for i, chunk in enumerate(results, 1):
            title = chunk.get('title', 'No Title')
            text = chunk.get('text', '[EMPTY TEXT]')
            url = chunk.get('url', 'No URL')
            
            print(f"--- Chunk {i} ---")
            print(f"Title: {title}")
            print(f"URL:   {url}")
            print(f"Text Length: {len(text)} chars")
            print(f"PREVIEW: {text[:500].replace(chr(10), ' ')}...") 
            print("----------------")
            sys.stdout.flush()

if __name__ == "__main__":
    test_rag_retrieval_content()
