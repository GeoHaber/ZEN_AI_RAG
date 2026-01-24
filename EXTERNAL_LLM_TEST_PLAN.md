# External LLM Testing - TDD Plan

**Date:** 2026-01-23
**Objective:** Test multi-LLM consensus with external APIs (Anthropic, Google, Grok)
**Approach:** Test-Driven Development (TDD) - "Trust but Verify"

---

## Overview

We need to test the **External Agent Bridge** (Improvement #12) that allows the swarm arbitrator to query external LLM APIs and synthesize their responses.

**Current Implementation:** `zena_mode/arbitrage.py` lines 221-285
**Feature Status:** Implemented but needs comprehensive testing

---

## TDD Strategy - Three Phases

### Phase 1: Test Design & Mock Testing
**Goal:** Design tests WITHOUT hitting real APIs (use mocks)
**Why:** Fast, free, deterministic, no API keys needed
**What:** Test the integration logic, not the APIs themselves

**Tests to Create:**
1. ✅ Test external agent request formatting
2. ✅ Test response parsing
3. ✅ Test error handling (API down, timeout, auth failure)
4. ✅ Test consensus calculation with mixed local + external results
5. ✅ Test cost tracking for external APIs

**Success Criteria:** All mocked tests pass

---

### Phase 2: Real API Integration Testing
**Goal:** Test with REAL APIs (Anthropic, Google, Grok)
**Why:** Verify actual API compatibility
**What:** Send same question to multiple providers, compare results

**Requirements:**
- API keys configured (user provides)
- Safety: Single test query per API (minimize cost)
- Verification: Check response format matches expectations

**Tests to Create:**
1. ✅ Send test query to Anthropic Claude API
2. ✅ Send test query to Google Gemini API
3. ✅ Send test query to Grok API
4. ✅ Compare response quality
5. ✅ Verify consensus/arbitrage logic
6. ✅ Track API costs

**Success Criteria:** All APIs respond, consensus calculated correctly

---

### Phase 3: Improvement & Production Testing
**Goal:** Optimize based on Phase 2 results
**Why:** Real-world performance tuning
**What:** Multi-query testing, performance benchmarks, error recovery

**Improvements to Test:**
1. ✅ Retry logic for API failures
2. ✅ Fallback priority (if Claude fails, try Gemini)
3. ✅ Response caching (avoid duplicate API calls)
4. ✅ Rate limiting (respect API quotas)
5. ✅ Cost optimization (use cheaper models for simple queries)

**Success Criteria:** Production-ready with all edge cases handled

---

## Test Questions

We'll use standardized test questions to compare LLM responses:

### Question 1: Factual (Easy)
```
"What is the capital of France?"
```
**Expected:** All LLMs agree: "Paris"
**Tests:** Basic functionality

### Question 2: Math/Reasoning (Medium)
```
"If a train travels 60 miles per hour for 2.5 hours, how far does it go?"
```
**Expected:** All LLMs agree: "150 miles"
**Tests:** Reasoning capability

### Question 3: Nuanced/Opinion (Hard)
```
"Should investors buy stocks during a recession?"
```
**Expected:** Different perspectives, semantic consensus
**Tests:** Arbitrage logic with disagreement

### Question 4: Code Generation (Domain-Specific)
```
"Write a Python function to check if a number is prime."
```
**Expected:** Different implementations, functional equivalence
**Tests:** Task-specific routing

---

## API Configuration

### Required Environment Variables:

```bash
# Anthropic Claude
export ANTHROPIC_API_KEY="sk-ant-..."

# Google Gemini
export GOOGLE_API_KEY="AIza..."

# Grok (xAI)
export XAI_API_KEY="xai-..."

# OpenAI (optional, for comparison)
export OPENAI_API_KEY="sk-..."
```

### Safety Configuration:

```python
# Limit API calls during testing
MAX_TEST_QUERIES_PER_API = 1  # Phase 2: Just verify connectivity
MAX_TEST_QUERIES_PER_API = 5  # Phase 3: Performance testing

# Cost limits
MAX_COST_PER_TEST_RUN = 0.10  # $0.10 max per test run
```

---

## Expected Results Matrix

| Test Question | Claude | Gemini | Grok | Consensus | Cost |
|---------------|--------|--------|------|-----------|------|
| Capital of France | "Paris" | "Paris" | "Paris" | 100% | $0.001 |
| Train Distance | "150 miles" | "150 miles" | "150 miles" | 100% | $0.002 |
| Recession Investing | Nuanced | Nuanced | Nuanced | 70-80% | $0.010 |
| Prime Number Code | Python | Python | Python | 85-95% | $0.015 |

**Total Expected Cost:** ~$0.03 for full Phase 2 testing

---

## Phase 1: Mock Testing (START HERE)

### Test File: `tests/test_external_llm_mock.py`

**What We'll Test:**

1. **Request Formation:**
   ```python
   def test_format_external_request():
       """Test that we format API requests correctly."""
       messages = [
           {"role": "system", "content": "You are helpful"},
           {"role": "user", "content": "What is 2+2?"}
       ]
       request = format_anthropic_request(messages)
       assert "model" in request
       assert "messages" in request
       assert request["messages"][0]["role"] == "system"
   ```

2. **Response Parsing:**
   ```python
   def test_parse_anthropic_response():
       """Test parsing Anthropic API response."""
       mock_response = {
           "content": [{"text": "The answer is 4"}],
           "model": "claude-3-5-sonnet-20241022"
       }
       parsed = parse_anthropic_response(mock_response)
       assert parsed["content"] == "The answer is 4"
       assert parsed["model"] == "claude-3-5-sonnet-20241022"
   ```

3. **Error Handling:**
   ```python
   def test_api_timeout_handling():
       """Test graceful timeout handling."""
       with patch('httpx.AsyncClient.post', side_effect=asyncio.TimeoutError):
           result = await query_external_agent("claude-3", messages)
           assert result["content"].startswith("[ERROR:")
           assert result["confidence"] == 0.0
   ```

4. **Consensus with Mixed Sources:**
   ```python
   def test_consensus_local_plus_external():
       """Test consensus with mix of local and external LLMs."""
       responses = [
           {"content": "Paris", "model": "local-llama", "confidence": 0.9},
           {"content": "Paris", "model": "claude-3", "confidence": 0.95},
           {"content": "Paris", "model": "gemini-pro", "confidence": 0.92}
       ]
       consensus = calculate_consensus(responses)
       assert consensus > 0.95  # High agreement
   ```

5. **Cost Tracking:**
   ```python
   def test_cost_tracking():
       """Test API cost calculation."""
       tracker = CostTracker()
       tracker.record_query("claude-3-5-sonnet", "What is 2+2?", 50)  # 50 tokens
       tracker.record_query("gemini-pro", "What is 2+2?", 45)

       total_cost = tracker.get_total_cost()
       assert total_cost > 0
       assert total_cost < 0.01  # Should be very cheap
   ```

**Success Criteria for Phase 1:** All 5 mock tests pass

---

## Phase 2: Real API Testing

### Test File: `tests/test_external_llm_real.py`

**Prerequisites:**
- User has configured API keys
- User approves spending ~$0.03 on test queries
- Internet connection available

**What We'll Test:**

1. **Anthropic Claude API:**
   ```python
   @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="No API key")
   async def test_anthropic_api_real():
       """Test real Anthropic API call."""
       response = await query_anthropic("What is the capital of France?")

       assert response["success"] == True
       assert "paris" in response["content"].lower()
       assert response["model"].startswith("claude-")
       assert response["confidence"] > 0.8
   ```

2. **Google Gemini API:**
   ```python
   @pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY"), reason="No API key")
   async def test_gemini_api_real():
       """Test real Gemini API call."""
       response = await query_gemini("What is the capital of France?")

       assert response["success"] == True
       assert "paris" in response["content"].lower()
       assert "gemini" in response["model"].lower()
   ```

3. **Grok API:**
   ```python
   @pytest.mark.skipif(not os.getenv("XAI_API_KEY"), reason="No API key")
   async def test_grok_api_real():
       """Test real Grok API call."""
       response = await query_grok("What is the capital of France?")

       assert response["success"] == True
       assert "paris" in response["content"].lower()
       assert "grok" in response["model"].lower()
   ```

4. **Multi-LLM Consensus:**
   ```python
   async def test_multi_llm_consensus():
       """Test consensus across Claude, Gemini, Grok."""
       question = "What is 2+2?"

       responses = await asyncio.gather(
           query_anthropic(question),
           query_gemini(question),
           query_grok(question)
       )

       # All should answer "4"
       for r in responses:
           assert "4" in r["content"]

       # Calculate consensus
       consensus = calculate_semantic_consensus([r["content"] for r in responses])
       assert consensus > 0.9  # Very high agreement on simple math
   ```

5. **Cost Verification:**
   ```python
   async def test_api_cost_tracking():
       """Verify cost tracking for all APIs."""
       tracker = CostTracker()

       # Send test query to each API
       await query_anthropic("Test", cost_tracker=tracker)
       await query_gemini("Test", cost_tracker=tracker)
       await query_grok("Test", cost_tracker=tracker)

       total_cost = tracker.get_total_cost()
       print(f"Total API cost: ${total_cost:.4f}")

       assert total_cost < 0.10  # Should be under 10 cents

       # Show breakdown
       breakdown = tracker.get_cost_breakdown()
       for provider, cost in breakdown.items():
           print(f"  {provider}: ${cost:.4f}")
   ```

**Success Criteria for Phase 2:**
- All available APIs respond successfully
- Consensus calculation works with real responses
- Total cost < $0.10

---

## Phase 3: Improvement Testing

### Test File: `tests/test_external_llm_advanced.py`

**What We'll Test:**

1. **Retry Logic:**
   ```python
   async def test_api_retry_on_failure():
       """Test retry with exponential backoff."""
       # Simulate API failure then success
       responses = [
           Exception("API Error"),
           {"content": "Success", "model": "claude-3"}
       ]

       with patch('query_api', side_effect=responses):
           result = await query_with_retry("claude-3", "Test", max_retries=3)
           assert result["success"] == True
   ```

2. **Fallback Priority:**
   ```python
   async def test_fallback_priority():
       """Test fallback when primary API fails."""
       # Claude fails, should fallback to Gemini
       with patch('query_anthropic', side_effect=Exception("API Down")):
           result = await query_with_fallback("Test", priority=["claude-3", "gemini-pro"])
           assert "gemini" in result["model"].lower()
   ```

3. **Response Caching:**
   ```python
   async def test_response_caching():
       """Test that identical queries use cache."""
       question = "What is the capital of France?"

       # First call - hits API
       start1 = time.time()
       response1 = await query_with_cache("claude-3", question)
       duration1 = time.time() - start1

       # Second call - uses cache
       start2 = time.time()
       response2 = await query_with_cache("claude-3", question)
       duration2 = time.time() - start2

       assert response1["content"] == response2["content"]
       assert duration2 < duration1 / 10  # Cache should be 10x+ faster
   ```

4. **Rate Limiting:**
   ```python
   async def test_rate_limiting():
       """Test that we respect API rate limits."""
       # Send 5 queries rapidly
       start = time.time()
       tasks = [query_with_rate_limit("claude-3", f"Test {i}") for i in range(5)]
       await asyncio.gather(*tasks)
       duration = time.time() - start

       # Should take at least 4 seconds (1s delay between requests)
       assert duration >= 4.0
   ```

5. **Cost Optimization:**
   ```python
   async def test_cost_optimization():
       """Test using cheaper models for simple queries."""
       simple_question = "What is 2+2?"
       complex_question = "Explain quantum entanglement"

       # Should route simple question to cheap model
       simple_result = await query_optimized(simple_question)
       assert "haiku" in simple_result["model"].lower() or "flash" in simple_result["model"].lower()

       # Should route complex question to powerful model
       complex_result = await query_optimized(complex_question)
       assert "sonnet" in complex_result["model"].lower() or "pro" in complex_result["model"].lower()
   ```

**Success Criteria for Phase 3:**
- All advanced features work correctly
- Cost < $0.05 for full test suite (caching helps)
- Production-ready error handling

---

## Test Execution Order

### Step 1: Phase 1 - Mock Testing (NO API KEYS NEEDED)
```bash
cd C:\Users\dvdze\.claude-worktrees\ZEN_AI_RAG\naughty-antonelli
python -m pytest tests/test_external_llm_mock.py -v
```
**Expected:** All 5 tests pass
**Time:** ~5 seconds
**Cost:** $0.00

### Step 2: Phase 2 - Real API Testing (REQUIRES API KEYS)
```bash
# User provides API keys
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="AIza..."
export XAI_API_KEY="xai-..."

# Run real tests
python -m pytest tests/test_external_llm_real.py -v
```
**Expected:** 3-5 tests pass (depends on which APIs user has)
**Time:** ~30-60 seconds
**Cost:** ~$0.03

### Step 3: Phase 3 - Advanced Testing
```bash
python -m pytest tests/test_external_llm_advanced.py -v
```
**Expected:** 5 tests pass
**Time:** ~60-90 seconds
**Cost:** ~$0.05 (with caching)

---

## Success Metrics

### Phase 1 Success:
- ✅ All mock tests pass
- ✅ Request/response formatting correct
- ✅ Error handling robust
- ✅ Consensus logic works

### Phase 2 Success:
- ✅ At least 2 external APIs working
- ✅ Responses semantically similar
- ✅ Consensus > 70% on factual questions
- ✅ Total cost < $0.10

### Phase 3 Success:
- ✅ Retry logic recovers from failures
- ✅ Caching reduces API calls by 50%+
- ✅ Rate limiting prevents abuse
- ✅ Cost optimization saves 30%+

---

## Next Steps

**Ready to start?**

1. **I'll create Phase 1 tests** (mock testing - free, fast)
2. **You approve and we run them**
3. **I'll create Phase 2 tests** (real API - requires your keys)
4. **You provide API keys and approve spending ~$0.03**
5. **We run real tests and analyze results**
6. **I'll create Phase 3 improvements** based on Phase 2 findings
7. **Final production-ready testing**

**Total Time:** ~2-3 hours
**Total Cost:** ~$0.08-$0.10
**Deliverable:** Production-ready external LLM integration with comprehensive tests

---

**Ready to start Phase 1?** Say "yes" and I'll create the mock tests!
