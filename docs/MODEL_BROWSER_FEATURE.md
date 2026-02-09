# 🤖 Model Browser Feature - Streamlit RAG Chat v2

## What's New

Added comprehensive **Model Browser** to `streamlit_rag_chat_v2.py` that allows users to:

1. ✅ **Browse local models** from `C:/AI/Models`
2. ✅ **View model metadata** (type, specialty, quantization, size)
3. ✅ **Load models** directly from the sidebar
4. ✅ **See active model** status in real-time
5. ✅ **Search multiple directories** (C:/AI/Models, ~/AI/Models, config MODEL_DIR)

---

## Features Added

### 1. **Model Discovery Function** (`get_local_models()`)
```python
# Automatically scans:
- C:/AI/Models
- ~/AI/Models  
- config.MODEL_DIR (if set)

# Returns list of models with:
- File name
- Full path
- Size (MB/GB)
- Formatted size string
```

### 2. **Model Info Parser** (`parse_model_info()`)
Extracts metadata from filename:
- **Type**: Coding, Math, Llama, Qwen, General
- **Specialty**: What task it excels at
- **Quantization**: Q3/Q4/Q5/Q8 (quality level)
- **Size**: 3B/7B/13B (parameter count)
- **Icon**: 💻 🔢 🦙 🧠 etc.

### 3. **Model Browser UI** (`render_model_browser()`)
Displays each model in an expandable card:
```
🧠 qwen2.5-coder-7b-instruct-q4_k_m.gguf
├─ Type: Coding ✓
├─ Best for: Code generation & debugging
├─ Quantization: Q4 (⭐ Balanced)
├─ Size: Medium (7B) - ⚡⚡ Balanced
├─ File Size: 4.4 GB
└─ [📦 Load Model] button
```

### 4. **Load Model Integration**
- Click "Load Model" button
- Sends POST to `http://localhost:8002/swap`
- Shows loading spinner
- Displays success/error message
- Updates active model display

### 5. **Active Model Status**
- Shows currently loaded model
- Fetches from `http://localhost:8002/model/status`
- Updates automatically

---

## UI Layout

```
┌─────────────────────────────────────┐
│           SIDEBAR                   │
├─────────────────────────────────────┤
│  🤖 Model Manager                   │
│  ├─ 🧠 qwen2.5-coder-7b [+] expand │
│  │  Type: Coding                    │
│  │  Best for: Code gen & debug      │
│  │  Quant: Q4 ⭐ Balanced           │
│  │  Size: 7B ⚡⚡ Balanced          │
│  │  File: 4.4 GB                   │
│  │  [📦 Load Model] btn             │
│  └─ 🦙 Llama-3.2-3B [+] expand     │
│     Type: General                   │
│     ...                             │
│  ────────────────────────────────   │
│  ✅ Currently Active: qwen2.5...    │
│                                     │
│  ─── separator ───                  │
│  📚 Add Knowledge                    │
│  ├─ [🌐 Web] [📄 Files]            │
│  │  (URL input, file upload)        │
│  ...                                │
└─────────────────────────────────────┘
```

---

## How It Works

### Backend Integration

When user clicks "Load Model":

1. **Validation**: Check rate limiter
2. **HTTP Request**: POST to orchestrator
   ```
   POST http://localhost:8002/swap
   {"model": "qwen2.5-coder-7b-instruct-q4_k_m.gguf"}
   ```

3. **Orchestrator Response**:
   ```json
   {
     "status": "swap_scheduled",
     "model": "qwen2.5-coder-7b-instruct-q4_k_m.gguf"
   }
   ```

4. **Status Check**: Fetch from `/model/status`
   ```json
   {
     "model": "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
     "loaded": true,
     "engine_port": 8001
   }
   ```

### Directory Scanning

```python
# Checks in order:
1. C:/AI/Models (primary location)
2. ~/AI/Models (home directory)
3. config.MODEL_DIR (custom config)

# Deduplicates results
# Filters only *.gguf files
# Sorts alphabetically
```

---

## Error Handling

- **No models found**: Friendly message with instructions
- **Load fails**: Shows HTTP error response
- **Orchestrator unavailable**: Graceful degradation
- **Invalid paths**: Skipped silently with warning log

---

## Performance

- **Caching**: Model list NOT cached (scans fresh each load)
- **Async**: Non-blocking UI during model load
- **Timeouts**: 30 second max for model swap
- **Rate Limiting**: Same as other endpoints (20 req/min)

---

## Example Models

### Recommended
```
💻 qwen2.5-coder-7b-instruct-q4_k_m.gguf
   - Type: Coding
   - Size: 7B (4.4 GB)
   - Quant: Q4 ⭐ Balanced
   - Speed: ⚡⚡
   - Quality: ⭐⭐⭐⭐

🦙 Llama-3.2-3B-Instruct-Q4_K_M.gguf
   - Type: General
   - Size: 3B (2.0 GB)
   - Quant: Q4 ⭐ Balanced
   - Speed: ⚡⚡⚡⚡
   - Quality: ⭐⭐⭐
```

---

## Testing

### Manual Test Steps

1. **Place models** in `C:/AI/Models/` (or ~/AI/Models/)
   ```bash
   cd C:/AI/Models
   # Put qwen2.5-coder-7b-instruct-q4_k_m.gguf here
   ```

2. **Start main orchestrator**:
   ```bash
   python start_llm.py
   ```

3. **Start Streamlit app**:
   ```bash
   streamlit run streamlit_rag_chat_v2.py
   ```

4. **Test Model Browser**:
   - ✅ Models appear in sidebar
   - ✅ Can expand each model
   - ✅ Click "Load Model" button
   - ✅ See success message
   - ✅ Active model updates

### Verification Checklist
```
☐ Models list populates from C:/AI/Models
☐ Model icons correct (💻 for Coder, 🦙 for Llama, etc.)
☐ File sizes display correctly (MB/GB format)
☐ Quantization detected (Q3/Q4/Q5/Q8)
☐ Model size category correct (3B/7B/13B)
☐ Load button works without crashes
☐ Error messages are helpful
☐ Active model status shows correctly
```

---

## Code Structure

### New Functions
```python
get_local_models() -> List[Dict]
  ├─ Scan directories
  ├─ Filter .gguf files
  ├─ Get file sizes
  └─ Return sorted list

parse_model_info(name: str) -> Dict
  ├─ Detect type (Coder, Math, Llama, etc.)
  ├─ Extract quantization (Q3/Q4/Q5)
  ├─ Detect size (3B/7B/13B)
  └─ Return metadata dict

render_model_browser()
  ├─ Get local models
  ├─ Show count
  ├─ Expand/collapse each
  ├─ Display metadata
  ├─ Handle load click
  └─ Show active model
```

### Modified Functions
```python
render_sidebar()
  ├─ Add "Model Manager" section (NEW)
  ├─ Call render_model_browser()
  ├─ Keep existing sections
  └─ Reorganize layout
```

### Backend Integration
```
HTTP Endpoints Called:
├─ POST /swap (load model)
├─ GET /model/status (check active)
└─ Timeout: 30 seconds max
```

---

## Next Steps

### Suggested Enhancements
1. **Model Download Button** - Download from HuggingFace
2. **Model Comparison** - Compare specs side-by-side
3. **Benchmark Results** - Show performance metrics
4. **Model Rating** - Community ratings/reviews
5. **Quick Swap** - Dropdown selector for faster switching
6. **Model Cache** - Cache list for faster load times

### Integration with LLM
Once models are loaded:
- [ ] Add LLM response generation to RAG chat
- [ ] Stream responses to UI
- [ ] Show model used for response
- [ ] Display token count/generation speed

---

## Files Modified

- **streamlit_rag_chat_v2.py** (+120 lines)
  - Added `load_backend()` function
  - Added `get_local_models()` function  
  - Added `parse_model_info()` function
  - Added `render_model_browser()` function
  - Updated `render_sidebar()` to include model browser

---

## References

- [llama.cpp Model Format (GGUF)](https://github.com/ggerganov/llama.cpp)
- [ZenAI Orchestrator](zena_mode/server.py)
- [Model Manager](model_manager.py)
- [Async Backend](async_backend.py)
- [LLM Integration Guide](LLM_INTEGRATION_GUIDE.md)

---

## Troubleshooting

### Models not appearing?
```bash
# Check directory exists
ls -la C:/AI/Models/

# Check file extension
dir C:/AI/Models/*.gguf

# Check permissions
# Ensure read access to directory
```

### Load fails silently?
```bash
# Check orchestrator running
netstat -an | grep 8002

# Check port 8002 accessible
curl http://localhost:8002/model/status

# Check logs
# Orchestrator should show swap request
```

### Wrong model metadata?
- Metadata parsed from filename only
- Rename files to standard format:
  - `{model}-{size}b-{instruction}-{quant}.gguf`
  - Example: `qwen2.5-coder-7b-instruct-q4_k_m.gguf`

---

## License
Same as ZenAI project (Apache 2.0)
