import requests
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SwarmTest")

HUB_URL = "http://127.0.0.1:8002"
MODEL_NAME = "tinyllama-1.1b-chat.Q4_K_M.gguf"
SWARM_PORT = 8005

def test_launch():
    """Test launch."""
    logger.info(f"🚀 Launching {MODEL_NAME} on port {SWARM_PORT}...")
    try:
        resp = requests.post(f"{HUB_URL}/swarm/launch", json={
            "model": MODEL_NAME,
            "port": SWARM_PORT
        }, timeout=10)
        
        logger.info(f"Launch Response: {resp.status_code} {resp.text}")
        if resp.status_code != 200:
            return
            
    except Exception as e:
        logger.error(f"Launch Request failed: {e}")
        return

    logger.info("⏳ Waiting for expert to bind...")
    
    # Poll output
    url = f"http://127.0.0.1:{SWARM_PORT}/health"
    for i in range(30):
        try:
            resp = requests.get(url, timeout=1)
            if resp.status_code == 200:
                logger.info("✅ Expert is ONLINE!")
                logger.info(resp.json())
                return
        except Exception:
            pass
        time.sleep(1)
        print(".", end="", flush=True)
    
    logger.error("❌ TIMEOUT: Expert did not start.")

if __name__ == "__main__":
    test_launch()
