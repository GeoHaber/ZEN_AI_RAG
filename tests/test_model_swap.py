
import requests
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SwapTest")

HUB_URL = "http://127.0.0.1:8002"
MODEL_NAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"

def test_swap():
    logger.info(f"🔄 Triggering Swap to {MODEL_NAME}...")
    try:
        resp = requests.post(f"{HUB_URL}/swap", json={"model": MODEL_NAME}, timeout=5)
        logger.info(f"Response: {resp.status_code} {resp.text}")
    except Exception as e:
        logger.error(f"Request failed (expected if server restarts immediately): {e}")

    logger.info("⏳ Waiting for restart...")
    
    # Monitor for 60 seconds
    start = time.time()
    while time.time() - start < 60:
        try:
            # Check Health
            resp = requests.get(f"{HUB_URL}/health", timeout=1)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("llm_online"):
                    logger.info(f"✅ Server is BACK ONLINE! (Time: {time.time()-start:.1f}s)")
                    return
                else:
                    logger.info("Hub online, LLM booting...")
            else:
                logger.info(f"Hub Status: {resp.status_code}")
        except requests.exceptions.ConnectionError:
            logger.info("❌ Connection Refused (Server Down)")
        except Exception as e:
            logger.info(f"Error: {e}")
        
        time.sleep(2)
    
    logger.error("❌ TIMEOUT: Server did not return within 60s.")

if __name__ == "__main__":
    test_swap()
