import asyncio
import httpx
import json
import logging
from typing import List, AsyncGenerator, Dict
from config_system import config, EMOJI

logger = logging.getLogger(__name__)

class SwarmArbitrator:
    """
    Manages parallel LLM queries and implements arbitrage logic 
    to correct hallucinations and improve response quality.
    """
    
    def __init__(self, ports: List[int] = [8001, 8005, 8006]):
        self.ports = ports
        self.endpoints = [f"http://127.0.0.1:{p}/v1/chat/completions" for p in ports]
        logger.info(f"[Arbitrator] Swarm initialized on ports: {self.ports}")

    async def _query_model(self, client: httpx.AsyncClient, endpoint: str, messages: List[Dict]) -> str:
        """Query a single model and return full text."""
        try:
            payload = {
                "messages": messages,
                "stream": False, # Arbitrators need full text for comparison
                "temperature": 0.7,
                "max_tokens": 512
            }
            response = await client.post(endpoint, json=payload, timeout=60.0)
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content'].strip()
            return f"Error: Server returned {response.status_code}"
        except Exception as e:
            return f"Connect Error: {e}"

    async def get_cot_response(self, text: str, system_prompt: str) -> AsyncGenerator[str, None]:
        """
        Main CoT Flow:
        1. Query all experts in parallel.
        2. Present individual thoughts (Expert 1, 2, 3).
        3. Arbitrate: Ask Master to resolve differences.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        
        yield f"{EMOJI['loading']} **Expert Swarm Activated.** Querying {len(self.endpoints)} models in parallel...\n\n"
        
        async with httpx.AsyncClient() as client:
            # 1. Parallel Execute
            tasks = [self._query_model(client, ep, messages) for ep in self.endpoints]
            responses = await asyncio.gather(*tasks)
            
            # 2. Show individual thoughts (briefly)
            for i, resp in enumerate(responses):
                expert_label = "Master Expert" if i == 0 else f"Expert {i+1}"
                yield f"--- **{expert_label} Analysis** ---\n{resp[:300]}...\n\n"

            # 3. Arbitrage Logic
            yield "⚖️ **Arbitrage in Progress**: Resolving hallucinations and finalizing answer...\n\n"
            
            arbitrage_prompt = f"""
I have received {len(responses)} different answers to the question: "{text}"

ANSWERS RECEIVED:
{chr(10).join([f"Expert {i+1}: {r}" for i, r in enumerate(responses)])}

TASK:
1. Examine all answers for logic, facts, and consistency.
2. Identify any contradictions or hallucinations.
3. Provide the FINAL, absolute best answer based on the consensus of the most logical points.

FINAL VERIFIED ANSWER:
"""
            # Use Master (Port 8001) as the Referee
            referee_messages = [
                {"role": "system", "content": "You are the Arbitrator. Your job is to verify logic and synthesize the best response from a swarm of models."},
                {"role": "user", "content": arbitrage_prompt}
            ]
            
            # Stream the final referee result
            payload = {
                "messages": referee_messages,
                "stream": True,
                "temperature": 0.3 # Low temp for arbitration
            }
            
            try:
                async with client.stream('POST', self.endpoints[0], json=payload) as response:
                    async for line in response.aiter_lines():
                        if line.startswith('data: '):
                            json_str = line[6:]
                            if json_str.strip() == '[DONE]': break
                            try:
                                data = json.loads(json_str)
                                content = data['choices'][0]['delta'].get('content', '')
                                if content: yield content
                            except: pass
            except Exception as e:
                yield f"\n\n{EMOJI['error']} Arbitration failed: {e}"

def get_arbitrator():
    return SwarmArbitrator()
