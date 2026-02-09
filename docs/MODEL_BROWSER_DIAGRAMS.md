# Model Browser Architecture & Flow Diagram

## System Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                     STREAMLIT UI BROWSER                           │
│  streamlit_rag_chat_v2.py                                          │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              MAIN CONTENT AREA                               │  │
│  │  ┌──────────────────────────────────────────────────────┐   │  │
│  │  │ 💬 Chat with Your Knowledge                         │   │  │
│  │  │                                                       │   │  │
│  │  │ [Chat history and messages]                         │   │  │
│  │  │                                                       │   │  │
│  │  │ [User input box]                                    │   │  │
│  │  └──────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────┐  ┌──────────────────────────────┐   │
│  │      SIDEBAR (LEFT)      │  │  SIDEBAR (RIGHT) - Settings  │   │
│  │                          │  │                              │   │
│  │  🤖 MODEL MANAGER (NEW)  │  │  ⚙️ Settings                 │   │
│  │  ├─ 💻 qwen2.5-coder  │  │  ├─ Search k                 │   │
│  │  │  • Type: Coding    │  │  ├─ Hybrid α                 │   │
│  │  │  • Quant: Q4 ⭐   │  │  ├─ Reranking               │   │
│  │  │  • Size: 4.4GB     │  │  ├─ Show Sources             │   │
│  │  │  [📦 Load Model]   │  │  └─ Enable Cache             │   │
│  │  │                    │  │                              │   │
│  │  ├─ 🦙 Llama-3.2-3B  │  │  📊 Stats                     │   │
│  │  │  • Type: General   │  │  ├─ 📄 Docs: 42             │   │
│  │  │  • Quant: Q4 ⭐   │  │  ├─ 🧩 Chunks: 128          │   │
│  │  │  • Size: 2.0GB     │  │  └─ ✅ RAG Ready             │   │
│  │  │  [📦 Load Model]   │  │                              │   │
│  │  │                    │  │  📚 Add Knowledge            │   │
│  │  ├─ ✅ Currently:    │  │  ├─ [🌐 Web]                │   │
│  │  │  qwen2.5-coder    │  │  ├─ [📄 Files]              │   │
│  │  │                    │  │  └─ [📁 Folder]            │   │
│  │  └────────────────────┘  │                              │   │
│  │                          └──────────────────────────────┘   │
│  │                                                              │
│  └──────────────────────────────────────────────────────────────┘
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
                               ↕
         HTTP Calls (port 8501 → 8002, 8001)
                               ↕
┌────────────────────────────────────────────────────────────────────┐
│              BACKEND ORCHESTRATOR (server.py)                       │
│  Port 8002: HTTP Management API                                    │
│                                                                     │
│  GET  /model/status       → Returns active model info             │
│  POST /swap               → Load different model                  │
│  POST /swarm/launch       → Start expert on new port              │
│  GET  /models/available   → List available models                 │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ subprocess.Popen(llama-server.exe)                          │  │
│  │ Port 8001: OpenAI-compatible LLM API                        │  │
│  │   /v1/chat/completions  (streaming)                        │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ GGUF Model Files (from C:/AI/Models)                        │  │
│  │   • qwen2.5-coder-7b-instruct-q4_k_m.gguf (4.4GB)          │  │
│  │   • Llama-3.2-3B-Instruct-Q4_K_M.gguf (2.0GB)             │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## User Flow Diagram

```
START
  ↓
[Open Streamlit App]
  ↓
[Initialize Session State]
  ↓
[Render Sidebar]
  ├→ Load Model Browser
  │   └→ get_local_models()
  │       ├─ Scan C:/AI/Models
  │       ├─ Scan ~/AI/Models
  │       ├─ Scan config.MODEL_DIR
  │       ├─ Filter *.gguf files
  │       └─ Return list → Cache
  │
  └→ Display Models
      ├─ For each model:
      │   ├─ parse_model_info()
      │   │   ├─ Extract type (Coder/Math/Llama)
      │   │   ├─ Extract quantization (Q3/Q4/Q5)
      │   │   ├─ Extract size (3B/7B/13B)
      │   │   └─ Return metadata
      │   ├─ Show expandable card
      │   ├─ Display metadata
      │   └─ [📦 Load Model] button
      │
      └─ Fetch & display active model
          └─ GET /model/status
              └─ "Currently Active: qwen2.5..."
  ↓
[User clicks "Load Model" button]
  ↓
[Input Validation]
  ├─ Check rate limiter (20 req/min)
  ├─ Validate model name
  └─ Check HTTP connectivity
  ↓
[Send HTTP Request]
  └─ POST http://localhost:8002/swap
      └─ {"model": "qwen2.5-coder-7b-instruct-q4_k_m.gguf"}
  ↓
[Show Spinner: "Loading qwen2.5-coder-7b..."]
  ↓
[Backend: Orchestrator receives request]
  ├─ Set PENDING_MODEL_SWAP flag
  ├─ Kill current llama-server process
  ├─ Wait for graceful shutdown (2-3s)
  ├─ Launch new llama-server with new model
  ├─ Wait for server ready (health check)
  └─ Return HTTP 200 response
  ↓
[Frontend: Success message]
  ├─ 🎉 "✅ qwen2.5-coder-7b loaded!"
  ├─ Update session state
  └─ Rerun to refresh UI
  ↓
[Fetch & display active model]
  └─ GET /model/status
      └─ Display "Currently Active: qwen2.5..."
  ↓
[User can now use model]
  ├─ Chat interface (once LLM integrated)
  ├─ Load RAG documents
  ├─ Switch models anytime
  └─ Use with inference API
  ↓
END
```

---

## Model Metadata Parsing Flow

```
Model Filename: "qwen2.5-coder-7b-instruct-q4_k_m.gguf"
                     ↓
        parse_model_info(filename)
                     ↓
    ┌───────────────┬──────────────┬──────────────┐
    ↓               ↓              ↓              ↓
[Detect Type]  [Detect Quant]  [Detect Size]  [Icon]
    ↓               ↓              ↓              ↓
"coder"         "q4_k_m"        "7b"         "💻"
    ↓               ↓              ↓              ↓
"Coding"        "Q4 (⭐         "Medium        Icon: 💻
icon: 💻        Balanced)"      (7B)"          Type: Coding
Specialty:                      Speed:         Specialty:
"Code gen &                     "⚡⚡"         "Code generation
debugging"                      RAM: ~5GB      & debugging"
                                               Quant: "Q4 ⭐"
                                               Size: "7B"
```

---

## HTTP Request/Response Flow

### Model Load Request

```
┌─ FRONTEND ──────────────────────────────────────────┐
│                                                      │
│  User clicks: [📦 Load Model]                       │
│       ↓                                              │
│  render_model_browser() → "Load Model" click        │
│       ↓                                              │
│  rate_limiter.is_allowed("swap") → True/False       │
│       ↓                                              │
│  requests.post(                                     │
│    "http://localhost:8002/swap",                   │
│    json={"model": "qwen2.5-coder-7b...gguf"},     │
│    timeout=30                                       │
│  )                                                  │
│       ↓ HTTP POST ↓                                 │
├──────────────────────────────────────────────────────┤
│                                                      │
│  BACKEND: Port 8002                                │
│       ↓                                              │
│  do_POST() {                                        │
│    if self.path == '/swap':                        │
│      model_name = data.get('model')                │
│      validate(model_name)                          │
│      PENDING_MODEL_SWAP = model_name               │
│      return HTTP 200 {                             │
│        "status": "swap_scheduled",                 │
│        "model": "qwen2.5-..."                      │
│      }                                              │
│  }                                                  │
│       ↓ HTTP 200 ↓                                  │
├──────────────────────────────────────────────────────┤
│                                                      │
│  FRONTEND: Receive response                        │
│       ↓                                              │
│  if response.status_code == 200:                   │
│    st.success("✅ qwen2.5... loaded!")             │
│    st.session_state['active_model'] = model_name  │
│    st.rerun()  # Refresh UI                        │
│  else:                                              │
│    st.error(f"❌ Failed: {response.text}")        │
│       ↓                                              │
│  GET /model/status                                 │
│       ↓ HTTP GET ↓                                  │
├──────────────────────────────────────────────────────┤
│                                                      │
│  BACKEND: Return current model                     │
│       ↓                                              │
│  return HTTP 200 {                                 │
│    "model": "qwen2.5-coder-7b-...",               │
│    "loaded": true,                                 │
│    "engine_port": 8001                            │
│  }                                                  │
│       ↓ HTTP 200 ↓                                  │
├──────────────────────────────────────────────────────┤
│                                                      │
│  FRONTEND: Display active model                    │
│       ↓                                              │
│  st.success(                                        │
│    "✅ Currently Active: qwen2.5-coder-7b..."     │
│  )                                                  │
│       ↓                                              │
│  UI Updates ✓                                       │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## File Scanning Logic

```
get_local_models()
    ↓
Initialize: models = [], checked_dirs = set()
    ↓
Search directories:
├─ C:/AI/Models (PRIMARY)
├─ ~/AI/Models (HOME)
└─ config.MODEL_DIR (CONFIG)
    ↓
For each directory:
├─ Check exists() ✓
├─ Check not already scanned (dedup)
├─ Mark as checked: checked_dirs.add(dir_str)
├─ Glob for *.gguf files
│   └─ Sort alphabetically
├─ For each file:
│   ├─ Get file size (MB)
│   ├─ Create model dict:
│   │   {
│   │     'name': 'qwen2.5-coder-7b...',
│   │     'path': 'C:/AI/Models/qwen2.5...',
│   │     'size_mb': 4505.0,
│   │     'size_str': '4.4GB'
│   │   }
│   └─ Append to models list
│
└─ On error: Log warning, continue
    ↓
Return sorted_models
```

---

## Directory Search Pattern

```
Check Locations (in order):
    ↓
1. C:/AI/Models
   ├─ qwen2.5-coder-7b-instruct-q4_k_m.gguf ✓
   ├─ Llama-3.2-3B-Instruct-Q4_K_M.gguf ✓
   └─ other-model.gguf ✓
    ↓
2. ~/AI/Models (if different from #1)
   └─ (Skip if already found)
    ↓
3. config.MODEL_DIR (if different from #1 & #2)
   └─ (Skip if already found)
    ↓
Result: [
  {name: "qwen2.5-coder-7b-instruct-q4_k_m.gguf", ...},
  {name: "Llama-3.2-3B-Instruct-Q4_K_M.gguf", ...},
  {name: "other-model.gguf", ...}
]
```

---

## UI Component Hierarchy

```
streamlit_rag_chat_v2.py
├─ apply_custom_theme()
│  └─ CSS styling
├─ render_header()
│  └─ Animated banner
├─ render_sidebar()
│  ├─ render_model_browser() ← NEW
│  │  ├─ get_local_models()
│  │  ├─ For each model:
│  │  │  ├─ parse_model_info()
│  │  │  ├─ st.expander()
│  │  │  ├─ Display metadata
│  │  │  ├─ [📦 Load Model] button
│  │  │  └─ Handle click → POST /swap
│  │  └─ Fetch active model → GET /status
│  ├─ render_web_input()
│  ├─ render_file_upload()
│  ├─ render_stats()
│  └─ render_settings()
├─ render_chat()
│  ├─ load_rag_system()
│  ├─ render_message()
│  └─ handle_user_message()
└─ main()
   ├─ init_session_state()
   ├─ render_header()
   ├─ render_sidebar()
   └─ render_chat()
```

---

## State Management

```
Session State Variables (NEW):
    ↓
'active_model': str | None
├─ Set when user loads model
├─ Displayed in "Currently Active:"
└─ Used for LLM integration
    ↓
'llm_enabled': bool
├─ Flag to enable LLM responses
├─ Set when model loaded + connected
└─ Checked before calling LLM
```

---

## Error Handling Flow

```
Try to get models:
    ↓
    ├─ Directory exists? ✓
    │  └─ Continue
    │
    ├─ Can read files? ✓
    │  └─ Continue
    │
    └─ Error? (permission, etc.)
       └─ Log warning, skip dir
            ↓
            Continue to next directory
            ↓
            Return models found so far
```

---

## Integration Points

```
Current Integration:
├─ Streamlit UI ←→ HTTP Orchestrator
│  ├─ POST /swap (load model)
│  └─ GET /model/status (check active)
│
├─ Model Filesystem ←→ Backend
│  ├─ Read C:/AI/Models/
│  ├─ Load GGUF file
│  └─ Launch llama-server
│
└─ RAG System ←→ LLM (Future)
   ├─ Retrieve documents
   ├─ Send to LLM (future)
   └─ Generate response
```

---

## Performance Characteristics

```
Model Scanning:
├─ Frequency: Every UI render (cache-less)
├─ Time: ~50-100ms for 5 models
└─ I/O: Filesystem glob + stat()

Model Loading:
├─ Time: 5-15 seconds (disk I/O)
├─ RAM: 3-6 GB (depends on model)
└─ Network: 1 HTTP request + polling

Model Switching:
├─ Kill old: 1-2 seconds
├─ Start new: 3-5 seconds
├─ Total: ~8-10 seconds
└─ Blocking: Yes (orchestrator busy)
```

---

## Future Enhancement Points

```
Possible additions:
├─ Model Download Button
│  └─ Download from HuggingFace in-app
├─ Model Comparison View
│  └─ Compare specs side-by-side
├─ Benchmark Results
│  └─ Show performance metrics
├─ Model Rating System
│  └─ Community ratings/reviews
├─ Quick Swap Dropdown
│  └─ Faster switching UI
├─ Model Cache
│  └─ Cache list for fast loads
├─ LLM Response Generation
│  └─ Integrate with RAG
└─ Expert Swarm Mode
   └─ Multiple models routing
```

---

## References

- [llama.cpp GitHub](https://github.com/ggerganov/llama.cpp)
- [GGUF Format Spec](https://github.com/ggerganov/ggml/blob/master/docs/gguf.md)
- [HuggingFace Models](https://huggingface.co/models?library=gguf)
- [Streamlit API](https://docs.streamlit.io/)
