"""
Enhanced SwarmArbitrator with research-backed improvements (2026).

This module provides backward-compatible API while using the new
swarm_arbitrator.py backend with all 15 improvements implemented.
"""
import asyncio
import httpx
import json
import logging
import time
from typing import List, AsyncGenerator, Dict
from config_system import config, EMOJI

# Import enhanced SwarmArbitrator and CostTracker
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from swarm_arbitrator import SwarmArbitrator as EnhancedSwarmArbitrator, CostTracker

logger = logging.getLogger(__name__)


class SwarmArbitrator:
    """
    Manages parallel LLM queries with enhanced arbitrage logic.

    Backward-compatible wrapper around EnhancedSwarmArbitrator that
    maintains the original get_cot_response() API while adding:
    - Async discovery (httpx)
    - Per-expert timeouts
    - Confidence extraction
    - Semantic consensus
    - Performance tracking
    - Protocol routing
    - Adaptive rounds
    """

    def __init__(self, ports: List[int] = None):
        # Create enhanced arbitrator with config from config_system
        arbitrator_config = {
            "enabled": config.SWARM_ENABLED,
            "max_swarm_size": config.SWARM_SIZE if config.SWARM_SIZE > 0 else 8,
            "async_discovery": True,  # IMPROVEMENT #1
            "timeout_per_expert": 60.0,  # IMPROVEMENT #2
            "confidence_extraction": True,  # IMPROVEMENT #3
            "semantic_consensus": True,  # IMPROVEMENT #4
            "performance_tracking": True,  # IMPROVEMENT #5
            "protocol_routing": True,  # IMPROVEMENT #6
            "adaptive_rounds": True,  # IMPROVEMENT #7
        }

        self._enhanced = EnhancedSwarmArbitrator(config=arbitrator_config)

        # Default scan range (8001 main, 8005-8012 experts)
        self.scan_ports = [8001] + list(range(8005, 8013))
        self.ports = []
        self.endpoints = []

        if ports:
            self.ports = ports
            self.endpoints = [f"http://127.0.0.1:{p}/v1/chat/completions" for p in ports]
            self._enhanced.ports = ports
            self._enhanced.endpoints = self.endpoints
        else:
            self.discover_swarm()

    def discover_swarm(self):
        """Synchronous wrapper around async discovery for backward compatibility."""
        if not config.SWARM_ENABLED:
            self.ports = [8001]
            self.endpoints = [f"http://127.0.0.1:8001/v1/chat/completions"]
            self._enhanced.ports = self.ports
            self._enhanced.endpoints = self.endpoints
            logger.debug("[Arbitrator] Swarm disabled in config. Using 8001 only.")
            return

        # Run async discovery in sync context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in async context - create task
                future = asyncio.ensure_future(self._enhanced.discover_swarm())
                # Wait briefly for discovery
                time.sleep(0.1)
            else:
                # Not in async context - run sync
                loop.run_until_complete(self._enhanced.discover_swarm())
        except RuntimeError:
            # No event loop - create one
            asyncio.run(self._enhanced.discover_swarm())

        # Sync state
        self.ports = self._enhanced.ports
        self.endpoints = self._enhanced.endpoints
        logger.debug(f"[Arbitrator] Enhanced discovery found ports: {self.ports}")

    async def _query_model(self, client: httpx.AsyncClient, endpoint: str, messages: List[Dict]) -> Dict:
        """Query a single model with timeout handling (IMPROVEMENT #2)."""
        return await self._enhanced._query_model_with_timeout(
            client, endpoint, messages, timeout=60.0
        )

    def _calculate_consensus_simple(self, responses: List[str]) -> float:
        """
        Backward-compatible consensus using enhanced semantic method.
        Automatically uses semantic if available, falls back to word-set.
        """
        # Import ConsensusMethod enum
        from swarm_arbitrator import ConsensusMethod
        # Use hybrid method for best results (IMPROVEMENT #4)
        return self._enhanced._calculate_consensus(responses, method=ConsensusMethod.HYBRID)

    async def _query_external_agent(self, model: str, messages: List[Dict]) -> Dict:
        """Bridge to external LLM APIs (delegated to enhanced arbitrator)."""
        return await self._enhanced._query_external_agent(model, messages)

    async def get_cot_response(self, text: str, system_prompt: str, verbose: bool = False) -> AsyncGenerator[str, None]:
        """
        Memory-First CoT Flow with Enhanced Consensus & Performance Tracking.

        Maintains original API while adding:
        - Confidence extraction from responses
        - Semantic consensus calculation
        - Agent performance tracking
        - Adaptive round selection
        """
        # --- TERMINAL TRACE: QUESTION ---
        print("\n" + "="*80)
        print(f"      🔍 ENHANCED SWARM INQUIRY: {text[:150]}...")
        print("="*80)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]

        yield f"{EMOJI['loading']} **Thinking...** (Enhanced Swarm size: {len(self.endpoints)})\n\n"

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
                raw_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Filter out errors (IMPROVEMENT #8: Partial failure handling)
                valid_results = []
                for i, r in enumerate(raw_results):
                    if isinstance(r, Exception):
                        logger.warning(f"[Arbitrator] Expert {i+1} failed: {r}")
                        continue
                    if r.get('error'):
                        logger.warning(f"[Arbitrator] Expert {i+1} error: {r.get('content')}")
                        continue
                    valid_results.append(r)
                    agent_name = r.get('model', f"Expert {i+1}")
                    print(f"  > Analysis [{agent_name}] ({r['time']:.2f}s): {r['content'][:300]}...")

                if not valid_results:
                    yield f"\n\n{EMOJI['error']} All experts failed. Using fallback mode."
                    raw_results = valid_results
                    return

                raw_results = valid_results

            responses = [r['content'] for r in raw_results]
            timings = [r['time'] for r in raw_results]
            model_names = [r.get('model', 'Unknown') for r in raw_results]

            # 2. Enhanced Consensus Score (IMPROVEMENT #4: Semantic)
            agreement = self._calculate_consensus_simple(responses)

            # 3. Extract Confidence Scores (IMPROVEMENT #3)
            confidence_scores = [self._enhanced._extract_confidence(r) for r in responses]
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.7

            # Track performance (IMPROVEMENT #5)
            import hashlib
            query_hash = hashlib.md5(text.encode()).hexdigest()[:16]
            for i, (endpoint, response, confidence) in enumerate(zip(self.endpoints, responses, confidence_scores)):
                port = endpoint.split(':')[-1].split('/')[0]
                self._enhanced.performance_tracker.record_response(
                    agent_id=f"port_{port}",
                    task_type="general",  # Could be enhanced with task classification
                    query_hash=query_hash,
                    response_text=response,
                    was_selected=True,  # All responses contribute to final synthesis
                    consensus_score=agreement,
                    confidence=confidence,
                    response_time=timings[i]
                )

            confidence = "High" if agreement > 0.6 else "Medium" if agreement > 0.3 else "Low"

            # Show enhanced metrics
            print(f"[ENHANCED METRICS]")
            print(f"  Agreement: {agreement:.1%} (Semantic)")
            print(f"  Avg Confidence: {avg_confidence:.1%}")
            print(f"  Expert Confidences: {[f'{c:.1%}' for c in confidence_scores]}")

            # 3. YIELD Intermediate Thoughts ONLY if Verbose
            if verbose:
                for i, resp_data in enumerate(raw_results):
                    expert_label = "Reflection" if len(self.endpoints) == 1 and i == 0 else f"Expert {i+1}"
                    if len(self.endpoints) == 1 and i == 1: expert_label = "Self-Correction"
                    conf_badge = f"[{confidence_scores[i]:.0%}]" if i < len(confidence_scores) else ""
                    yield f"--- **{expert_label}** {conf_badge} ({resp_data['time']:.2f}s) ---\n{resp_data['content'][:300]}...\n\n"
                yield f"⚖️ **Enhanced Arbitrage Hub**: Synthesizing ({confidence} Consensus, {avg_confidence:.0%} Confidence)...\n\n"

            # 4. Adaptive Round Selection (IMPROVEMENT #7)
            skip_round_two = self._enhanced.should_do_round_two(agreement, confidence_scores)
            if not skip_round_two and agreement > 0.8:
                print(f"[OPTIMIZATION] Skipping Round 2: High agreement ({agreement:.1%})")

            # 5. Arbitrage Logic (Synthesis in Memory)
            referee_endpoint = self.endpoints[0] if self.endpoints else None
            if not referee_endpoint:
                yield "Error: No expert models available."
                return

            # --- TERMINAL TRACE: DECISION ---
            print("\n[DECISION MATRIX]")
            print(f"  PROCESSOR: Enhanced Master Arbitrator (Active)")
            print(f"  START TIME: {time.strftime('%H:%M:%S')}")
            print(f"  RATIONALE: {confidence} Consensus ({agreement:.1%}) with {avg_confidence:.0%} avg confidence")
            print(f"  STRATEGY: Harmonizing {len(responses)} thoughts into unified result.")
            print("  STATUS: Processing final synthesis...")

            arbitrage_prompt = f"""
You are the **Enhanced Swarm Referee**. I have received {len(responses)} expert responses with confidence tracking.

CONSENSUS: {confidence} ({agreement:.1%})
AVG CONFIDENCE: {avg_confidence:.0%}

USER QUERY: {text[:500]}

EXPERT CONTRIBUTIONS (with confidence):
{chr(10).join([f"--- Expert {i+1} [{confidence_scores[i]:.0%} confident] ---\n{r}\n" for i, r in enumerate(responses)])}

INSTRUCTIONS:
- Weight responses by confidence scores shown above
- Harmonize the insights and resolve any conflicts
- Provide a clean, unified, and authoritative final answer
- Append a 'Summary of Reasoning' if the experts had major disagreements

FINAL VERIFIED RESPONSE:
"""
            referee_messages = [
                {"role": "system", "content": "Resolve conflicts and provide the final verified truth. Weight higher-confidence responses more heavily."},
                {"role": "user", "content": arbitrage_prompt}
            ]

            payload = {
                "messages": referee_messages,
                "stream": True,
                "temperature": 0.2,
                "max_tokens": -1
            }

            print("\n" + "-"*40)
            print("🚀 ENHANCED FINAL RESPONSE STREAMING:")
            print("-"*40)

            full_referee_text = ""
            start_ref = time.time()
            try:
                async with client.stream('POST', referee_endpoint, json=payload, timeout=120.0) as response:
                    async for line in response.aiter_lines():
                        if line.startswith('data: '):
                            json_str = line[6:]
                            if json_str.strip() == '[DONE]': break
                            try:
                                data = json.loads(json_str)
                                content = data['choices'][0]['delta'].get('content', '')
                                if content:
                                    full_referee_text += content
                                    print(content, end="", flush=True)
                                    yield content
                            except: pass
            except Exception as e:
                yield f"\n\n{EMOJI['error']} Arbitration failed: {e}"

            dur_ref = time.time() - start_ref
            print("\n" + "-"*40)
            print(f"✅ COMPLETED in {dur_ref:.1f}s")
            print("="*80 + "\n")

            # Final Enhanced Metrics Badge
            yield f"\n\n---\n📊 **Enhanced Swarm Metrics**: Consensus **{agreement:.1%}** | Confidence **{avg_confidence:.0%}** | Synthesis **{dur_ref:.1f}s**"


def get_arbitrator():
    """Factory function to create SwarmArbitrator instance."""
    return SwarmArbitrator()
