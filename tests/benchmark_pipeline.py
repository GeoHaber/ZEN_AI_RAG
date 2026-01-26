
import time
import logging
import sys
import os
import asyncio
from pathlib import Path

# Setup paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Benchmark")

def benchmark_rag():
    logger.info("🚀 Starting RAG Pipeline Benchmark provided by ZenAI...")
    
    try:
        from zena_mode.rag_pipeline import LocalRAG
        from zena_mode.arbitrage import SwarmArbitrator
        from sentence_transformers import CrossEncoder
    except ImportError as e:
        logger.error(f"❌ Dependencies missing: {e}")
        return

    # 1. Initialize System (Measure Startup/Warmup Time)
    start_init = time.time()
    logger.info("Initializing LocalRAG...")
    
    # Use a temp directory for benchmark index to avoid polluting main DB
    rag = LocalRAG(cache_dir=Path("./benchmark_storage"))
    arbitrator = SwarmArbitrator()
    
    # Run Warmup
    t0 = time.time()
    rag.warmup()
    # Mocking async call for arbitrator warmup in sync context (or actually running it if possible)
    # We'll just init the heavy model directly for benchmarking pure inference
    if arbitrator.nli_model is None:
         logger.info("Warming up NLI model manually for benchmark...")
         arbitrator.nli_model = CrossEncoder('cross-encoder/nli-distilroberta-base')
    
    warmup_time = time.time() - t0
    logger.info(f"✅ System Warmup took: {warmup_time:.4f}s")

    # 2. Ingest Sample Data
    documents = [
        {"content": "The capital of France is Paris. It is known for the Eiffel Tower.", "url": "doc1", "title": "France Info"},
        {"content": "The capital of Germany is Berlin. It has a rich history.", "url": "doc2", "title": "Germany Info"},
        {"content": "Python is a programming language created by Guido van Rossum.", "url": "doc3", "title": "Python History"},
        {"content": "Rust is a systems programming language focused on safety.", "url": "doc4", "title": "Rust Info"},
        {"content": "Machine learning is a subset of artificial intelligence.", "url": "doc5", "title": "AI Basics"},
    ]
    logger.info(f"Building index with {len(documents)} documents...")
    rag.build_index(documents)

    # 3. Benchmark Search (Retrieval Only)
    query = "What is the capital of France?"
    
    logger.info(f"\n--- Benchmarking Query: '{query}' ---")
    
    # Metric: Retrieval Latency
    t_start = time.time()
    results = rag.search(query, k=5)
    t_retrieval = time.time() - t_start
    logger.info(f"🔹 Vector Search: {t_retrieval:.4f}s")

    # Metric: Re-ranking Latency
    t_start = time.time()
    reranked = rag.rerank(query, results, top_k=3)
    t_rerank = time.time() - t_start
    logger.info(f"🔹 Cross-Encoder Re-ranking: {t_rerank:.4f}s")
    
    # 4. Benchmark Verification (NLI Latency)
    response_text = "The capital of France is Paris."
    context_chunks = [c['text'] for c in reranked]
    
    t_start = time.time()
    verification = arbitrator.verify_hallucination(response_text, context_chunks)
    t_verify = time.time() - t_start
    logger.info(f"🔹 NLI Verification: {t_verify:.4f}s")
    
    # 5. Throughput Test (Simulating Load)
    logger.info("\n--- Stress Test (10 Iterations) ---")
    total_time = 0
    valid_iters = 0
    for i in range(10):
        t0 = time.time()
        # Full Pipeline Simulation
        res = rag.search(query, k=5)
        top = rag.rerank(query, res, top_k=3)
        _ = arbitrator.verify_hallucination(response_text, [c['text'] for c in top])
        dur = time.time() - t0
        total_time += dur
        valid_iters += 1
        print(f".", end="", flush=True)
    
    avg_latency = total_time / valid_iters
    logger.info(f"\n✅ Average Full Pipeline Latency: {avg_latency:.4f}s")
    
    # Summary
    logger.info("\n=== BENCHMARK REPORT ===")
    logger.info(f"Warmup Time: {warmup_time:.2f}s")
    logger.info(f"Retrieval: {t_retrieval:.4f}s")
    logger.info(f"Re-ranking: {t_rerank:.4f}s")
    logger.info(f"Verification: {t_verify:.4f}s")
    logger.info(f"Total Per Request: {t_retrieval + t_rerank + t_verify:.4f}s")
    logger.info("========================")

if __name__ == "__main__":
    benchmark_rag()
