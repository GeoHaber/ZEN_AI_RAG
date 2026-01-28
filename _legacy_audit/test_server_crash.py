import subprocess
import threading
import time
import os
import sys
from pathlib import Path

# --- Configuration ---
BASE_DIR = Path(__file__).parent.absolute()
BIN_DIR = BASE_DIR / "_bin"
SERVER_EXE = BIN_DIR / "llama-server.exe"
MODEL_PATH = Path(r"C:\AI\Models\qwen2.5-coder-7b-instruct-q4_k_m.gguf")

def log_relay(process):
    print("[Relay] Thread started")
    try:
        while True:
            chunk = process.stdout.read(1024)
            if not chunk:
                if process.poll() is not None:
                    print("[Relay] Process ended")
                    break
                time.sleep(0.1)
                continue
            
            try:
                text = chunk.decode('utf-8', errors='replace')
                print(f"[Engine] {text}", end="", flush=True)
            except Exception as e:
                print(f"[Relay] Decode error: {e}")
    except Exception as e:
        print(f"[Relay] Error: {e}")
    print("[Relay] Thread exiting")

def run_test():
    if not SERVER_EXE.exists():
        print(f"Error: {SERVER_EXE} not found")
        return

    cmd = [
        str(SERVER_EXE), "--model", str(MODEL_PATH), "--host", "127.0.0.1", "--port", "8001",
        "--ctx-size", "2048", "--threads", "4", "--n-gpu-layers", "0",
        "--alias", "test-model", "--no-warmup", "-np", "1"
    ]

    print(f"[*] Starting process: {' '.join(cmd)}")
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False,
        bufsize=0,
        cwd=str(BIN_DIR)
    )

    relay_thread = threading.Thread(target=log_relay, args=(process,), daemon=True)
    relay_thread.start()

    print("[*] Waiting for 20 seconds...")
    for i in range(20):
        poll = process.poll()
        if poll is not None:
            print(f"[!] Process exited with code {poll}")
            break
        time.sleep(1)
    
    if process.poll() is None:
        print("[*] Process still alive. Sending test request...")
        try:
            import httpx
            resp = httpx.post("http://127.0.0.1:8001/v1/chat/completions", 
                             json={"messages": [{"role": "user", "content": "Hello"}], "stream": False},
                             timeout=10)
            print(f"[*] Response Status: {resp.status_code}")
            print(f"[*] Response Text: {resp.text[:100]}")
        except Exception as e:
            print(f"[!] Request failed: {e}")
        
        print("[*] Waiting 10 more seconds...")
        time.sleep(10)
    
    if process.poll() is None:
        print("[*] Test complete. Process survived.")
        process.terminate()
    else:
        print("[!] Test failed. Process died.")

if __name__ == "__main__":
    run_test()
