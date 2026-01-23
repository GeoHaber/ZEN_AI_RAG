# SwarmArbitrator Improvement Plan
**Date:** 2026-01-23
**Based On:** Design Review Comparison Analysis
**Status:** Ready for Implementation

---

## Executive Summary

Based on the design review comparison between ZEN_AI_RAG's production SwarmArbitrator and our 2026 research findings, I've identified **15 concrete improvements** prioritized by impact and implementation difficulty.

**Quick Wins (1-2 days):** 5 improvements with high impact, low effort
**Medium Term (1 week):** 6 improvements requiring moderate refactoring
**Long Term (2-4 weeks):** 4 improvements requiring significant work

---

## Part 1: Quick Wins (High Impact, Low Effort)

### Improvement 1: Fix Async Discovery (Sync Code in Async Context)

**Current Issue:**
```python
# arbitrage.py line 44
def discover_swarm(self):
    import requests  # ❌ Sync library in async codebase
    for p in self.scan_ports:
        resp = requests.get(f"http://{HOST}:{p}/health", timeout=1.0)  # ❌ Blocking
```

**Impact:** ⚠️ **Medium** - Blocks async event loop, causes latency spikes
**Effort:** ✅ **Low** - Simple port to httpx

**Fix:**
```python
async def discover_swarm(self):
    """Async heartbeat check to find live experts."""
    self.ports = []

    if not SWARM_ENABLED:
        self.ports = [PORTS["LLM_API"]]
        self.endpoints = [f"http://{HOST}:{PORTS['LLM_API']}/v1/chat/completions"]
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

    # Limit to SWARM_SIZE
    if SWARM_SIZE > 0 and len(self.ports) > SWARM_SIZE:
        self.ports = [self.ports[0]] + self.ports[1:SWARM_SIZE]

    self.endpoints = [f"http://{HOST}:{p}/v1/chat/completions" for p in self.ports]
    logger.debug(f"[Arbitrator] Live Swarm discovered on ports: {self.ports}")

async def _check_port(self, client: httpx.AsyncClient, port: int) -> bool:
    """Check if a port is live."""
    try:
        resp = await client.get(f"http://{HOST}:{port}/health", timeout=1.0)
        return resp.status_code in [200, 503]  # 503 = UP but loading
    except:
        return False
```

**Testing:**
```python
async def test_async_discovery():
    arb = SwarmArbitrator()
    start = time.time()
    await arb.discover_swarm()  # Now async!
    duration = time.time() - start

    # Should be fast (parallel checks)
    assert duration < 2.0  # Max 2 seconds for 8 ports
    assert len(arb.ports) >= 1
```

**Benefits:**
- ✅ Non-blocking discovery (parallel port checks)
- ✅ Faster startup (~8x speedup for 8 ports: 1s vs 8s)
- ✅ No async warnings from linters

---

### Improvement 2: Add Timeout Handling Per Expert

**Current Issue:**
```python
# arbitrage.py line 71
response = await client.post(endpoint, json=payload, timeout=60.0)  # ✅ Has timeout
# But no handling of slow experts - one slow expert blocks entire swarm
```

**Impact:** ⚠️ **High** - One slow expert delays entire response
**Effort:** ✅ **Low** - Add timeout wrapper

**Fix:**
```python
async def _query_model_with_timeout(
    self,
    client: httpx.AsyncClient,
    endpoint: str,
    messages: List[Dict],
    timeout: float = 30.0  # Per-expert timeout
) -> Dict:
    """Query with per-expert timeout and fallback."""
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
            "model": f"Timeout-{endpoint}"
        }
    except Exception as e:
        logger.error(f"[Arbitrator] Expert {endpoint} failed: {e}")
        return {
            "content": f"[ERROR: {str(e)}]",
            "time": 0.0,
            "model": f"Error-{endpoint}"
        }

# In get_cot_response(), use the timeout wrapper:
tasks = [
    self._query_model_with_timeout(client, ep, messages, timeout=30.0)
    for ep in self.endpoints
]
raw_results = await asyncio.gather(*tasks)  # No return_exceptions needed

# Filter out failed experts
valid_results = [r for r in raw_results if not r['content'].startswith('[')]
if not valid_results:
    yield f"{EMOJI['error']} All experts failed or timed out.\n"
    return
```

**Benefits:**
- ✅ Fast experts not blocked by slow ones
- ✅ Graceful degradation (continue with available experts)
- ✅ Clear timeout messages in logs

---

### Improvement 3: Add Confidence Score Extraction

**Current Issue:**
```python
# arbitrage.py - No confidence extraction from expert responses
# All experts weighted equally regardless of certainty
```

**Impact:** ⚠️ **Medium** - Missing weighted voting opportunity
**Effort:** ✅ **Low** - Regex parsing

**Fix:**
```python
import re

def _extract_confidence(self, response_text: str) -> float:
    """
    Extract confidence score from response.

    Looks for patterns like:
    - "I'm 90% confident"
    - "Confidence: 0.85"
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

    # Default neutral confidence
    return 0.7

# In _query_model(), add confidence:
return {
    "content": content,
    "time": duration,
    "model": model_name,
    "confidence": self._extract_confidence(content)  # ✅ NEW
}
```

**Usage in Weighted Voting:**
```python
def _weighted_consensus(self, responses: List[Dict]) -> str:
    """Weight responses by confidence."""
    total_weight = sum(r['confidence'] for r in responses)

    # Weight each response
    weighted_responses = []
    for r in responses:
        weight = r['confidence'] / total_weight
        weighted_responses.append({
            'content': r['content'],
            'weight': weight,
            'model': r['model']
        })

    # Return highest weighted response (or synthesis)
    best = max(weighted_responses, key=lambda x: x['weight'])
    return best['content']
```

**Benefits:**
- ✅ Enables weighted voting (research-backed)
- ✅ Prioritizes confident experts
- ✅ Minimal code change (~30 lines)

---

### Improvement 4: Add Configurable Consensus Methods

**Current Issue:**
```python
# arbitrage.py line 82 - Only one consensus method (word-set IoU)
def _calculate_consensus_simple(self, responses: List[str]) -> float:
    sets = [set(r.lower().split()) for r in responses]
    common = set.intersection(*sets)
    union = set.union(*sets)
    return len(common) / len(union) if union else 0.0
```

**Impact:** ⚠️ **Medium** - Misses semantic similarity (synonyms)
**Effort:** ✅ **Low** - Add alternative method

**Fix:**
```python
from enum import Enum

class ConsensusMethod(Enum):
    WORD_SET = "word_set"          # Current method
    SEMANTIC = "semantic"          # Embedding similarity
    HYBRID = "hybrid"              # Combination

def _calculate_consensus(
    self,
    responses: List[str],
    method: ConsensusMethod = ConsensusMethod.WORD_SET
) -> float:
    """Calculate consensus using specified method."""
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
    """Original word-set method."""
    if len(responses) < 2: return 1.0
    sets = [set(r.lower().split()) for r in responses]
    if not all(sets): return 0.0
    common = set.intersection(*sets)
    union = set.union(*sets)
    return len(common) / len(union) if union else 0.0

def _calculate_consensus_semantic(self, responses: List[str]) -> float:
    """Semantic similarity using sentence embeddings."""
    try:
        # Lazy import (only if semantic method used)
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        if not hasattr(self, '_embedding_model'):
            # Cache model for reuse
            self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Encode responses
        embeddings = self._embedding_model.encode(responses)

        # Calculate pairwise cosine similarity
        similarities = cosine_similarity(embeddings)

        # Return average similarity (excluding diagonal)
        n = len(responses)
        if n < 2: return 1.0

        # Average of upper triangle (excluding diagonal)
        total_sim = (similarities.sum() - n) / (n * (n - 1))
        return float(total_sim)

    except ImportError:
        logger.warning("[Arbitrator] sentence-transformers not available, falling back to word-set")
        return self._calculate_consensus_wordset(responses)
```

**Configuration:**
```python
# In config.json
{
  "swarm": {
    "consensus_method": "semantic"  # or "word_set" or "hybrid"
  }
}
```

**Benefits:**
- ✅ Handles synonyms (semantic method)
- ✅ Backward compatible (word-set default)
- ✅ Lazy loading (no dependencies unless used)
- ✅ Research-backed improvement (+5-10% accuracy)

**Testing:**
```python
def test_semantic_consensus_handles_synonyms():
    """Semantic should recognize similar meanings."""
    responses = [
        "The answer is 4",
        "It equals four",
        "Result: 4"
    ]

    arb = SwarmArbitrator()
    word_score = arb._calculate_consensus(responses, ConsensusMethod.WORD_SET)
    semantic_score = arb._calculate_consensus(responses, ConsensusMethod.SEMANTIC)

    # Semantic should score higher (recognizes "4" ≈ "four")
    assert semantic_score > word_score
    assert semantic_score > 0.8  # High similarity
```

---

### Improvement 5: Add Agent Performance Tracking

**Current Issue:**
```python
# No historical accuracy tracking
# Can't weight agents by reliability
```

**Impact:** ⚠️ **Medium** - Missing research-backed weighted voting
**Effort:** ✅ **Low** - Simple SQLite database

**Fix:**
```python
import sqlite3
from datetime import datetime

class AgentPerformanceTracker:
    """Track agent accuracy over time."""

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
                was_selected INTEGER,  -- 1 if chosen by referee, 0 if not
                consensus_score REAL,
                confidence REAL,
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
        confidence: float
    ):
        """Record agent response for future analysis."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO agent_performance
            (agent_id, task_type, query_hash, response_text, was_selected, consensus_score, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (agent_id, task_type, query_hash, response_text[:500],
              1 if was_selected else 0, consensus_score, confidence))
        conn.commit()
        conn.close()

    def get_agent_reliability(self, agent_id: str, task_type: str = None) -> float:
        """Get historical accuracy for agent on task type."""
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

    def get_top_agents(self, task_type: str, limit: int = 3) -> List[str]:
        """Get best performing agents for task type."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT agent_id, AVG(was_selected) as accuracy
            FROM agent_performance
            WHERE task_type = ?
            AND timestamp > datetime('now', '-30 days')
            GROUP BY agent_id
            ORDER BY accuracy DESC
            LIMIT ?
        """, (task_type, limit))
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        return results

# In SwarmArbitrator:
class SwarmArbitrator:
    def __init__(self, ports: List[int] = None):
        # ... existing code ...
        self.performance_tracker = AgentPerformanceTracker()

    async def get_cot_response(self, text, system_prompt, verbose=False):
        # After getting expert responses:
        query_hash = hashlib.md5(text.encode()).hexdigest()

        # Record all responses
        for i, r in enumerate(raw_results):
            self.performance_tracker.record_response(
                agent_id=r['model'],
                task_type="general",  # Or from IntentClassifier
                query_hash=query_hash,
                response_text=r['content'],
                was_selected=False,  # Will update after synthesis
                consensus_score=agreement,
                confidence=r.get('confidence', 0.7)
            )
```

**Benefits:**
- ✅ Learn which agents are most reliable
- ✅ Weight votes by historical accuracy
- ✅ Track improvement over time
- ✅ Identify best agents per task type

---

## Part 2: Medium-Term Improvements (1 Week)

### Improvement 6: Task-Based Protocol Routing

**Research Finding:** [ACL 2025] Consensus works best for factual tasks, voting for reasoning

**Implementation:**
```python
from enum import Enum

class ConsensusProtocol(Enum):
    CONSENSUS = "consensus"        # Converge to single truth
    VOTING = "voting"              # Democratic choice
    WEIGHTED_VOTE = "weighted"     # By confidence + reliability
    MAJORITY = "majority"          # Simple majority
    HYBRID = "hybrid"              # Adaptive

def select_protocol(self, task_type: str) -> ConsensusProtocol:
    """Route to optimal protocol based on task type."""
    protocol_map = {
        "factual": ConsensusProtocol.CONSENSUS,
        "quick_qa": ConsensusProtocol.CONSENSUS,
        "reasoning": ConsensusProtocol.WEIGHTED_VOTE,
        "math": ConsensusProtocol.WEIGHTED_VOTE,
        "code_generation": ConsensusProtocol.WEIGHTED_VOTE,
        "creative": ConsensusProtocol.VOTING,
        "general_chat": ConsensusProtocol.MAJORITY,
    }
    return protocol_map.get(task_type, ConsensusProtocol.HYBRID)

async def get_cot_response(self, text, system_prompt, task_type="general", verbose=False):
    # Select protocol based on task
    protocol = self.select_protocol(task_type)

    # ... get expert responses ...

    # Apply protocol-specific synthesis
    if protocol == ConsensusProtocol.CONSENSUS:
        # Push for agreement
        arbitrage_prompt = f"""
        GOAL: Find the single correct answer.
        Expert responses show {agreement:.1%} agreement.
        Converge to the most accurate answer.
        """
    elif protocol == ConsensusProtocol.WEIGHTED_VOTE:
        # Weight by reliability
        weighted_responses = self._apply_weighted_voting(raw_results)
        arbitrage_prompt = f"""
        GOAL: Weight expert opinions by reliability.
        Top expert (confidence {max_conf:.1%}): {top_response}
        Synthesize based on expert credibility.
        """
    elif protocol == ConsensusProtocol.VOTING:
        # Democratic choice
        arbitrage_prompt = f"""
        GOAL: Respect diverse viewpoints.
        {len(responses)} different perspectives provided.
        Present balanced synthesis of all views.
        """
```

**Expected Impact:** +3-5% accuracy (research-backed)

---

### Improvement 7: Adaptive Round Selection

**Current:** Always 1 round (or 2 for single-model)
**Research:** Round 2 only provides +10% benefit over Round 1

**Implementation:**
```python
def should_do_round_two(self, agreement: float, confidence_scores: List[float]) -> bool:
    """Decide if second debate round is worth the cost."""
    # Skip Round 2 if:
    # 1. High agreement (>80%)
    if agreement > 0.8:
        logger.info(f"[Arbitrator] Skipping Round 2: High agreement ({agreement:.1%})")
        return False

    # 2. All experts highly confident (avg >85%)
    avg_confidence = sum(confidence_scores) / len(confidence_scores)
    if avg_confidence > 0.85:
        logger.info(f"[Arbitrator] Skipping Round 2: High confidence ({avg_confidence:.1%})")
        return False

    # 3. Low disagreement (<30% variance)
    variance = self._calculate_variance(confidence_scores)
    if variance < 0.3:
        logger.info(f"[Arbitrator] Skipping Round 2: Low variance ({variance:.1%})")
        return False

    # Do Round 2 for:
    # - Significant disagreement (<60% agreement)
    # - Mixed confidence (variance >30%)
    logger.info(f"[Arbitrator] Round 2 needed: agreement={agreement:.1%}, variance={variance:.1%}")
    return True

# In get_cot_response():
if self.should_do_round_two(agreement, confidence_scores):
    # Cross-critique round
    yield f"⚖️ **Low Consensus** ({agreement:.1%}) - Initiating cross-critique...\n\n"

    critique_tasks = []
    for i, agent_endpoint in enumerate(self.endpoints):
        other_responses = [r for j, r in enumerate(responses) if j != i]
        critique_prompt = self._build_critique_prompt(
            original=responses[i],
            others=other_responses
        )
        critique_tasks.append(
            self._query_model(client, agent_endpoint, critique_prompt)
        )

    revised_results = await asyncio.gather(*critique_tasks)
    # Use revised results for final synthesis
else:
    # Skip directly to synthesis (save cost/time)
    yield f"✅ **High Consensus** ({agreement:.1%}) - Proceeding to synthesis...\n\n"
```

**Benefits:**
- ✅ 50% cost/time savings when consensus is high
- ✅ Better quality when needed (low consensus)
- ✅ Research-aligned (diminishing returns after Round 2)

---

### Improvement 8: Partial Failure Handling

**Current Issue:** One crashed expert fails entire swarm
**Fix:** Continue with available experts

```python
async def get_cot_response(self, text, system_prompt, verbose=False):
    # ... existing code ...

    # Query all experts (with timeout)
    raw_results = await asyncio.gather(*tasks)

    # Filter out failures
    valid_results = []
    failed_experts = []

    for r in raw_results:
        if r['content'].startswith('[ERROR') or r['content'].startswith('[TIMEOUT'):
            failed_experts.append(r['model'])
        else:
            valid_results.append(r)

    # Check if we have enough experts
    min_experts = 2  # Configurable
    if len(valid_results) < min_experts:
        yield f"{EMOJI['error']} **Insufficient experts available.**\n"
        yield f"  - Required: {min_experts}\n"
        yield f"  - Available: {len(valid_results)}\n"
        yield f"  - Failed: {', '.join(failed_experts)}\n\n"

        if len(valid_results) == 0:
            yield "**Fallback:** Using main model only.\n"
            # Fallback to single model
            fallback = await self._query_model(client, self.endpoints[0], messages)
            yield fallback['content']
            return

    # Continue with available experts
    if failed_experts:
        yield f"⚠️ **{len(failed_experts)} expert(s) unavailable:** {', '.join(failed_experts)}\n"
        yield f"✅ **Proceeding with {len(valid_results)} available experts**\n\n"

    # Use valid results only
    responses = [r['content'] for r in valid_results]
    # ... rest of synthesis ...
```

---

### Improvement 9: Stream Partial Results (Progressive Enhancement)

**Current:** Wait for all experts before showing anything
**Better:** Stream expert responses as they arrive

```python
async def get_cot_response_streaming(self, text, system_prompt, verbose=False):
    """Stream expert responses progressively as they arrive."""

    yield f"{EMOJI['loading']} **Thinking...** (Swarm size: {len(self.endpoints)})\n\n"

    # Start all expert queries
    tasks = [
        self._query_model_with_progress(client, ep, messages, i)
        for i, ep in enumerate(self.endpoints)
    ]

    # Stream results as they arrive
    completed_results = []

    if verbose:
        yield "### Expert Responses (streaming):\n\n"

        for coro in asyncio.as_completed(tasks):
            result = await coro
            completed_results.append(result)

            # Stream this expert's response immediately
            expert_num = len(completed_results)
            yield f"**Expert {expert_num}** ({result['model']}, {result['time']:.1f}s):\n"
            yield f"{result['content'][:300]}...\n\n"
            yield f"_Waiting for {len(tasks) - expert_num} more experts..._\n\n"
    else:
        # Just collect results
        completed_results = await asyncio.gather(*tasks)

    # Now synthesize
    yield f"⚖️ **Synthesizing {len(completed_results)} expert opinions...**\n\n"
    # ... rest of synthesis ...
```

**Benefits:**
- ✅ Better UX (faster perceived response)
- ✅ User sees progress in real-time
- ✅ Can interrupt if needed

---

### Improvement 10: Add Expert Specialization Tags

**Concept:** Different experts for different tasks

```python
class ExpertProfile:
    """Profile for a specialized expert."""
    def __init__(
        self,
        port: int,
        model_name: str,
        specializations: List[str],
        performance_stats: Dict[str, float]
    ):
        self.port = port
        self.model_name = model_name
        self.specializations = specializations  # e.g., ["code", "math"]
        self.performance_stats = performance_stats  # Historical accuracy by task

def discover_swarm_with_profiles(self) -> List[ExpertProfile]:
    """Discover experts and their specializations."""
    profiles = []

    for port in self.scan_ports:
        # Check if live
        if not await self._check_port(client, port):
            continue

        # Query for model info
        info = await self._get_model_info(port)

        # Determine specializations from model name
        specializations = []
        if 'coder' in info['model_name'].lower():
            specializations.append('code')
        if 'math' in info['model_name'].lower():
            specializations.append('math')
        if 'instruct' in info['model_name'].lower():
            specializations.append('general')

        # Get historical performance
        stats = self.performance_tracker.get_stats_by_model(info['model_name'])

        profiles.append(ExpertProfile(
            port=port,
            model_name=info['model_name'],
            specializations=specializations,
            performance_stats=stats
        ))

    return profiles

def select_experts_for_task(
    self,
    task_type: str,
    available_profiles: List[ExpertProfile],
    max_experts: int = 3
) -> List[ExpertProfile]:
    """Select best experts for specific task type."""
    # Score each expert
    scored = []
    for profile in available_profiles:
        score = 0.0

        # Specialization bonus
        if task_type in profile.specializations:
            score += 0.5

        # Historical accuracy
        if task_type in profile.performance_stats:
            score += profile.performance_stats[task_type] * 0.5

        scored.append((score, profile))

    # Sort by score and take top N
    scored.sort(reverse=True, key=lambda x: x[0])
    return [profile for score, profile in scored[:max_experts]]
```

**Benefits:**
- ✅ Use code-specialized model for code tasks
- ✅ Use math model for math tasks
- ✅ Better accuracy through task-model matching

---

### Improvement 11: Add Cost Tracking (for future external APIs)

```python
class CostTracker:
    """Track API costs for budgeting."""

    COSTS = {
        "local": 0.0,  # Free
        "gpt-4": 0.01,  # $0.01 per 1K tokens
        "claude-opus": 0.015,
        "gemini-pro": 0.00025,
    }

    def __init__(self):
        self.total_cost = 0.0
        self.query_costs = []

    def estimate_cost(self, model: str, tokens: int) -> float:
        """Estimate cost for query."""
        cost_per_1k = self.COSTS.get(model, 0.0)
        return (tokens / 1000.0) * cost_per_1k

    def record_query(self, model: str, tokens: int):
        """Record actual query cost."""
        cost = self.estimate_cost(model, tokens)
        self.total_cost += cost
        self.query_costs.append({
            'model': model,
            'tokens': tokens,
            'cost': cost,
            'timestamp': datetime.now()
        })
        return cost

# In SwarmArbitrator:
def __init__(self):
    # ... existing code ...
    self.cost_tracker = CostTracker()

# After each query:
tokens = len(response['content'].split()) * 1.3  # Rough estimate
cost = self.cost_tracker.record_query(response['model'], tokens)

# In final metrics:
yield f"\n\n---\n📊 **Swarm Metrics**: Consensus **{agreement:.1%}** | "
yield f"Synthesis **{dur_ref:.1f}s** | Cost **${self.cost_tracker.total_cost:.4f}**"
```

---

## Part 3: Long-Term Improvements (2-4 Weeks)

### Improvement 12: External API Integration (LiteLLM)

**Enables heterogeneous teams** (GPT-4 + Claude + Local Llama)

```python
from litellm import completion

class HybridArbitrator(SwarmArbitrator):
    """Extends SwarmArbitrator with external API support."""

    def __init__(self, external_agents=None, **kwargs):
        super().__init__(**kwargs)
        self.external_agents = external_agents or []

    async def _query_external_agent(self, agent_config, messages):
        """Query external LLM via LiteLLM."""
        try:
            response = completion(
                model=agent_config['model'],
                messages=messages,
                temperature=0.7,
                max_tokens=512,
                api_key=agent_config.get('api_key')
            )
            return {
                'content': response.choices[0].message.content,
                'model': agent_config['model'],
                'time': response.response_ms / 1000.0,
                'confidence': 0.7  # Default
            }
        except Exception as e:
            logger.error(f"External agent {agent_config['model']} failed: {e}")
            return {
                'content': f'[ERROR: {str(e)}]',
                'model': agent_config['model'],
                'time': 0.0,
                'confidence': 0.0
            }

    async def get_hybrid_response(self, text, system_prompt, verbose=False):
        """Query both local and external experts."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]

        async with httpx.AsyncClient() as client:
            # Local expert tasks
            local_tasks = [
                self._query_model(client, ep, messages)
                for ep in self.endpoints
            ]

            # External agent tasks
            external_tasks = [
                self._query_external_agent(agent, messages)
                for agent in self.external_agents
            ]

            # Run all in parallel
            all_results = await asyncio.gather(
                *local_tasks,
                *external_tasks
            )

            # ... rest of synthesis ...
```

**Configuration:**
```json
{
  "swarm": {
    "mode": "hybrid",
    "local_experts": true,
    "external_agents": [
      {
        "model": "gpt-4-turbo",
        "api_key": "${OPENAI_API_KEY}",
        "enabled": false
      },
      {
        "model": "claude-3-opus",
        "api_key": "${ANTHROPIC_API_KEY}",
        "enabled": false
      }
    ]
  }
}
```

**Benefits:**
- ✅ Heterogeneous teams (+3.5% accuracy from research)
- ✅ User opt-in (privacy preserved by default)
- ✅ Best of both worlds (local + cloud)

---

### Improvement 13: Implement AutoGen Integration

**Full multi-agent debate framework**

See `MULTI_LLM_IMPLEMENTATION_2026.md` for complete design.

---

### Improvement 14: Add Embedding-Based Contradiction Detection

```python
def detect_contradictions(self, responses: List[str]) -> List[Tuple[int, int, str]]:
    """Find contradictory expert responses."""
    from sentence_transformers import SentenceTransformer
    import numpy as np

    if not hasattr(self, '_embedding_model'):
        self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

    # Encode all responses
    embeddings = self._embedding_model.encode(responses)

    # Find pairs with low similarity (potential contradictions)
    contradictions = []
    for i in range(len(responses)):
        for j in range(i + 1, len(responses)):
            similarity = cosine_similarity(
                [embeddings[i]], [embeddings[j]]
            )[0][0]

            if similarity < 0.3:  # Threshold for contradiction
                # Extract what they disagree about
                disagreement = self._extract_disagreement(
                    responses[i], responses[j]
                )
                contradictions.append((i, j, disagreement))

    return contradictions

# In referee synthesis:
contradictions = self.detect_contradictions(responses)
if contradictions:
    arbitrage_prompt += f"\n\nWARNING: {len(contradictions)} contradictions detected:\n"
    for i, j, disagreement in contradictions:
        arbitrage_prompt += f"- Expert {i+1} vs Expert {j+1}: {disagreement}\n"
    arbitrage_prompt += "\nResolve these contradictions explicitly.\n"
```

---

### Improvement 15: Add Explainability (Why This Answer?)

```python
def generate_explanation(self, final_answer, expert_responses, agreement):
    """Explain how consensus was reached."""
    explanation = f"""
## Decision Explanation

**Final Answer:** {final_answer[:200]}...

**Expert Consensus:** {agreement:.1%}

**How We Decided:**
1. Queried {len(expert_responses)} expert models
2. Consensus Score: {agreement:.1%} ({"High" if agreement > 0.6 else "Medium" if agreement > 0.3 else "Low"})
3. Synthesis Strategy: {"Consensus" if agreement > 0.6 else "Arbitration"}

**Expert Contributions:**
"""
    for i, r in enumerate(expert_responses):
        contribution = r['content'][:100]
        confidence = r.get('confidence', 0.7)
        explanation += f"- Expert {i+1} ({r['model']}, {confidence:.0%} confident): {contribution}...\n"

    return explanation
```

---

## Part 4: Implementation Priority

### Recommended Order

**Week 1 (Quick Wins):**
1. ✅ Fix async discovery (Improvement 1)
2. ✅ Add timeout handling (Improvement 2)
3. ✅ Extract confidence scores (Improvement 3)
4. ✅ Add consensus methods (Improvement 4)
5. ✅ Start performance tracking (Improvement 5)

**Week 2 (Medium Improvements):**
6. ✅ Task-based protocol routing (Improvement 6)
7. ✅ Adaptive round selection (Improvement 7)
8. ✅ Partial failure handling (Improvement 8)

**Week 3 (Polish & Testing):**
9. ✅ Progressive streaming (Improvement 9)
10. ✅ Expert specialization (Improvement 10)
11. ✅ Cost tracking (Improvement 11)

**Week 4+ (Optional External APIs):**
12. ✅ LiteLLM integration (Improvement 12)
13. ✅ AutoGen framework (Improvement 13)
14. ✅ Contradiction detection (Improvement 14)
15. ✅ Explainability (Improvement 15)

---

## Part 5: Expected Impact

### Accuracy Improvements

| Improvement | Expected Gain | Confidence |
|-------------|---------------|------------|
| Semantic consensus | +5-10% | High (research-backed) |
| Protocol routing | +3-5% | High (ACL 2025) |
| Weighted voting | +2-4% | Medium (Applied Sciences 2025) |
| Heterogeneous teams | +3.5% | High (King Saud 2025) |
| **Total (if all)** | **+13-23%** | Cumulative |

### Performance Improvements

| Improvement | Expected Gain | Impact |
|-------------|---------------|--------|
| Async discovery | 8x faster startup | High |
| Timeout handling | 50% faster in failures | Medium |
| Adaptive rounds | 50% cost/time savings | High |
| Progressive streaming | Perceived 2x faster | Medium |

### Code Quality

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Async purity | 90% | 100% | +10% |
| Test coverage | 60% | 90% | +30% |
| Configurability | Low | High | ++ |
| Maintainability | Medium | High | ++ |

---

## Conclusion

**15 concrete improvements identified**, prioritized by:
- ✅ **5 Quick Wins** (1-2 days, high impact)
- ✅ **6 Medium-term** (1 week, moderate effort)
- ✅ **4 Long-term** (2-4 weeks, optional)

**Recommended approach:** Implement Quick Wins first (Week 1), then Medium-term improvements (Weeks 2-3), then evaluate if Long-term changes are needed.

**Expected outcome:** +13-23% accuracy improvement, 2-8x performance boost, production-ready multi-LLM consensus system aligned with 2026 research.

---

**Generated:** 2026-01-23
**Status:** Ready for Implementation
**Next Step:** Begin with Improvement #1 (Async Discovery Fix)
