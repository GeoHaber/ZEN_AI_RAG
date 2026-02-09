
import requests
import time
import subprocess
import sys
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("SwarmDiag")

SWARM_LAUNCH_URL = "http://127.0.0.1:8002/swarm/launch"
HEALTH_URL = "http://127.0.0.1:8005/health"
MODEL_NAME = "tinyllama-1.1b-chat.Q4_K_M.gguf"

def check_server_health():
    for _ in range(15): # Wait up to 30s
        try:
            resp = requests.get("http://127.0.0.1:8002/health", timeout=2)
            if resp.status_code == 200: return True
        except:
            pass
        time.sleep(2)
        logger.info("   ... waiting for Main Server (8002) ...")
    return False

def diagnose_launch():
    logger.info("🔍 DIAGNOSING SWARM LAUNCH...")

    # 1. Check Main Server
    if not check_server_health():
        logger.error("❌ Main Orchestrator (Port 8002) is OFFLINE. Cannot proceed.")
        logger.info("👉 Run 'python -m zena_mode.server' in another terminal first.")
        return

    logger.info("✅ Main Orchestrator is ONLINE.")

    # 2. Launch Request
    logger.info(f"🚀 Sending Launch Request for {MODEL_NAME} on Port 8005...")
    start_time = time.time()
    try:
        resp = requests.post(SWARM_LAUNCH_URL, json={
            "model": MODEL_NAME,
            "port": 8005
        }, timeout=15)
        
        logger.info(f"📥 Response ({resp.status_code}): {resp.text}")
        
        if resp.status_code != 200:
            logger.error("❌ Launch API refused command.")
            return

    except Exception as e:
        logger.error(f"❌ Launch Request Failed: {e}")
        return

    # 3. Monitor Port Binding
    logger.info("⏳ Waiting for Port 8005 to bind...")
    
    for i in range(30):
        try:
            # Try specific health check
            r = requests.get(HEALTH_URL, timeout=1)
            if r.status_code == 200:
                elapsed = time.time() - start_time
                logger.info(f"✅ EXPERT IS ONLINE! (Took {elapsed:.2f}s)")
                return
            else:
                logger.warning(f"⚠️ Port active but returned {r.status_code}")
        except requests.exceptions.ConnectionError:
             pass # Port likely closed
        except requests.exceptions.ReadTimeout:
             logger.warning("⚠️ Connection Timeout (Port open but hanging?)")
        
        time.sleep(1)
        if i % 5 == 0: logger.info(f"   ... waiting {i}s")

    logger.error("❌ Timed out waiting for Expert Health Check.")

if __name__ == "__main__":
    diagnose_launch()
