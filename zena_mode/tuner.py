import time
import httpx
import asyncio
import json
import os
import logging
from typing import List, Dict
from pathlib import Path
import sys

# Add root to path for utils import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import safe_print

logger = logging.getLogger("SwarmTuner")


class SwarmTuner:
    """
    Benchmarks the system to find the 'Saturation Point'.
    Where T_parallel ≈ T_serial, adding more experts is useless.
    """

    def __init__(self, endpoints: List[str]):
        self.endpoints = endpoints
        self.config_path = Path("config.json")

    async def _probe_parallel(self, client: httpx.AsyncClient, active_endpoints: List[str], prompt: str) -> Dict:
        """Measure time to complete parallel query and return content."""
        start = time.time()
        tasks = []
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 64,  # Short for quick benchmarking
            "stream": False,
        }

        for ep in active_endpoints:
            tasks.append(client.post(ep, json=payload, timeout=60))

        responses = await asyncio.gather(*tasks)
        duration = time.time() - start

        results = []
        for r in responses:
            if r.status_code == 200:
                results.append(r.json()["choices"][0]["message"]["content"].strip())
            else:
                results.append(f"Error: {r.status_code}")

        return {"duration": duration, "content": results}

    async def find_optimal_n(self) -> int:
        """
        Step through N=1 to N_max and find the performance 'Knee'.
        """
        if not self.endpoints:
            safe_print("[Tuner] !!! No experts discovered. Initialization failed?")
            return 1

        prompt = "Write a 20-word logic puzzle about a hat."
        safe_print(f"\n[Tuner] QUESTION: {prompt}")
        safe_print(f"[Tuner] Starting Hardware-In-The-Loop Benchmark on {len(self.endpoints)} slots...")

        results_stats = []

        async with httpx.AsyncClient() as client:
            # Baseline: N=1
            probe1 = await self._probe_parallel(client, self.endpoints[:1], prompt)
            t1 = probe1["duration"]
            safe_print(f"[Tuner] Baseline (N=1): {t1:.2f}s | Answer: '{probe1['content'][0][:50]}...'")
            results_stats.append(t1)

            optimal_n = 1

            for n in range(2, len(self.endpoints) + 1):
                probe_n = await self._probe_parallel(client, self.endpoints[:n], prompt)
                tn = probe_n["duration"]

                # Analysis
                seq_total = t1 * n
                speedup = seq_total / tn
                efficiency = speedup / n

                safe_print(f"[Tuner] Tier N={n}: Time={tn:.2f}s | Speedup={speedup:.2f}x | Efficiency={efficiency:.1%}")
                for i, ans in enumerate(probe_n["content"]):
                    safe_print(f"    - Expert {i + 1} Result: {ans[:60]}...")

                # RECOVERY: User requested to see results for 1-6, so we disable the break for this run.
                # if efficiency < 0.40:
                #    safe_print(f"[Tuner]!!! SATURATION DETECTED AT N={n}. Speedup is too low.")
                #    break

                if efficiency > 0.5:
                    optimal_n = n

                time.sleep(1)  # Cool down

        safe_print(f"\n[Tuner] Optimization Complete. Optimal Expert Swarm Size: {optimal_n}")
        self._save_to_config(optimal_n)
        return optimal_n

    def _save_to_config(self, n: int):
        """Persist the optimal swarm size to config.json."""
        config_data = {}
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                config_data = json.load(f)

        if "zena_mode" not in config_data:
            config_data["zena_mode"] = {}

        config_data["zena_mode"]["optimal_experts"] = n

        with open(self.config_path, "w") as f:
            json.dump(config_data, f, indent=4)
        safe_print(f"[Tuner] Saved optimal_experts={n} to {self.config_path}")


async def run_auto_tune(arb):
    tuner = SwarmTuner(arb.endpoints)
    return await tuner.find_optimal_n()
