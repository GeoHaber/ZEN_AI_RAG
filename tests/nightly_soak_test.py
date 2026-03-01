import sys
import os
import time
import subprocess
import random
import glob
import datetime
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIG ---
ROOT_DIR = Path(__file__).parent.parent.resolve()
BIN_DIR = ROOT_DIR / "_bin"
CLI_EXE = BIN_DIR / "llama-cli.exe"
MODELS_DIR = Path("C:/AI/Models")
LOG_FILE = ROOT_DIR / "soak_report.log"

PROMPTS = [
    "Explain quantum physics roughly.",
    "Write a poem about rust.",
    "Calculate fibonacci 20.",
    "Describe the solar system.",
    "Why is the sky blue?",
    "How does a CPU work?",
    "What is DNA?",
    "History of Rome.",
    "Write a short scifi story.",
    "Explain the concept of love.",
    "List 10 types of cheese.",
    "Draft a resignation letter."
]

class SoakTester:
    """SoakTester class."""
    def __init__(self, hours=12):
        """Initialize instance."""
        self.target_duration = hours * 3600
        self.start_time = time.time()
        self.models = self._scan_models()
        self.cycle_count = 0
        self.total_requests = 0
        self.failed_requests = 0
        
        # Verify binary
        if not CLI_EXE.exists():
            raise FileNotFoundError(f"CLI binary not found at {CLI_EXE}")
            
    def log(self, msg):
        """Log."""
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        # Resilient append log
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + "\n")

    def _scan_models(self):
        if not MODELS_DIR.exists():
            return []
        return list(MODELS_DIR.glob("*.gguf"))

    def run_instance(self, worker_id, model, prompt):
        """Run a single chaos instance"""
        # Randomize temp
        temp = round(random.uniform(0.5, 0.9), 1)
        
        cmd = [
            str(CLI_EXE),
            "-m", str(model),
            "-p", prompt,
            "-n", str(random.randint(64, 256)), # Variable output length
            "-c", "2048",
            "--temp", str(temp),
            # "--log-disable" 
        ]
        
        start_t = time.time()
        try:
            res = subprocess.run(
                cmd,
                cwd=BIN_DIR,
                capture_output=True,
                text=True,
                encoding='utf-8', 
                errors='replace',
                timeout=600 # 10 min timeout
            )
            duration = time.time() - start_t
            success = (res.returncode == 0) and (len(res.stdout) > 10)
            
            result_data = {
                "worker_id": worker_id + 1, # 1-based index for display
                "success": success,
                "duration": duration,
                "model": model.name,
                "prompt": prompt,
                "answer": res.stdout[:200].replace("\n", " ") + "..." if success else "N/A", # Snippet
                "error": None
            }
            
            if not success:
                 result_data["error"] = f"Exit {res.returncode}"
                 
            return result_data
            
        except Exception as e:
            return {"worker_id": worker_id + 1, "success": False, "error": str(e), "model": model.name}

    def run(self):
        """Run."""
        self.log(f"--- STARTING NIGHTLY SOAK TEST (Target: {self.target_duration/3600:.1f} hours) ---")
        self.log(f"Models Available: {len(self.models)}")
        
        while (time.time() - self.start_time) < self.target_duration:
            self.cycle_count += 1
            
            # Chaos: Pick variable N (1 to 6)
            N = random.choice([1, 2, 2, 3, 3, 4, 6])
            
            self.log(f"\n--- Cycle {self.cycle_count} | Threads: {N} ---")
            
            futures = []
            results = []
            
            time.time()
            
            # Launch Workers
            with ThreadPoolExecutor(max_workers=N) as executor:
                for i in range(N):
                    model = random.choice(self.models)
                    prompt = random.choice(PROMPTS)
                    futures.append(executor.submit(self.run_instance, i, model, prompt))
                    
                for ft in as_completed(futures):
                    res = ft.result()
                    results.append(res)
                    
                    # USER REQUESTED FORMAT
                    # ====== 1 llama.cpp  ===== 
                    # LLM model conected to ...
                    wid = res.get('worker_id', '?')
                    mod = res.get('model', 'Unknown')
                    qst = res.get('prompt', 'Unknown')
                    ans = res.get('answer', 'No Answer')
                    dur = res.get('duration', 0)
                    
                    log_block = (
                        f"\n====== {wid} llama.cpp =====\n"
                        f"LLM model conected to: {mod}\n"
                        f"Question asked: {qst}\n"
                        f"Answer received: {ans}\n"
                        f"Time stats: {dur:.2f}s\n"
                    )
                    self.log(log_block)

            # Analyze Cycle
            successes = [r for r in results if r['success']]
            failures = [r for r in results if not r['success']]
            
            self.total_requests += len(results)
            self.failed_requests += len(failures)
            
            avg_time = 0
            if successes:
                avg_time = sum(r['duration'] for r in successes) / len(successes)
                
            elapsed_total = time.time() - self.start_time
            
            self.log(f"Cycle Complete. Succ: {len(successes)} Fail: {len(failures)} AvgT: {avg_time:.2f}s")
            self.log(f"Stats: TotalReq={self.total_requests} FailRate={self.failed_requests/self.total_requests*100:.1f}% Elapsed={elapsed_total/3600:.2f}h")
            
            if failures:
                self.log(f"Errors this cycle: {[f['error'] for f in failures]}")

            # Random Delay between cycles (Simulate user thinking time)
            delay = random.randint(1, 10)
            time.sleep(delay)
            
        self.log("--- SOAK TEST COMPLETE ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=float, default=12.0, help="Duration in hours")
    args = parser.parse_args()
    
    tester = SoakTester(hours=args.hours)
    try:
        tester.run()
    except KeyboardInterrupt:
        tester.log("Test Interrupted by User")
