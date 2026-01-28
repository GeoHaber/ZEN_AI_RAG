import subprocess
import time
import httpx
import os
from pathlib import Path

BASE_DIR = Path(r"c:\Users\dvdze\Documents\_Python\Dev\ZEN_AI_RAG")
BIN_DIR = BASE_DIR / "_bin"
MODEL_PATH = Path(r"C:\AI\Models\qwen2.5-coder-7b-instruct-q4_k_m.gguf")
SERVER_EXE = BIN_DIR / "llama-server.exe"

def run_test():
    cmd = [
        str(SERVER_EXE), "--model", str(MODEL_PATH), 
        "--host", "127.0.0.1", "--port", "8005",
        "--ctx-size", "4096", "--threads", "4",
        "--batch-size", "256", "--ubatch-size", "256",
        "--no-warmup", "-np", "1"
    ]
    
    print(f"[*] Launching: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, cwd=str(BIN_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # Wait for online
    online = False
    for _ in range(30):
        try:
            resp = httpx.get("http://127.0.0.1:8005/health", timeout=1)
            if resp.status_code == 200:
                online = True
                break
        except:
            pass
        if proc.poll() is not None:
            print(f"❌ Server died during startup!")
            break
        time.sleep(1)
        
    if not online:
        print("❌ Server failed to go online.")
        proc.kill()
        return

    print("✅ Server online. Sending prompt...")
    try:
        with httpx.stream("POST", "http://127.0.0.1:8005/v1/chat/completions", 
                          json={"messages": [{"role": "user", "content": "What are the three pillars of ZenAI 2.1?"}], "stream": True},
                          timeout=60) as r:
            for chunk in r.iter_text():
                print(chunk, end="", flush=True)
    except Exception as e:
        print(f"\n❌ Inference Error: {e}")
        
    print("\n[*] Checking server status after inference...")
    time.sleep(2)
    poll = proc.poll()
    if poll is not None:
        print(f"❌ Server CRASHED with code {poll}")
    else:
        print("✅ Server still alive.")
        proc.kill()

if __name__ == "__main__":
    run_test()
