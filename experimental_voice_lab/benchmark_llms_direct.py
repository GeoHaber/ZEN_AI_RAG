# benchmark_llms_direct.py
"""
Benchmark llama-server.exe directly via subprocess for each .gguf model in C:/AI/Models.
Measures response time and output for technical prompts.
"""
import subprocess
import time
import os
from pathlib import Path

import json
# Configuration (match start_voice_server.py)
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / "config.json"
try:
    with open(CONFIG_FILE) as f:
        config = json.load(f)
        MODEL_DIR = Path(config.get("model_dir", "models"))
        BIN_DIR = Path(config.get("bin_dir", "_bin"))
except Exception as e:
    print(f"⚠️ Config load failed: {e}")
    MODEL_DIR = PROJECT_ROOT / "models"
    BIN_DIR = PROJECT_ROOT / "_bin"
SERVER_EXE = BIN_DIR / "llama-server.exe"
PORT = 8005
N_TOKENS = 128
PROMPTS = [
    {
        "desc": "Short technical question",
        "prompt": "What is the time complexity of binary search?"
    },
    {
        "desc": "Medium technical question",
        "prompt": "Explain the difference between a Python list and a tuple, and give an example where a tuple is preferred."
    },
    {
        "desc": "Long technical question",
        "prompt": "Describe how a transformer neural network works, including the concepts of self-attention, positional encoding, and how it differs from a recurrent neural network."
    },
]

RESULTS_FILE = "llm_direct_benchmark_results.txt"

def run_llama_server(model_path):
    cmd = [
        str(SERVER_EXE),
        "--model", str(model_path),
        "--port", str(PORT),
        "--ctx-size", "2048",
        "-np", "4",
        "--n-gpu-layers", "33"
    ]
    return subprocess.Popen(cmd, cwd=BIN_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def wait_for_server(timeout=120):
    import requests
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(f"http://localhost:{PORT}/health", timeout=2)
            if resp.status_code == 200:
                return True
        except Exception:
            time.sleep(1)
    return False

def send_prompt(prompt):
    import requests
    payload = {
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8,
        "max_tokens": N_TOKENS
    }
    t0 = time.time()
    resp = requests.post(f"http://localhost:{PORT}/v1/chat/completions", json=payload, timeout=60)
    elapsed = time.time() - t0
    if resp.status_code == 200:
        text = resp.json()['choices'][0]['message']['content'].strip()
    else:
        text = f"[Error {resp.status_code}]"
    return text, elapsed


import psutil
def kill_zombie_servers():
    """Kill all running llama-server.exe processes."""
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and 'llama-server' in proc.info['name'].lower():
                print(f"Killing zombie process: {proc.info['pid']} {proc.info['name']}")
                proc.kill()
        except Exception:
            pass

def is_port_free(port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

def main():
    models = list(MODEL_DIR.glob("*.gguf"))
    results = []
    for model in models:
        print(f"\n=== Benchmarking {model.name} ===")
        kill_zombie_servers()
        while not is_port_free(PORT):
            print(f"Waiting for port {PORT} to become free...")
            time.sleep(2)
        proc = run_llama_server(model)
        if not wait_for_server():
            print(f"Server failed to start for {model.name}")
            proc.kill()
            continue
        for p in PROMPTS:
            print(f"Prompt: {p['desc']}")
            output, elapsed = send_prompt(p['prompt'])
            print(f"Time: {elapsed:.2f}s\nOutput: {output[:400]}\n")
            results.append((model.name, p['desc'], elapsed, output))
        proc.kill()
        kill_zombie_servers()
        time.sleep(5)  # Let port free up
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        for name, desc, elapsed, output in results:
            f.write(f"=== {name} | {desc} ===\nTime: {elapsed:.2f}s\nOutput: {output}\n\n")
    print(f"\nBenchmark complete. Results saved to {RESULTS_FILE}")

if __name__ == "__main__":
    main()
