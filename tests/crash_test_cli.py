import sys
import os
import time
import subprocess
import glob
import random
import statistics
import json
import csv
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from test_utils import scan_models

# --- CONFIG ---
ROOT_DIR = Path(__file__).parent.parent.resolve()
BIN_DIR = ROOT_DIR / "_bin"
CLI_EXE = BIN_DIR / "llama-cli.exe"
REPORT_FILE = ROOT_DIR / "cli_crash_report.csv"
MODELS_DIR = Path("C:/AI/Models")

# --- PROMPTS ---
PROMPTS = [
    "Explain the theory of relativity to a 5 year old.",
    "Write a python function to Fibonacci sequence.",
    "What is the capital of France? Explain its history.",
    "Draft a professional email to a client about delay.",
    "Write a poem about the ocean deeply.",
    "Explain how a Neural Network learns weights.",
    "Recipe for a chocolate cake.",
    "Who was Julius Caesar?",
    "Summarize the plot of Hamlet.",
    "Differences between TCP and UDP."
]

class CLITester:
    def __init__(self, max_N=10, safe_mode=True):
        self.max_N = max_N
        self.safe_mode = safe_mode
        self.models = scan_models(MODELS_DIR)
        self.results = []
        
        if not CLI_EXE.exists():
            raise FileNotFoundError(f"CLI binary not found at {CLI_EXE}")
            

    def run_single_cli(self, index, model_path, prompt):
        """Run one standalone llama-cli process"""
        start_t = time.time()
        
        # Args: -m [model] -p [prompt] -n 64 --temp 0.X --no-display-prompt
        # We assume standard llama-cli args
        cmd = [
            str(CLI_EXE),
            "-m", str(model_path),
            "-p", prompt,
            "-n", "64",       # Prediction length
            "-c", "2048",      # Context
            # "--log-disable"    # REMOVED for debugging
        ]
        
        try:
            # Run Process
            # CRITICAL: Set cwd to BIN_DIR so it finds llama.dll/ggml.dll
            res = subprocess.run(
                cmd,
                cwd=BIN_DIR,
                capture_output=True,
                text=True,
                encoding='utf-8', 
                errors='replace',
                timeout=300
            ) 
            
            end_t = time.time()
            duration = end_t - start_t
            
            success = (res.returncode == 0)
            # Basic validation: did it generate text?
            # With logs enabled, stdout should definitely be > 10 chars (loading info etc)
            # We want to check if it generated *new* text, but for crash test, any output is good sign of life.
            if success and len(res.stdout) < 10:
                success = False # Output too short
                print(f"[Err] Output too short for {model_path.name}")
            
            if not success:
               # Print MORE dump
               print(f"[Err] {model_path.name} Failed. Exit:{res.returncode}")
               print(f"--- STDERR ---\n{res.stderr[:500]}\n--- STDOUT ---\n{res.stdout[:500]}")
            
            return {
                "index": index,
                "model": model_path.name,
                "prompt": prompt[:20] + "...",
                "duration": duration,
                "success": success,
                "stdout": res.stdout[:100].replace('\n', ' ') 
            }
            
        except subprocess.TimeoutExpired:
            return {"index": index, "model": model_path.name, "success": False, "error": "Timeout"}
        except Exception as e:
            return {"index": index, "model": model_path.name, "success": False, "error": str(e)}

    def run_cycle(self, N):
        print(f"\n[CLI-Test] Starting Cycle N={N} (Parallel Instances) ---")
        
        futures = []
        cycle_results = []
        
        start_cycle = time.time()
        
        with ThreadPoolExecutor(max_workers=N) as executor:
            for i in range(N):
                # Round Robin Model
                if not self.models:
                    print("[Error] No models found!")
                    return False
                model = self.models[i % len(self.models)]
                
                # Random Prompt
                prompt = PROMPTS[i % len(PROMPTS)]
                
                futures.append(executor.submit(self.run_single_cli, i, model, prompt))
                
            for ft in as_completed(futures):
                cycle_results.append(ft.result())
        
        end_cycle = time.time()
        total_cycle_time = end_cycle - start_cycle
        
        # Analyze
        success_count = sum(1 for r in cycle_results if r['success'])
        avg_time = 0
        if success_count > 0:
            avg_time = statistics.mean([r['duration'] for r in cycle_results if r['success']])
            
        print(f"[CLI-Test] Cycle N={N} Complete in {total_cycle_time:.2f}s")
        print(f"           Success: {success_count}/{N}")
        print(f"           Avg Duration Per Instance: {avg_time:.2f}s")
        
        # Log to list
        row = {
            "instances": N,
            "success_rate": success_count/N,
            "avg_latency": avg_time,
            "total_wall_time": total_cycle_time,
            "models_used": "|".join([r['model'] for r in cycle_results])
        }
        self.results.append(row)
        
        # Append to CSV
        file_exists = REPORT_FILE.exists()
        with open(REPORT_FILE, 'a', newline='') as f:
            w = csv.DictWriter(f, fieldnames=row.keys())
            if not file_exists: w.writeheader()
            w.writerow(row)
            
        return (success_count == N)

    def run(self):
        # Clear old report
        if REPORT_FILE.exists():
            os.remove(REPORT_FILE)
            
        for n in range(1, self.max_N + 1):
            success = self.run_cycle(n)
            
            if not success:
                print(f"[CLI-Test] Crash/Failure detected at N={n}. Stopping.")
                break
                
            if self.safe_mode and n >= 2:
                print("[CLI-Test] Safe Mode: Stopping at N=2.")
                break
                
            # Cool down
            time.sleep(2)

if __name__ == "__main__":
    is_safe = True
    if len(sys.argv) > 1 and sys.argv[1] == "FULL":
        is_safe = False
        
    print(f"--- ZenAI Standalone CLI Crash Test (SafeMode={is_safe}) ---")
    tester = CLITester(max_N=12, safe_mode=is_safe)
    tester.run()
