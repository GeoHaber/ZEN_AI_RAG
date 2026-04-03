import asyncio
import json
import httpx
from zena_mode.arbitrage import SwarmArbitrator


async def test_quiet_cot_logic():
    """Test quiet cot logic."""
    print("--- TESTING QUIET COT EVOLUTION (Phase 19) ---")

    # Mock arbitrator with a single endpoint for reflection test
    arb = SwarmArbitrator()
    arb.endpoints = ["http://127.0.0.1:8001/v1/chat/completions"]

    print(f"\n[Test 1] Single-LLM Self-Reflection (Quiet Mode)...")
    prompt = "Why is the sky blue?"

    chunks = []
    async for chunk in arb.get_cot_response(prompt, "You are ZenAI.", verbose=False):
        chunks.append(chunk)

    print(f"Captured {len(chunks)} stream chunks.")
    # The first chunk should be the 'Thinking...' indicator
    # The middle chunks should be the synthesis
    # The final chunk should be the metrics

    full_response = "".join(chunks)
    print(f"Final Response Length: {len(full_response)}")
    # Verification: Should NOT contain "Expert Analysis" or "Reflection Analysis" strings used for verbose mode
    if "--- **Expert" in full_response or "--- **Reflection" in full_response:
        print("❌ FAILED: Intermediate thoughts found in Quiet Mode output!")
    else:
        print("✅ PASSED: Intermediate thoughts kept in memory.")

    if "Swarm Metrics" in full_response:
        print("✅ PASSED: Swarm Metrics footer present.")
    else:
        print("❌ FAILED: Swarm Metrics footer missing.")

    print("\n[Test 2] Verbose Mode Validation...")
    v_chunks = []
    async for chunk in arb.get_cot_response(prompt, "You are ZenAI.", verbose=True):
        v_chunks.append(chunk)

    v_full = "".join(v_chunks)
    if "--- **Reflection**" in v_full:
        print("✅ PASSED: Intermediate thoughts visible in Verbose Mode.")
    else:
        print("❌ FAILED: Intermediate thoughts missing from Verbose Mode.")


if __name__ == "__main__":
    asyncio.run(test_quiet_cot_logic())
