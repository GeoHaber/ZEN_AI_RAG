# ZenAI User Guide

**Version:** 2.0 with Multi-LLM Consensus
**Date:** 2026-01-23

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Features](#features)
3. [External LLM Configuration](#external-llm-configuration)
4. [RAG (Retrieval-Augmented Generation)](#rag-retrieval-augmented-generation)
5. [Multi-LLM Consensus](#multi-llm-consensus)
6. [Cost Tracking](#cost-tracking)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### First Time Setup

1. **Run the application:**
   ```powershell
   python start_llm.py
   ```

2. **What happens automatically:**
   - Checks for required dependencies
   - Downloads Qwen2.5-Coder model (if needed)
   - Starts the local LLM server
   - Opens ZenAI in your browser

3. **Start chatting!**
   - The local LLM (Zena) is ready immediately
   - No API keys needed for basic use

---

## Features

### 🤖 Local LLM (Zena)
- **Model:** Qwen2.5-Coder (7B parameters)
- **Speed:** Fast local responses
- **Privacy:** Everything runs on your machine
- **Role:** Primary assistant, coordinator

### ☁️ External LLM Integration
- **Providers:** Anthropic Claude, Google Gemini, xAI Grok
- **Consensus:** Query multiple LLMs and calculate agreement
- **Cost Tracking:** Budget limits and spending monitoring
- **Optional:** Works fine with just the local LLM

### 📚 RAG (Retrieval-Augmented Generation)
- **Web scraping:** Extract content from URLs
- **Document indexing:** Built-in documentation search
- **Context enhancement:** Answers with real-time web data
- **Bot protection:** Handles CAPTCHAs and rate limits

### 💰 Cost Tracking
- **Real-time monitoring:** See API costs as you use external LLMs
- **Budget enforcement:** Set spending limits
- **Per-provider breakdown:** Track costs for each LLM separately

---

## External LLM Configuration

### Why Use External LLMs?

The local LLM (Zena) is fast and private, but external LLMs offer:
- **More knowledge:** Trained on larger datasets
- **Better code:** Higher quality code generation
- **Consensus:** Multiple LLMs can validate answers

### How to Enable

1. **Open Settings** (⚙️ button in ZenAI)

2. **Navigate to "External LLMs (Multi-LLM Consensus)"**

3. **Toggle "Enable External LLMs"** to ON

4. **Add API Keys** (see below)

### Getting FREE API Keys

#### Option 1: Google Gemini (Recommended - FREE Forever)

1. Visit: https://aistudio.google.com/app/apikey
2. Sign in with Google
3. Click "Create API Key"
4. Copy the key (starts with `AIza`)
5. Paste into ZenAI settings

**Cost:** FREE forever!

#### Option 2: Anthropic Claude ($5 Free Credits)

1. Visit: https://console.anthropic.com/
2. Sign up for an account
3. Get $5 free credits automatically
4. Go to Settings → API Keys
5. Create a new key (starts with `sk-ant-`)
6. Paste into ZenAI settings

**Cost:** $5 free credits (~250 queries)

#### Option 3: xAI Grok ($25 Free Credits)

1. Visit: https://x.ai/api
2. Sign up for an account
3. Get $25 free credits
4. Copy your API key (starts with `xai-`)
5. Paste into ZenAI settings

**Cost:** $25 free credits (~2,500 queries)

### Configuration Options

**Multi-LLM Consensus:**
- **ON:** Query all configured LLMs and calculate agreement score
- **OFF:** Use single LLM (faster, cheaper)

**Cost Tracking:**
- **ON:** Track spending and enforce budget limits
- **OFF:** No cost monitoring (not recommended)

**Budget Limit:**
- Set maximum monthly spend (default: $10)
- Prevents unexpected charges

---

## RAG (Retrieval-Augmented Generation)

### What is RAG?

RAG enhances Zena's answers by:
1. Fetching real-time information from the web
2. Extracting relevant content
3. Using that content to inform the response

### How to Use RAG

Simply include a URL in your question:

**Example 1: Technical Documentation**
```
User: "What's new in Python 3.12? https://docs.python.org/3/whatsnew/3.12.html"
Zena: [Scrapes the page and summarizes new features]
```

**Example 2: News Article**
```
User: "Summarize this article: https://example.com/news/article"
Zena: [Extracts article text and provides summary]
```

**Example 3: Built-in Documentation**
```
User: "How do I configure external LLMs?"
Zena: [Searches local documentation and explains]
```

### RAG Features

✅ **Bot protection handling:** Detects and handles CAPTCHAs
✅ **Polite scraping:** Respects robots.txt and rate limits
✅ **Content extraction:** Removes ads, banners, cookies
✅ **Fallback handling:** Graceful degradation if scraping fails

---

## Multi-LLM Consensus

### How It Works

When consensus is enabled and you have multiple API keys configured:

1. **Local LLM decides:** Is this query complex enough for external help?
2. **Query external LLMs:** Send the question to Claude, Gemini, Grok
3. **Calculate consensus:** Compare answers and compute agreement score
4. **Return result:** Best answer + confidence level

### When to Use Consensus

**Good for:**
- Complex code generation
- Nuanced advice questions
- Critical decisions

**Not needed for:**
- Simple facts ("What is the capital of France?")
- Greetings and casual chat
- Math calculations

### Example

**User:** "Should I buy stocks during a recession?"

**Zena's Process:**
1. Recognizes this is a complex, nuanced question
2. Queries Claude, Gemini, and Grok
3. Claude says: "It depends on your risk tolerance..."
4. Gemini says: "Historical data shows mixed results..."
5. Grok says: "Consider dollar-cost averaging..."
6. Calculates consensus: 75% agreement on "it depends"
7. Returns: Combined answer with confidence score

**Cost:** ~$0.03 for 3 LLM queries

---

## Cost Tracking

### Viewing Costs

Zena tracks costs in real-time:
- **Total spent:** Overall API spending
- **Per-provider:** Claude vs Gemini vs Grok breakdown
- **Per-query:** Cost of individual questions

### Setting Budget Limits

1. Open Settings → External LLMs
2. Enable "Cost Tracking"
3. Set "Budget Limit" (e.g., $10/month)
4. Zena will stop using external LLMs if budget is exceeded

### Cost Examples

**Single LLM Query:**
- Gemini: $0.00 (FREE tier)
- Claude Sonnet: ~$0.01
- Grok: ~$0.01

**Consensus Query (3 LLMs):**
- Total: ~$0.02-$0.03

**100 Queries:**
- Gemini only: $0.00
- Claude only: ~$1.00
- All three (consensus): ~$2.00-$3.00

---

## Troubleshooting

### Issue: "External LLMs not working"

**Checks:**
1. ✅ External LLMs enabled in settings?
2. ✅ API keys entered correctly? (no spaces)
3. ✅ Internet connection working?
4. ✅ Provider website not down?

**Solution:** Verify API keys at provider consoles

### Issue: "Local LLM slow or crashing"

**Checks:**
1. ✅ Enough RAM? (8GB minimum, 16GB recommended)
2. ✅ Model downloaded? (Check `models/` folder)
3. ✅ CPU supports required instructions? (AVX2 on Intel/AMD)

**Solution:** Restart app with `python start_llm.py`

### Issue: "RAG not extracting content"

**Checks:**
1. ✅ Website blocking bots? (Try different user agent)
2. ✅ CAPTCHA present? (RAG will skip these)
3. ✅ Website requires login? (RAG can't handle auth)

**Solution:** Some websites cannot be scraped (by design)

### Issue: "Costs higher than expected"

**Checks:**
1. ✅ Consensus mode enabled? (Uses multiple LLMs)
2. ✅ Budget limit set? (Prevent overspending)
3. ✅ Using Gemini? (It's FREE!)

**Solution:** Disable consensus or use only Gemini

---

## FAQ

### Q: Do I need API keys to use ZenAI?
**A:** No! The local LLM works without any API keys. External LLMs are optional.

### Q: Which external LLM should I use?
**A:** Start with Google Gemini (FREE). Add others if you want consensus.

### Q: How much does consensus cost?
**A:** ~$0.02-$0.03 per query (using all three LLMs). FREE if using only Gemini.

### Q: Can I use ZenAI offline?
**A:** Yes! The local LLM works completely offline. External LLMs require internet.

### Q: Is my data private?
**A:** Local LLM: 100% private (runs on your machine). External LLMs: Sent to provider APIs.

### Q: What's the model size?
**A:** Qwen2.5-Coder is 7B parameters (~4.5GB download).

### Q: Can I use my own LLM?
**A:** Yes! Edit `config.py` to point to your own llama.cpp server.

---

## Getting Help

### Documentation Files
- **README_PHASE2.md** - Quick start for Phase 2 testing
- **FREE_API_KEYS_GUIDE.md** - Step-by-step API key instructions
- **PHASE_2_GUIDE.md** - Understanding Phase 2 tests
- **EXTERNAL_LLM_INTEGRATION_COMPLETE.md** - Technical details

### Ask Zena!
```
User: "How do I configure external LLMs?"
Zena: [Searches this documentation and explains]
```

Zena can answer questions about itself by searching the built-in documentation!

---

**Enjoy using ZenAI! 🎉**
