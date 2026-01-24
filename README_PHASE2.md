# Phase 2: Real API Testing - Quick Start

**Status:** ✅ Ready to Run
**Cost:** FREE (using free credits from providers)
**Time:** 5 minutes setup + 30 seconds testing

---

## 🎯 Quick Start (3 Steps)

### Step 1: Get a FREE API Key (1 minute)

**Easiest:** Google Gemini (FREE forever)
```
Visit: https://aistudio.google.com/app/apikey
Sign in → Click "Create API Key" → Copy key
```

**Alternative:** Anthropic Claude ($5 free credits)
```
Visit: https://console.anthropic.com/
Sign up → Get $5 credits → Copy API key
```

**Alternative:** Grok ($25 free credits)
```
Visit: https://x.ai/api
Sign up → Get $25 credits → Copy API key
```

---

### Step 2: Run the Script (30 seconds)

**Option A: Interactive Script (Recommended)**
```powershell
.\run_phase2_with_free_keys.ps1
```
*The script will prompt you to paste your API key(s)*

**Option B: Manual Setup**
```powershell
# Set API key
$env:GOOGLE_API_KEY="AIzaYOUR_KEY_HERE"

# Run tests
python -m pytest tests/test_external_llm_real.py -v
```

---

### Step 3: Review Results (1 minute)

**Expected output:**
```
============================== 6 passed in ~30s ===============================

Test Results:
✅ Factual query (capital of France)
✅ Math query (train distance)
✅ Nuanced query (stock buying)
✅ Code generation (prime checker)
✅ Cost tracking
✅ Confidence extraction

Total Cost: ~$0.03 (from your free credits)
```

---

## 📚 Full Documentation

### Getting API Keys:
- **FREE_API_KEYS_GUIDE.md** - Step-by-step for all providers

### Understanding Tests:
- **PHASE_2_GUIDE.md** - Detailed test descriptions and expectations

### Implementation Details:
- **EXTERNAL_LLM_INTEGRATION_COMPLETE.md** - Complete technical summary

### Session Summary:
- **SESSION_SUMMARY_2026-01-23_FINAL.md** - Everything accomplished

---

## 💰 Cost Breakdown

### Free Credits Available:
| Provider | Free Credits | Enough For |
|----------|-------------|------------|
| Google Gemini | FREE forever | ♾️ Unlimited |
| Anthropic | $5 | ~250 test runs |
| Grok | $25 | ~2,500 test runs |

### Phase 2 Cost:
- **With 1 provider:** ~$0.01
- **With 2 providers:** ~$0.02
- **With 3 providers:** ~$0.03

**Reality:** Effectively FREE using provider credits!

---

## 🎓 What Phase 2 Tests

### Test 1: Factual Knowledge
**Query:** "What is the capital of France?"
**Purpose:** Verify all LLMs agree on basic facts

### Test 2: Math Calculation
**Query:** "Train traveling 60mph for 2.5 hours?"
**Purpose:** Test numerical accuracy

### Test 3: Nuanced Opinion
**Query:** "Buy stocks during recession?"
**Purpose:** Test disagreement handling

### Test 4: Code Generation
**Query:** "Python prime checker function"
**Purpose:** Test code quality

### Test 5: Cost Tracking
**Purpose:** Verify cost tracking works

### Test 6: Confidence
**Purpose:** Test confidence extraction

---

## 🚀 Recommended Approach

### For Fastest Results (1 minute):
1. Get Google Gemini key (FREE)
2. Run script
3. Done!

### For Best Coverage (5 minutes):
1. Get all three keys (Gemini, Claude, Grok)
2. Run script
3. See multi-LLM consensus in action!

---

## ❓ FAQ

### Q: Do I need all three providers?
**A:** No! Just one is enough for Phase 2. Google Gemini is easiest (FREE).

### Q: Will I be charged money?
**A:** No! All providers offer free credits. Phase 2 uses ~$0.03 from your free credits.

### Q: Which provider is best?
**A:**
- **Gemini:** Cheapest (FREE forever)
- **Claude:** Most capable ($5 free credits)
- **Grok:** Most generous ($25 free credits)

### Q: How long does setup take?
**A:** 1-5 minutes total (get key + run tests)

### Q: What if tests fail?
**A:** Check:
- API key copied correctly (no spaces)
- Internet connection working
- Provider website not down
- See troubleshooting in FREE_API_KEYS_GUIDE.md

---

## 🎉 After Phase 2

### Success Indicators:
- ✅ All 6 tests pass
- ✅ Total cost ~$0.03 (from free credits)
- ✅ Multi-LLM consensus working
- ✅ Ready for production!

### What You'll Have:
- ✅ Fully tested external LLM integration
- ✅ Working cost tracking
- ✅ Consensus calculation validated
- ✅ Production-ready code

### Next Steps:
- Use the integration in your app
- Monitor costs with CostTracker
- Enjoy multi-LLM consensus!

---

## 🔗 Quick Links

**Get API Keys:**
- Gemini: https://aistudio.google.com/app/apikey
- Claude: https://console.anthropic.com/
- Grok: https://x.ai/api

**Run Phase 2:**
```powershell
.\run_phase2_with_free_keys.ps1
```

**Need Help?**
- See: FREE_API_KEYS_GUIDE.md
- See: PHASE_2_GUIDE.md

---

**Ready?** Get a FREE API key and run `.\run_phase2_with_free_keys.ps1` 🚀
