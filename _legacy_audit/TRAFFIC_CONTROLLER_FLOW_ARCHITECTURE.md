# Traffic Controller Flow Architecture

**Date:** 2026-01-24
**Purpose:** Document data flow and decision logic for multi-LLM orchestration
**Philosophy:** Traffic controller distributes work efficiently, stepping in as fallback if needed

---

## 🎯 Core Philosophy

**Traffic Controller Role:**
1. **Router:** Directs queries to appropriate LLM based on complexity
2. **Evaluator:** Assesses worker efficiency and accuracy
3. **Fallback:** Handles queries itself if no workers available
4. **Monitor:** Tracks performance metrics for continuous optimization

**Worker Distribution:**
- If **0 workers:** Traffic controller handles everything
- If **1 worker:** Traffic controller routes based on difficulty
- If **2+ workers:** Traffic controller orchestrates parallel work + consensus

---

## 📊 Decision Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                       USER QUERY ARRIVES                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   TRAFFIC CONTROLLER (Phi-3-mini)                │
│                   Port 8020 - Always Running                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │  WORKER SCAN   │
                    │  Discovery     │
                    └────────┬───────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   ┌────────┐          ┌──────────┐        ┌──────────┐
   │0 WORKERS│         │ 1 WORKER │        │2+ WORKERS│
   └────┬───┘          └─────┬────┘        └─────┬────┘
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌────────────────┐    ┌─────────────────┐
│ FALLBACK MODE│    │ ROUTING MODE   │    │ ORCHESTRATION   │
│              │    │                │    │ MODE            │
│ Controller   │    │ Easy→Worker    │    │ Parallel+       │
│ answers      │    │ Hard→Traffic   │    │ Consensus       │
│ directly     │    │ Medium→Verify  │    │                 │
└──────────────┘    └────────────────┘    └─────────────────┘
```

---

## 🔄 Detailed Flow: 0 Workers (Fallback Mode)

**Scenario:** No worker LLMs available, only traffic controller

### Flow Chart:
```
User Query
    │
    ▼
┌─────────────────────────────────────┐
│ Traffic Controller (Port 8020)      │
│ - Receives query                    │
│ - Scans ports 8001, 8005-8012       │
│ - Finds: 0 workers                  │
└────────────┬────────────────────────┘
             │
             ▼
      ┌──────────────┐
      │ FALLBACK     │
      │ ACTIVATED    │
      └──────┬───────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Traffic Controller ANSWERS          │
│ - Uses own Phi-3-mini model         │
│ - Generates response directly       │
│ - Logs: "No workers, using fallback"│
└────────────┬────────────────────────┘
             │
             ▼
        Response to User
        ⚠️ "Fallback mode (no workers)"
```

### Data Flow:
```python
# Input
{
    "query": "What is 2+2?",
    "system_prompt": "You are a helpful assistant",
    "available_workers": []
}

# Processing
traffic_controller.scan_workers()  # → []
traffic_controller.fallback_mode = True

# Output
{
    "response": "2+2 equals 4.",
    "mode": "fallback",
    "llm_used": "Phi-3-mini (traffic controller)",
    "latency_ms": 180,
    "worker_count": 0
}
```

### Code Flow:
```python
async def get_consensus(self, query: str) -> AsyncGenerator[str, None]:
    """Main entry point."""

    # Discover workers
    await self.discover_swarm()

    if len(self.endpoints) == 0:
        # FALLBACK MODE: Traffic controller handles it
        yield "⚠️ No workers available - using fallback mode\n\n"

        async for chunk in self._traffic_controller_answers(query):
            yield chunk

        # Log performance
        self.metrics.record_fallback(query)
```

---

## 🔄 Detailed Flow: 1 Worker (Routing Mode)

**Scenario:** 1 worker LLM available + traffic controller

### Flow Chart:
```
User Query
    │
    ▼
┌─────────────────────────────────────┐
│ Traffic Controller (Port 8020)      │
│ - Evaluates difficulty              │
│ - Classifies domain                 │
│ - Measures confidence               │
└────────────┬────────────────────────┘
             │
             ▼
      ┌──────────────┐
      │ DIFFICULTY?  │
      └──────┬───────┘
             │
   ┌─────────┼─────────┐
   │         │         │
   ▼         ▼         ▼
┌─────┐  ┌────────┐  ┌──────┐
│EASY │  │MEDIUM  │  │HARD  │
│0.9  │  │0.6     │  │0.3   │
│conf │  │conf    │  │conf  │
└──┬──┘  └───┬────┘  └───┬──┘
   │         │           │
   ▼         ▼           ▼
┌──────┐  ┌─────────┐  ┌────────┐
│Worker│  │Verify   │  │Traffic │
│LLM   │  │w/Worker │  │Ctrl    │
│      │  │         │  │Handles │
└──┬───┘  └────┬────┘  └────┬───┘
   │           │            │
   └───────────┴────────────┘
               │
               ▼
         Response to User
```

### Decision Matrix:

| Difficulty | Confidence | Route To | Reasoning |
|------------|------------|----------|-----------|
| Easy | > 0.8 | Worker | Fast, simple query → delegate |
| Easy | < 0.8 | Verify | Uncertain → get confirmation |
| Medium | > 0.7 | Verify | Medium complexity → double-check |
| Medium | < 0.7 | Traffic Ctrl | Uncertain → use better model |
| Hard | Any | Traffic Ctrl | Complex → use best available |

### Data Flow Examples:

#### Example 1: Easy Query → Worker
```python
# Input
{
    "query": "What is the capital of France?",
    "available_workers": ["worker_8001"]
}

# Traffic Controller Evaluation
{
    "difficulty": "easy",
    "domain": "factual",
    "confidence": 0.95,
    "reasoning": "Simple factual query"
}

# Routing Decision
route_to = "worker_8001"  # High confidence, easy query

# Worker Response (Port 8001)
{
    "response": "The capital of France is Paris.",
    "latency_ms": 850
}

# Output
{
    "response": "The capital of France is Paris.",
    "mode": "routed",
    "llm_used": "worker_8001",
    "classification_ms": 150,
    "answer_ms": 850,
    "total_ms": 1000,
    "llm_calls": 2  # 1 classification + 1 answer
}
```

#### Example 2: Hard Query → Traffic Controller
```python
# Input
{
    "query": "Prove the Riemann Hypothesis",
    "available_workers": ["worker_8001"]
}

# Traffic Controller Evaluation
{
    "difficulty": "hard",
    "domain": "math",
    "confidence": 0.85,
    "reasoning": "Complex mathematical proof"
}

# Routing Decision
route_to = "traffic_controller"  # Too hard for worker

# Traffic Controller Response
{
    "response": "The Riemann Hypothesis...",
    "latency_ms": 2200
}

# Output
{
    "response": "The Riemann Hypothesis...",
    "mode": "traffic_controller",
    "llm_used": "Phi-3-mini",
    "classification_ms": 150,
    "answer_ms": 2200,
    "total_ms": 2350,
    "llm_calls": 1  # Classification + answer in one
}
```

#### Example 3: Medium Query → Verification
```python
# Input
{
    "query": "Write a function to reverse a string in Python",
    "available_workers": ["worker_8001"]
}

# Traffic Controller Evaluation
{
    "difficulty": "medium",
    "domain": "code",
    "confidence": 0.72,
    "reasoning": "Standard coding task"
}

# Routing Decision
verify_with_worker = True  # Medium difficulty → get both opinions

# Parallel Query (Worker + Traffic Controller)
worker_answer = await worker_8001.answer(query)  # 1.2s
traffic_answer = await traffic_controller.answer(query)  # 0.3s

# Consensus Check
agreement = calculate_consensus([worker_answer, traffic_answer])
# → 0.85 (high agreement)

# Output (use faster worker answer)
{
    "response": worker_answer,
    "mode": "verified",
    "llm_used": "worker_8001 (verified by traffic controller)",
    "agreement": 0.85,
    "total_ms": 1500,  # Parallel execution
    "llm_calls": 3  # 1 classification + 2 answers
}
```

### Code Flow:
```python
async def _routing_mode(self, query: str) -> AsyncGenerator[str, None]:
    """1 Worker routing mode."""

    worker_llm = self.endpoints[0]  # Single worker

    # Step 1: Evaluate difficulty
    evaluation = await self._evaluate_query_difficulty(query)

    difficulty = evaluation['difficulty']
    confidence = evaluation['confidence']

    # Step 2: Route decision
    if difficulty == 'easy' and confidence > 0.8:
        # Route to worker
        yield f"💨 Routing to worker ({difficulty}, {confidence:.0%})\n\n"
        async for chunk in self._stream_from_llm(worker_llm, query):
            yield chunk

        self.metrics.record_routing("worker", difficulty, confidence)

    elif difficulty == 'hard' or confidence < 0.5:
        # Traffic controller handles it
        yield f"🧠 Traffic controller handling ({difficulty})\n\n"
        async for chunk in self._traffic_controller_answers(query):
            yield chunk

        self.metrics.record_routing("traffic_controller", difficulty, confidence)

    else:
        # Verify with worker
        yield f"⚖️ Verifying with worker ({difficulty})\n\n"

        worker_answer, traffic_answer = await asyncio.gather(
            self._get_answer(worker_llm, query),
            self._traffic_controller_answers(query)
        )

        agreement = self._calculate_consensus([worker_answer, traffic_answer])

        if agreement > 0.7:
            yield worker_answer  # Trust worker
        else:
            yield traffic_answer  # Use traffic controller

        self.metrics.record_verification(difficulty, agreement)
```

---

## 🔄 Detailed Flow: 2+ Workers (Orchestration Mode)

**Scenario:** Multiple worker LLMs available + traffic controller

### Flow Chart:
```
User Query
    │
    ▼
┌─────────────────────────────────────┐
│ Traffic Controller (Port 8020)      │
│ - Evaluates complexity              │
│ - Selects workers                   │
│ - Orchestrates parallel queries     │
└────────────┬────────────────────────┘
             │
             ▼
      ┌──────────────┐
      │ COMPLEXITY?  │
      └──────┬───────┘
             │
   ┌─────────┼─────────┐
   │         │         │
   ▼         ▼         ▼
┌─────┐  ┌────────┐  ┌──────┐
│LOW  │  │MEDIUM  │  │HIGH  │
└──┬──┘  └───┬────┘  └───┬──┘
   │         │           │
   ▼         ▼           ▼
┌──────┐  ┌─────────┐  ┌────────────┐
│Best  │  │Parallel │  │Full        │
│Worker│  │2 Workers│  │Consensus   │
│      │  │         │  │All Workers │
└──┬───┘  └────┬────┘  └─────┬──────┘
   │           │              │
   │           ▼              ▼
   │    ┌──────────────┐  ┌──────────────┐
   │    │Quick         │  │Weighted      │
   │    │Consensus     │  │Voting        │
   │    └──────┬───────┘  └──────┬───────┘
   │           │                 │
   └───────────┴─────────────────┘
                    │
                    ▼
            ┌──────────────┐
            │ SYNTHESIS    │
            │ (Best Answer)│
            └──────┬───────┘
                   │
                   ▼
             Response to User
```

### Worker Selection Algorithm:

```python
def select_workers(self, difficulty: str, num_workers: int) -> List[str]:
    """
    Select best workers based on difficulty and historical performance.

    Algorithm:
    1. Retrieve worker performance history
    2. Filter by domain expertise
    3. Rank by accuracy + speed
    4. Select top N for query
    """

    # Get performance metrics
    worker_stats = [
        {
            "endpoint": w,
            "accuracy": self.metrics.get_accuracy(w, domain),
            "avg_speed": self.metrics.get_avg_speed(w),
            "reliability": self.metrics.get_reliability(w)
        }
        for w in self.endpoints
    ]

    # Calculate score: accuracy(70%) + speed(20%) + reliability(10%)
    for w in worker_stats:
        w['score'] = (
            w['accuracy'] * 0.7 +
            (1.0 / w['avg_speed']) * 0.2 +  # Lower speed = higher score
            w['reliability'] * 0.1
        )

    # Sort by score
    ranked = sorted(worker_stats, key=lambda x: x['score'], reverse=True)

    # Select based on difficulty
    if difficulty == 'easy':
        # Use fastest worker
        return [ranked[0]['endpoint']]

    elif difficulty == 'medium':
        # Use top 2 for verification
        return [w['endpoint'] for w in ranked[:2]]

    else:  # hard
        # Use all workers for consensus
        return [w['endpoint'] for w in ranked]
```

### Orchestration Strategies:

#### Strategy 1: Low Complexity (Single Best Worker)
```python
# Input
{
    "query": "What is 2+2?",
    "available_workers": ["worker_8001", "worker_8005", "worker_8006"]
}

# Worker Selection
best_worker = select_workers("easy", 3)
# → ["worker_8001"]  # Fastest with 95% accuracy on factual

# Execution
{
    "selected_workers": 1,
    "parallel_queries": 1,
    "consensus_needed": False
}

# Output
{
    "response": "2+2 equals 4.",
    "mode": "single_worker",
    "llm_used": "worker_8001",
    "total_ms": 950,
    "llm_calls": 2  # 1 classification + 1 answer
}
```

#### Strategy 2: Medium Complexity (Parallel Verification)
```python
# Input
{
    "query": "Explain how binary search works",
    "available_workers": ["worker_8001", "worker_8005", "worker_8006"]
}

# Worker Selection
selected = select_workers("medium", 3)
# → ["worker_8001", "worker_8005"]  # Top 2 by score

# Parallel Execution
answers = await asyncio.gather(
    worker_8001.answer(query),
    worker_8005.answer(query)
)

# Quick Consensus
agreement = calculate_consensus(answers)  # → 0.82

if agreement > 0.75:
    # Use faster answer
    best_answer = min(answers, key=lambda x: x['latency'])
else:
    # Traffic controller synthesizes
    best_answer = await traffic_controller.synthesize(answers)

# Output
{
    "response": best_answer,
    "mode": "parallel_verification",
    "workers_used": ["worker_8001", "worker_8005"],
    "agreement": 0.82,
    "total_ms": 1200,  # Parallel = max(worker times)
    "llm_calls": 3  # 1 classification + 2 parallel answers
}
```

#### Strategy 3: High Complexity (Full Consensus)
```python
# Input
{
    "query": "Design a distributed consensus algorithm",
    "available_workers": ["worker_8001", "worker_8005", "worker_8006"]
}

# Worker Selection
selected = select_workers("hard", 3)
# → ["worker_8001", "worker_8005", "worker_8006"]  # All workers

# Parallel Round 1
round1_answers = await asyncio.gather(
    worker_8001.answer(query),
    worker_8005.answer(query),
    worker_8006.answer(query)
)

# Consensus Check
agreement = calculate_consensus(round1_answers)  # → 0.45 (low)

# Round 2: Cross-critique (if needed)
if agreement < 0.6:
    round2_answers = await cross_critique(round1_answers)
    agreement = calculate_consensus(round2_answers)  # → 0.72

# Traffic Controller Synthesis
final_answer = await traffic_controller.synthesize(
    round2_answers,
    agreement=agreement,
    protocol="weighted_vote"
)

# Output
{
    "response": final_answer,
    "mode": "full_consensus",
    "workers_used": ["worker_8001", "worker_8005", "worker_8006"],
    "rounds": 2,
    "final_agreement": 0.72,
    "total_ms": 4500,
    "llm_calls": 7  # 1 classification + 3 round1 + 3 round2
}
```

### Code Flow:
```python
async def _orchestration_mode(self, query: str) -> AsyncGenerator[str, None]:
    """2+ Workers orchestration mode."""

    # Step 1: Evaluate complexity
    evaluation = await self._evaluate_query_difficulty(query)
    difficulty = evaluation['difficulty']

    # Step 2: Select workers
    selected_workers = self.select_workers(
        difficulty=difficulty,
        num_workers=len(self.endpoints)
    )

    yield f"🎯 Selected {len(selected_workers)} worker(s) for {difficulty} query\n\n"

    # Step 3: Execute based on complexity
    if difficulty == 'easy' and len(selected_workers) == 1:
        # Single best worker
        async for chunk in self._stream_from_llm(selected_workers[0], query):
            yield chunk

    elif difficulty == 'medium' and len(selected_workers) == 2:
        # Parallel verification
        answers = await asyncio.gather(*[
            self._get_answer(w, query) for w in selected_workers
        ])

        agreement = self._calculate_consensus(answers)

        if agreement > 0.75:
            # High agreement - use fastest
            yield min(answers, key=lambda x: x['latency'])['content']
        else:
            # Low agreement - synthesize
            synthesis = await self._synthesize(answers, agreement)
            yield synthesis

    else:
        # Full consensus (existing implementation)
        async for chunk in self._full_consensus_mode(query, selected_workers):
            yield chunk

    # Step 4: Update performance metrics
    self.metrics.record_orchestration(
        difficulty=difficulty,
        workers_used=selected_workers,
        agreement=agreement
    )
```

---

## 📈 Efficiency Tracking

### Performance Metrics Collected:

```python
@dataclass
class WorkerPerformance:
    """Track individual worker performance."""

    worker_id: str

    # Accuracy metrics
    total_queries: int = 0
    correct_answers: int = 0  # Verified by consensus
    accuracy_by_domain: Dict[str, float] = field(default_factory=dict)

    # Speed metrics
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0

    # Reliability
    timeout_count: int = 0
    error_count: int = 0
    reliability_score: float = 1.0  # 0.0-1.0

    # Consensus metrics
    avg_agreement_score: float = 0.0  # When paired with others
    times_selected_as_best: int = 0

    # Cost efficiency
    avg_cost_per_query: float = 0.0
    cost_to_accuracy_ratio: float = 0.0


class EfficiencyJudge:
    """Judge worker efficiency and make routing decisions."""

    def __init__(self):
        self.workers: Dict[str, WorkerPerformance] = {}

    def record_query_result(
        self,
        worker_id: str,
        query: str,
        domain: str,
        latency_ms: float,
        was_correct: bool,
        consensus_score: float
    ):
        """Record query result for efficiency tracking."""

        if worker_id not in self.workers:
            self.workers[worker_id] = WorkerPerformance(worker_id=worker_id)

        w = self.workers[worker_id]

        # Update counts
        w.total_queries += 1
        if was_correct:
            w.correct_answers += 1

        # Update domain accuracy
        if domain not in w.accuracy_by_domain:
            w.accuracy_by_domain[domain] = []
        w.accuracy_by_domain[domain].append(1 if was_correct else 0)

        # Update latency (running average)
        w.avg_latency_ms = (
            (w.avg_latency_ms * (w.total_queries - 1) + latency_ms)
            / w.total_queries
        )

        # Update consensus score
        w.avg_agreement_score = (
            (w.avg_agreement_score * (w.total_queries - 1) + consensus_score)
            / w.total_queries
        )

    def judge_efficiency(self, worker_id: str) -> Dict:
        """Calculate comprehensive efficiency score."""

        w = self.workers.get(worker_id)
        if not w or w.total_queries < 10:
            return {"score": 0.5, "confidence": "low"}  # Not enough data

        # Calculate accuracy
        accuracy = w.correct_answers / w.total_queries

        # Calculate speed score (inverse latency, normalized)
        speed_score = 1.0 / (w.avg_latency_ms / 1000.0)  # Higher = faster
        speed_score = min(1.0, speed_score)  # Cap at 1.0

        # Calculate reliability
        reliability = 1.0 - (
            (w.timeout_count + w.error_count) / w.total_queries
        )

        # Weighted efficiency score
        efficiency = (
            accuracy * 0.5 +        # 50% weight on accuracy
            speed_score * 0.3 +     # 30% weight on speed
            reliability * 0.2       # 20% weight on reliability
        )

        return {
            "score": efficiency,
            "accuracy": accuracy,
            "speed_score": speed_score,
            "reliability": reliability,
            "confidence": "high" if w.total_queries > 50 else "medium",
            "total_queries": w.total_queries
        }

    def recommend_worker(
        self,
        difficulty: str,
        domain: str,
        available_workers: List[str]
    ) -> str:
        """Recommend best worker for query based on historical performance."""

        scores = []
        for worker_id in available_workers:
            efficiency = self.judge_efficiency(worker_id)

            # Bonus for domain expertise
            w = self.workers.get(worker_id)
            domain_bonus = 0.0
            if w and domain in w.accuracy_by_domain:
                domain_accuracy = sum(w.accuracy_by_domain[domain]) / len(w.accuracy_by_domain[domain])
                domain_bonus = domain_accuracy * 0.2

            final_score = efficiency['score'] + domain_bonus

            scores.append({
                "worker_id": worker_id,
                "score": final_score,
                "efficiency": efficiency
            })

        # Return best worker
        best = max(scores, key=lambda x: x['score'])
        return best['worker_id']
```

### Efficiency Dashboard Output:

```
==================== WORKER EFFICIENCY REPORT ====================

Worker: worker_8001 (Main LLM)
  Total Queries:        547
  Accuracy:             87.2%
  Avg Latency:          1,250 ms
  Reliability:          95.3%
  Efficiency Score:     0.82 / 1.0  ⭐⭐⭐⭐

  Domain Performance:
    Code:               91.2% (245 queries)
    Factual:            89.7% (178 queries)
    Math:               82.1% (124 queries)

  Recommendation:       EXCELLENT - Use for code/factual queries

------------------------------------------------------------------

Worker: worker_8005 (Fast LLM)
  Total Queries:        423
  Accuracy:             76.3%
  Avg Latency:          650 ms
  Reliability:          98.1%
  Efficiency Score:     0.71 / 1.0  ⭐⭐⭐

  Domain Performance:
    Factual:            85.4% (312 queries)
    Code:               62.1% (89 queries)
    Math:               71.2% (22 queries)

  Recommendation:       GOOD - Use for simple factual queries

------------------------------------------------------------------

Worker: worker_8006 (Specialized LLM)
  Total Queries:        189
  Accuracy:             93.1%
  Avg Latency:          2,100 ms
  Reliability:          91.5%
  Efficiency Score:     0.75 / 1.0  ⭐⭐⭐⭐

  Domain Performance:
    Math:               97.8% (134 queries)
    Reasoning:          89.3% (55 queries)

  Recommendation:       SPECIALIST - Use for math/reasoning queries

==================================================================
```

---

## 🎯 Routing Decision Tree (Complete)

```python
def route_query(
    self,
    query: str,
    available_workers: List[str]
) -> Dict:
    """
    Complete routing decision tree.

    Returns:
        {
            "mode": "fallback|routing|orchestration",
            "selected_workers": List[str],
            "strategy": str,
            "expected_llm_calls": int,
            "expected_latency_ms": float
        }
    """

    # Step 1: Check worker availability
    num_workers = len(available_workers)

    # Step 2: Evaluate query
    evaluation = self._evaluate_query_difficulty(query)
    difficulty = evaluation['difficulty']
    confidence = evaluation['confidence']
    domain = evaluation['domain']

    # Step 3: Route decision
    if num_workers == 0:
        # FALLBACK MODE
        return {
            "mode": "fallback",
            "selected_workers": [],
            "strategy": "traffic_controller_answers",
            "expected_llm_calls": 1,  # Classification + answer combined
            "expected_latency_ms": 200
        }

    elif num_workers == 1:
        # ROUTING MODE
        worker = available_workers[0]

        if difficulty == 'easy' and confidence > 0.8:
            # Route to worker
            return {
                "mode": "routing",
                "selected_workers": [worker],
                "strategy": "delegate_to_worker",
                "expected_llm_calls": 2,  # Classification + answer
                "expected_latency_ms": 1100  # 150 + 950
            }

        elif difficulty == 'hard' or confidence < 0.5:
            # Traffic controller handles
            return {
                "mode": "routing",
                "selected_workers": [],
                "strategy": "traffic_controller_answers",
                "expected_llm_calls": 1,
                "expected_latency_ms": 200
            }

        else:
            # Verify with worker
            return {
                "mode": "routing",
                "selected_workers": [worker],
                "strategy": "verify_with_worker",
                "expected_llm_calls": 3,  # Classification + 2 answers
                "expected_latency_ms": 1300  # 150 + max(950, 200)
            }

    else:
        # ORCHESTRATION MODE (2+ workers)

        # Select best workers based on historical performance
        ranked_workers = self.efficiency_judge.rank_workers(
            domain=domain,
            available=available_workers
        )

        if difficulty == 'easy':
            # Single best worker
            return {
                "mode": "orchestration",
                "selected_workers": [ranked_workers[0]],
                "strategy": "single_best_worker",
                "expected_llm_calls": 2,
                "expected_latency_ms": 1100
            }

        elif difficulty == 'medium':
            # Top 2 workers for verification
            return {
                "mode": "orchestration",
                "selected_workers": ranked_workers[:2],
                "strategy": "parallel_verification",
                "expected_llm_calls": 3,  # Classification + 2 parallel
                "expected_latency_ms": 1200  # Parallel execution
            }

        else:  # hard
            # Full consensus with all workers
            return {
                "mode": "orchestration",
                "selected_workers": ranked_workers,
                "strategy": "full_consensus",
                "expected_llm_calls": 1 + len(ranked_workers) + 1,  # Class + workers + synthesis
                "expected_latency_ms": 3500
            }
```

---

## 📊 Summary: Cost & Performance by Configuration

| Workers | Difficulty | Strategy | LLM Calls | Latency | Cost Savings |
|---------|------------|----------|-----------|---------|--------------|
| **0** | Any | Fallback | 1 | 200ms | N/A |
| **1** | Easy | Worker | 2 | 1100ms | 60% vs consensus |
| **1** | Medium | Verify | 3 | 1300ms | 40% vs consensus |
| **1** | Hard | Traffic Ctrl | 1 | 200ms | 80% vs consensus |
| **2+** | Easy | Best Worker | 2 | 1100ms | 70% vs consensus |
| **2+** | Medium | Parallel x2 | 3 | 1200ms | 50% vs consensus |
| **2+** | Hard | Full Consensus | 7 | 3500ms | 0% (baseline) |

**Average Savings (Mixed Queries):** 60%
**Average Latency Reduction:** 55%

---

**Status:** ✅ Architecture Complete
**Next:** Implementation in swarm_arbitrator.py
