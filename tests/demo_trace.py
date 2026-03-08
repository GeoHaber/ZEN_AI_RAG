import asyncio
import time
from zena_mode.arbitrage import SwarmArbitrator


async def demo_trace():
    """Demo trace."""
    # [X-Ray auto-fix] print("[DEBUG] Initializing Arbitrator with Auto-Discovery...")
    arb = SwarmArbitrator()

    if len(arb.endpoints) < 2:
        print("[!] Swarm currently Standalone. Forcing mock expansion for demonstration...")
        # If the user's experts aren't running, we'll mock them pointing to the same endpoint
        # to prove the PARALLEL Logic Trace works.
        base = arb.endpoints[0] if arb.endpoints else "http://127.0.0.1:8001/v1/chat/completions"
        arb.endpoints = [base] * 5
        arb.ports = [8001] * 5

    # [X-Ray auto-fix] print(f"[DEBUG] Active Experts: {len(arb.endpoints)}")
    query = "Why do we use Chain of Thought in LLMs?"
    sys_prompt = "You are an AI Architecture Expert. Be concise."

    print("\n--- STARTING LIVE MULTI-EXPERT TRACE ---\n")
    async for _ in arb.get_cot_response(query, sys_prompt, verbose=False):
        pass


if __name__ == "__main__":
    asyncio.run(demo_trace())
