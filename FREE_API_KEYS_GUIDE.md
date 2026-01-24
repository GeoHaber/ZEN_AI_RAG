# How to Get FREE API Keys for Phase 2 Testing

**Good News:** All three providers offer free tiers or trial credits!

You can run Phase 2 tests for **FREE** or very low cost (~$0.03).

---

## Option 1: Anthropic Claude (RECOMMENDED) 💰 FREE TRIAL

### Free Credits: $5 on signup
**Enough for:** ~300 Phase 2 test runs

### How to Get:
1. **Visit:** https://console.anthropic.com/
2. **Sign up** with email (no credit card required initially)
3. **Get $5 free credits** on new accounts
4. **Copy API key** from Settings → API Keys

### Set API Key:
```bash
# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="sk-ant-..."

# Windows (CMD)
set ANTHROPIC_API_KEY=sk-ant-...

# Linux/Mac
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Verify:
```bash
python -c "import os; print('Key set:', bool(os.getenv('ANTHROPIC_API_KEY')))"
```

**Phase 2 Cost with Claude:**
- Single test run: ~$0.02
- With $5 credits: ~250 test runs
- **Effectively FREE for testing!**

---

## Option 2: Google Gemini (CHEAPEST) 💰 FREE TIER

### Free Tier: 60 requests/minute (FREE forever)
**Enough for:** Unlimited Phase 2 testing (within rate limits)

### How to Get:
1. **Visit:** https://makersuite.google.com/app/apikey
   - Alternative: https://aistudio.google.com/app/apikey
2. **Sign in** with Google account (no credit card needed)
3. **Click "Create API Key"**
4. **Copy the key** (starts with "AIza...")

### Set API Key:
```bash
# Windows (PowerShell)
$env:GOOGLE_API_KEY="AIza..."

# Windows (CMD)
set GOOGLE_API_KEY=AIza...

# Linux/Mac
export GOOGLE_API_KEY="AIza..."
```

### Verify:
```bash
python -c "import os; print('Key set:', bool(os.getenv('GOOGLE_API_KEY')))"
```

**Phase 2 Cost with Gemini:**
- Single test run: ~$0.005 (or FREE with free tier)
- Rate limit: 60 requests/minute
- **Completely FREE!**

---

## Option 3: Grok (xAI) 💰 $25 FREE CREDITS

### Free Credits: $25 on signup
**Enough for:** ~2,500 Phase 2 test runs

### How to Get:
1. **Visit:** https://x.ai/api
2. **Sign up** (may require X/Twitter account)
3. **Get $25 free credits**
4. **Copy API key** from console

### Set API Key:
```bash
# Windows (PowerShell)
$env:XAI_API_KEY="xai-..."

# Windows (CMD)
set XAI_API_KEY=xai-...

# Linux/Mac
export XAI_API_KEY="xai-..."
```

### Verify:
```bash
python -c "import os; print('Key set:', bool(os.getenv('XAI_API_KEY')))"
```

**Phase 2 Cost with Grok:**
- Single test run: ~$0.01
- With $25 credits: ~2,500 test runs
- **Effectively FREE for testing!**

---

## Quick Setup (All Three - RECOMMENDED)

### Get All Three Keys (5 minutes total):

```bash
# 1. Anthropic Claude ($5 free)
Visit: https://console.anthropic.com/
Copy key → starts with "sk-ant-"

# 2. Google Gemini (FREE forever)
Visit: https://makersuite.google.com/app/apikey
Copy key → starts with "AIza"

# 3. Grok ($25 free)
Visit: https://x.ai/api
Copy key → starts with "xai-"
```

### Set All Keys (Windows):
```powershell
$env:ANTHROPIC_API_KEY="sk-ant-YOUR_KEY_HERE"
$env:GOOGLE_API_KEY="AIzaYOUR_KEY_HERE"
$env:XAI_API_KEY="xai-YOUR_KEY_HERE"
```

### Verify All Keys:
```bash
python -c "import os; print('Anthropic:', bool(os.getenv('ANTHROPIC_API_KEY'))); print('Google:', bool(os.getenv('GOOGLE_API_KEY'))); print('Grok:', bool(os.getenv('XAI_API_KEY')))"
```

### Run Phase 2:
```bash
cd "C:\Users\dvdze\.claude-worktrees\ZEN_AI_RAG\naughty-antonelli"
python -m pytest tests/test_external_llm_real.py -v
```

**Expected:**
```
============================== 6 passed in ~30s ===============================
Total Cost: ~$0.03 (deducted from your free credits)
```

---

## Cost Comparison (Phase 2 Single Run)

| Provider | Free Credits | Phase 2 Cost | Runs Available |
|----------|-------------|--------------|----------------|
| **Gemini** | FREE tier | $0.005 | ♾️ Unlimited* |
| **Grok** | $25 | $0.010 | ~2,500 |
| **Claude** | $5 | $0.018 | ~250 |
| **All 3** | $30 total | $0.033 | 900+ |

*Within 60 req/min rate limit

---

## Recommended Setup Path

### Path 1: Fastest (1 minute)
**Get Google Gemini only** (FREE forever)
- No credit card needed
- Instant activation
- Good enough for Phase 2

### Path 2: Best Coverage (5 minutes)
**Get all three keys**
- $30+ in free credits
- Test multi-LLM consensus
- Full Phase 2 experience

### Path 3: Most Affordable (3 minutes)
**Get Gemini + Grok**
- $25 in free credits
- Two LLM consensus
- Very low cost

---

## Step-by-Step: Google Gemini (Easiest)

### 1. Visit Google AI Studio
```
https://aistudio.google.com/app/apikey
```

### 2. Sign In
- Use your Google account
- No credit card needed
- No trial expiration

### 3. Create API Key
- Click "Create API Key"
- Choose "Create API key in new project" (or existing)
- Copy the key (starts with "AIza")

### 4. Set Environment Variable
```powershell
# PowerShell (Windows)
$env:GOOGLE_API_KEY="AIzaYOUR_KEY_HERE"
```

### 5. Run Phase 2
```bash
cd "C:\Users\dvdze\.claude-worktrees\ZEN_AI_RAG\naughty-antonelli"
python -m pytest tests/test_external_llm_real.py -v
```

**Done!** Phase 2 will run with Gemini (FREE).

---

## Troubleshooting Free Tiers

### Issue: "Credit card required"
**Solution:** Try Google Gemini first - no card needed

### Issue: "Free credits expired"
**Some providers:** Free credits expire after 3 months
**Solution:** Google Gemini has no expiration

### Issue: "Rate limit exceeded"
**Google Gemini:** 60 requests/minute
**Solution:** Wait 1 minute between test runs

### Issue: "Invalid API key"
**Check:**
- Key copied correctly (no extra spaces)
- Key starts with correct prefix (sk-ant-, AIza, xai-)
- Account activated (check email for verification)

---

## After Getting Keys

### Run Phase 2 Tests:
```bash
cd "C:\Users\dvdze\.claude-worktrees\ZEN_AI_RAG\naughty-antonelli"
python -m pytest tests/test_external_llm_real.py -v
```

### Check Results:
```
tests/test_external_llm_real.py::TestRealAPIQueries::test_factual_query_consensus PASSED
tests/test_external_llm_real.py::TestRealAPIQueries::test_math_query_consensus PASSED
tests/test_external_llm_real.py::TestRealAPIQueries::test_nuanced_query_disagreement PASSED
tests/test_external_llm_real.py::TestRealAPIQueries::test_code_generation_query PASSED
tests/test_external_llm_real.py::TestCostTracking::test_total_cost_under_budget PASSED
tests/test_external_llm_real.py::TestConfidenceExtraction::test_confidence_in_real_responses PASSED

============================== 6 passed in 28.3s ===============================

Total Cost: $0.03 (using free credits)
Remaining Credits: $29.97
```

---

## Summary

### Best Option for Phase 2:
🥇 **Google Gemini** - FREE forever, no card needed, instant

### Best for Full Testing:
🥇 **All Three** - $30+ free credits, complete multi-LLM testing

### Cost Reality:
- **Google Gemini:** FREE (rate limited)
- **Phase 2 with all three:** ~$0.03 (from $30 free credits)
- **Effective Cost:** $0.00

---

## Quick Links

### Get API Keys:
- **Claude:** https://console.anthropic.com/
- **Gemini:** https://aistudio.google.com/app/apikey
- **Grok:** https://x.ai/api

### Documentation:
- **Claude Docs:** https://docs.anthropic.com/
- **Gemini Docs:** https://ai.google.dev/docs
- **Grok Docs:** https://docs.x.ai/

---

**Next Step:** Get at least one FREE API key (recommend Gemini) and run Phase 2!

**Time Required:** 1-5 minutes
**Cost:** $0.00 (using free credits)
**Result:** Complete external LLM integration testing ✅
