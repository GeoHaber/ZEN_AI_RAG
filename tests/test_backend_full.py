# -*- coding: utf-8 -*-
"""
test_backend_full.py - Comprehensive Headless Backend Verification
Tests LLM Connectivity, RAG performance, and API stability.
"""
import asyncio
import sys
import os
import time
import requests
from pathlib import Path

# --- Bootstrapping ---
BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(BASE_DIR))

from async_backend import AsyncZenAIBackend
from zena_mode.rag_pipeline import LocalRAG
from config_system import config, EMOJI

async def test_llm_chat():
    print(f"🔎 {EMOJI['robot']} Testing LLM Chat Connectivity...")
    backend = AsyncZenAIBackend()
    
    try:
        async with backend:
            print(f"  - Sending 'Say HELLO' to {backend.api_url}")
            full_response = ""
            async for chunk in backend.send_message_async("Say only the word HELLO"):
                full_response += chunk
                
            if "HELLO" in full_response:
                print(f"  ✅ Received: {repr(full_response)}")
                return True
            
            print(f"  ❌ Failed to get expected response. Received: {repr(full_response)}")
            return False
    except Exception as e:
        print(f"  ❌ LLM Test Error: {e}")
        return False

def test_rag_standalone():
    print(f"🔎 {EMOJI['database']} Testing RAG Indexing & Retrieval...")
    test_cache = Path("tests/rag_test_cache")
    if test_cache.exists():
        try:
            import shutil
            shutil.rmtree(test_cache)
        except: pass
    
    rag = LocalRAG(cache_dir=test_cache)
    
    try:
        # Create dummy document
        docs = [
            {
                "url": "test://secret-file",
                "title": "Secret Doc",
                "content": "The top secret password for the ZenAI system is 'PURPLE-ORANGUTAN-77'. This is located in the basement."
            }
        ]
        
        print("  - Building Index...")
        rag.build_index(docs, filter_junk=False)
        
        print("  - Querying 'What is the secret password?'...")
        results = rag.search("What is the secret password?", k=1)
        
        if len(results) > 0 and "PURPLE-ORANGUTAN" in results[0]['text']:
            print(f"  ✅ RAG Success: Found secret content")
            # Close/Cleanup RAG before directory deletion
            del rag
            import gc; gc.collect()
            time.sleep(1) 
            return True
        else:
            print(f"  ❌ RAG Failure: Could not find indexed content")
            return False
    except Exception as e:
        print(f"  ❌ RAG Test Error: {e}")
        return False
    finally:
        # Avoid crashing during shutdown if file is still locked
        try:
            import shutil
            if test_cache.exists():
                shutil.rmtree(test_cache)
        except:
            pass

def test_hub_api():
    print(f"🔎 {EMOJI['web']} Testing Hub API Status...")
    hub_url = f"http://{config.host}:{config.mgmt_port}"
    try:
        # Check mgmt port - server.py might be running as part of start_llm.py
        resp = requests.get(f"{hub_url}/models/available", timeout=5)
        if resp.status_code == 200:
            print(f"  ✅ Hub API Online")
            return True
        else:
            print(f"  ❌ Hub API returned status {resp.status_code}")
            return False
    except Exception as e:
        print(f"  ⚠️ Hub API unreachable: {e}")
        return False

async def main():
    print("="*60)
    print("🚀 ZENAI BACKEND HEADLESS VERIFICATION")
    print("="*60)
    
    results = {
        "LLM Chat": await test_llm_chat(),
        "RAG Logic": test_rag_standalone(),
        "Hub Status": test_hub_api()
    }
    
    print("\n" + "="*60)
    print("📊 FINAL REPORT")
    print("="*60)
    all_ok = True
    for test, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test:<20} : {status}")
        if not passed: all_ok = False
        
    if all_ok:
        print("\n✨ BACKEND IS STABLE AND READY FOR INTEGRATION ✨")
        sys.exit(0)
    else:
        print("\n⚠️ BACKEND HAS ISSUES. FIX BEFORE INTEGRATION.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
