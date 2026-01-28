import sys
import os
import time
import requests
import subprocess
import psutil
import csv
import json
import statistics
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIG ---
ROOT_DIR = Path(__file__).parent.parent.resolve()
START_SCRIPT = ROOT_DIR / "start_llm.py"
MODEL_PATH = Path("C:/AI/Models/qwen2.5-0.5b-instruct-q5_k_m.gguf")
REPORT_FILE = ROOT_DIR / "scalability_report.csv"
START_PORT = 9000

class ScalabilityTester:
    def __init__(self, max_instances=10, safe_mode=False):
        self.procs = []
        self.metrics = []
        self.max_instances = max_instances
        self.safe_mode = safe_mode
        self.active_ports = []

    def log(self, msg):
        print(f"[CrashTest] {msg}")

    def clean_all(self):
        self.log("Cleaning up processes...")
        for p in self.procs:
            try: p.terminate() 
            except: pass
        
        # Aggressive cleanup of orphaned llama-server
        for p in psutil.process_iter(['pid', 'name']):
            if p.info['name'] == 'llama-server.exe':
                try: p.terminate()
                except: pass
        self.procs = []
        self.active_ports = []
        time.sleep(2)

    def launch_instance(self, port):
        env = os.environ.copy()
        env["LLM_PORT"] = str(port)
        
        # Guard Bypass is Essential
        cmd = [sys.executable, str(START_SCRIPT), "--model", str(MODEL_PATH), "--guard-bypass"]
        
        proc = subprocess.Popen(
            cmd,
            cwd=ROOT_DIR,
            stdout=subprocess.DEVNULL, # Mute stdout for cleaner benchmark logs
            stderr=subprocess.DEVNULL,
            env=env,
            stdin=subprocess.PIPE
        )
        return proc

    def wait_health(self, port, timeout_sec=60):
        start = time.time()
        while time.time() - start < timeout_sec:
            try:
                r = requests.get(f"http://127.0.0.1:{port}/health", timeout=1)
                if r.status_code == 200:
                    return True
            except:
                time.sleep(1)
        return False

    def benchmark_single(self, port, question="Verify system check."):
        """Measure inference time on a single instance"""
        start_t = time.time()
        ttft = 0
        end_t = 0
        
        # Simple completion payload
        payload = {
            "prompt": f"<|im_start|>user\n{question}<|im_end|>\n<|im_start|>assistant\n",
            "n_predict": 128,
            "temperature": 0.7,
            "stream": False # Streaming is harder to measure simply without client, we measure total duration
        }
        
        try:
            # We measure Total Round Trip Time (RTT) here as proxy for load
            # Proper TTFT requires streaming support
            resp = requests.post(f"http://127.0.0.1:{port}/completion", json=payload, timeout=60)
            end_t = time.time()
            if resp.status_code == 200:
                return {
                    "success": True,
                    "duration": end_t - start_t,
                    "tokens": resp.json().get('timings', {}).get('predicted_n', 0),
                    "port": port
                }
        except Exception as e:
            pass
            
        return {"success": False, "port": port}

    def run_cycle(self, count):
        self.log(f"--- Starting Cycle N={count} ---")
        cycle_ports = [START_PORT + i for i in range(count)]
        
        # Launch Group
        launch_start = time.time()
        for p in cycle_ports:
            proc = self.launch_instance(p)
            self.procs.append(proc)
        
        # Wait for Ready
        ready_count = 0
        for p in cycle_ports:
            if self.wait_health(p):
                ready_count += 1
            else:
                self.log(f"Port {p} failed to start")
                
        launch_duration = time.time() - launch_start
        self.log(f"Ready: {ready_count}/{count} (Launch took {launch_duration:.2f}s)")
        
        if ready_count < count:
            self.log("CRITICAL: Not all instances started. System limit reached?")
            return False

        # Benchmark Parallel
        self.log("Generating Parallel Load...")
        questions = [
            "Explain quantum physics roughly.",
            "Write a poem about rust.",
            "Calculate fibonacci 10.",
            "Describe the solar system.",
            "Why is the sky blue?",
            "How does a CPU work?",
            "What is DNA?",
            "History of Rome."
        ]
        
        results = []
        with ThreadPoolExecutor(max_workers=count) as executor:
            futures = []
            for i, p in enumerate(cycle_ports):
                q = questions[i % len(questions)]
                futures.append(executor.submit(self.benchmark_single, p, q))
                
            for ft in as_completed(futures):
                results.append(ft.result())

        # Analyze
        successes = [r for r in results if r['success']]
        avg_time = statistics.mean([r['duration'] for r in successes]) if successes else 0
        total_tokens = sum([r.get('tokens', 0) for r in successes])
        tps = total_tokens / avg_time if avg_time > 0 else 0 # Rough estimate per instance stream
        
        row = {
            "instances": count,
            "success_rate": len(successes)/count,
            "avg_latency": avg_time,
            "launch_overhead": launch_duration,
            "cpu_usage": psutil.cpu_percent(),
            "ram_usage": psutil.virtual_memory().percent
        }
        self.metrics.append(row)
        self.log(f"Cycle Result: {json.dumps(row, indent=2)}")
        
        return len(successes) == count

    def run(self):
        # CSV Header
        with open(REPORT_FILE, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["instances", "success_rate", "avg_latency", "launch_overhead", "cpu_usage", "ram_usage"])
            writer.writeheader()

        for n in range(1, self.max_instances + 1):
            if not self.run_cycle(n):
                self.log("Stopping due to failure.")
                break
                
            # Append Record
            with open(REPORT_FILE, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=["instances", "success_rate", "avg_latency", "launch_overhead", "cpu_usage", "ram_usage"])
                writer.writerow(self.metrics[-1])
            
            self.clean_all()
            if self.safe_mode and n >= 2:
                self.log("Safe Mode: Stopping at N=2")
                break
                
        self.log(f"Test Complete. Report saved to {REPORT_FILE}")

if __name__ == "__main__":
    # If run directly with no args, default to safe mode (N=2) for verification
    # User can run with "python tests/crash_test_scalability.py FULL" for full test
    is_safe = True
    if len(sys.argv) > 1 and sys.argv[1] == "FULL":
        is_safe = False
        
    tester = ScalabilityTester(max_instances=10, safe_mode=is_safe)
    try:
        tester.clean_all() # Pre-clean
        tester.run()
    finally:
        tester.clean_all()
