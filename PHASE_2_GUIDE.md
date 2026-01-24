# Phase 2: Real API Testing - User Guide

**Status:** ✅ Ready to Run
**Prerequisites:** ✅ Phase 1 Complete (22/22 tests passing)
**Expected Cost:** ~$0.03
**Expected Time:** ~30 seconds

---

## Prerequisites

### 1. API Keys Required

You need at least ONE of the following API keys:

#### Option A: Anthropic Claude (Recommended)
```bash
# Get key from: https://console.anthropic.com/
export ANTHROPIC_API_KEY="sk-ant-..."
```

#### Option B: Google Gemini
```bash
# Get key from: https://makersuite.google.com/app/apikey
export GOOGLE_API_KEY="AIza..."
```

#### Option C: Grok (Optional)
```bash
# Get key from: https://x.ai/api
export XAI_API_KEY="xai-..."
```

**Windows Users:**
```cmd
set ANTHROPIC_API_KEY=sk-ant-...
set GOOGLE_API_KEY=AIza...
set XAI_API_KEY=xai-...
```

### 2. Code Requirements ✅
- ✅ Phase 1 complete (all features implemented)
- ✅ `_query_external_agent` method available
- ✅ `CostTracker` class available
- ✅ All dependencies installed

---

## What Phase 2 Tests

### Test 1: Factual Query (High Agreement Expected)
**Query:** "What is the capital of France?"

**Purpose:**
- Test basic API connectivity
- Test response parsing
- Verify consensus on factual information

**Expected Result:**
- ✅ All LLMs should answer "Paris"
- ✅ High consensus score (>80%)
- ✅ Cost: ~$0.005

**Example Output:**
```
[Claude] The capital of France is Paris. (0.8s)
[Gemini] Paris is the capital of France. (1.1s)
[Grok] The capital city of France is Paris. (0.9s)

Consensus: 85.3%
Test Cost: $0.0047
```

---

### Test 2: Math Query (High Agreement Expected)
**Query:** "If a train travels at 60mph for 2.5 hours, how far does it go?"

**Purpose:**
- Test calculation accuracy
- Verify consensus on numerical results
- Test confidence extraction

**Expected Result:**
- ✅ All LLMs should answer "150 miles"
- ✅ High consensus score (>70%)
- ✅ Cost: ~$0.005

**Example Output:**
```
[Claude] The train travels 150 miles. (0.7s)
[Gemini] Distance = 60 × 2.5 = 150 miles (1.0s)
[Grok] 150 miles (0.8s)

Consensus: 78.2%
Test Cost: $0.0051
```

---

### Test 3: Nuanced Query (Disagreement Expected)
**Query:** "Should investors buy stocks during a recession?"

**Purpose:**
- Test handling of subjective questions
- Test disagreement detection
- Verify confidence weighting works

**Expected Result:**
- ⚠️ Different opinions expected
- ⚠️ Low/moderate consensus (30-60%)
- ✅ Cost: ~$0.01

**Example Output:**
```
[Claude] It depends on risk tolerance and time horizon... (0.9s)
[Gemini] Some investors see recessions as buying opportunities... (1.2s)
[Grok] Historically, buying during recessions has been profitable... (1.0s)

Consensus: 42.7% (as expected - nuanced topic)
Test Cost: $0.0089
```

---

### Test 4: Code Generation Query (Different Implementations)
**Query:** "Write a Python function to check if a number is prime"

**Purpose:**
- Test code generation
- Handle format differences (comments, style)
- Verify semantic understanding

**Expected Result:**
- ✅ All provide working prime checker
- ⚠️ Different implementations (moderate consensus)
- ✅ Cost: ~$0.01

**Example Output:**
```
[Claude] def is_prime(n):
    if n < 2: return False
    for i in range(2, int(n**0.5)+1):
        if n % i == 0: return False
    return True (1.1s)

[Gemini] def is_prime(num):
    if num <= 1:
        return False
    for i in range(2, num):
        if num % i == 0:
            return False
    return True (1.3s)

Consensus: 58.4% (different implementations, same logic)
Test Cost: $0.0103
```

---

### Test 5: Cost Tracking
**Purpose:**
- Verify cost tracking works with real APIs
- Ensure total cost stays under budget
- Test cost breakdown by provider

**Expected Result:**
- ✅ Total cost < $0.05
- ✅ Cost breakdown shows per-provider costs
- ✅ Gemini cheapest, Claude most expensive

**Example Output:**
```
Total Cost: $0.0312

Cost Breakdown:
  claude-3-5-sonnet-20241022: $0.0187
  gemini-pro: $0.0045
  grok-beta: $0.0080
```

---

### Test 6: Confidence Extraction
**Purpose:**
- Test confidence extraction on real responses
- Verify linguistic markers work
- Test explicit confidence percentages

**Expected Result:**
- ✅ Extracts confidence from responses
- ✅ High confidence for simple math (>90%)
- ✅ Moderate confidence for nuanced questions

---

## How to Run Phase 2

### Step 1: Set API Keys
```bash
# Choose at least ONE:
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="AIza..."
export XAI_API_KEY="xai-..."  # Optional
```

### Step 2: Run Tests
```bash
cd "C:\Users\dvdze\.claude-worktrees\ZEN_AI_RAG\naughty-antonelli"
python -m pytest tests/test_external_llm_real.py -v --tb=short
```

### Step 3: Review Results
Tests will output:
- Response from each LLM
- Consensus scores
- Cost per test
- Total cost breakdown

### Step 4: Check Total Cost
```bash
# Look for summary at end:
# "Total Cost: $0.0312"
```

---

## Expected Results

### If ALL API Keys Present (Claude + Gemini + Grok):
```
tests/test_external_llm_real.py::TestRealAPIQueries::test_factual_query_consensus PASSED
tests/test_external_llm_real.py::TestRealAPIQueries::test_math_query_consensus PASSED
tests/test_external_llm_real.py::TestRealAPIQueries::test_nuanced_query_disagreement PASSED
tests/test_external_llm_real.py::TestRealAPIQueries::test_code_generation_query PASSED
tests/test_external_llm_real.py::TestCostTracking::test_total_cost_under_budget PASSED
tests/test_external_llm_real.py::TestConfidenceExtraction::test_confidence_in_real_responses PASSED

============================== 6 passed in 28.3s ===============================

Total Cost: ~$0.03
```

### If Only ONE API Key (e.g., Anthropic):
```
tests/test_external_llm_real.py::TestRealAPIQueries::test_factual_query_consensus PASSED
  (Single LLM - no consensus calculation)
tests/test_external_llm_real.py::TestRealAPIQueries::test_math_query_consensus PASSED
tests/test_external_llm_real.py::TestRealAPIQueries::test_nuanced_query_disagreement PASSED
tests/test_external_llm_real.py::TestRealAPIQueries::test_code_generation_query PASSED
tests/test_external_llm_real.py::TestCostTracking::test_total_cost_under_budget PASSED
tests/test_external_llm_real.py::TestConfidenceExtraction::test_confidence_in_real_responses PASSED

============================== 6 passed in 12.1s ===============================

Total Cost: ~$0.01
```

---

## Cost Breakdown

### Per Test Costs:
| Test | Providers | Estimated Cost |
|------|-----------|----------------|
| Test 1: Factual | 3 LLMs | $0.005 |
| Test 2: Math | 3 LLMs | $0.005 |
| Test 3: Nuanced | 3 LLMs | $0.010 |
| Test 4: Code | 3 LLMs | $0.010 |
| Test 5: Cost Tracking | 3 LLMs | $0.002 |
| Test 6: Confidence | 1 LLM | $0.001 |
| **Total** | | **$0.033** |

### Cost by Provider (Estimated):
- **Gemini:** ~$0.005 (cheapest)
- **Grok:** ~$0.010 (moderate)
- **Claude:** ~$0.018 (most capable, slightly higher cost)

**Note:** Actual costs may vary slightly based on response length.

---

## Troubleshooting

### Issue 1: "No API keys found"
**Error:**
```
SKIPPED [1] tests/test_external_llm_real.py:44: No API keys found
```

**Solution:**
Set at least one API key:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Issue 2: Authentication Failure (401)
**Error:**
```
[API Error: 401]
```

**Solution:**
- Verify API key is correct
- Check key hasn't expired
- Ensure key has proper permissions

### Issue 3: Rate Limit (429)
**Error:**
```
[API Error: 429]
```

**Solution:**
- Wait 1 minute and re-run tests
- Check your API usage limits
- Consider running tests with fewer providers

### Issue 4: Network Error
**Error:**
```
[Bridge Error: Connection timeout]
```

**Solution:**
- Check internet connection
- Verify firewall not blocking HTTPS
- Try again in a few minutes

### Issue 5: High Costs
**Error:**
```
Total Cost: $0.08 (expected ~$0.03)
```

**Solution:**
- Check response lengths (very long responses cost more)
- Verify test queries haven't changed
- Review cost breakdown to identify expensive provider

---

## What to Expect

### Success Indicators:
- ✅ All 6 tests pass
- ✅ Total cost < $0.05
- ✅ High consensus on factual queries (>70%)
- ✅ Low consensus on nuanced queries (30-60%)
- ✅ All responses relevant to questions
- ✅ Confidence scores extracted correctly

### Normal Variations:
- ⚠️ Response times vary (0.5s - 2.0s)
- ⚠️ Consensus scores vary by query type
- ⚠️ Different code implementations (still correct)
- ⚠️ Cost varies by response length

### Red Flags:
- ❌ All tests fail → Check API keys
- ❌ Cost > $0.10 → Something wrong with cost calculation
- ❌ Consensus always 0% → Check consensus calculation
- ❌ No responses → Check network/firewall

---

## After Phase 2

### If Tests Pass:
1. ✅ External LLM integration working
2. ✅ Consensus calculation validated
3. ✅ Cost tracking verified
4. ✅ Ready for Phase 3 (optimization)

### Phase 3 Preview (Optional):
- Caching identical queries (50% cost reduction)
- Retry logic with exponential backoff
- Fallback priority (Claude → Gemini → Grok)
- Rate limiting protection
- Estimated cost: ~$0.05

### Next Steps:
1. Review Phase 2 results
2. Decide if Phase 3 optimization needed
3. Integrate into production (if satisfied)
4. Monitor costs in production

---

## Quick Start (TL;DR)

```bash
# 1. Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# 2. Run tests
cd "C:\Users\dvdze\.claude-worktrees\ZEN_AI_RAG\naughty-antonelli"
python -m pytest tests/test_external_llm_real.py -v

# 3. Check cost at end of output
# Expected: ~$0.03
```

---

**Ready to run?** Set your API keys and execute the tests!

**Questions before running?** Review the troubleshooting section above.

**Want to skip Phase 2?** You can use the mock tests (Phase 1) for integration testing without API costs.
