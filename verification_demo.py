
import requests
import sys
import json
import time

BASE_URL = "http://127.0.0.1:8080"
API_URL = "http://127.0.0.1:8002"  # Hub Port

def test_rag():
    print(">>> Testing RAG Extraction & Search...")
    # 1. Ingest a mock document (if possible via API, or just assume system state)
    # Since we can't easily ingest via HTTP in this simple script without auth/complex payload,
    # we will test the 'Search' capability if exposed, or check status.
    
    # Actually, let's check /api/rag/status if it exists, or similar.
    # Based on server.py, RAG might not be directly exposed via the Hub API yet?
    # Let's check server.py again. It has /models/download, /voice/..., but maybe not RAG search.
    pass

def test_voice_lab():
    print("\n>>> Testing Voice Lab API Connectivity...")
    
    # 1. Check Devices
    try:
        resp = requests.get(f"{API_URL}/api/devices", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Voice Backend Online. Inputs: {len(data.get('inputs', []))}, Outputs: {len(data.get('outputs', []))}")
        else:
            print(f"❌ Voice Backend Error: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Voice Backend Unreachable: {e}")

    # 2. Check TTS Voices
    try:
        resp = requests.get(f"{API_URL}/api/tts-voices", timeout=2)
        if resp.status_code == 200:
            print(f"✅ TTS Voices Endpoint: OK")
        else:
            print(f"❌ TTS Voices Error: {resp.status_code}")
    except Exception as e:
        print(f"❌ TTS Voices Unreachable: {e}")

    try:
        resp = requests.get(f"{API_URL}/voice/lab", timeout=2)
        if resp.status_code == 200:
            print(f"✅ Voice Lab UI Serving: OK")
        else:
            print(f"❌ Voice Lab UI Error: {resp.status_code}")
    except Exception as e:
        print(f"❌ Voice Lab UI Unreachable: {e}")

if __name__ == "__main__":
    print(f"Running ZenAI Feature Verification on {API_URL}")
    test_voice_lab()
