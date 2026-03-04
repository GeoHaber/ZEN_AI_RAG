import asyncio
import httpx
import sys
import os
import time
import random
from pathlib import Path

# Add root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from async_backend import AsyncZenAIBackend
from config_system import config
import model_manager
from ui.registry import UI_IDS, MONKEY_TARGETS, UI_METADATA

async def check_service(name, url, timeout=2.0):
    """Check service."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=timeout)
            if resp.status_code == 200:
                print(f"✅ {name:15} | Online ({url})")
                return True
            else:
                print(f"⚠️ {name:15} | Warning: Status {resp.status_code} ({url})")
                return False
    except Exception as e:
        print(f"❌ {name:15} | Offline ({url}) - {type(e).__name__}")
        return False

MONKEY_PROMPTS = [
    "Tell me a joke about robots.",
    "Explain the architecture of ZenAI in 3 words.",
    "What happens if I delete my knowledge base?",
    "Summarize the project README.",
    "Perform a consensus analysis on the future of AI.",
    "Analyze the security of local LLM storage.",
    "Who is George Haber?",
    "How does the expert swarm handle disagreements?",
    "What is the current TPS of the engine?",
    "Write a poem about RAG systems."
]

async def run_monkey_test(backend, iterations=5):
    """Run monkey test."""
    print("\n" + "🐒" * 25)
    print("      LIVE MONKEY TEST: CHAOS INJECTION")
    print("🐒" * 25 + "\n")
    
    success_count = 0
    for i in range(1, iterations + 1):
        prompt = random.choice(MONKEY_PROMPTS)
        print(f"[{i}/{iterations}] 🐒 Monkey injecting: \"{prompt}\"")
        
        full_text = ""
        start = time.time()
        try:
            async for chunk in backend.send_message_async(prompt):
                full_text += chunk
                if len(full_text) % 20 == 0: print(".", end="", flush=True)
            
            duration = time.time() - start
            if full_text.strip():
                print(f" ✅ Received {len(full_text)} chars ({duration:.1f}s)")
                success_count += 1
            else:
                print(f" ❌ RECEIVED EMPTY RESPONSE!")
        except Exception as e:
            print(f" ❌ ERROR DURING MONKEY TEST: {e}")
        
    print(f"\n🐒 Monkey Test Complete: {success_count}/{iterations} successful injections.")
    return success_count == iterations

async def run_ui_chaos_test(backend, iterations=10):
    """Run ui chaos test."""
    print("\n" + "🌀" * 25)
    print("      UI SMART CHAOS TEST: AI-VALIDATED POKING")
    print("🌀" * 25 + "\n")
    
    success_count = 0
    async with httpx.AsyncClient() as client:
        for i in range(1, iterations + 1):
            target_id = random.choice(MONKEY_TARGETS)
            description = UI_METADATA.get(target_id, "Unknown action")
            print(f"[{i}/{iterations}] 🌀 Poking: {target_id} ({description})")
            
            # Ask the LLM to predict outcome for verification
            prompt = f"UI Action: Click '{description}'. Based on this action, what is the expected UI change? Answer in 1 short sentence."
            print("  🤖 AI Prediction: ", end="", flush=True)
            async for chunk in backend.send_message_async(prompt):
                print(chunk.strip(), end=" ", flush=True)
            print()

            try:
                # Use a POST to the hidden test endpoint
                resp = await client.post(f"http://{HOST}:8080/test/click/{target_id}", timeout=2.0)
                if resp.status_code == 200:
                    print(" ✅ Triggered")
                    success_count += 1
                else:
                    print(f" ⚠️ Failed (Status {resp.status_code})")
            except Exception as e:
                print(f" ❌ ERROR: {e}")
            
            # Wait a bit between pokes to allow UI to react
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
    print(f"\n🌀 UI Chaos Test Complete: {success_count}/{iterations} successful pokes.")
    return success_count > 0

async def run_semantic_ui_audit(backend):
    """Uses the LLM to verify if the UI Registry makes sense according to its metadata."""
    print("\n" + "🧠" * 25)
    print("      AI SEMANTIC UI AUDIT")
    print("🧠" * 25 + "\n")
    
    registry_dump = json.dumps(UI_METADATA, indent=2)
    prompt = f"""
    As the ZenAI Quality Auditor, analyze the following UI Registry and its metadata descriptions.
    Registry:
    {registry_dump}
    
    Determine:
    1. Are these actions logical for a local AI assistant?
    2. Are the descriptions clear enough for an automated monkey?
    3. Identify any potentially 'dead' paths or missing critical controls.
    
    Provide a concise audit report.
    """
    
    print("🚀 AI is auditing the UI Registry...")
    full_response = ""
    async for chunk in backend.send_message_async(prompt):
        full_response += chunk
        print(chunk, end="", flush=True)
    print("\n\n✅ Audit Complete.")
    return "error" not in full_response.lower()

async def run_diagnostics(monkey_mode=False):
    """Run diagnostics."""
    print("\n" + "="*50)
    print("      ZENAI LIVE DIAGNOSTICS & SYSTEM CHECK")
    print("="*50 + "\n")
    
    # 1. Check Infrastructure
    infra_healthy = True
    infra_healthy &= await check_service("Engine API", f"http://{config.host}:{config.llm_port}/health")
    infra_healthy &= await check_service("Hub API", f"http://{config.host}:{config.mgmt_port}/models/available")
    infra_healthy &= await check_service("UI Server", f"http://{config.host}:8080")
    
    if not infra_healthy:
        print("\n😱 SYSTEM UNHEALTHY: Some core services are offline.")
        print("Please ensure 'python start_llm.py' and 'python zena.py' are running.")
    
    # 2. Test LLM Generation
    print("\n" + "-"*50)
    print("🧪 TESTING LLM GENERATION (Multi-Prompt Injection)")
    print("-"*50)
    
    backend = AsyncZenAIBackend()
    
    test_prompts = [
        {"name": "Simple Greeting", "prompt": "Say only 'HELLO'"},
        {"name": "Internal Knowledge", "prompt": "What documents are in the help system? (Tests RAG)"},
        {"name": "Swarm Analysis", "prompt": "What are the benefits of local LLMs? (Tests Engine)"}
    ]
    
    all_passed = True
    try:
        async with backend:
            for test in test_prompts:
                print(f"\n🚀 Testing: {test['name']}")
                print(f"Prompt : \"{test['prompt']}\"")
                print("Response: ", end="", flush=True)
                
                full_text = ""
                start = time.time()
                
                async for chunk in backend.send_message_async(test['prompt']):
                    full_text += chunk
                    print(chunk, end="", flush=True)
                
                duration = time.time() - start
                print(f"\n(Received {len(full_text)} chars in {duration:.2f}s)")
                
                if len(full_text) > 2:
                    print(f"✅ {test['name']}: PASS")
                else:
                    print(f"❌ {test['name']}: FAIL (Empty or too short)")
                    all_passed = False
                    
    except Exception as e:
        print(f"\n❌ GENERATION ERROR: {e}")
        all_passed = False

    # 3. Optional Monkey Mode
    if monkey_mode:
        all_passed &= await run_monkey_test(backend, iterations=3)
        all_passed &= await run_ui_chaos_test(backend, iterations=5)
        all_passed &= await run_semantic_ui_audit(backend)

    print("\n" + "="*50)
    if infra_healthy and all_passed:
        print("🎉 SYSTEM READY: All live tests passed!")
    else:
        print("🛠️ ACTION REQUIRED: System is alive but responses are failing.")
    print("="*50 + "\n")

if __name__ == "__main__":
    monkey = "--monkey" in sys.argv
    asyncio.run(run_diagnostics(monkey_mode=monkey))
