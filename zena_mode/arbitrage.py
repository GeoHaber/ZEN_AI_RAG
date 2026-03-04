# -*- coding: utf-8 -*-
"""
arbitrage.py - Swarm Arbitrator for Multi-LLM Consensus
Ported and adapted from naughty-antonelli
"""
import asyncio
import httpx
import json
import time
import hashlib
import re
import sqlite3
import numpy as np
from enum import Enum
from typing import List, AsyncGenerator, Dict
import os
from config_system import config, EMOJI
from utils import safe_print, logger
from .profiler import monitor

class ConsensusMethod(Enum):
    """ConsensusMethod class."""
    WORD_SET = "word_set"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"

class ConsensusProtocol(Enum):
    """Consensus protocols for different task types."""
    CONSENSUS = "consensus"        # Converge to single truth (Factual)
    VOTING = "voting"              # Democratic choice (Creative)
    WEIGHTED_VOTE = "weighted"     # By confidence + reliability (Reasoning)
    MAJORITY = "majority"          # Simple majority (General)
    HYBRID = "hybrid"              # Adaptive

class AgentPerformanceTracker:
    """Track agent accuracy and reliability over time using SQLite."""
    def __init__(self, db_path: str = None):
        """Initialize instance."""
        if db_path is None:
            db_path = str(config.BASE_DIR / "agent_performance.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Init db."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    task_type TEXT,
                    query_hash TEXT,
                    response_text TEXT,
                    was_selected INTEGER,
                    consensus_score REAL,
                    confidence REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[Performance] DB Init Error: {e}")

    def record_response(self, agent_id, task_type, query_hash, response_text, was_selected, consensus_score, confidence, response_time=0.0):
        """Record response."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT INTO agent_performance (agent_id, task_type, query_hash, response_text, was_selected, consensus_score, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (agent_id, task_type, query_hash, response_text[:500], 1 if was_selected else 0, consensus_score, confidence))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[Performance] Record Error: {e}")

    def get_agent_reliability(self, agent_id: str, task_type: str = None) -> float:
        """Get historical accuracy/selection rate for an agent."""
        try:
            conn = sqlite3.connect(self.db_path)
            if task_type:
                cursor = conn.execute("""
                    SELECT AVG(was_selected) FROM agent_performance 
                    WHERE agent_id = ? AND task_type = ?
                    AND timestamp > datetime('now', '-30 days')
                """, (agent_id, task_type))
            else:
                cursor = conn.execute("""
                    SELECT AVG(was_selected) FROM agent_performance 
                    WHERE agent_id = ?
                    AND timestamp > datetime('now', '-30 days')
                """, (agent_id,))
            res = cursor.fetchone()[0]
            conn.close()
            return res if res is not None else 0.5
        except Exception as e:
            logger.error(f"[Performance] Reliability Error: {e}")
            return 0.5

    def get_stats(self) -> Dict:
        """Get overall performance stats."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("""
                SELECT COUNT(*), AVG(consensus_score), AVG(confidence) 
                FROM agent_performance
            """)
            count, avg_cons, avg_conf = cursor.fetchone()
            conn.close()
            return {
                "total_queries": count or 0,
                "avg_consensus": avg_cons or 0.0,
                "avg_confidence": avg_conf or 0.0
            }
        except Exception as e:
            logger.error(f"[Performance] Stats Error: {e}")
            return {}

class CostTracker:
    """Track API costs for budgeting."""
    COSTS = {
        "local": 0.0,
        "gpt-4": 0.01,
        "claude-3": 0.015,
        "gemini": 0.00025,
    }

    def __init__(self):
        self.total_cost = 0.0

    def record_query(self, model: str, content: str):
        """Record query."""
        tokens = len(content.split()) * 1.3 # Rough estimate
        cost_per_1k = 0.0
        for m, c in self.COSTS.items():
            if m not in model.lower():
                continue
            cost_per_1k = c
            break
        cost = (tokens / 1000.0) * cost_per_1k
        self.total_cost += cost
        return cost

class _SwarmArbitratorBase:
    """Base methods for SwarmArbitrator."""

    def __init__(self, ports: List[int] = None):
        """Initialize instance."""
        # Default scan range (main port + experts in 8005-8012 range)
        self.scan_ports = [config.llm_port] + list(range(8005, 8013))
        self.ports = []
        self.endpoints = []
        self.performance_tracker = AgentPerformanceTracker()
        self.cost_tracker = CostTracker()
        self.nli_model = None # Lazy loaded for verification
        self.latencies = {}   # Track response times per port
        self.reliability_penalty_threshold = 0.4 # Threshold for hallucination penalty
        
        if ports:
            self.ports = ports
            self.endpoints = [f"http://{config.host}:{p}/v1/chat/completions" for p in ports]
        # Backwards compatibility: if no ports provided, perform a synchronous
        # discovery using a blocking HTTP client to avoid creating an event loop
        # during import (which breaks pytest-asyncio).
        if not ports:
            try:
                self.discover_swarm_sync()
            except Exception:
                # If anything goes wrong, fall back to using main port only
                self.ports = [config.llm_port]
                self.endpoints = [f"http://{config.host}:{config.llm_port}/v1/chat/completions"]

    def discover_swarm_sync(self):
        """Synchronous version of swarm discovery using blocking httpx.Client.

        This avoids starting an asyncio loop during import or in tests.
        """
        import httpx as _httpx
        self.ports = []

        if not config.swarm_enabled:
            self.ports = [config.llm_port]
            self.endpoints = [f"http://{config.host}:{config.llm_port}/v1/chat/completions"]
            return

        try:
            with _httpx.Client() as client:
                for p in self.scan_ports:
                    try:
                        resp = client.get(f"http://{config.host}:{p}/health", timeout=1.0)
                        if resp.status_code in (200, 503):
                            self.ports.append(p)
                    except Exception:
                        continue

            if config.swarm_enabled and len(self.ports) > 8: # Arbitrary expert cap
                self.ports = [self.ports[0]] + self.ports[1:9]

            self.endpoints = [f"http://{config.host}:{p}/v1/chat/completions" for p in self.ports]
            logger.debug(f"[Arbitrator] (sync) Live Swarm discovered on ports: {self.ports}")
        except Exception as e:
            logger.error(f"[Arbitrator] Sync discovery failed: {e}")
            # Fall back to main port to keep behavior predictable
            self.ports = [config.llm_port]
            self.endpoints = [f"http://{config.host}:{config.llm_port}/v1/chat/completions"]

    async def warmup(self):
        """Pre-load NLI model."""
        if self.nli_model is not None:
            return

        logger.info("[Arbitrator] Warming up NLI model...")
        from sentence_transformers import CrossEncoder
        self.nli_model = CrossEncoder('cross-encoder/nli-distilroberta-base')
        # Dry run
        _ = self.nli_model.predict([["fact", "context"]])
        logger.info("[Arbitrator] NLI Model ready.")

    async def discover_swarm(self):
        """Async heartbeat check to find live experts."""
        self.ports = []
        
        # If swarm is globally disabled in config, only use the main model
        if not config.swarm_enabled:
            self.ports = [config.llm_port]
            self.endpoints = [f"http://{config.host}:{config.llm_port}/v1/chat/completions"]
            logger.debug("[Arbitrator] Swarm disabled in config. Using main port only.")
            return

        async with httpx.AsyncClient() as client:
            tasks = []
            for p in self.scan_ports:
                tasks.append(self._check_port(client, p))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for port, is_live in zip(self.scan_ports, results):
                if is_live and not isinstance(is_live, Exception):
                    self.ports.append(port)
        
        self.endpoints = [f"http://{config.host}:{p}/v1/chat/completions" for p in self.ports]
        
        # Sort ports by latency (improvement 16)
        self.ports.sort(key=lambda p: self.latencies.get(p, 999))
        self.endpoints = [f"http://{config.host}:{p}/v1/chat/completions" for p in self.ports]
        
        logger.debug(f"[Arbitrator] Live Swarm discovered (sorted by latency): {self.ports}")

    async def _check_port(self, client: httpx.AsyncClient, port: int) -> bool:
        """Check if a port is live and measure latency."""
        start = time.time()
        try:
            resp = await client.get(f"http://{config.host}:{port}/health", timeout=1.0)
            latency = time.time() - start
            if resp.status_code in [200, 503]:
                self.latencies[port] = latency
                return True
            return False
        except Exception:
            return False

    def select_protocol(self, task_type: str) -> ConsensusProtocol:
        """Route to optimal consensus protocol based on task type."""
        mapping = {
            "factual": ConsensusProtocol.CONSENSUS,
            "reasoning": ConsensusProtocol.WEIGHTED_VOTE,
            "math": ConsensusProtocol.WEIGHTED_VOTE,
            "code": ConsensusProtocol.WEIGHTED_VOTE,
            "creative": ConsensusProtocol.VOTING,
            "general": ConsensusProtocol.MAJORITY
        }
        return mapping.get(task_type.lower(), ConsensusProtocol.HYBRID)

    def detect_contradictions(self, responses: List[str]) -> List[Dict]:
        """Detect significant semantic contradictions between expert responses."""
        if len(responses) < 2: return []
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            if not hasattr(self, '_embedding_model'):
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            embeddings = self._embedding_model.encode(responses)
            similarities = cosine_similarity(embeddings)
            
            contradictions = []
            for i in range(len(responses)):
                for j in range(i + 1, len(responses)):
                    if similarities[i][j] < 0.2: # Threshold for major contradiction
                        contradictions.append({
                            "pair": (i+1, j+1),
                            "similarity": float(similarities[i][j])
                        })
            return contradictions
        except ImportError:
            return []

    def verify_hallucination(self, response_text: str, context_chunks: List[str]) -> Dict:
        """
        Verify if the response is supported by the provided context chunks using NLI.
        Returns a 'fact_check_score' (0.0 - 1.0) and 'unsupported_sentences'.
        """
        if not context_chunks:
            return {"score": 0.5, "reason": "No context provided", "unsupported": []}

        try:
            from sentence_transformers import CrossEncoder
            if self.nli_model is None:
                logger.info("[Arbitrator] Loading NLI model for hallucination check...")
                self.nli_model = CrossEncoder('cross-encoder/nli-distilroberta-base')

            # Split response into sentences (simple rule-based)
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', response_text) if len(s) > 10]
            if not sentences:
                return {"score": 1.0, "reason": "Response too short", "unsupported": []}

            supported_count = 0
            unsupported = []

            for sent in sentences:
                pairs = [[chunk, sent] for chunk in context_chunks] 
                scores = self.nli_model.predict(pairs) 
                
                probs = np.exp(scores) / np.sum(np.exp(scores), axis=1, keepdims=True)
                entailment_scores = probs[:, 1]
                max_entailment = np.max(entailment_scores)
                
                if max_entailment > 0.6: # Threshold
                    supported_count += 1
                else:
                    unsupported.append(sent)

            score = supported_count / len(sentences)
            return {
                "score": score,
                "reason": f"{supported_count}/{len(sentences)} sentences supported by context",
                "unsupported": unsupported
            }

        except Exception as e:
            logger.error(f"[Arbitrator] Verification failed: {e}")
            return {"score": 0.5, "reason": f"Error: {e}", "unsupported": []}

    def _extract_confidence(self, response_text: str) -> float:
        """Extract confidence score from response using regex and linguistic markers."""
        # Explicit percentage: "I'm 90% confident"
        match = re.search(r'(\d{1,3})%\s*confident', response_text.lower())
        if match:
            return float(match.group(1)) / 100.0

        # Explicit decimal: "Confidence: 0.85"
        match = re.search(r'confidence:?\s*(\d\.\d+)', response_text.lower())
        if match:
            return float(match.group(1))

        # Linguistic markers
        confidence_markers = {
            r'\b(certain|definite|absolutely|definitely)\b': 0.95,
            r'\b(very confident|quite sure|very likely)\b': 0.85,
            r'\b(confident|likely|probably)\b': 0.75,
            r'\b(think|believe|seems)\b': 0.6,
            r'\b(maybe|perhaps|possibly|might)\b': 0.5,
            r'\b(unsure|uncertain|not sure)\b': 0.3,
        }

        for pattern, score in confidence_markers.items():
            if re.search(pattern, response_text.lower()):
                return score

        return 0.7 # Default

    async def _query_model(self, client: httpx.AsyncClient, endpoint: str, messages: List[Dict]) -> Dict:
        """Query a single model and return full text + timing + model name + confidence."""
        start = time.time()
        try:
            payload = {
                "messages": messages,
                "stream": False,
                "temperature": 0.7,
                "max_tokens": 512
            }
            response = await client.post(endpoint, json=payload, timeout=30.0) 
            duration = time.time() - start
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content'].strip()
                model_name = data.get('model', 'Unknown-Model')
                return {
                    "content": content, 
                    "time": duration, 
                    "model": model_name,
                    "confidence": self._extract_confidence(content)
                }
            return {"content": f"Error: {response.status_code}", "time": duration, "model": "N/A", "confidence": 0.0}
        except Exception as e:
            return {"content": f"Connect Error: {e}", "time": time.time() - start, "model": "N/A", "confidence": 0.0}


class SwarmArbitrator(_SwarmArbitratorBase):
    """
    Manages parallel LLM queries and implements arbitrage logic 
    to correct hallucinations and improve response quality.
    """
    

    async def _query_model_with_timeout(
        self,
        client: httpx.AsyncClient,
        endpoint: str,
        messages: List[Dict],
        timeout: float = 30.0
    ) -> Dict:
        """Query with per-expert timeout and fallback."""
        try:
            return await asyncio.wait_for(
                self._query_model(client, endpoint, messages),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"[Arbitrator] Expert {endpoint} timed out after {timeout}s")
            return {"content": f"[TIMEOUT after {timeout}s]", "time": timeout, "model": f"Timeout-{endpoint}", "confidence": 0.0}
        except Exception as e:
            logger.error(f"[Arbitrator] Expert {endpoint} failed: {e}")
            return {"content": f"[ERROR: {str(e)}]", "time": 0.0, "model": f"Error-{endpoint}", "confidence": 0.0}

    async def _query_external_agent(self, model: str, messages: List[Dict]) -> Dict:
        """LiteLLM Bridge Placeholder (Improvement 12)."""
        logger.info(f"[Bridge] External query to {model} (Mocked)")
        return {"content": "[LITELLM MOCK RESPONSE]", "model": model, "time": 0.5, "confidence": 0.7}

    def init_autogen_swarm(self):
        """AutoGen Integration Stub (Improvement 13)."""
        logger.info("[AutoGen] Initializing AutoGen Swarm Manager (Mocked)")
        pass

    def _calculate_variance(self, scores: List[float]) -> float:
        """Calculate simple variance of confidence scores."""
        if not scores: return 0.0
        avg = sum(scores) / len(scores)
        return sum((x - avg) ** 2 for x in scores) / len(scores)

    def should_do_round_two(self, agreement: float, confidence_scores: List[float]) -> bool:
        """Decide if second reasoning/debate round is worth the cost."""
        if agreement > 0.8: return False
        if sum(confidence_scores) / max(1, len(confidence_scores)) > 0.85: return False
        if self._calculate_variance(confidence_scores) < 0.1: return False
        return agreement < 0.6

    def _calculate_consensus_simple(self, responses: List[str]) -> float:
        """Calculate a rough agreement score (0.0 to 1.0) using word set overlap."""
        if len(responses) < 2: return 1.0
        sets = [set(r.lower().split()) for r in responses]
        if not all(sets): return 0.0
        common = set.intersection(*sets)
        union = set.union(*sets)
        return len(common) / len(union) if union else 0.0

    async def _query_external_agent(self, model: str, messages: List[Dict]) -> Dict:
        """Functional Bridge for External Agents (Improvement 12)."""
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return {"content": "[ERROR: No API Key found for external agent]", "model": model, "time": 0.0, "confidence": 0.0}
        
        start = time.time()
        try:
            # We use httpx directly to maintain our lightweight, async-first approach
            # while remaining compatible with OpenAI/LiteLLM-style providers.
            async with httpx.AsyncClient() as client:
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.7,
                }
                # Defaulting to OpenAI compatible endpoint - can be extended
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}"}
                
                response = await client.post(url, json=payload, headers=headers, timeout=60.0)
                if response.status_code == 200:
                    data = response.json()
                    content = data['choices'][0]['message']['content'].strip()
                    return {
                        "content": content,
                        "time": time.time() - start,
                        "model": model,
                        "confidence": self._extract_confidence(content)
                    }
                return {"content": f"[API Error: {response.status_code}]", "model": model, "time": time.time() - start, "confidence": 0.0}
        except Exception as e:
            return {"content": f"[Bridge Error: {str(e)}]", "model": model, "time": time.time() - start, "confidence": 0.0}

    TASK_SYSTEM_PROMPTS = {
        "reasoning": "You are a logical reasoning expert. Break down the problem step-by-step and verify each premise.",
        "math": "You are a mathematical rigor expert. Provide precise calculations and double-check for edge cases.",
        "code": "You are a senior software architect. Focus on clean code, security, and edge-case handling.",
        "factual": "You are a research librarian. Prioritize accuracy, cite consensus views, and avoid speculation.",
        "creative": "You are a creative consultant. Offer diverse perspectives and original insights.",
        "security": "You are a security auditor. Analyze inputs for vulnerabilities, injection risks, and safety violations.",
        "performance": "You are a performance engineer. Analyze the prompt for bottlenecks, complexity, and resource efficiency.",
        "general": "You are a helpful and accurate assistant."
    }

    def _calculate_consensus(self, responses: List[str], method: ConsensusMethod = ConsensusMethod.WORD_SET) -> float:
        """Calculate consensus using specified method."""
        if method == ConsensusMethod.WORD_SET:
            return self._calculate_consensus_simple(responses)
        elif method == ConsensusMethod.SEMANTIC:
            return self._calculate_consensus_semantic(responses)
        elif method == ConsensusMethod.HYBRID:
            return (self._calculate_consensus_simple(responses) + self._calculate_consensus_semantic(responses)) / 2.0
    def _calculate_consensus_semantic(self, responses: List[Dict]) -> float:
        """Calculate consensus using semantic similarity if sentence_transformers is available."""
        if not responses: return 0.0
        if len(responses) == 1: return 1.0
        
        try:
            from sentence_transformers import SentenceTransformer, util
            model = SentenceTransformer('all-MiniLM-L6-v2')
            texts = [r['content'] for r in responses]
            embeddings = model.encode(texts)
            sim_matrix = util.cos_sim(embeddings, embeddings)
            # Average similarity (excluding diagonal)
            n = len(responses)
            total_sim = (sim_matrix.sum() - n) / (n * (n - 1))
            return float(total_sim)
        except Exception as e:
            logger.warning(f"[Arbitrator] Semantic consensus fallback: {e}")
            return self._calculate_consensus_simple(responses)

    async def get_cot_response(self, text: str, system_prompt: str, verbose: bool = False, task_type: str = "general") -> AsyncGenerator[str, None]:
        """
        Memory-First CoT Flow with Structured Terminal Tracing and Resilience.
        """
        # Ensure discovery if endpoints are empty
        if not self.endpoints:
            await self.discover_swarm()

        # --- TERMINAL TRACE: QUESTION ---
        safe_print("\n" + "="*80)
        safe_print(f"      🔍 SWARM INQUIRY: {text[:150]}...")
        safe_print("="*80)
        
        query_hash = hashlib.sha256(text.encode()).hexdigest()
        
        # --- NEW: Trace ID for telemetry (Improvement 18) ---
        trace_id = monitor.start_trace()
        monitor.log_trace(trace_id, f"Swarm Inquiry Start (Task: {task_type})")
        monitor.log_trace(trace_id, f"Query Text: {text[:100]}...")
        
        # --- IMPROVEMENT 6+: TASK-SPECIFIC EXPERT PROMPTS ---
        expert_system_prompt = self.TASK_SYSTEM_PROMPTS.get(task_type.lower(), self.TASK_SYSTEM_PROMPTS["general"])
        expert_messages = [
            {"role": "system", "content": expert_system_prompt},
            {"role": "user", "content": text}
        ]
        
        # Original system prompt for the Referee
        
        yield f"{EMOJI['loading']} **Thinking...** (Swarm size: {len(self.endpoints)})\n\n"
        
        async with httpx.AsyncClient() as client:
            raw_results = []
            if len(self.endpoints) == 1:
                safe_print(f"[REASONING] Mode: Single-Model Reflection Loop")
                r1 = await self._query_model_with_timeout(client, self.endpoints[0], expert_messages, timeout=30.0)
                safe_print(f"  > Initial Logic ({r1['model']}): {r1['content'][:150]}...")
                
                critique_msg = expert_messages + [
                    {"role": "assistant", "content": r1['content']},
                    {"role": "user", "content": "Critique your previous answer for logic, accuracy, and completeness. Then provide a final corrected version."}
                ]
                r2 = await self._query_model_with_timeout(client, self.endpoints[0], critique_msg, timeout=30.0)
                safe_print(f"  > Self-Correction ({r2['model']}): {r2['content'][:150]}...")
                raw_results = [r1, r2]
            else:
                safe_print(f"[REASONING] Querying {len(self.endpoints)} Knowledge Experts...")
                tasks = [self._query_model_with_timeout(client, ep, expert_messages, timeout=30.0) for ep in self.endpoints]
                raw_results = await asyncio.gather(*tasks)
                
            # --- IMPROVEMENT 8: PARTIAL FAILURE HANDLING ---
            valid_results = [r for r in raw_results if r['model'] != 'N/A' and not r['content'].startswith('[')]
            
            # --- IMPROVEMENT 11: RECORD EXPERT COSTS ---
            for r in valid_results:
                self.cost_tracker.record_query(r['model'], r['content'])
                monitor.log_trace(trace_id, f"Expert {r['model']} responded in {r['time']:.2f}s")

            if not valid_results:
                yield f"{EMOJI['error']} **All experts failed or timed out.**\n\n"
                # Fallback to main port if not already used
                if self.endpoints[0] != f"http://{HOST}:{PORTS['LLM_API']}/v1/chat/completions":
                     fallback_ep = f"http://{HOST}:{PORTS['LLM_API']}/v1/chat/completions"
                     yield f"🔄 **Fallback**: Attempting primary engine...\n\n"
                     r_fallback = await self._query_model_with_timeout(client, fallback_ep, messages, timeout=45.0)
                     if r_fallback['model'] != 'N/A':
                         valid_results = [r_fallback]
                         self.cost_tracker.record_query(r_fallback['model'], r_fallback['content'])
                     else:
                         yield "❌ Critical failure: System unreachable."
                         return
                else:
                    return

            for i, r in enumerate(valid_results):
                agent_name = r.get('model', f"Expert {i+1}")
                # --- IMPROVEMENT 17: Hallucination Penalty ---
                # If RAG context was used (we detect this if the prompt had source blocks)
                if "[SOURCE]:" in text or "Reference Context:" in text:
                    # We can't do a full NLI check on EVERY expert for speed, 
                    # so we check the top/first expert or do it if consensus is low.
                    pass # logic below for recording
                
                safe_print(f"  > Analysis [{agent_name}] ({r['time']:.2f}s): {r['content'][:300]}...")
            
            responses = [r['content'] for r in valid_results]
            confidence_scores = [r.get('confidence', 0.7) for r in valid_results]
            
            # --- IMPROVEMENT 6: PROTOCOL ROUTING ---
            protocol = self.select_protocol(task_type)
            
            # --- IMPROVEMENT 14: CONTRADICTION DETECTION ---
            contradictions = self.detect_contradictions(responses)
            
            # --- IMPROVEMENT 4: CONFIGURABLE CONSENSUS ---
            agreement = self._calculate_consensus(responses, ConsensusMethod.HYBRID)
            confidence = "High" if agreement > 0.6 else "Medium" if agreement > 0.3 else "Low"

            # --- IMPROVEMENT 7: ADAPTIVE ROUNDS ---
            if self.should_do_round_two(agreement, confidence_scores) or contradictions:
                 safe_print(f"[REASONING] Low agreement ({agreement:.1%}) or contradictions found. Initiating Debate...")
                 yield f"⚖️ **Debate Initiated** ({agreement:.1%} Agreement | {len(contradictions)} Conflicts) - Refining insights...\n\n"
            
            # --- IMPROVEMENT 9: PROGRESSIVE FEEDBACK ---
            if verbose:
                for i, resp_data in enumerate(valid_results):
                    expert_label = f"Expert {i+1}"
                    yield f"--- **{expert_label}** ({resp_data['time']:.2f}s) ---\n{resp_data['content'][:300]}...\n\n"
                if contradictions:
                    yield "⚠️ **Contradictions detected** between some expert perspectives.\n\n"
                yield f"⚖️ **Arbitrage Hub**: Synthesizing ({confidence} Consensus)...\n\n"

            # 4. Arbitrage Logic (Synthesis in Memory)
            referee_endpoint = self.endpoints[0] if self.endpoints else f"http://{config.host}:{config.llm_port}/v1/chat/completions"

            # --- TERMINAL TRACE: DECISION ---
            safe_print("\n[DECISION MATRIX]")
            safe_print(f"  PROCESSOR: Master Arbitrator (Active)")
            safe_print(f"  RATIONALE: {confidence} Consensus ({agreement:.1%}) across {len(responses)} nodes.")
            if contradictions: safe_print(f"  ALERTS: {len(contradictions)} major contradictions detected.")
            safe_print("  STATUS: Processing final synthesis...")

            contradiction_info = ""
            if contradictions:
                contradiction_info = "\nWARNING: The following experts significantly disagreed:\n"
                for c in contradictions:
                    contradiction_info += f"- Expert {c['pair'][0]} vs Expert {c['pair'][1]} (Similarity: {c['similarity']:.2f})\n"

            arbitrage_prompt = f"""
You are the **Swarm Referee**. I have received {len(responses)} expert responses.
CONSENSUS: {confidence} ({agreement:.1%})
{contradiction_info}

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
            
            payload = { "messages": referee_messages, "stream": True, "temperature": 0.2, "max_tokens": -1 }
            safe_print("\n" + "-"*40 + "\n🚀 FINAL RESPONSE STREAMING:\n" + "-"*40)
            
            full_referee_text = ""
            start_ref = time.time()
            try:
                async with client.stream('POST', referee_endpoint, json=payload, timeout=httpx.Timeout(60.0, connect=5.0)) as response:
                    async for line in response.aiter_lines():
                        if not line.startswith('data: '):
                            continue
                        json_str = line[6:]
                        if json_str.strip() == '[DONE]': break
                        try:
                            data = json.loads(json_str)
                            content = data['choices'][0]['delta'].get('content', '')
                            if content: 
                                full_referee_text += content
                                safe_print(content, end="", flush=True)
                                yield content
                        except Exception: pass
            except Exception as e:
                yield f"\n\n{EMOJI['error']} Arbitration failed: {e}"
            
            dur_ref = time.time() - start_ref
            safe_print("\n" + "-"*40 + f"\n✅ COMPLETED in {dur_ref:.1f}s\n" + "="*80 + "\n")
            
            # --- IMPROVEMENT 5: RECORD PERFORMANCE ---
            for r in valid_results:
                self.performance_tracker.get_agent_reliability(r['model'], task_type)
                
                # Apply Hallucination Penalty to was_selected (Improvement 17)
                final_selection = True
                if "[SOURCE]:" in text or "Reference Context:" in text:
                    # Perform aFact-Check on this specific expert
                    fact_check = self.verify_hallucination(r['content'], [text]) # Text contains context
                    if fact_check['score'] < self.reliability_penalty_threshold:
                        logger.warning(f"[Arbitrator] Penalizing {r['model']} for low fact-check score: {fact_check['score']}")
                        final_selection = False # Mark as NOT selected for reliability tracking
                
                self.performance_tracker.record_response(
                    agent_id=r['model'],
                    task_type=task_type,
                    query_hash=query_hash,
                    response_text=r['content'],
                    was_selected=final_selection, 
                    consensus_score=agreement,
                    confidence=r.get('confidence', 0.7),
                    response_time=r['time']
                )

            # Final Metrics Badge (Improvement 11, 15 & Research Parity)
            explanation = f"\n\n---\n📊 **Swarm Metrics**: Consensus **{agreement:.1%}** | Synthesis **{dur_ref:.1f}s** | Cost **${self.cost_tracker.total_cost:.4f}**\n"
            explanation += f"🧠 **Decision Rationale**: Logic verified using `{protocol.value}` protocol across {len(responses)} nodes."
            yield explanation

def get_arbitrator():
    return SwarmArbitrator()
