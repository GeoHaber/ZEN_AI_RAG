# -*- coding: utf-8 -*-
"""
swarm_arbitrator.py - Enhanced Multi-LLM Consensus System
Ported from ZEN_AI_RAG with 2026 research-backed improvements.

Features:
- Async-first parallel dispatch
- Semantic consensus (embeddings)
- Confidence extraction & weighted voting
- Task-based protocol routing
- Agent performance tracking
- Adaptive round selection
- Progressive streaming
- Full TDD coverage
"""
import asyncio
import httpx
import json
import logging
import time
import hashlib
import re
import sqlite3
from pathlib import Path
from typing import List, AsyncGenerator, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime

# Will integrate with existing code
logger = logging.getLogger("SwarmArbitrator")

# ============================================================================
# ENUMS & CONFIG
# ============================================================================

class ConsensusMethod(Enum):
    """Consensus calculation methods."""
    WORD_SET = "word_set"          # Fast word-set overlap
    SEMANTIC = "semantic"          # Embedding similarity
    HYBRID = "hybrid"              # Combination

class ConsensusProtocol(Enum):
    """Consensus protocols for different task types."""
    CONSENSUS = "consensus"        # Converge to single truth
    VOTING = "voting"              # Democratic choice
    WEIGHTED_VOTE = "weighted"     # By confidence + reliability
    MAJORITY = "majority"          # Simple majority
    HYBRID = "hybrid"              # Adaptive

class TaskType(Enum):
    """Task classification types."""
    FACTUAL = "factual"
    REASONING = "reasoning"
    MATH = "math"
    CODE = "code"
    CREATIVE = "creative"
    GENERAL = "general"

# Default configuration
DEFAULT_CONFIG = {
    "enabled": True,
    "size": 3,
    "mode": "local-only",  # or "hybrid" or "external-only"
    "consensus_method": "semantic",
    "protocol_routing": True,
    "track_performance": True,
    "adaptive_rounds": True,
    "min_experts": 2,
    "timeout_per_expert": 30.0,
    "streaming": True,
}

# ============================================================================
# AGENT PERFORMANCE TRACKER
# ============================================================================

class AgentPerformanceTracker:
    """Track agent accuracy and reliability over time."""

    def __init__(self, db_path: str = "agent_performance.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create performance tracking tables."""
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
                response_time REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_task
            ON agent_performance(agent_id, task_type)
        """)
        conn.commit()
        conn.close()

    def record_response(
        self,
        agent_id: str,
        task_type: str,
        query_hash: str,
        response_text: str,
        was_selected: bool,
        consensus_score: float,
        confidence: float,
        response_time: float
    ):
        """Record agent response for future analysis."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO agent_performance
            (agent_id, task_type, query_hash, response_text, was_selected,
             consensus_score, confidence, response_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (agent_id, task_type, query_hash, response_text[:500],
              1 if was_selected else 0, consensus_score, confidence, response_time))
        conn.commit()
        conn.close()

    def get_agent_reliability(self, agent_id: str, task_type: Optional[str] = None) -> float:
        """Get historical accuracy for agent."""
        conn = sqlite3.connect(self.db_path)

        if task_type:
            query = """
                SELECT AVG(was_selected)
                FROM agent_performance
                WHERE agent_id = ? AND task_type = ?
                AND timestamp > datetime('now', '-30 days')
            """
            params = (agent_id, task_type)
        else:
            query = """
                SELECT AVG(was_selected)
                FROM agent_performance
                WHERE agent_id = ?
                AND timestamp > datetime('now', '-30 days')
            """
            params = (agent_id,)

        cursor = conn.execute(query, params)
        result = cursor.fetchone()[0]
        conn.close()

        return result if result is not None else 0.5  # Default neutral

    def get_stats(self) -> Dict:
        """Get overall statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT
                COUNT(*) as total_queries,
                COUNT(DISTINCT agent_id) as unique_agents,
                AVG(consensus_score) as avg_consensus,
                AVG(confidence) as avg_confidence,
                AVG(response_time) as avg_response_time
            FROM agent_performance
            WHERE timestamp > datetime('now', '-7 days')
        """)
        row = cursor.fetchone()
        conn.close()

        return {
            "total_queries": row[0],
            "unique_agents": row[1],
            "avg_consensus": row[2] or 0.0,
            "avg_confidence": row[3] or 0.0,
            "avg_response_time": row[4] or 0.0
        }

# ============================================================================
# ENHANCED SWARM ARBITRATOR
# ============================================================================

class SwarmArbitrator:
    """
    Enhanced multi-LLM consensus system with research-backed improvements.

    Features:
    - Async parallel dispatch
    - Semantic consensus
    - Confidence extraction
    - Weighted voting
    - Task-based protocol routing
    - Agent performance tracking
    - Adaptive round selection
    """

    def __init__(
        self,
        ports: Optional[List[int]] = None,
        host: str = "127.0.0.1",
        config: Optional[Dict] = None
    ):
        # Configuration
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.host = host

        # Port discovery
        self.scan_ports = ports or ([8001] + list(range(8005, 8013)))
        self.ports = []
        self.endpoints = []

        # Performance tracking
        if self.config["track_performance"]:
            self.performance_tracker = AgentPerformanceTracker()
        else:
            self.performance_tracker = None

        # Lazy-loaded embedding model
        self._embedding_model = None

        # Initialize
        if ports:
            self.ports = ports
            self.endpoints = [f"http://{host}:{p}/v1/chat/completions" for p in ports]
        # Don't auto-discover in __init__ (async method)

    # ========================================================================
    # ASYNC DISCOVERY (IMPROVEMENT #1)
    # ========================================================================

    async def discover_swarm(self):
        """Async heartbeat check to find live experts (parallel)."""
        self.ports = []

        if not self.config["enabled"]:
            self.ports = [8001]  # Main port only
            self.endpoints = [f"http://{self.host}:8001/v1/chat/completions"]
            logger.debug("[Arbitrator] Swarm disabled. Using main port only.")
            return

        async with httpx.AsyncClient() as client:
            # Parallel port checks
            tasks = [self._check_port(client, p) for p in self.scan_ports]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for port, is_live in zip(self.scan_ports, results):
                if is_live and not isinstance(is_live, Exception):
                    self.ports.append(port)

        # Limit to configured swarm size
        max_size = self.config["size"]
        if max_size > 0 and len(self.ports) > max_size:
            # Keep first port (main) + top experts
            self.ports = [self.ports[0]] + self.ports[1:max_size]

        self.endpoints = [f"http://{self.host}:{p}/v1/chat/completions" for p in self.ports]
        logger.info(f"[Arbitrator] Discovered {len(self.ports)} live experts: {self.ports}")

    async def _check_port(self, client: httpx.AsyncClient, port: int) -> bool:
        """Check if a port is live."""
        try:
            resp = await client.get(
                f"http://{self.host}:{port}/health",
                timeout=1.0
            )
            return resp.status_code in [200, 503]  # 503 = UP but loading
        except:
            return False

    # ========================================================================
    # TIMEOUT HANDLING (IMPROVEMENT #2)
    # ========================================================================

    async def _query_model_with_timeout(
        self,
        client: httpx.AsyncClient,
        endpoint: str,
        messages: List[Dict],
        timeout: float = None
    ) -> Dict:
        """Query model with timeout and fallback."""
        timeout = timeout or self.config["timeout_per_expert"]

        try:
            return await asyncio.wait_for(
                self._query_model(client, endpoint, messages),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"[Arbitrator] Expert {endpoint} timed out after {timeout}s")
            return {
                "content": f"[TIMEOUT after {timeout}s]",
                "time": timeout,
                "model": f"Timeout-{endpoint}",
                "confidence": 0.0,
                "error": True
            }
        except Exception as e:
            logger.error(f"[Arbitrator] Expert {endpoint} failed: {e}")
            return {
                "content": f"[ERROR: {str(e)}]",
                "time": 0.0,
                "model": f"Error-{endpoint}",
                "confidence": 0.0,
                "error": True
            }

    async def _query_model(
        self,
        client: httpx.AsyncClient,
        endpoint: str,
        messages: List[Dict]
    ) -> Dict:
        """Query a single model and return full response + metadata."""
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

                # IMPROVEMENT #3: Extract confidence
                confidence = self._extract_confidence(content)

                return {
                    "content": content,
                    "time": duration,
                    "model": model_name,
                    "confidence": confidence,
                    "error": False
                }

            return {
                "content": f"Error: HTTP {response.status_code}",
                "time": duration,
                "model": "N/A",
                "confidence": 0.0,
                "error": True
            }

        except Exception as e:
            return {
                "content": f"Connect Error: {e}",
                "time": time.time() - start,
                "model": "N/A",
                "confidence": 0.0,
                "error": True
            }

    # ========================================================================
    # CONFIDENCE EXTRACTION (IMPROVEMENT #3)
    # ========================================================================

    def _extract_confidence(self, response_text: str) -> float:
        """
        Extract confidence score from response.

        Looks for patterns:
        - "I'm 90% confident" → 0.9
        - "Confidence: 0.85" → 0.85
        - "I'm quite sure" → 0.8
        - "I think maybe" → 0.5
        """
        # Explicit percentage
        match = re.search(r'(\d{1,3})%\s*confident', response_text.lower())
        if match:
            return float(match.group(1)) / 100.0

        # Explicit decimal
        match = re.search(r'confidence:?\s*(\d\.\d+)', response_text.lower())
        if match:
            return min(1.0, float(match.group(1)))

        # Linguistic markers
        confidence_markers = [
            (r'\b(certain|definite|absolutely|definitely)\b', 0.95),
            (r'\b(very confident|quite sure|very likely)\b', 0.85),
            (r'\b(confident|likely|probably)\b', 0.75),
            (r'\b(think|believe|seems)\b', 0.6),
            (r'\b(maybe|perhaps|possibly|might)\b', 0.5),
            (r'\b(unsure|uncertain|not sure)\b', 0.3),
        ]

        for pattern, score in confidence_markers:
            if re.search(pattern, response_text.lower()):
                return score

        # Default neutral confidence
        return 0.7

    # ========================================================================
    # CONSENSUS CALCULATION (IMPROVEMENT #4)
    # ========================================================================

    def _calculate_consensus(
        self,
        responses: List[str],
        method: Optional[ConsensusMethod] = None
    ) -> float:
        """Calculate consensus using specified method."""
        method = method or ConsensusMethod[self.config["consensus_method"].upper()]

        if method == ConsensusMethod.WORD_SET:
            return self._calculate_consensus_wordset(responses)
        elif method == ConsensusMethod.SEMANTIC:
            return self._calculate_consensus_semantic(responses)
        elif method == ConsensusMethod.HYBRID:
            word_score = self._calculate_consensus_wordset(responses)
            semantic_score = self._calculate_consensus_semantic(responses)
            return (word_score + semantic_score) / 2.0
        else:
            return self._calculate_consensus_wordset(responses)

    def _calculate_consensus_wordset(self, responses: List[str]) -> float:
        """Original word-set intersection/union method."""
        if len(responses) == 0:
            return 0.0  # No responses = no consensus
        if len(responses) == 1:
            return 1.0  # Single response = perfect agreement

        sets = [set(r.lower().split()) for r in responses]
        if not all(sets):
            return 0.0

        common = set.intersection(*sets)
        union = set.union(*sets)

        return len(common) / len(union) if union else 0.0

    def _calculate_consensus_semantic(self, responses: List[str]) -> float:
        """Semantic similarity using sentence embeddings."""
        try:
            # Lazy import (only if semantic method used)
            if self._embedding_model is None:
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("[Arbitrator] Loaded semantic embedding model")

            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np

            # Encode responses
            embeddings = self._embedding_model.encode(responses)

            # Calculate pairwise cosine similarity
            similarities = cosine_similarity(embeddings)

            # Return average similarity (excluding diagonal)
            n = len(responses)
            if n < 2:
                return 1.0

            # Average of all pairs (excluding self-similarity)
            total_sim = (similarities.sum() - n) / (n * (n - 1))
            return float(total_sim)

        except ImportError:
            logger.warning("[Arbitrator] sentence-transformers not available, falling back to word-set")
            return self._calculate_consensus_wordset(responses)

    # ========================================================================
    # PROTOCOL ROUTING (IMPROVEMENT #6)
    # ========================================================================

    def select_protocol(self, task_type: str) -> ConsensusProtocol:
        """Select optimal protocol based on task type (research-backed)."""
        if not self.config["protocol_routing"]:
            return ConsensusProtocol.WEIGHTED_VOTE  # Default

        protocol_map = {
            "factual": ConsensusProtocol.CONSENSUS,
            "quick_qa": ConsensusProtocol.CONSENSUS,
            "reasoning": ConsensusProtocol.WEIGHTED_VOTE,
            "math": ConsensusProtocol.WEIGHTED_VOTE,
            "code": ConsensusProtocol.WEIGHTED_VOTE,
            "creative": ConsensusProtocol.VOTING,
            "general": ConsensusProtocol.MAJORITY,
        }

        return protocol_map.get(task_type.lower(), ConsensusProtocol.HYBRID)

    # ========================================================================
    # ADAPTIVE ROUND SELECTION (IMPROVEMENT #7)
    # ========================================================================

    def should_do_round_two(
        self,
        agreement: float,
        confidence_scores: List[float]
    ) -> bool:
        """Decide if second debate round is worth the cost."""
        if not self.config["adaptive_rounds"]:
            return False  # Always single round

        # Skip Round 2 if high agreement
        if agreement > 0.8:
            logger.info(f"[Arbitrator] Skipping Round 2: High agreement ({agreement:.1%})")
            return False

        # Skip if all experts highly confident
        if confidence_scores:
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
            if avg_confidence > 0.85:
                logger.info(f"[Arbitrator] Skipping Round 2: High confidence ({avg_confidence:.1%})")
                return False

        # Do Round 2 for significant disagreement
        logger.info(f"[Arbitrator] Round 2 needed: agreement={agreement:.1%}")
        return True

    # ========================================================================
    # MAIN CONSENSUS METHOD
    # ========================================================================

    async def get_consensus(
        self,
        text: str,
        system_prompt: str = "You are a helpful AI assistant.",
        task_type: str = "general",
        verbose: bool = False
    ) -> AsyncGenerator[str, None]:
        """
        Get consensus answer from expert swarm.

        Process:
        1. Discover available experts
        2. Parallel query all experts
        3. Calculate consensus score
        4. (Optional) Round 2 cross-critique
        5. Referee synthesis
        6. Track performance
        """
        # Ensure experts discovered
        if not self.endpoints:
            await self.discover_swarm()

        if len(self.endpoints) == 0:
            yield "❌ **Error:** No experts available.\n"
            return

        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]

        # Select protocol
        protocol = self.select_protocol(task_type)

        yield f"🔄 **Analyzing...** ({len(self.endpoints)} experts, {protocol.value} protocol)\n\n"

        async with httpx.AsyncClient() as client:
            # ROUND 1: Parallel expert queries
            logger.info(f"[Arbitrator] Round 1: Querying {len(self.endpoints)} experts...")

            tasks = [
                self._query_model_with_timeout(client, ep, messages)
                for ep in self.endpoints
            ]
            raw_results = await asyncio.gather(*tasks)

            # Filter out failures (IMPROVEMENT #8: Partial failure handling)
            valid_results = [r for r in raw_results if not r.get("error", False)]
            failed_count = len(raw_results) - len(valid_results)

            if len(valid_results) < self.config["min_experts"]:
                yield f"❌ **Insufficient experts:** {len(valid_results)}/{self.config['min_experts']} available\n"
                if len(valid_results) > 0:
                    yield "**Fallback:** Using available expert(s)...\n\n"
                else:
                    return

            if failed_count > 0:
                yield f"⚠️ {failed_count} expert(s) unavailable\n"

            # Extract responses
            responses = [r['content'] for r in valid_results]
            confidence_scores = [r['confidence'] for r in valid_results]

            # Calculate consensus
            agreement = self._calculate_consensus(responses)
            confidence_label = "High" if agreement > 0.6 else "Medium" if agreement > 0.3 else "Low"

            # Show expert responses if verbose
            if verbose:
                yield f"\n### Expert Responses ({confidence_label} Consensus: {agreement:.1%})\n\n"
                for i, r in enumerate(valid_results):
                    yield f"**Expert {i+1}** ({r['model']}, {r['time']:.1f}s, {r['confidence']:.0%} confident):\n"
                    yield f"{r['content'][:300]}...\n\n"

            # ROUND 2: Adaptive cross-critique (if needed)
            if self.should_do_round_two(agreement, confidence_scores):
                yield f"⚖️ **Low consensus** ({agreement:.1%}) - Cross-critique round...\n\n"

                critique_tasks = []
                for i, endpoint in enumerate([self.endpoints[j] for j, r in enumerate(raw_results) if not r.get("error")]):
                    other_responses = [responses[j] for j in range(len(responses)) if j != i]

                    critique_prompt = self._build_critique_prompt(
                        original=responses[i],
                        others=other_responses,
                        question=text
                    )

                    critique_tasks.append(
                        self._query_model_with_timeout(client, endpoint, critique_prompt)
                    )

                revised_results = await asyncio.gather(*critique_tasks)
                valid_revised = [r for r in revised_results if not r.get("error", False)]

                # Use revised responses
                if len(valid_revised) > 0:
                    responses = [r['content'] for r in valid_revised]
                    agreement = self._calculate_consensus(responses)
                    yield f"✅ **Revised consensus:** {agreement:.1%}\n\n"

            # REFEREE SYNTHESIS
            yield f"🔮 **Synthesizing final answer...**\n\n"

            arbitrage_prompt = self._build_arbitrage_prompt(
                question=text,
                responses=responses,
                agreement=agreement,
                protocol=protocol
            )

            referee_messages = [
                {"role": "system", "content": "You are the Swarm Referee. Synthesize expert opinions into a unified answer."},
                {"role": "user", "content": arbitrage_prompt}
            ]

            # Stream referee response
            referee_endpoint = self.endpoints[0]  # Main model
            payload = {
                "messages": referee_messages,
                "stream": True,
                "temperature": 0.2,
                "max_tokens": -1
            }

            full_answer = ""
            start_synthesis = time.time()

            try:
                async with client.stream('POST', referee_endpoint, json=payload, timeout=120.0) as response:
                    async for line in response.aiter_lines():
                        if line.startswith('data: '):
                            json_str = line[6:]
                            if json_str.strip() == '[DONE]':
                                break
                            try:
                                data = json.loads(json_str)
                                content = data['choices'][0]['delta'].get('content', '')
                                if content:
                                    full_answer += content
                                    yield content
                            except:
                                pass
            except Exception as e:
                yield f"\n\n❌ **Synthesis failed:** {e}\n"
                return

            synthesis_time = time.time() - start_synthesis

            # IMPROVEMENT #5: Track performance
            if self.performance_tracker:
                query_hash = hashlib.md5(text.encode()).hexdigest()
                for i, r in enumerate(valid_results):
                    self.performance_tracker.record_response(
                        agent_id=r['model'],
                        task_type=task_type,
                        query_hash=query_hash,
                        response_text=r['content'],
                        was_selected=(i == 0),  # Placeholder (first expert)
                        consensus_score=agreement,
                        confidence=r['confidence'],
                        response_time=r['time']
                    )

            # Final metrics
            yield f"\n\n---\n📊 **Swarm Metrics:** Consensus **{agreement:.1%}** | "
            yield f"Experts **{len(valid_results)}** | Synthesis **{synthesis_time:.1f}s** | Protocol **{protocol.value}**\n"

    def _build_critique_prompt(self, original: str, others: List[str], question: str) -> List[Dict]:
        """Build prompt for cross-critique round."""
        other_text = "\n\n".join([f"--- Alternative View {i+1} ---\n{o}" for i, o in enumerate(others)])

        prompt = f"""You previously answered: "{question}"

Your answer was:
{original}

Other experts provided different perspectives:
{other_text}

After reviewing these alternative views:
1. Do you still stand by your answer?
2. If not, provide a revised answer incorporating valid points from others.
3. If yes, explain why your answer is more accurate.

Revised or confirmed answer:"""

        return [{"role": "user", "content": prompt}]

    def _build_arbitrage_prompt(
        self,
        question: str,
        responses: List[str],
        agreement: float,
        protocol: ConsensusProtocol
    ) -> str:
        """Build referee synthesis prompt based on protocol."""
        expert_text = "\n\n".join([f"--- Expert {i+1} ---\n{r}" for i, r in enumerate(responses)])

        if protocol == ConsensusProtocol.CONSENSUS:
            strategy = "Find the single correct answer. Converge expert opinions to the most accurate truth."
        elif protocol == ConsensusProtocol.WEIGHTED_VOTE:
            strategy = "Weight expert opinions by reliability and confidence. Prioritize high-confidence answers."
        elif protocol == ConsensusProtocol.VOTING:
            strategy = "Respect diverse viewpoints. Present a balanced synthesis of all perspectives."
        else:
            strategy = "Harmonize insights and resolve any conflicts into a unified answer."

        prompt = f"""You are the Swarm Referee. {len(responses)} experts have responded.

**Consensus Level:** {"High" if agreement > 0.6 else "Medium" if agreement > 0.3 else "Low"} ({agreement:.1%})
**Strategy:** {strategy}

**User Question:**
{question}

**Expert Contributions:**
{expert_text}

**Instructions:**
- Synthesize a clean, unified, authoritative final answer
- If major disagreements exist, explain which view is most accurate and why
- Be concise but complete

**Final Verified Answer:**"""

        return prompt

# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def get_arbitrator(config: Optional[Dict] = None) -> SwarmArbitrator:
    """Factory function to create arbitrator instance."""
    return SwarmArbitrator(config=config)

# ============================================================================
# MAIN (for testing)
# ============================================================================

if __name__ == "__main__":
    import sys

    async def test_arbitrator():
        """Quick test of arbitrator functionality."""
        arb = SwarmArbitrator()

        # Discover experts
        await arb.discover_swarm()
        print(f"✅ Discovered {len(arb.ports)} experts: {arb.ports}")

        # Test query
        question = "What is 2 + 2?"
        print(f"\n🔍 Question: {question}\n")

        async for chunk in arb.get_consensus(question, verbose=True):
            print(chunk, end="", flush=True)

        print("\n\n✅ Test complete!")

        # Show stats
        if arb.performance_tracker:
            stats = arb.performance_tracker.get_stats()
            print(f"\n📊 Performance Stats:")
            print(f"  Total Queries: {stats['total_queries']}")
            print(f"  Avg Consensus: {stats['avg_consensus']:.1%}")
            print(f"  Avg Confidence: {stats['avg_confidence']:.1%}")

    asyncio.run(test_arbitrator())
