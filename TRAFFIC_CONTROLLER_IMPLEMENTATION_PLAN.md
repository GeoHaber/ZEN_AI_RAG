# Traffic Controller Implementation Plan

**Date:** 2026-01-24
**Status:** ✅ RESEARCH COMPLETE - READY TO IMPLEMENT
**Goal:** Implement efficient 2-LLM traffic controller pattern

---

## 📋 Summary of Work Completed

### 1. Research Complete ✅
**File:** `TRAFFIC_CONTROLLER_LLM_RESEARCH.md`

**Findings:**
- **Best LLM:** Phi-3-mini (3.8B parameters)
  - Latency: 150-200ms
  - Accuracy: ~88%
  - Memory: ~2.5GB
  - Size: 2.3GB (quantized Q4)

**Alternatives:**
- TinyLlama (1.1B) - Faster but less accurate
- SetFit (110M) - Needs fine-tuning

### 2. Strategy Analysis Complete ✅
**File:** `MULTI_LLM_STRATEGY_ANALYSIS.md`

**Key Finding:** Current implementation MISSING 2-LLM mode
- 1 LLM: ✅ Works (direct routing)
- 2 LLMs: ❌ Falls through to 3+ logic (inefficient)
- 3+ LLMs: ✅ Works (full consensus)

**Recommended Strategy:** Traffic Controller (Strategy A)
- 60% cost savings
- 70% faster on easy queries
- Same quality on hard queries

### 3. Benchmark Infrastructure Complete ✅
**File:** `benchmark_traffic_controller.py`

**Features:**
- 100-query test suite (30 easy, 40 medium, 30 hard)
- Latency profiling
- Memory profiling
- Accuracy tracking
- JSON export

**Test Results (Mock Controller):**
```
Latency:  154.7ms avg (PASS < 300ms)
Accuracy: 35% (FAIL - mock heuristics too simple)
Cost:     60% savings (PASS)
```

---

## 🚀 Implementation Plan

### Phase 1: Add Traffic Controller Method (1-2 hours)

**File to Modify:** `swarm_arbitrator.py`

**Add Three New Methods:**

#### 1. `_traffic_controller_mode()` - Main orchestrator
```python
async def _traffic_controller_mode(
    self,
    query: str,
    system_prompt: str = "You are a helpful AI assistant."
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

    # Step 1: Evaluate difficulty
    yield "🚦 Evaluating query complexity...\n"
    evaluation = await self._evaluate_query_difficulty(query)

    difficulty = evaluation['difficulty']
    confidence = evaluation['confidence']

    # Step 2: Route based on evaluation
    if difficulty == 'easy' and confidence > 0.8:
        # Fast LLM handles it
        yield f"💨 **Fast response** ({difficulty}, confidence: {confidence:.0%})\n\n"
        async for chunk in self._stream_from_llm(fast_llm, query, system_prompt):
            yield chunk

    elif difficulty == 'hard' or confidence < 0.5:
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
```

#### 2. `_evaluate_query_difficulty()` - Classification
```python
async def _evaluate_query_difficulty(self, query: str) -> Dict:
    """
    Use fast LLM to classify query difficulty.

    Returns:
        {
            "difficulty": "easy|medium|hard",
            "domain": "code|math|creative|factual|reasoning",
            "confidence": 0.0-1.0,
            "reasoning": "brief explanation"
        }
    """
    # Use traffic controller LLM (Phi-3-mini on port 8020)
    controller_endpoint = f"http://{self.host}:8020/v1/chat/completions"

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
                timeout=5.0  # Fast timeout for classifier
            )

            # Parse JSON response
            content = response['content']

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
            "reasoning": "Classification failed, defaulting to medium"
        }
```

#### 3. Helper methods
```python
async def _stream_from_llm(
    self,
    endpoint: str,
    query: str,
    system_prompt: str
) -> AsyncGenerator[str, None]:
    """Stream response from a single LLM."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ]

    payload = {
        "messages": messages,
        "stream": True,
        "temperature": 0.7,
        "max_tokens": -1
    }

    async with httpx.AsyncClient() as client:
        async with client.stream('POST', endpoint, json=payload, timeout=120.0) as response:
            async for line in response.aiter_lines():
                if line.startswith('data: '):
                    json_str = line[6:]
                    if json_str.strip() == '[DONE]':
                        break
                    try:
                        data = json.loads(json_str)
                        content = data['choices'][0]['delta'].get('content', '')
                        if content:
                            yield content
                    except:
                        pass

async def _get_answer(
    self,
    endpoint: str,
    query: str,
    system_prompt: str
) -> str:
    """Get complete answer from a single LLM (non-streaming)."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ]

    async with httpx.AsyncClient() as client:
        response = await self._query_model_with_timeout(client, endpoint, messages)
        return response['content']
```

---

### Phase 2: Update Main Dispatcher

**Modify:** `get_consensus()` method

```python
async def get_consensus(
    self,
    text: str,
    system_prompt: str = "You are a helpful AI assistant.",
    task_type: str = "general",
    verbose: bool = False
) -> AsyncGenerator[str, None]:
    """Smart routing based on swarm size."""

    # Discover swarm
    if not self.endpoints:
        await self.discover_swarm()

    num_llms = len(self.endpoints)

    if num_llms == 0:
        yield "❌ No LLMs available\n"
        return

    elif num_llms == 1:
        # Direct routing (already works)
        logger.info("[Arbitrator] Single LLM mode")
        async for chunk in self._single_llm_mode(text, system_prompt):
            yield chunk

    elif num_llms == 2:
        # NEW: Traffic controller mode
        logger.info("[Arbitrator] Traffic controller mode (2 LLMs)")
        async for chunk in self._traffic_controller_mode(text, system_prompt):
            yield chunk

    else:
        # 3+ LLMs: Full consensus (existing code)
        logger.info(f"[Arbitrator] Consensus mode ({num_llms} LLMs)")
        # ... existing full consensus logic ...
```

---

### Phase 3: Configuration

**Add to:** `config_system.py`

```python
@dataclass
class AppConfig:
    # Swarm Settings
    SWARM_SIZE: int = 3
    SWARM_ENABLED: bool = False

    # Traffic Controller Settings (NEW)
    TRAFFIC_CONTROLLER_ENABLED: bool = True
    TRAFFIC_CONTROLLER_PORT: int = 8020  # Phi-3-mini
    TRAFFIC_CONTROLLER_THRESHOLD: float = 0.8  # Confidence threshold
    TRAFFIC_CONTROLLER_MODEL: str = "Phi-3-mini-4k-instruct-q4.gguf"
```

---

### Phase 4: Setup Phi-3-mini

**Download Model:**
```bash
cd models/
wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf
```

**Start Traffic Controller:**
```bash
# Terminal 1: Traffic Controller (Phi-3-mini)
llamafile -m models/Phi-3-mini-4k-instruct-q4.gguf --port 8020 --threads 4

# Terminal 2: Main LLM (your current model)
python start_llm.py  # Port 8001

# Terminal 3: Optional powerful LLM
llamafile -m models/llama-3-70b.gguf --port 8005 --threads 8
```

**Test:**
```bash
# Test 2-LLM mode
export SWARM_SIZE=2
export SWARM_ENABLED=True
python zena_modern.py
```

---

### Phase 5: Benchmark Real Performance

**Run Benchmark with Phi-3-mini:**
```bash
# Modify benchmark_traffic_controller.py to use real Phi-3-mini
# Replace MockTrafficController with real HTTP calls

python benchmark_traffic_controller.py --profile memory
```

**Expected Results:**
```
Latency:    150-200ms avg
Accuracy:   85-90%
Memory:     2.5GB
Cost:       60% savings
```

---

### Phase 6: Profiling & Optimization

**Use cProfile for bottlenecks:**
```bash
python -m cProfile -o profile.stats benchmark_traffic_controller.py
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"
```

**Expected Bottlenecks:**
1. JSON parsing (5-10ms) - Use `orjson` instead
2. HTTP overhead (20-30ms) - Keep connection pools
3. Embedding calculation (if using semantic consensus)

**Optimizations:**
```python
# 1. Use orjson for faster JSON parsing
import orjson
result = orjson.loads(content)

# 2. Keep connection pools alive
self._client = httpx.AsyncClient(
    limits=httpx.Limits(max_connections=10),
    timeout=httpx.Timeout(60.0)
)

# 3. Cache embeddings for repeated queries
@lru_cache(maxsize=1000)
def get_embedding(text: str):
    return self._embedding_model.encode(text)
```

---

## 📊 Success Criteria

### Minimum Viable Product (MVP):
- ✅ Latency < 300ms (avg classification)
- ✅ Accuracy > 80% (routing decisions)
- ✅ Memory < 3GB (Phi-3-mini)
- ✅ Cost savings > 50% vs full consensus

### Ideal Performance:
- ⭐ Latency < 150ms (avg classification)
- ⭐ Accuracy > 90% (routing decisions)
- ⭐ Memory < 2.5GB
- ⭐ Cost savings > 60%

---

## 🧪 Testing Plan

### Unit Tests:
```python
# tests/test_traffic_controller.py
async def test_classify_easy_query():
    """Test classification of easy query."""
    arb = SwarmArbitrator(ports=[8020, 8001, 8005])
    result = await arb._evaluate_query_difficulty("What is 2+2?")
    assert result['difficulty'] == 'easy'
    assert result['confidence'] > 0.8

async def test_classify_hard_query():
    """Test classification of hard query."""
    arb = SwarmArbitrator(ports=[8020, 8001, 8005])
    result = await arb._evaluate_query_difficulty("Prove the Riemann Hypothesis")
    assert result['difficulty'] == 'hard'

async def test_traffic_controller_routing():
    """Test that easy queries go to fast LLM."""
    arb = SwarmArbitrator(ports=[8020, 8001, 8005])

    # Easy query should use fast LLM (1 call)
    calls_before = arb.performance_tracker.total_queries
    async for _ in arb._traffic_controller_mode("What is 2+2?"):
        pass
    calls_after = arb.performance_tracker.total_queries

    # Should be 2 calls: 1 classification + 1 answer
    assert (calls_after - calls_before) <= 2
```

### Integration Tests:
```python
async def test_2llm_vs_consensus_cost():
    """Verify cost savings vs full consensus."""

    # Baseline: Full consensus (3 LLMs)
    arb_consensus = SwarmArbitrator(ports=[8001, 8005, 8006])
    baseline_cost = await run_100_queries(arb_consensus)

    # Traffic controller (2 LLMs)
    arb_traffic = SwarmArbitrator(ports=[8020, 8001])
    traffic_cost = await run_100_queries(arb_traffic)

    savings_percent = (baseline_cost - traffic_cost) / baseline_cost * 100
    assert savings_percent > 50, f"Only {savings_percent:.1f}% savings"
```

---

## 📈 Performance Monitoring

**Add Metrics Dashboard:**
```python
# swarm_metrics.py
class TrafficControllerMetrics:
    """Track traffic controller performance."""

    def __init__(self):
        self.classifications = []
        self.routing_decisions = []
        self.latencies = []

    def record_classification(
        self,
        query: str,
        difficulty: str,
        confidence: float,
        latency_ms: float,
        route_used: str
    ):
        self.classifications.append({
            "query": query[:100],
            "difficulty": difficulty,
            "confidence": confidence,
            "latency_ms": latency_ms,
            "route": route_used,
            "timestamp": datetime.now()
        })

    def get_stats(self) -> Dict:
        """Get aggregate statistics."""
        return {
            "total_classifications": len(self.classifications),
            "avg_latency_ms": statistics.mean([c['latency_ms'] for c in self.classifications]),
            "avg_confidence": statistics.mean([c['confidence'] for c in self.classifications]),
            "routing_breakdown": {
                "fast_llm": sum(1 for c in self.classifications if c['route'] == 'fast'),
                "powerful_llm": sum(1 for c in self.classifications if c['route'] == 'powerful'),
                "verified": sum(1 for c in self.classifications if c['route'] == 'verified')
            }
        }
```

---

## 🎯 Next Steps (In Order)

1. **[ ] Implement Phase 1** - Add 3 new methods to `swarm_arbitrator.py`
2. **[ ] Implement Phase 2** - Update dispatcher
3. **[ ] Implement Phase 3** - Add config options
4. **[ ] Download Phi-3-mini** - Setup traffic controller LLM
5. **[ ] Test locally** - Verify 2-LLM mode works
6. **[ ] Run benchmark** - Profile real performance
7. **[ ] Optimize** - Fix bottlenecks found
8. **[ ] Write tests** - Unit + integration tests
9. **[ ] Document** - Update README
10. **[ ] Commit to GitHub** - Merge to main

---

**Status:** ✅ Ready to implement
**Estimated Time:** 2-4 hours
**Risk:** Low (falls back to consensus if classification fails)
**Expected Impact:** 60% cost reduction, 70% faster on easy queries
