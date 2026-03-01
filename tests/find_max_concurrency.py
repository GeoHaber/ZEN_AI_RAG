import sys
import os
import time
import subprocess
import glob
import statistics
import csv
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIG ---
ROOT_DIR = Path(__file__).parent.parent.resolve()
BIN_DIR = ROOT_DIR / "_bin"
CLI_EXE = BIN_DIR / "llama-cli.exe"
MODELS_DIR = Path("C:/AI/Models")
REPORT_FILE = ROOT_DIR / "concurrency_report.csv"

# Fixed Prompt for consistent load measurement
PROMPT = "Write a short poem about the concept of infinity."
# We use a fixed short prompt to ensure consistent work, 
# but we can vary it slightly if cache contention is a concern.
# For CPU bound testing, different models is the main variable.

class MaxConcurrencyTester:
    """MaxConcurrencyTester class."""
    def __init__(self, max_cap=16):
        """Initialize instance."""
        self.max_cap = max_cap
        self.models = self._scan_models()
        self.baseline_latency = 0
        
        if not CLI_EXE.exists():
            raise FileNotFoundError(f"CLI binary not found at {CLI_EXE}")

    def _scan_models(self):
        if not MODELS_DIR.exists():
            return []
        # Sort by size or name to be deterministic? 
        # Using sorted list ensures N=1 always uses Model A, N=2 uses A+B, etc.
        return sorted(list(MODELS_DIR.glob("*.gguf")), key=lambda p: p.stat().st_size)

    def run_single(self, index, model, prompt):
        """Run single."""
        start_t = time.time()
        cmd = [
            str(CLI_EXE),
            "-m", str(model),
            "-p", prompt,
            "-n", "128",       # Fixed output length for fair comparison
            "-c", "2048",
            "--temp", "0.7",
            # "--log-disable" # REMOVED to validte output
            # "--log-disable"
        ]
        
        try:
            res = subprocess.run(
                cmd,
                cwd=BIN_DIR,
                capture_output=True,
                text=True,
                encoding='utf-8', 
                errors='replace',
                timeout=180
            )
            duration = time.time() - start_t
            success = (res.returncode == 0) and (len(res.stdout) > 10)
            
            if not success:
                # Debug Failure
                print(f"[Err] Model {model.name} Failed. Exit: {res.returncode}")
                print(f"STDERR: {res.stderr[:200]}")
            
            return {
                "index": index,
                "model": model.name,
                "duration": duration,
                "success": success,
                "output": res.stdout[:50].replace('\n', ' ') + "..."
            }
        except Exception as e:
            print(f"[Err] Exception: {e}")
            return {"index": index, "model": model.name, "success": False, "duration": 0, "error": str(e)}

    def run(self):
        """Run."""
        print(f"--- THOUGHPUT TEST: SEQUENTIAL VS PARALLEL (Models: {len(self.models)}) ---")
        
        # Header
        print(f"{'N':<3} | {'Seq Time':<10} | {'Par Time':<10} | {'Speedup':<8} | {'Status'}")
        print("-" * 60)

        for n in range(1, self.max_cap + 1):
            
            # Select models for this tier
            current_models = []
            for i in range(n):
                current_models.append(self.models[i % len(self.models)])
            
            # --- PHASE 1: SEQUENTIAL BASELINE ---
            seq_start = time.time()
            # print(f"    [N={n}] Running Sequential baseline...")
            for i, model in enumerate(current_models):
                # We reuse run_single but calculate sum
                # Mute output for baseline to keep log clean
                self.run_single(i, model, PROMPT)
            seq_duration = time.time() - seq_start
            
            time.sleep(1) # Cool down
            
            # --- PHASE 2: PARALLEL ---
            par_start = time.time()
            # print(f"    [N={n}] Running Parallel...")
            
            futures = []
            results = []
            with ThreadPoolExecutor(max_workers=n) as executor:
                for i, model in enumerate(current_models):
                    futures.append(executor.submit(self.run_single, i, model, PROMPT))
                
                for ft in as_completed(futures):
                    res = ft.result()
                    results.append(res)
                    if res['success']:
                         # Print succinct status
                         pass 
                         
            par_duration = time.time() - par_start
            
            # --- ANALYSIS ---
            # Speedup = Seq / Par
            # If Seq=10s, Par=5s -> Speedup = 2.0x (Good)
            # If Seq=10s, Par=10s -> Speedup = 1.0x (Saturated)
            speedup = seq_duration / par_duration if par_duration > 0 else 0
            
            status = "GAINING"
            if speedup < 0.8: status = "THRASHING"
            elif speedup < 1.2: status = "SATURATED"
            elif speedup > 1.5: status = "EFFICIENT"
            
            print(f"{n:<3} | {seq_duration:<9.2f}s | {par_duration:<9.2f}s | {speedup:<7.2f}x | {status}")
            
            # Print Q&A only for the last parallel batch item to show it worked
            if results and results[0]['success']:
                 # print(f"    Sample A: {results[0]['output'][:50]}...")
                 pass

            time.sleep(2)

        print("-" * 60)
        print("Test Complete.")

if __name__ == "__main__":
    tester = MaxConcurrencyTester(max_cap=6) # Cap at 6 for quick test
    tester.run()
