
import time
import random
import string
import shutil
import logging
from pathlib import Path
from zena_mode.rag_pipeline import LocalRAG

# --- Configuration ---
NUM_DOCS = 100
DOC_LENGTH = 2000 # chars
TEST_DIR = Path("benchmark_rag_data")
DB_PATH = TEST_DIR / "rag_db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAG_Benchmark")

def generate_synthetic_data(num_docs, length):
    """Generate random documents to simulate load."""
    docs = []
    logger.info(f"Generating {num_docs} synthetic documents...")
    for i in range(num_docs):
        # Generate random text
        text = ''.join(random.choices(string.ascii_letters + " " * 10, k=length))
        # Insert some searchable keywords
        if i % 10 == 0:
            text += " The secret password is BlueSky."
        docs.append({
            "content": text,
            "url": f"http://fake.com/doc_{i}",
            "title": f"Synthetic Doc {i}"
        })
    return docs

def run_benchmark():
    # Setup
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)
    TEST_DIR.mkdir()

    # Data
    docs = generate_synthetic_data(NUM_DOCS, DOC_LENGTH)

    # Init RAG
    rag = LocalRAG(cache_dir=DB_PATH)
    
    # Measure Ingest
    logger.info("--- Starting Ingest Benchmark ---")
    start_time = time.time()
    rag.build_index(docs)
    end_time = time.time()
    
    ingest_duration = end_time - start_time
    docs_per_sec = NUM_DOCS / ingest_duration
    
    # Check Storage Size
    rag.save(DB_PATH)
    total_size = sum(f.stat().st_size for f in DB_PATH.glob('**/*') if f.is_file()) / (1024*1024)
    
    logger.info(f"Ingest Complete: {ingest_duration:.2f}s")
    logger.info(f"Throughput: {docs_per_sec:.2f} docs/sec")
    logger.info(f"Storage Size: {total_size:.2f} MB")

    # Measure Search
    logger.info("--- Starting Search Benchmark ---")
    search_start = time.time()
    results = rag.search("secret password BlueSky", k=3)
    search_end = time.time()
    
    search_latency = (search_end - search_start) * 1000 # ms
    logger.info(f"Search Latency: {search_latency:.2f} ms")
    logger.info(f"Found: {len(results)} results")
    if results:
         logger.info(f"Top Result Score: {results[0].get('score', 0):.4f}")

    # Report
    print(f"\n=== BENCHMARK RESULTS (Baseline) ===")
    print(f"Documents: {NUM_DOCS}")
    print(f"Total Time: {ingest_duration:.4f} s")
    print(f"Throughput: {docs_per_sec:.2f} docs/s")
    print(f"Search Latency: {search_latency:.2f} ms")
    print(f"Storage: {total_size:.2f} MB")
    print("====================================")

    # Cleanup
    # shutil.rmtree(TEST_DIR)

if __name__ == "__main__":
    run_benchmark()
