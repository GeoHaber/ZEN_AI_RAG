# 🧠 ZenAI LLM Integration Architecture

## Overview
The RAG Chat integrates **llama.cpp** as the local LLM backend, running GGUF-quantized models via a subprocess-based orchestrator.

---

## 🏗️ Architecture Stack

```
┌─────────────────────────────────────────────────────────────┐
│                   Streamlit UI Layer                        │
│            (streamlit_rag_chat.py / v2.py)                 │
└─────────────────┬───────────────────────────────────────────┘
                  │ HTTP/AsyncIO
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              AsyncZenAIBackend (async_backend.py)           │
│  • Async HTTP client using httpx                           │
│  • Non-blocking streaming responses                         │
│  • Model management (download, swap, list)                 │
└─────────────────┬───────────────────────────────────────────┘
                  │ HTTP Requests (port 8001, 8002)
                  ▼
┌─────────────────────────────────────────────────────────────┐
│           ZenAI Orchestrator (server.py)                    │
│  • Port 8001: LLM API (OpenAI compatible)                  │
│  • Port 8002: Management (model swap, swarm launch)        │
│  • Port 8003: Voice/TTS                                     │
│  • Health checks, process monitoring                        │
└─────────────────┬───────────────────────────────────────────┘
                  │ subprocess.Popen
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              llama-server.exe (llama.cpp)                   │
│  • GPU/CPU inference via llama.cpp                         │
│  • Loads .gguf model files from disk                        │
│  • Exposes OpenAI-compatible /v1/chat/completions API      │
│  • Streaming support                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🤖 Current LLM Models

### Primary Model (Default)
**Qwen 2.5 Coder 7B (Q4_K_M)**
- **File**: `qwen2.5-coder-7b-instruct-q4_k_m.gguf` (4.4 GB)
- **Repository**: `Qwen/Qwen2.5-Coder-7B-Instruct-GGUF`
- **Parameters**: 7 billion (7B)
- **Quantization**: Q4_K_M (4-bit, balanced speed/quality)
- **RAM Required**: ~5-6 GB
- **Context Window**: 32K tokens (~24,000 words)
- **Speed**: ⚡⚡⚡ Fast
- **Quality**: ⭐⭐⭐⭐ Excellent
- **Best For**: 💻 Coding, programming, code analysis
- **License**: Apache 2.0 (Commercial OK)
- **Benchmark**: HumanEval 88% (top tier)

### Alternative Models (Fallback)
**Llama 3.2 3B (Q4_K_M)**
- **File**: `Llama-3.2-3B-Instruct-Q4_K_M.gguf` (2.0 GB)
- **Repository**: `bartowski/Llama-3.2-3B-Instruct-GGUF`
- **Parameters**: 3 billion (3B)
- **Quantization**: Q4_K_M
- **RAM Required**: ~4 GB
- **Context Window**: 128K tokens (huge!)
- **Speed**: ⚡⚡⚡⚡ Ultra Fast
- **Quality**: ⭐⭐⭐ Good
- **Best For**: Long documents, retrieval tasks
- **License**: Llama 2 (Commercial OK)

---

## 🔧 Integration Points

### 1. **Model Loading & Initialization**
```python
# config_system.py
MODEL_DIR = Path("C:/AI/Models")  # or auto-detected central store
MODEL_FILE = "qwen2.5-coder-7b-instruct-q4_k_m.gguf"
DEFAULT_MODEL_PATH = MODEL_DIR / MODEL_FILE

# config.py defaults
DEFAULT_MODEL_PATH: Path = MODEL_DIR / MODEL_FILE
BIN_DIR = Path("_bin/")  # Contains llama-server.exe
```

### 2. **Process Management (server.py)**
```python
# Launch llama.cpp subprocess
SERVER_EXE = config.BIN_DIR / "llama-server.exe"
MODEL_PATH = config.MODEL_DIR / config.default_model

# Command line
subprocess.Popen([
    str(SERVER_EXE),
    "-m", str(MODEL_PATH),
    "--port", "8001",
    "-n", "2048",  # Context
    "-ngl", "33",  # GPU layers
], 
stdout=PIPE, stderr=PIPE
)
```

### 3. **HTTP API (Port 8001)**
OpenAI-compatible endpoint:
```
POST /v1/chat/completions
{
  "model": "qwen2.5-coder",
  "messages": [{"role": "user", "content": "..."}],
  "stream": true,
  "temperature": 0.7
}
```

### 4. **Async Backend (async_backend.py)**
```python
class AsyncZenAIBackend:
    api_url = f"http://localhost:8001/v1/chat/completions"
    
    async def get_models(self):
        # Fetch from port 8002 (management)
        response = await client.get("/models/available")
        
    async def chat(self, messages, stream=True):
        # Stream response from port 8001
        async with httpx.stream("POST", self.api_url, ...) as response:
            async for line in response.aiter_lines():
                # yield tokens
```

---

## 📊 Model Download Flow

### Process:
1. User selects model in UI
2. Request sent to `/models/download` endpoint (port 8002)
3. `model_manager.py` downloads from HuggingFace
4. Saved to `MODEL_DIR`
5. User can swap to it with `/model/swap` endpoint

### Download Code:
```python
# model_manager.py
from huggingface_hub import hf_hub_download

def download_model(repo_id: str, filename: str):
    """Download GGUF model from HuggingFace"""
    model_path = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        local_dir=MODEL_DIR,
        local_dir_use_symlinks=False
    )
    return model_path
```

---

## 🔄 Hot Model Swapping

### Mechanism:
1. Receive `/model/swap` request with new model name
2. Gracefully shutdown current llama-server.exe
3. Wait for cleanup (2-3 seconds)
4. Launch new llama-server.exe with different model
5. Clients reconnect automatically

### Code (server.py):
```python
def swap_model(new_model_name: str):
    global PENDING_MODEL_SWAP
    PENDING_MODEL_SWAP = new_model_name
    
    # Orchestrator loop handles:
    # 1. Kill old process
    # 2. Load new model
    # 3. Start new process
    # 4. Health check
```

---

## 🚀 Swarm Expert Mode

Multiple instances of llama.cpp running on different ports for expert specialization:

```python
# /swarm/launch endpoint
{
  "model": "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
  "port": 8005
}

# Spawns llama-server.exe on port 8005 with same/different model
# For swarm of coding experts, reasoning experts, etc.
```

---

## 📁 Key Configuration Files

| File | Purpose | Key Settings |
|------|---------|--------------|
| `config_system.py` | Central config | llm_port, mgmt_port, host |
| `model_manager.py` | Model metadata | POPULAR_MODELS, parsing logic |
| `async_backend.py` | HTTP client | api_url, streaming |
| `server.py` | Process orchestrator | MODEL_PATH, SERVER_EXE |
| `zena_mode/handlers.py` | API handlers | /chat, /swap, /models/* |

---

## 🌍 Environment Variables

```bash
# Model directory (auto-detected if not set)
NEBULA_MODEL_DIR=C:/AI/Models

# Ports
ZENAI_PORT=8001          # LLM API
ZENAI_MGMT_PORT=8002     # Management
ZENAI_VOICE_PORT=8003    # Voice/TTS

# Host
ZENAI_HOST=localhost

# GPU acceleration
CUDA_VISIBLE_DEVICES=0   # Use GPU 0
```

---

## 🎯 Performance Characteristics

### Memory Usage (Q4 Quantization)
- **Model**: ~4-5 GB (stored on disk)
- **VRAM**: ~2-3 GB (if GPU acceleration)
- **RAM**: ~3-4 GB (context + overhead)
- **Total**: ~7-8 GB typical usage

### Inference Speed (7B Model, Q4, CPU)
- **First token**: 500-1000ms (loading from disk)
- **Subsequent tokens**: 50-100ms/token (on decent CPU)
- **With GPU**: 10-20ms/token (significant speedup)

### Streaming
- Response streamed token-by-token
- First token appears in ~2-3 seconds (CPU) / <1s (GPU)
- Subsequent tokens appear as they're generated

---

## 🔌 RAG Integration

The LLM is **optional** for RAG chat:

1. **Without LLM**: Pure retrieval (fast, no generation)
   ```python
   results = rag.hybrid_search(query, k=5)
   # Returns: [source1, source2, source3, ...]
   ```

2. **With LLM**: Generation over retrieval results
   ```python
   results = rag.hybrid_search(query, k=5)
   llm_response = llm.chat(f"Based on: {results}\n\nQuestion: {query}")
   ```

### Current streamlit_rag_chat Usage:
- Searches knowledge base with RAG
- Builds response from TOP-3 results
- **Does NOT call LLM** (pure retrieval)
- But `AsyncZenAIBackend` is loaded for future enhancement

---

## 📝 Usage in Streamlit Apps

### Current (v1):
```python
# Load RAG system (local retrieval)
rag, error = load_rag_system()

# Search only
results = rag.hybrid_search(user_input, k=5, alpha=0.6, rerank=True)

# Display results
st.write(f"Found {len(results)} sources")
```

### Planned (v2 Enhancement):
```python
# Load both RAG + LLM
rag, _ = load_rag_system()
backend, _ = load_backend()

# Retrieve context
sources = rag.hybrid_search(user_input, k=5)

# Generate with LLM
response = await backend.chat(
    messages=[
        {"role": "system", "content": f"Context: {sources}"},
        {"role": "user", "content": user_input}
    ],
    stream=True
)
```

---

## 🛠️ Troubleshooting

### "LLM unavailable" Error
```
Check:
1. Is llama-server.exe running? (Task Manager)
2. Is MODEL_FILE present in MODEL_DIR?
3. Is port 8001 accessible? (netstat -an | grep 8001)
4. Enough RAM? (Check free memory)
```

### Slow responses
```
1. CPU-bound → Enable GPU acceleration
2. Disk I/O → Use faster SSD
3. Model too large → Switch to smaller model (3B vs 7B)
4. Network latency → Check /stats endpoint
```

### Model not found
```
1. Check MODEL_DIR path
2. File name matches exactly (case-sensitive)
3. Enough disk space (2-5 GB per model)
4. Download from HuggingFace manually if needed
```

---

## 📚 References

- **llama.cpp**: https://github.com/ggerganov/llama.cpp
- **GGUF Format**: Binary quantized model format
- **Qwen 2.5**: https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF
- **Llama 3.2**: https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF
- **OpenAI API Compat**: https://platform.openai.com/docs/api-reference

---

## 🎬 Next Steps (From To_dodo.md)

1. **Integrate LLM into streamlit_rag_chat**
   - Add response generation after retrieval
   - Streaming responses to UI
   - LLM-powered response refinement

2. **Model library scanner** (background task)
   - Periodically check HuggingFace for new models
   - Research alternatives (coding, reasoning, multilingual)
   - Auto-download when available

3. **Expert swarm system**
   - Different models for different tasks
   - Coordinator model to route queries
   - Consensus voting from multiple experts

4. **Response enhancement**
   - Animate thinking indicator (face scratching 🤔)
   - Language-dependent "working on it..." messages
   - Progress updates for long operations
