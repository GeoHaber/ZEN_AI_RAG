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
from typing import List, AsyncGenerator, Dict, Optional, Any
from enum import Enum

# Will integrate with existing code
logger = logging.getLogger("SwarmArbitrator")

# ============================================================================
# ENUMS & CONFIG
# ============================================================================


class ConsensusMethod(Enum):
    """Consensus calculation methods."""

    WORD_SET = "word_set"  # Fast word-set overlap
    SEMANTIC = "semantic"  # Embedding similarity
    HYBRID = "hybrid"  # Combination


class ConsensusProtocol(Enum):
    """Consensus protocols for different task types."""

    CONSENSUS = "consensus"  # Converge to single truth
    VOTING = "voting"  # Democratic choice
    WEIGHTED_VOTE = "weighted"  # By confidence + reliability
    MAJORITY = "majority"  # Simple majority
    HYBRID = "hybrid"  # Adaptive


class TaskType(Enum):
    """Task classification types."""

    FACTUAL = "factual"
    REASONING = "reasoning"
    MATH = "math"
    CODE = "code"
    CREATIVE = "creative"
    GENERAL = "general"


from dataclasses import dataclass


@dataclass
class ArbitrationRequest:
    """Request for swarm arbitration."""

    id: str
    query: str
    task_type: str
    timestamp: float = 0.0


ExpertResponse = Dict[str, Any]


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
        response_time: float,
    ):
        """Record agent response for future analysis."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            INSERT INTO agent_performance
            (agent_id, task_type, query_hash, response_text, was_selected,
             consensus_score, confidence, response_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                agent_id,
                task_type,
                query_hash,
                response_text[:500],
                1 if was_selected else 0,
                consensus_score,
                confidence,
                response_time,
            ),
        )
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
            "avg_response_time": row[4] or 0.0,
        }


# ============================================================================
# COST TRACKING
# ============================================================================


class CostTracker:
    """Track API costs for budgeting (Improvement #12 companion)."""

    COSTS = {
        "local": 0.0,
        "gpt-4": 0.01,
        "claude-3": 0.015,
        "gemini": 0.00025,
    }

    def __init__(self):
        self.total_cost = 0.0
        self.cost_breakdown = {}  # Track per provider

    def record_query(self, model: str, content: str, tokens: int = None):
        """Record a query cost.

        Args:
            model: Model name (e.g., "claude-3", "gpt-4")
            content: Response content (for token estimation if tokens not provided)
            tokens: Explicit token count (optional)

        Returns:
            Cost of this query in dollars
        """
        if tokens is None:
            tokens = len(content.split()) * 1.3  # Rough estimate

        cost_per_1k = 0.0
        for m, c in self.COSTS.items():
            if m not in model.lower():
                continue
            cost_per_1k = c
            break

        cost = (tokens / 1000.0) * cost_per_1k
        self.total_cost += cost

        # Track breakdown by provider
        if model not in self.cost_breakdown:
            self.cost_breakdown[model] = 0.0
        self.cost_breakdown[model] += cost

        return cost

    def get_total_cost(self) -> float:
        """Get total cost across all queries."""
        return self.total_cost

    def get_cost_breakdown(self) -> Dict[str, float]:
        """Get cost breakdown by provider."""
        return self.cost_breakdown.copy()

    def estimate_cost(self, model: str, tokens: int) -> float:
        """Estimate cost for a query without recording it.

        Args:
            model: Model name
            tokens: Token count

        Returns:
            Estimated cost in dollars
        """
        cost_per_1k = 0.0
        for m, c in self.COSTS.items():
            if m not in model.lower():
                continue
            cost_per_1k = c
            break

        return (tokens / 1000.0) * cost_per_1k


# ============================================================================
# RAGED SWARM STORAGE (Memory for Experts)
# ============================================================================


class RagedSwarmStorage:
    """
    Dedicated RAG storage for expert opinions to reduce hallucinations.
    Stores query -> expert_consensus mappings.
    """

    def __init__(self, db_path: str = "swarm_memory.db"):
        self.db_path = db_path
        self._init_db()
        # reusing sentence transformer from arbitrator if possible, or load own

    def _init_db(self):
        """Init db."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS swarm_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT,
                query_text TEXT,
                consensus_response TEXT,
                contributing_experts TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Simple FTS for retrieval for now
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS swarm_fts USING fts5(query_text, consensus_response)")
        conn.commit()
        conn.close()

    def store_consensus(self, query: str, response: str, experts: List[str]):
        """Store a finalized consensus."""
        conn = sqlite3.connect(self.db_path)
        q_hash = hashlib.sha256(query.encode()).hexdigest()

        try:
            conn.execute(
                """
                INSERT INTO swarm_memory (query_hash, query_text, consensus_response, contributing_experts)
                VALUES (?, ?, ?, ?)
            """,
                (q_hash, query, response, json.dumps(experts)),
            )
            conn.execute("INSERT INTO swarm_fts (query_text, consensus_response) VALUES (?, ?)", (query, response))
            conn.commit()
        except Exception as e:
            logger.error(f"[SwarmMemory] Store failed: {e}")
        finally:
            conn.close()

    def retrieve_similar(self, query: str, limit: int = 3) -> List[Dict]:
        """Retrieve similar past swarm decisions."""
        conn = sqlite3.connect(self.db_path)
        try:
            # Using FTS for basic similarity
            cursor = conn.execute(
                """
                SELECT query_text, consensus_response FROM swarm_fts 
                WHERE swarm_fts MATCH ? ORDER BY rank LIMIT ?
            """,
                (query, limit),
            )

            results = []
            for row in cursor:
                results.append({"query": row[0], "response": row[1]})
            return results
        except Exception:
            return []
        finally:
            conn.close()


# ============================================================================
# ENHANCED SWARM ARBITRATOR
# ============================================================================


class _SwarmArbitratorBase:
    """Base methods for SwarmArbitrator."""

    def __init__(self, ports: Optional[List[int]] = None, host: str = "127.0.0.1", config: Optional[Dict] = None):
        """Initialize instance."""
        # Configuration
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.host = host

        # Port discovery
        # Exclude 8005 (Voice Server) to prevent protocol mismatch hangs
        self.scan_ports = ports or ([8001] + list(range(8006, 8013)))
        self.ports = []
        self.endpoints = []

        # Performance tracking
        if self.config["track_performance"]:
            self.performance_tracker = AgentPerformanceTracker()
        else:
            self.performance_tracker = None

        # RAGed Swarm Memory
        self.swarm_memory = RagedSwarmStorage() if self.config.get("rag_swarm_enabled", True) else None

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
            resp = await client.get(f"http://{self.host}:{port}/health", timeout=1.0)
            return resp.status_code in [200, 503]  # 503 = UP but loading
        except Exception:
            return False

    # ========================================================================
    # TIMEOUT HANDLING (IMPROVEMENT #2)
    # ========================================================================

    async def _query_model_with_timeout(
        self, client: httpx.AsyncClient, endpoint: str, messages: List[Dict], timeout: float = None
    ) -> Dict:
        """Query model with timeout and fallback."""
        timeout = timeout or self.config["timeout_per_expert"]

        try:
            return await asyncio.wait_for(self._query_model(client, endpoint, messages), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"[Arbitrator] Expert {endpoint} timed out after {timeout}s")
            return {
                "content": f"[TIMEOUT after {timeout}s]",
                "time": timeout,
                "model": f"Timeout-{endpoint}",
                "confidence": 0.0,
                "error": True,
            }
        except Exception as e:
            logger.error(f"[Arbitrator] Expert {endpoint} failed: {e}")
            return {
                "content": f"[ERROR: {str(e)}]",
                "time": 0.0,
                "model": f"Error-{endpoint}",
                "confidence": 0.0,
                "error": True,
            }

    async def _query_model(self, client: httpx.AsyncClient, endpoint: str, messages: List[Dict]) -> Dict:
        """Query a single model and return full response + metadata."""
        start = time.time()

        try:
            payload = {"messages": messages, "stream": False, "temperature": 0.7, "max_tokens": 512}

            response = await client.post(endpoint, json=payload, timeout=60.0)
            duration = time.time() - start

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                model_name = data.get("model", "Unknown-Model")

                # IMPROVEMENT #3: Extract confidence
                confidence = self._extract_confidence(content)

                return {
                    "content": content,
                    "time": duration,
                    "model": model_name,
                    "confidence": confidence,
                    "error": False,
                }

            return {
                "content": f"Error: HTTP {response.status_code}",
                "time": duration,
                "model": "N/A",
                "confidence": 0.0,
                "error": True,
            }

        except Exception as e:
            return {
                "content": f"Connect Error: {e}",
                "time": time.time() - start,
                "model": "N/A",
                "confidence": 0.0,
                "error": True,
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
        match = re.search(r"(\d{1,3})%\s*confident", response_text.lower())
        if match:
            return float(match.group(1)) / 100.0

        # Explicit decimal
        match = re.search(r"confidence:?\s*(\d\.\d+)", response_text.lower())
        if match:
            return min(1.0, float(match.group(1)))

        # Linguistic markers
        confidence_markers = [
            (r"\b(certain|definite|absolutely|definitely)\b", 0.95),
            (r"\b(very confident|quite sure|very likely)\b", 0.85),
            (r"\b(confident|likely|probably)\b", 0.75),
            (r"\b(think|believe|seems)\b", 0.6),
            (r"\b(maybe|perhaps|possibly|might)\b", 0.5),
            (r"\b(unsure|uncertain|not sure)\b", 0.3),
        ]

        for pattern, score in confidence_markers:
            if re.search(pattern, response_text.lower()):
                return score

        # Default neutral confidence
        return 0.7

    # ========================================================================
    # EXTERNAL AGENT BRIDGE (IMPROVEMENT #12)
    # ========================================================================

    async def _query_external_agent(self, model: str, messages: List[Dict]) -> Dict:
        """Functional Bridge for External Agents (Improvement 12).

        Queries external LLM APIs (Anthropic Claude, Google Gemini, Grok) using
        httpx for async API calls.

        Args:
            model: Model name (e.g., "claude-3-5-sonnet", "gemini-pro", "grok-beta")
            messages: List of message dicts with "role" and "content" keys

        Returns:
            Dict with keys:
                - content: Response text or error message
                - model: Model name
                - time: Response time in seconds
                - confidence: Extracted confidence score (0.0-1.0)
        """
        import os

        # Check for API keys (try multiple env vars)
        api_key = (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("XAI_API_KEY")
        )

        if not api_key:
            return {
                "content": "[ERROR: No API Key found for external agent]",
                "model": model,
                "time": 0.0,
                "confidence": 0.0,
            }

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

                # Defaulting to OpenAI compatible endpoint
                # Can be extended for Anthropic, Google, Grok specific endpoints
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}"}

                response = await client.post(url, json=payload, headers=headers, timeout=60.0)

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    return {
                        "content": content,
                        "time": time.time() - start,
                        "model": model,
                        "confidence": self._extract_confidence(content),
                    }

                # Non-200 status codes
                return {
                    "content": f"[API Error: {response.status_code}]",
                    "model": model,
                    "time": time.time() - start,
                    "confidence": 0.0,
                }

        except Exception as e:
            # Network errors, timeouts, etc.
            return {
                "content": f"[Bridge Error: {str(e)}]",
                "model": model,
                "time": time.time() - start,
                "confidence": 0.0,
            }

    # ========================================================================
    # CONSENSUS CALCULATION (IMPROVEMENT #4)
    # ========================================================================

    def _calculate_consensus(self, responses: List[str], method: Optional[ConsensusMethod] = None) -> float:
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

                self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
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


class SwarmArbitrator(_SwarmArbitratorBase):
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

    def should_do_round_two(self, agreement: float, confidence_scores: List[float]) -> bool:
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
    # TRAFFIC CONTROLLER MODE (2 LLMs)
    # ========================================================================

    async def _traffic_controller_mode(
        self, query: str, system_prompt: str = "You are a helpful AI assistant."
    ) -> AsyncGenerator[str, None]:
        """
        Traffic controller mode for 2 LLMs.

        Strategy:
        1. Fast LLM evaluates difficulty
        2. Easy → Fast LLM answers
        3. Hard → Powerful LLM answers
        4. Medium → Get second opinion
        """
        fast_llm = self.endpoints[0]
        powerful_llm = self.endpoints[1]

        if self.endpoints:
            # Step 1: Evaluate difficulty using the first LLM (Fast/Local)
            yield "🚦 Evaluating query complexity...\n"
            evaluation = await self._evaluate_query_difficulty(query, evaluator_endpoint=fast_llm)
        else:
            # Fallback if no endpoints (unlikely here)
            evaluation = {"difficulty": "medium", "confidence": 0.5}

        difficulty = evaluation.get("difficulty", "medium")
        confidence = evaluation.get("confidence", 0.5)

        threshold = self.config.get("traffic_controller_threshold", 0.8)

        # Step 2: Route based on evaluation
        if difficulty == "easy" and confidence > threshold:
            # Fast LLM handles it
            yield f"💨 **Fast response** ({difficulty}, confidence: {confidence:.0%})\n\n"
            async for chunk in self._stream_from_llm(fast_llm, query, system_prompt):
                yield chunk

        elif difficulty == "hard" or confidence < 0.5:
            # Route to powerful LLM
            yield f"🚀 **Expert routing** ({difficulty}, confidence: {confidence:.0%})\n\n"
            async for chunk in self._stream_from_llm(powerful_llm, query, system_prompt):
                yield chunk

        else:
            # Medium difficulty - get second opinion
            yield f"⚖️ **Verification** ({difficulty}, confidence: {confidence:.0%})\n\n"

            # Get both answers
            fast_answer = await self._get_answer(fast_llm, query, system_prompt)
            powerful_answer = await self._get_answer(powerful_llm, query, system_prompt)

            # Quick consensus
            agreement = self._calculate_consensus([fast_answer, powerful_answer])

            if agreement > 0.7:
                # They agree - use fast answer (cheaper)
                yield fast_answer
            else:
                # Disagree - use powerful answer (safer)
                yield powerful_answer

    async def _evaluate_query_difficulty(self, query: str, evaluator_endpoint: str = None) -> Dict:
        """
        Use fast LLM to classify query difficulty.

        Args:
            query: The user query
            evaluator_endpoint: Endpoint to use for evaluation (defaults to self.endpoints[0])

        Returns:
            {
                "difficulty": "easy|medium|hard",
                "domain": "code|math|creative|factual|reasoning",
                "confidence": 0.0-1.0,
                "reasoning": "brief explanation"
            }
        """
        # Use provided endpoint or default to first available (Fast LLM)
        if evaluator_endpoint:
            controller_endpoint = evaluator_endpoint
        elif self.endpoints:
            controller_endpoint = self.endpoints[0]
        else:
            # Fallback to hardcoded if state is really broken, but prefer config
            controller_endpoint = f"http://{self.host}:8001/v1/chat/completions"

        eval_prompt = f"""Analyze this query and respond ONLY with JSON:

Query: {query}

{{
    "difficulty": "easy|medium|hard",
    "domain": "code|math|creative|factual|reasoning",
    "confidence": 0.0-1.0,
    "reasoning": "1 sentence"
}}

Rules:
- "easy": Factual QA, simple math, definitions
- "medium": Code, explanations, analysis
- "hard": Complex reasoning, research, proofs

JSON:"""

        try:
            async with httpx.AsyncClient() as client:
                response = await self._query_model_with_timeout(
                    client,
                    controller_endpoint,
                    [{"role": "user", "content": eval_prompt}],
                    timeout=5.0,  # Fast timeout for classifier
                )

                # Parse JSON response
                content = response["content"]

                # Extract JSON (handle markdown code blocks)
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                result = json.loads(content)
                return result

        except Exception as e:
            logger.error(f"[Traffic Controller] Classification failed: {e}")
            # Fallback: default to medium difficulty
            return {
                "difficulty": "medium",
                "domain": "general",
                "confidence": 0.5,
                "reasoning": "Classification failed, defaulting to medium",
            }

    async def _stream_from_llm(self, endpoint: str, query: str, system_prompt: str) -> AsyncGenerator[str, None]:
        """Stream response from a single LLM."""
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": query}]

        payload = {"messages": messages, "stream": True, "temperature": 0.7, "max_tokens": -1}

        async with httpx.AsyncClient() as client:
            async with client.stream("POST", endpoint, json=payload, timeout=120.0) as response:
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    json_str = line[6:]
                    if json_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(json_str)
                        content = data["choices"][0]["delta"].get("content", "")
                        if content:
                            yield content
                    except Exception:
                        pass

    async def _get_answer(self, endpoint: str, query: str, system_prompt: str) -> str:
        """Get complete answer from a single LLM (non-streaming)."""
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": query}]

        async with httpx.AsyncClient() as client:
            response = await self._query_model_with_timeout(client, endpoint, messages)
            return response["content"]

    # ========================================================================
    # STRUCTURED DECISION (API MODE)
    # ========================================================================

    async def arbiter_decision(self, request: ArbitrationRequest) -> Dict:
        """
        Structured consensus decision (non-streaming) for API usage.
        """
        start_time = time.time()

        # 1. Discover
        if not self.endpoints:
            await self.discover_swarm()

        if not self.endpoints:
            return {
                "consensus_answer": "Error: No experts available.",
                "individual_responses": [],
                "method": "failure",
                "confidence": 0.0,
                "duration": 0.0,
            }

        # 2. Query Experts (Parallel)
        # Use simple system prompt for experts
        sys_prompt = {"role": "system", "content": "You are a swarm expert. Answer concisely."}
        messages = [sys_prompt, {"role": "user", "content": request.query}]

        async with httpx.AsyncClient() as client:
            tasks = [self._query_model_with_timeout(client, ep, messages) for ep in self.endpoints]
            results = await asyncio.gather(*tasks)

        valid_results = [r for r in results if not r.get("error")]
        responses = [r["content"] for r in valid_results]

        # 3. Consensus
        agreement = self._calculate_consensus(responses)
        # Handle TaskType enumeration conversion if needed
        # Assuming request.task_type is string compatible or Enum
        t_type = request.task_type.value if hasattr(request.task_type, "value") else str(request.task_type)
        protocol = self.select_protocol(t_type)

        # 4. Referee Synthesis (Non-streaming)
        # Use main model as referee
        referee_endpoint = self.endpoints[0]
        prompt = self._build_arbitrage_prompt(request.query, responses, agreement, protocol)

        final_answer = await self._get_answer(referee_endpoint, prompt, "You are the Swarm Referee.")

        return {
            "consensus_answer": final_answer,
            "individual_responses": valid_results,
            "method": protocol.value,
            "confidence": agreement,
            "duration": time.time() - start_time,
        }

    # ========================================================================
    # MAIN CONSENSUS METHOD
    # ========================================================================

    async def _get_consensus_continued(self, messages, protocol, response):
        """Continue get_consensus logic."""
        async with httpx.AsyncClient() as client:
            # ROUND 1: Parallel expert queries
            logger.info(f"[Arbitrator] Round 1: Querying {len(self.endpoints)} experts...")

            tasks = [self._query_model_with_timeout(client, ep, messages) for ep in self.endpoints]
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
            responses = [r["content"] for r in valid_results]
            confidence_scores = [r["confidence"] for r in valid_results]

            # Calculate consensus
            agreement = self._calculate_consensus(responses)
            confidence_label = "High" if agreement > 0.6 else "Medium" if agreement > 0.3 else "Low"

            # Show expert responses if verbose
            if verbose:
                yield f"\n### Expert Responses ({confidence_label} Consensus: {agreement:.1%})\n\n"
                for i, r in enumerate(valid_results):
                    yield f"**Expert {i + 1}** ({r['model']}, {r['time']:.1f}s, {r['confidence']:.0%} confident):\n"
                    yield f"{r['content'][:300]}...\n\n"

            # ROUND 2: Adaptive cross-critique (if needed)
            if self.should_do_round_two(agreement, confidence_scores):
                yield f"⚖️ **Low consensus** ({agreement:.1%}) - Cross-critique round...\n\n"

                critique_tasks = []
                for i, endpoint in enumerate(
                    [self.endpoints[j] for j, r in enumerate(raw_results) if not r.get("error")]
                ):
                    other_responses = [responses[j] for j in range(len(responses)) if j != i]

                    critique_prompt = self._build_critique_prompt(
                        original=responses[i], others=other_responses, question=text
                    )

                    critique_tasks.append(self._query_model_with_timeout(client, endpoint, critique_prompt))

                revised_results = await asyncio.gather(*critique_tasks)
                valid_revised = [r for r in revised_results if not r.get("error", False)]

                # Use revised responses
                if len(valid_revised) > 0:
                    responses = [r["content"] for r in valid_revised]
                    agreement = self._calculate_consensus(responses)
                    yield f"✅ **Revised consensus:** {agreement:.1%}\n\n"

            # REFEREE SYNTHESIS
            yield f"🔮 **Synthesizing final answer...**\n\n"

            arbitrage_prompt = self._build_arbitrage_prompt(
                question=text, responses=responses, agreement=agreement, protocol=protocol
            )

            referee_messages = [
                {
                    "role": "system",
                    "content": "You are the Swarm Referee. Synthesize expert opinions into a unified answer.",
                },
                {"role": "user", "content": arbitrage_prompt},
            ]

            # Stream referee response
            referee_endpoint = self.endpoints[0]  # Main model
            payload = {"messages": referee_messages, "stream": True, "temperature": 0.2, "max_tokens": -1}

            full_answer = ""
            start_synthesis = time.time()

            try:
                async with client.stream("POST", referee_endpoint, json=payload, timeout=120.0) as response:
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        json_str = line[6:]
                        if json_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(json_str)
                            content = data["choices"][0]["delta"].get("content", "")
                            if content:
                                full_answer += content
                                yield content
                        except Exception:
                            pass
            except Exception as e:
                yield f"\n\n❌ **Synthesis failed:** {e}\n"
                return

            synthesis_time = time.time() - start_synthesis

            # IMPROVEMENT #5: Track performance
            if self.performance_tracker:
                query_hash = hashlib.sha256(text.encode()).hexdigest()
                for i, r in enumerate(valid_results):
                    self.performance_tracker.record_response(
                        agent_id=r["model"],
                        task_type=task_type,
                        query_hash=query_hash,
                        response_text=r["content"],
                        was_selected=(i == 0),  # Placeholder (first expert)
                        consensus_score=agreement,
                        confidence=r["confidence"],
                        response_time=r["time"],
                    )

            # Final metrics
            yield f"\n\n---\n📊 **Swarm Metrics:** Consensus **{agreement:.1%}** | "
            yield f"Experts **{len(valid_results)}** | Synthesis **{synthesis_time:.1f}s** | Protocol **{protocol.value}**\n"

    async def get_consensus(
        self,
        text: str,
        system_prompt: str = "You are a helpful AI assistant.",
        task_type: str = "general",
        verbose: bool = False,
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

        num_llms = len(self.endpoints)

        if num_llms == 0:
            yield "❌ **Error:** No experts available.\n"
            return

        # Route based on swarm size
        elif num_llms == 1:
            # Single LLM mode - direct routing (no consensus needed)
            logger.info("[Arbitrator] Single LLM mode")
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]
            async with httpx.AsyncClient() as client:
                response = await self._query_model_with_timeout(client, self.endpoints[0], messages)
                yield response["content"]
            return

        elif num_llms == 2:
            # NEW: Traffic controller mode
            logger.info("[Arbitrator] Traffic controller mode (2 LLMs)")
            async for chunk in self._traffic_controller_mode(text, system_prompt):
                yield chunk
            return

        # 3+ LLMs: Full consensus mode (existing code below)
        logger.info(f"[Arbitrator] Consensus mode ({num_llms} LLMs)")

        # Build messages
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]

        # Select protocol
        protocol = self.select_protocol(task_type)

        yield f"🔄 **Analyzing...** ({len(self.endpoints)} experts, {protocol.value} protocol)\n\n"

        await _get_consensus_continued(self, messages, protocol, response)

    def _build_critique_prompt(self, original: str, others: List[str], question: str) -> List[Dict]:
        """Build prompt for cross-critique round."""
        other_text = "\n\n".join([f"--- Alternative View {i + 1} ---\n{o}" for i, o in enumerate(others)])

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
        self, question: str, responses: List[str], agreement: float, protocol: ConsensusProtocol
    ) -> str:
        """Build referee synthesis prompt based on protocol."""
        expert_text = "\n\n".join([f"--- Expert {i + 1} ---\n{r}" for i, r in enumerate(responses)])

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

    async def test_arbitrator():
        """Quick test of arbitrator functionality."""
        arb = SwarmArbitrator()

        # Discover experts
        await arb.discover_swarm()
        # [X-Ray auto-fix] print(f"✅ Discovered {len(arb.ports)} experts: {arb.ports}")
        # Test query
        question = "What is 2 + 2?"
        # [X-Ray auto-fix] print(f"\n🔍 Question: {question}\n")
        async for chunk in arb.get_consensus(question, verbose=True):
            print(chunk, end="", flush=True)

        print("\n\n✅ Test complete!")

        # Show stats
        if arb.performance_tracker:
            stats = arb.performance_tracker.get_stats()
            # [X-Ray auto-fix] print(f"\n📊 Performance Stats:")
            # [X-Ray auto-fix] print(f"  Total Queries: {stats['total_queries']}")
            # [X-Ray auto-fix] print(f"  Avg Consensus: {stats['avg_consensus']:.1%}")
            # [X-Ray auto-fix] print(f"  Avg Confidence: {stats['avg_confidence']:.1%}")

    asyncio.run(test_arbitrator())
