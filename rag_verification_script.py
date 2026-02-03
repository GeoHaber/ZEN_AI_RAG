
import sys
import os
import logging
from pathlib import Path
import shutil

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAGVerifier")

# Add project root to path
sys.path.append(os.getcwd())

from config_system import config

def verify_rag_core():
    print(">>> Verifying Core RAG Functionality...")
    try:
        from zena_mode import LocalRAG
        
        # storage path
        storage_path = config.BASE_DIR / "rag_verification_storage"
        if storage_path.exists():
            shutil.rmtree(storage_path)
        storage_path.mkdir(exist_ok=True)
        
        print(f"[*] Initializing LocalRAG at {storage_path}...")
        rag = LocalRAG(cache_dir=storage_path)
        
        # Test 1: Indexing
        print("[*] Testing Indexing...")
        docs = [
            {"content": "The capital of France is Paris.", "url": "doc1", "title": "France Info"},
            {"content": "Python is a programming language.", "url": "doc2", "title": "Python Info"},
            {"content": "ZenAI is a local RAG assistant.", "url": "doc3", "title": "ZenAI Info"}
        ]
        rag.build_index(docs, filter_junk=False)
        
        if rag.ntotal < 3:
            print(f"❌ Indexing Failed. Expected 3+, got {rag.ntotal}")
            return False
        print(f"✅ Indexed {rag.ntotal} chunks.")
        
        # Test 2: Search (Semantic)
        print("[*] Testing Semantic Search...")
        results = rag.search("capital of France", k=1)
        if results and "Paris" in results[0]['text']:
            print(f"✅ Semantic Search Verified: {results[0]['text']}")
        else:
            print(f"❌ Semantic Search Failed. Results: {results}")
            return False
            
        # Test 3: Hybrid Search
        print("[*] Testing Hybrid Search...")
        results = rag.hybrid_search("ZenAI assistant", k=1)
        if results and "ZenAI" in results[0]['text']:
            print(f"✅ Hybrid Search Verified: {results[0]['text']}")
        else:
            print(f"❌ Hybrid Search Failed. Results: {results}")
            return False
            
        return True
        
    except ImportError as e:
        print(f"❌ CRITICAL: ImportError - {e}")
        return False
    except Exception as e:
        print(f"❌ CRITICAL: RAG Exception - {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify_rag_core()
    if success:
        print("\n🎉 RAG Core is OPERATIONAL.")
        sys.exit(0)
    else:
        print("\n💀 RAG Core is BROKEN.")
        sys.exit(1)
