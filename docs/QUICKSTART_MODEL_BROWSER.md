# 🚀 Quick Start - Model Browser in Streamlit RAG Chat v2

## 1. Setup Models

### Option A: Use existing models
```bash
# Copy models to C:/AI/Models
mkdir C:\AI\Models
# Download from HuggingFace and place files here
```

### Option B: Download models
```bash
# Using main ZenAI app - download through UI
python start_llm.py

# Or via command line
# Download Qwen Coder
wget https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/qwen2.5-coder-7b-instruct-q4_k_m.gguf

# Download Llama 3.2
wget https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf
```

## 2. Start the Orchestrator

```bash
# Terminal 1: Start backend services
python start_llm.py

# Or just the HTTP orchestrator
cd zena_mode
python server.py
```

This will:
- ✅ Start llama-server on port 8001 (LLM inference)
- ✅ Start orchestrator on port 8002 (model management)
- ✅ Load default model

## 3. Run Streamlit App

```bash
# Terminal 2: Start Streamlit
streamlit run streamlit_rag_chat_v2.py

# Or with specific port
streamlit run streamlit_rag_chat_v2.py --server.port=8501
```

Opens in browser: http://localhost:8501

## 4. Use Model Browser

### In the Sidebar:
1. **Look for** "🤖 Model Manager" section
2. **Expand** each model to see details
3. **Click** "📦 Load Model" button
4. **Wait** for success message
5. **Check** "Currently Active" shows your model

### Model Details Shown:
```
💻 qwen2.5-coder-7b-instruct-q4_k_m.gguf
├─ Type: Coding
├─ Best for: Code generation & debugging
├─ Quantization: Q4 (⭐ Balanced)
├─ Size: Medium (7B) - ⚡⚡ Balanced
└─ File Size: 4.4 GB

🦙 Llama-3.2-3B-Instruct-Q4_K_M.gguf
├─ Type: General
├─ Best for: General purpose
├─ Quantization: Q4 (⭐ Balanced)
├─ Size: Small (3B) - ⚡ Fast
└─ File Size: 2.0 GB
```

## 5. Verify Setup

### Check if working:
```bash
# Model browser shows models?
# ✅ Yes: Models found in C:/AI/Models

# Can load models?
# ✅ Yes: Click button, see success message

# Active model updates?
# ✅ Yes: Shows "Currently Active: model-name"
```

### Troubleshoot:
```bash
# No models showing?
→ Check C:/AI/Models directory exists
→ Check files have .gguf extension
→ Check file permissions (readable)

# Can't load model?
→ Check orchestrator running (port 8002)
→ Check error message in Streamlit
→ Check orchestrator logs for errors

# Wrong model info?
→ Metadata parsed from filename
→ Rename to standard format:
   {name}-{size}b-{instruction}-{quant}.gguf
```

## 6. Next: Add LLM Responses

Once model is loaded, you can:

```python
# In streamlit_rag_chat_v2.py
# Add to handle_user_message():

if st.session_state.llm_enabled:
    # Get LLM response
    backend, _ = load_backend()
    response = await backend.chat(
        messages=[
            {"role": "user", "content": user_input}
        ],
        stream=True
    )
```

---

## File Locations

```
C:\Users\dvdze\Documents\_Python\Dev\ZEN_AI_RAG\
├── streamlit_rag_chat_v2.py    ← Run this
├── start_llm.py                 ← Or this first
├── async_backend.py             ← LLM client
├── model_manager.py             ← Model utils
├── MODEL_BROWSER_FEATURE.md     ← Feature docs
└── zena_mode/
    ├── server.py                ← Orchestrator
    ├── rag_pipeline.py          ← RAG system
    └── handlers.py              ← HTTP handlers
```

---

## Common Commands

### Check ports are open:
```bash
# Windows PowerShell
netstat -ano | findstr :8001
netstat -ano | findstr :8002
netstat -ano | findstr :8501
```

### List models:
```bash
dir C:\AI\Models\*.gguf
```

### Kill stuck processes:
```bash
# Windows
taskkill /IM llama-server.exe /F
taskkill /IM python.exe /F

# Then restart
```

### Check model file:
```bash
# Verify GGUF magic number
xxd -l 16 "C:\AI\Models\model.gguf"
# Should show: 4755 4646 (GGFF in hex)
```

---

## Expected Output

### Streamlit Console:
```
2026-02-03 10:15:42 streamlit.logger INFO Initializing...
2026-02-03 10:15:43 streamlit.logger INFO [AsyncBackend] Initialized with API: http://localhost:8001/v1/chat/completions
2026-02-03 10:15:44 root INFO Cache hit for query: What is...
> Network URL: http://localhost:8501
```

### Orchestrator Console:
```
[Engine] Loaded model: qwen2.5-coder-7b-instruct-q4_k_m.gguf
[Engine] Server running on port 8001
[Manager] HTTP server running on port 8002
[Manager] POST /swap - Swapping to llama-3.2-3b.gguf
[Engine] Model swap initiated...
```

### Streamlit Browser:
```
┌─ SIDEBAR ────────────────────┐
│ 🤖 Model Manager            │
│ ┌─ 💻 qwen2.5-coder-7b    │
│ │  Type: Coding            │
│ │  [📦 Load Model]         │
│ └─────────────────────────  │
│ ┌─ 🦙 Llama-3.2-3B        │
│ │  Type: General           │
│ │  [📦 Load Model]         │
│ └─────────────────────────  │
│ ✅ Currently Active:        │
│    qwen2.5-coder-7b...     │
│                             │
│ 📚 Add Knowledge            │
│ [🌐 Web] [📄 Files]        │
└─────────────────────────────┘
```

---

## Performance Tips

### Make it faster:
```python
# 1. Use smaller models (3B vs 7B)
#    ⚡⚡⚡ Faster, less memory

# 2. Use lower quantization (Q3 vs Q8)
#    ⚡⚡ Faster, less quality

# 3. Enable GPU acceleration
#    Set CUDA_VISIBLE_DEVICES=0

# 4. Increase max context if needed
#    Edit llama-server command
```

### Make it better quality:
```python
# 1. Use larger models (7B vs 3B)
#    ⭐⭐⭐ Better responses

# 2. Use higher quantization (Q5 vs Q3)
#    ⭐⭐ Better quality, slower

# 3. Use specialized model
#    💻 Coder for code, etc.

# 4. Combine with RAG
#    LLM answers based on your docs
```

---

## Next Features (Roadmap)

- [ ] One-click model download
- [ ] Model comparison side-by-side
- [ ] Benchmark performance metrics
- [ ] Model ratings & reviews
- [ ] Quick-swap dropdown
- [ ] Model caching for faster loads
- [ ] LLM response integration
- [ ] Multi-model swarm (expert routing)

---

## Support

**Questions?**
- Check [MODEL_BROWSER_FEATURE.md](MODEL_BROWSER_FEATURE.md)
- Check [LLM_INTEGRATION_GUIDE.md](LLM_INTEGRATION_GUIDE.md)
- Check [WEEK_1_ACTION_ITEMS.md](WEEK_1_ACTION_ITEMS.md)

**Issues?**
- Check logs in browser console (F12)
- Check terminal output
- Check network tab for API calls

**Want to extend?**
- Add to `render_model_browser()` in streamlit_rag_chat_v2.py
- Modify `parse_model_info()` for more metadata
- Add more HTTP endpoints to orchestrator
