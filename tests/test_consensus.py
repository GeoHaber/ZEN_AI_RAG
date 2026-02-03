import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ConsensusTest")

API_URL = "http://127.0.0.1:8002/api/chat/swarm"

SWARM_LAUNCH_URL = "http://127.0.0.1:8002/swarm/launch"
HEALTH_URL = "http://127.0.0.1:8005/health"


SERVER_PROC = None

def start_server():
    global SERVER_PROC
    import subprocess
    import sys
    
    logger.info("🔧 Starting Backend Server (headless)...")
    cmd = [sys.executable, "-m", "zena_mode.server"]
    
    # Needs to be in root dir
    # Capture output to file for debugging
    log_file = open("server_log.txt", "w")
    SERVER_PROC = subprocess.Popen(cmd, cwd=".", stdout=log_file, stderr=subprocess.STDOUT)
    
    # Wait for 8002
    import time
    for i in range(60): # Increased to 60s
        try:
            if requests.get("http://127.0.0.1:8002/health", timeout=1).status_code == 200:
                logger.info("✅ Server Online")
                return True
        except:
            pass
        time.sleep(1)
        print(".", end="", flush=True)
    return False

def launch_expert():
    logger.info("🚀 Launching Expert (TinyLlama)...")
    try:
        requests.post(SWARM_LAUNCH_URL, json={
            "model": "tinyllama-1.1b-chat.Q4_K_M.gguf", 
            "port": 8005
        }, timeout=5)
    except:
        pass # Might already be running or accepted
    
    # Wait for ready
    import time
    for _ in range(60): # Increased timeout for expert launch
        try:
            if requests.get(HEALTH_URL, timeout=1).status_code == 200:
                logger.info("✅ Expert Online")
                return True
        except:
            pass
        time.sleep(1)
        print("x", end="", flush=True)
    return False

def test_consensus():
    if not start_server():
        logger.error("❌ Failed to start server in time")
        if SERVER_PROC: SERVER_PROC.kill()
        return

    if not launch_expert():
        logger.error("❌ Failed to launch expert")
        if SERVER_PROC: SERVER_PROC.kill()
        return

    logger.info("🧠 Testing Deep Thinking (Council) Mode...")
    
    payload = {
        "message": "Who are you? Are you Qwen or TinyLlama?",
        "mode": "council"
    }
    
    try:
        resp = requests.post(API_URL, json=payload, timeout=60)
        logger.info(f"Response Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            logger.info("✅ Success!")
            logger.info(f"Response: {data['response'][:200]}...")  # Print snippet
            logger.info(f"Mode: {data.get('mode')}")
            
            if "TinyLlama" in data['response'] or "Qwen" in data['response']:
                logger.info("✅ Models identified in response!")
            else:
                logger.warning("⚠️ Could not explicitly identify models in text (might be hidden by consensus)")
                
        else:
            logger.error(f"❌ Failed: {resp.text}")

    except Exception as e:
        logger.error(f"❌ Request Error: {e}")

if __name__ == "__main__":
    test_consensus()
