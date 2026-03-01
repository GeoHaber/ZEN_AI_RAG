# -*- coding: utf-8 -*-
"""
profile_performance.py - ZenAI Performance Profiler
====================================================
Measures timing for critical code paths to identify optimization targets.
"""
import sys
import time
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def measure(name: str, func):
    """Measure execution time of a function."""
    start = time.perf_counter()
    try:
        result = func()
        elapsed = (time.perf_counter() - start) * 1000
        print(f"✅ {name}: {elapsed:.1f}ms")
        return result, elapsed
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        print(f"❌ {name}: FAILED after {elapsed:.1f}ms - {e}")
        return None, elapsed

def _do_main_setup():
    """Helper: setup phase for main."""

    print("\n" + "="*60)
    print("  ZenAI Performance Profiler")
    print("="*60 + "\n")

    results = {}

    # 1. Config System Load
    results['config'], _ = measure("Config System Import", lambda: __import__('config_system'))

    # 2. Heavy Module Imports
    print("\n--- Heavy Imports ---")
    results['sentence_tf'], results['sentence_tf_time'] = measure(
        "SentenceTransformers", 
        lambda: __import__('sentence_transformers')
    )

    results['faiss'], _ = measure("FAISS", lambda: __import__('faiss'))
    results['nicegui'], _ = measure("NiceGUI", lambda: __import__('nicegui'))

    # 3. RAG Pipeline Init
    print("\n--- RAG Pipeline ---")
    from zena_mode.rag_pipeline import LocalRAG
    import tempfile

    temp_dir = tempfile.mkdtemp()

    rag_instance, rag_init_time = measure(
        "RAG Init (cold)", 
        lambda: LocalRAG(cache_dir=temp_dir)
    )
    results['rag_init'] = rag_init_time

    # 4. RAG Indexing (small batch)
    print("\n--- RAG Indexing ---")
    test_docs = [
        {"content": f"This is test document {i} about artificial intelligence.", 
         "url": f"http://test.com/{i}", "title": f"Doc {i}"}
        for i in range(10)
    ]

    _, index_time = measure(
        "Index 10 Documents",
        lambda: rag_instance.build_index(test_docs)
    )
    results['rag_index_10'] = index_time

    return rag_instance, results, temp_dir


def main():
    """Main."""
    rag_instance, results, temp_dir = _do_main_setup()
    # 5. RAG Search (cold + warm)
    print("\n--- RAG Search ---")
    _, search_cold = measure(
        "Search (cold)",
        lambda: rag_instance.search("artificial intelligence", k=3)
    )
    results['search_cold'] = search_cold
    
    _, search_warm = measure(
        "Search (warm)",
        lambda: rag_instance.search("test document", k=3)
    )
    results['search_warm'] = search_warm
    
    # 6. Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    # Summary
    print("\n" + "="*60)
    print("  PERFORMANCE SUMMARY")
    print("="*60)
    
    critical = [
        ("Config Load", results.get('config', (None, 0))[1] if isinstance(results.get('config'), tuple) else 0),
        ("SentenceTransformers Import", results.get('sentence_tf_time', 0)),
        ("RAG Init", results.get('rag_init', 0)),
        ("Index 10 Docs", results.get('rag_index_10', 0)),
        ("Search (cold)", results.get('search_cold', 0)),
        ("Search (warm)", results.get('search_warm', 0)),
    ]
    
    for name, ms in critical:
        if ms > 1000:
            status = "🔴 SLOW"
        elif ms > 500:
            status = "🟡 OK"
        else:
            status = "🟢 FAST"
        print(f"  {status} {name}: {ms:.0f}ms")
    
    print("\n" + "="*60)
    print("  OPTIMIZATION RECOMMENDATIONS")
    print("="*60)
    
    if results.get('sentence_tf_time', 0) > 1000:
        print("  ⚡ SentenceTransformers is slow - use lazy loading")
    
    if results.get('rag_init', 0) > 500:
        print("  ⚡ RAG Init is slow - cache embedding model")
    
    if results.get('search_cold', 0) > 100:
        print("  ⚡ Search is slow - add result caching")
    
    print()

if __name__ == "__main__":
    main()
