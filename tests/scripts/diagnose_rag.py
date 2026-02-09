"""
diagnose_rag.py - End-to-End RAG Diagnostics
"""
import sys
import os
import asyncio
import logging

# Setup Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config_system import config
from zena_mode.rag_pipeline import AsyncLocalRAG

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAG_Diag")

async def test_rag():
    print("="*60)
    print("🔍 RAG DIAGNOSTICS START")
    print("="*60)

    # 1. Initialize Pipeline
    print("[1] Initializing Pipeline...")
    try:
        rag = AsyncLocalRAG()
        print("✅ Pipeline Initialized")
    except Exception as e:
        print(f"❌ Initialization Failed: {e}")
        return

    # 2. Check Embedding Model
    print("\n[2] Checking Embeddings...")
    if rag.model:
        print(f"✅ Transformer Loaded: {rag.model}")
    else:
        print("❌ Transformer NOT Loaded (Lazy Load pending?)")

    # 3. Ingest Test Document
    print("\n[3] Ingesting Test Document...")
    test_text = "The secret code for the vault is 'Blue-Omega-99'. Do not share this."
    try:
        # Use add_chunks_async with correct dictionary format
        chunk = {
            "text": test_text, 
            "title": "Secret Doc", 
            "url": "internal://test"
        }
        await rag.add_chunks_async([chunk])
        print("✅ Ingestion Triggered")
    except Exception as e:
        print(f"❌ Ingestion Failed: {e}")

    # 4. Query
    print("\n[4] Querying...")
    query = "What is the secret code?"
    try:
        results = await rag.search_async(query, k=3)
        print(f"✅ Search returned {len(results)} results")
        
        found = False
        for r in results:
            # Result is a dictionary, not object
            text = r.get('text', '')
            score = r.get('score', 0.0)
            print(f"   - Match ({score:.3f}): {text[:50]}...")
            if "Blue-Omega-99" in text:
                found = True
        
        if found:
            print("\n🎉 SUCCESS: Secret code retrieved!")
        else:
            print("\n⚠️ FAILURE: Secret code NOT found in results.")
            
    except Exception as e:
        print(f"❌ Search Failed: {e}")

    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_rag())
