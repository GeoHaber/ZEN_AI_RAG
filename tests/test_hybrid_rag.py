import pytest
import numpy as np
from zena_mode.rag_pipeline import LocalRAG
from pathlib import Path
import shutil

@pytest.fixture
def temp_rag(tmp_path):
    """Create a temporary RAG instance for testing using tmp_path for isolation."""
    test_dir = tmp_path / "test_rag_hybrid"
    test_dir.mkdir()
    
    rag = LocalRAG(cache_dir=test_dir)
    yield rag
    
    # Cleanup
    rag.close()
    if test_dir.exists():
        try:
            shutil.rmtree(test_dir, ignore_errors=True)
        except:
            pass

def test_hybrid_search_precision(temp_rag):
    """
    Test that Hybrid Search (Vector + BM25) can find specific keywords 
    that might be diluted in a semantic embedding.
    """
    # 1. Add documents with unique identifiers
    docs = [
        {
            "url": "doc1",
            "title": "General AI Discussion",
            "content": "Artificial intelligence is a branch of computer science that aims to create intelligent machines."
        },
        {
            "url": "doc2",
            "title": "Technical Specs",
            "content": "The system ID for this specific deployment is ZX-999-BETA. This key is used for authentication."
        },
        {
            "url": "doc3",
            "title": "Weather Report",
            "content": "Today it is sunny with a high of 25 degrees Celsius. Perfect for outdoor activities."
        }
    ]
    
    temp_rag.build_index(docs, filter_junk=False)
    
    # 2. Query for a very specific keyword (ZX-999-BETA)
    # Vector search might rank "Technical Specs" high, but BM25 guarantees it if the keyword is there.
    query = "What is the status of ZX-999-BETA?"
    
    # Test Standard Semantic Search
    vector_results = temp_rag.search(query, k=1)
    print(f"\nVector Top Result: {vector_results[0]['title'] if vector_results else 'None'}")
    
    # Test Hybrid Search (This is what we are implementing/improving)
    hybrid_results = temp_rag.hybrid_search(query, k=3, alpha=0.5)
    print("\nHybrid Search Results (query):")
    for r in hybrid_results:
        print(f"- {r['url']}: {r['title']} (Score: {r['fusion_score']:.4f})")
    
    assert len(hybrid_results) > 0
    assert hybrid_results[0]['url'] == "doc2"
    
    # 3. Verify that BM25 contributes
    tricky_query = "outdoor ZX-999-BETA"
    results = temp_rag.hybrid_search(tricky_query, k=3, alpha=0.3) 
    print("\nHybrid Search Results (tricky):")
    for r in results:
        print(f"- {r['url']}: {r['title']} (Score: {r['fusion_score']:.4f})")
        
    assert results[0]['url'] == "doc2"

def test_rrf_fusion_logic(temp_rag):
    """Verify that Reciprocal Rank Fusion correctly merges results."""
    # This is a unit-level test for the fusion logic
    # We'll mock the internal search results if needed, but for now, 
    # we'll use the actual hybrid_search call.
    
    docs = [{"url": str(i), "title": f"Doc {i}", "content": f"This is the full content of doc {i} which is now long enough."} for i in range(10)]
    temp_rag.build_index(docs, filter_junk=False)
    
    results = temp_rag.hybrid_search("content of doc 5", k=5)
    assert len(results) <= 5
    # Doc 5 should be near the top due to exact keyword and semantic match
    assert results[0]['url'] == "5"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
