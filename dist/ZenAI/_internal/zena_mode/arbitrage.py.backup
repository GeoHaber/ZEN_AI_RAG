import asyncio
import httpx
import json
import logging
import time
from typing import List, AsyncGenerator, Dict
from config_system import config, EMOJI

logger = logging.getLogger(__name__)

class SwarmArbitrator:
    """
    Manages parallel LLM queries and implements arbitrage logic 
    to correct hallucinations and improve response quality.
    """
    
    def __init__(self, ports: List[int] = None):
        # Default scan range (8001 main, 8005-8012 experts)
        self.scan_ports = [8001] + list(range(8005, 8013))
        self.ports = []
        self.endpoints = []
        
        if ports:
            self.ports = ports
            self.endpoints = [f"http://127.0.0.1:{p}/v1/chat/completions" for p in ports]
        else:
            self.discover_swarm()

    def discover_swarm(self):
        """Synchronous heartbeat check to find live experts."""
        self.ports = []
        
        # If swarm is globally disabled in config, only use the main model (8001)
        if not config.SWARM_ENABLED:
            self.ports = [8001]
            self.endpoints = [f"http://127.0.0.1:8001/v1/chat/completions"]
            logger.debug("[Arbitrator] Swarm disabled in config. Using 8001 only.")
            return

        import requests
        # Muffled discovery logs for "Quiet Mode"
        for p in self.scan_ports:
            try:
                # Use a larger timeout for discovery to avoid skips on busy machines
                resp = requests.get(f"http://127.0.0.1:{p}/health", timeout=1.0)
                if resp.status_code in [200, 503]: # 503 means UP but loading
                    self.ports.append(p)
            except Exception:
                pass
        
        # Limit to SWARM_SIZE if specified
        if config.SWARM_SIZE > 0 and len(self.ports) > config.SWARM_SIZE:
             # Keep first port (usually 8001) and then top N-1 experts
             self.ports = [self.ports[0]] + self.ports[1:config.SWARM_SIZE]

        self.endpoints = [f"http://127.0.0.1:{p}/v1/chat/completions" for p in self.ports]
        logger.debug(f"[Arbitrator] Live Swarm discovered on ports: {self.ports}")

    async def _query_model(self, client: httpx.AsyncClient, endpoint: str, messages: List[Dict]) -> Dict:
        """Query a single model and return full text + timing + model name."""
        start = time.time()
        try:
            payload = {
                "messages": messages,
                "stream": False,
                "temperature": 0.7,
                "max_tokens": 512
            }
            response = await client.post(endpoint, json=payload, timeout=60.0)
            duration = time.time() - start
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content'].strip()
                model_name = data.get('model', 'Unknown-Model')
                return {"content": content, "time": duration, "model": model_name}
            return {"content": f"Error: {response.status_code}", "time": duration, "model": "N/A"}
        except Exception as e:
            return {"content": f"Connect Error: {e}", "time": time.time() - start, "model": "N/A"}

    def _calculate_consensus_simple(self, responses: List[str]) -> float:
        """Calculate a rough agreement score (0.0 to 1.0) using word set overlap."""
        if len(responses) < 2: return 1.0
        
        sets = [set(r.lower().split()) for r in responses]
        if not all(sets): return 0.0
        
        # Intersection over Union for all sets
        common = set.intersection(*sets)
        union = set.union(*sets)
        
        return len(common) / len(union) if union else 0.0

    async def get_cot_response(self, text: str, system_prompt: str, verbose: bool = False) -> AsyncGenerator[str, None]:
        """
        Memory-First CoT Flow with Structured Terminal Tracing.
        """
        # --- TERMINAL TRACE: QUESTION ---
        print("\n" + "="*80)
        print(f"      🔍 SWARM INQUIRY: {text[:150]}...")
        print("="*80)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        
        yield f"{EMOJI['loading']} **Thinking...** (Swarm size: {len(self.endpoints)})\n\n"
        
        async with httpx.AsyncClient() as client:
            # 1. Parallel Execute (or Serial reflection if N=1)
            raw_results = []
            if len(self.endpoints) == 1:
                print(f"[REASONING] Mode: Single-Model Reflection Loop")
                # Phase A: Initial Thought
                r1 = await self._query_model(client, self.endpoints[0], messages)
                print(f"  > Initial Logic ({r1['model']}): {r1['content'][:150]}...")
                
                # Phase B: Hidden Critique
                critique_msg = messages + [
                    {"role": "assistant", "content": r1['content']},
                    {"role": "user", "content": "Critique your previous answer for logic, accuracy, and completeness. Then provide a final corrected version."}
                ]
                r2 = await self._query_model(client, self.endpoints[0], critique_msg)
                print(f"  > Self-Correction ({r2['model']}): {r2['content'][:150]}...")
                raw_results = [r1, r2]
            else:
                print(f"[REASONING] Querying {len(self.endpoints)} Knowledge Experts...")
                tasks = [self._query_model(client, ep, messages) for ep in self.endpoints]
                raw_results = await asyncio.gather(*tasks)
                for i, r in enumerate(raw_results):
                    agent_name = r.get('model', f"Expert {i+1}")
                    print(f"  > Analysis [{agent_name}] ({r['time']:.2f}s): {r['content'][:300]}...")
            
            responses = [r['content'] for r in raw_results]
            timings = [r['time'] for r in raw_results]
            model_names = [r.get('model', 'Unknown') for r in raw_results]
            
            # 2. Consensus Score
            agreement = self._calculate_consensus_simple(responses)
            confidence = "High" if agreement > 0.6 else "Medium" if agreement > 0.3 else "Low"

            # 3. YIELD Intermediate Thoughts ONLY if Verbose
            if verbose:
                for i, resp_data in enumerate(raw_results):
                    expert_label = "Reflection" if len(self.endpoints) == 1 and i == 0 else f"Expert {i+1}"
                    if len(self.endpoints) == 1 and i == 1: expert_label = "Self-Correction"
                    yield f"--- **{expert_label}** ({resp_data['time']:.2f}s) ---\n{resp_data['content'][:300]}...\n\n"
                yield f"⚖️ **Arbitrage Hub**: Synthesizing ({confidence} Consensus)...\n\n"

            # 4. Arbitrage Logic (Synthesis in Memory)
            referee_endpoint = self.endpoints[0] if self.endpoints else None
            if not referee_endpoint:
                yield "Error: No expert models available."
                return

            # --- TERMINAL TRACE: DECISION ---
            print("\n[DECISION MATRIX]")
            print(f"  PROCESSOR: Master Arbitrator (Active)")
            print(f"  START TIME: {time.strftime('%H:%M:%S')}") # Explicit start time
            print(f"  RATIONALE: {confidence} Consensus ({agreement:.1%}) found across internal memory buffers.")
            print(f"  STRATEGY: Harmonizing {len(responses)} thoughts into a unified result.")
            print("  STATUS: Processing final synthesis...")

            arbitrage_prompt = f"""
You are the **Swarm Referee**. I have received {len(responses)} expert responses.
CONSENSUS: {confidence} ({agreement:.1%})

USER QUERY: {text[:500]}

EXPERT CONTRIBUTIONS:
{chr(10).join([f"--- Expert {i+1} ---\n{r}\n" for i, r in enumerate(responses)])}

INSTRUCTIONS:
- Harmonize the insights and resolve any conflicts.
- Provide a clean, unified, and authoritative final answer.
- Append a 'Summary of Reasoning' if the experts had major disagreements.

FINAL VERIFIED RESPONSE:
"""
            referee_messages = [
                {"role": "system", "content": "Resolve conflicts and provide the final verified truth."},
                {"role": "user", "content": arbitrage_prompt}
            ]
            
            payload = {
                "messages": referee_messages,
                "stream": True,
                "temperature": 0.2, 
                "max_tokens": -1
            }
            
            print("\n" + "-"*40)
            print("🚀 FINAL RESPONSE STREAMING:")
            print("-"*40)
            
            full_referee_text = ""
            start_ref = time.time()
            try:
                async with client.stream('POST', referee_endpoint, json=payload) as response:
                    async for line in response.aiter_lines():
                        if line.startswith('data: '):
                            json_str = line[6:]
                            if json_str.strip() == '[DONE]': break
                            try:
                                data = json.loads(json_str)
                                content = data['choices'][0]['delta'].get('content', '')
                                if content: 
                                    full_referee_text += content
                                    # Print to terminal too!
                                    print(content, end="", flush=True)
                                    yield content
                            except: pass
            except Exception as e:
                yield f"\n\n{EMOJI['error']} Arbitration failed: {e}"
            
            dur_ref = time.time() - start_ref
            print("\n" + "-"*40)
            print(f"✅ COMPLETED in {dur_ref:.1f}s")
            print("="*80 + "\n")
            
            # Final Metrics Badge
            yield f"\n\n---\n📊 **Swarm Metrics**: Consensus **{agreement:.1%}** | Synthesis **{dur_ref:.1f}s**"


def get_arbitrator():
    return SwarmArbitrator()
