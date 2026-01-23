import time
import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def measure_tps(api_url: str) -> Dict[str, Any]:
    """
    Measure system performance (Tokens Per Second).
    api_url: The URL of the LLM server (e.g. http://127.0.0.1:8001)
    """
    try:
        # 1. Warm up - ensure server is actually responding
        for _ in range(5):
            try:
                r = requests.get(f"{api_url}/health", timeout=2)
                if r.status_code == 200:
                    break
            except:
                time.sleep(1)
        else:
            return {"tps": 0.0, "tokens": 0, "time": 0.0, "error": "Server not responding"}
        
        # 2. Run a small prompt for benchmarking
        # Using a deterministic prompt for consistent measurement
        prompt = "Write a 50-word summary of why local LLMs are important for privacy."
        payload = {
            "prompt": f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n",
            "n_predict": 100,
            "temperature": 0.0, # Deterministic for benchmark
            "stream": False
        }
        
        start_time = time.time()
        resp = requests.post(f"{api_url}/completion", json=payload, timeout=60)
        end_time = time.time()
        
        if resp.status_code != 200:
            return {"tps": 0.0, "tokens": 0, "time": 0.0, "error": f"HTTP {resp.status_code}"}
        
        data = resp.json()
        # 'predicted_n' is the number of tokens generated
        tokens = data.get("timings", {}).get("predicted_n", 0)
        duration = end_time - start_time
        
        # Calculate TPS
        tps = tokens / duration if duration > 0 else 0
        
        # Determine Rating
        rating = "Good"
        if tps > 50: rating = "Excellent (Top Tier)"
        elif tps > 30: rating = "Very Good"
        elif tps > 15: rating = "Good"
        elif tps > 5: rating = "Acceptable"
        else: rating = "Slow (Check hardware)"

        return {
            "tps": tps,
            "tokens": tokens,
            "time": duration,
            "rating": rating,
            "success": True
        }
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        return {"tps": 0.0, "tokens": 0, "time": 0.0, "error": str(e), "success": False}
