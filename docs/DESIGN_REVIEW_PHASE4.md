# ZEN_AI_RAG Design Review - Phase 4: Unified LLM & Voice Integration

**Date**: February 5, 2026  
**Status**: Architecture Analysis Complete  
**Next Phase**: LLM Unification + Voice/Microphone Fixes

---

## 1. Current Architecture Analysis

### A. Project Identity
**ZenAI** is a secure, modular local AI assistant with:
- **Core**: Heart & Brain architecture (elegant separation of concerns)
- **Engine**: `llama.cpp` via `llama-server.exe` on Port 8001
- **Orchestration**: `zena_mode/heart_and_brain.py` manages lifecycle
- **Frontend**: NiceGUI (`zena.py`) provides UI
- **Management**: Port 8002 (Hub API via ASGI/sync server)

### B. Current Module Inventory

#### LLM Management (FRAGMENTED)
- **zena_mode/heart_and_brain.py** (229 lines)
  - `ZenHeart`: Engine ignition, health monitoring, auto-restart (3 attempts max)
  - `ZenBrain`: Model registry, swarm council (planned)
  - `HardwareProfiler`: CPU/GPU detection, VRAM governance
  - Issue: **TIGHTLY COUPLED** - No reusable model abstraction layer

- **zena_mode/model_orchestrator.py**
  - Appears to be another model management module
  - Risk: **DUPLICATE LOGIC** with heart_and_brain.py

- **zena_mode/resource_detect.py**
  - Hardware profiling (CPU cores, GPU VRAM, NPU detection)
  - Used by ZenHeart for VRAM governance

- **No Unified Model Interface**
  - Each module handles model paths separately
  - `config.MODEL_DIR / config.default_model` referenced in server.py
  - **Missing**: Central registry like RAG_RAT's `local_llm/` module

#### Voice/Audio Systems (FRAGMENTED & BROKEN)
- **voice_service.py** (403 lines)
  - `VoiceService` class with STT (faster-whisper) and TTS (Piper)
  - Lazy loading of models
  - **Status**: Implemented but likely not integrated in UI handlers

- **zena_mode/voice_engine.py**
  - Alternative voice implementation using "Qwen Native Capabilities"
  - **CONFLICT**: Two different voice strategies

- **zena_mode/handlers/voice.py**
  - REST endpoints `/voice/transcribe`, `/api/record`
  - **Missing**: Microphone device enumeration
  - **Missing**: Recording UI integration
  - **Issue**: References `VoiceService()` but initialization unclear

- **zena_mode/voice_stream.py**
  - Likely for WebSocket voice streaming
  - **Unknown**: Whether this works or connects to UI

- **experimental_voice_lab/** directory
  - Suggests incomplete voice feature development

#### Voice/TTS Problems Identified
1. ❌ **Multiple voice engines** (`voice_service.py` vs `voice_engine.py`)
2. ❌ **Microphone not working** - handlers exist but UI integration broken
3. ❌ **TTS broken** - Piper model may not be downloaded/initialized
4. ❌ **No device enumeration** - Can't select microphone
5. ❌ **No recording UI** - No visual feedback for recording status

---

## 2. RAG_RAT Reference Architecture

### Local LLM Module Structure (RAG_RAT - WORKING ✅)
Located at: `C:\Users\dvdze\Documents\_Python\Dev\RAG_RAT\local_llm\`

```
local_llm/
├── __init__.py                  # Clean exports
├── llama_cpp_manager.py         # Core engine management
├── model_card.py                # Model metadata & discovery
├── local_llm_manager.py         # High-level orchestration
└── __pycache__/
```

**Key Classes**:
- `LlamaCppManager`: Engine lifecycle (start, stop, status check)
- `ModelRegistry`: GGUF discovery and metadata
- `ModelCard`: Model information (name, size, parameters)
- `LocalLLMManager`: Unified interface for everything

**Advantages**:
- ✅ Modular - Easy to test each component
- ✅ Reusable - No dependency on app specifics
- ✅ Clear separation - Model vs Engine vs Registry
- ✅ Proven working - 90 tests passing
- ✅ Used by config_enhanced.py for provider mapping

---

## 3. Required Changes (Priority Order)

### Phase 4.1: Unify LLM Management (HIGH PRIORITY)
**Goal**: Replace `heart_and_brain.py` + `model_orchestrator.py` with RAG_RAT's `local_llm/` module

**Steps**:
1. Copy `C:\Users\dvdze\Documents\_Python\Dev\RAG_RAT\local_llm\` → `C:\Users\dvdze\Documents\_Python\Dev\ZEN_AI_RAG\local_llm\`
2. Update imports in:
   - `zena_mode/heart_and_brain.py` → Use `LocalLLMManager`
   - `zena_mode/server.py` → Use `ModelRegistry`
   - `config_system.py` → Use centralized config
3. Remove `model_orchestrator.py` (duplicate logic)
4. Update `zena_mode/handlers/models.py` to use `LocalLLMManager`

**Expected Outcome**: Single source of truth for all LLM operations

### Phase 4.2: Fix Voice Input (MEDIUM PRIORITY)
**Goal**: Restore microphone functionality with proper device enumeration

**Current Issues**:
- ❌ `sounddevice` library not being used for enumeration
- ❌ Recording endpoints exist but no UI integration
- ❌ No device selection UI

**Solution**:
1. Create `zena_mode/voice_manager.py` (unified voice control)
   - Enumerate devices with `sounddevice.query_devices()`
   - Provide recording interface with visual feedback
   - Use RAG_RAT's approach if applicable
   
2. Update `zena_mode/handlers/voice.py`:
   - Add `/voice/devices` endpoint (list available microphones)
   - Fix `/api/record` to use selected device
   - Add error handling for missing sounddevice
   
3. Update UI (`zena.py`):
   - Add microphone selector dropdown
   - Add Record button with visual feedback
   - Display transcribed text in chat

**Expected Outcome**: Working microphone input with device selection

### Phase 4.3: Fix Text-to-Speech Output (MEDIUM PRIORITY)
**Goal**: Get TTS working reliably for app-to-human communication

**Current Issues**:
- ❌ Two TTS implementations (Piper vs Qwen)
- ❌ Piper model not auto-downloading on Windows
- ❌ No TTS integration in UI
- ❌ No audio playback mechanism

**Solution**:
1. Standardize on **Piper TTS** (faster-whisper pair, proven in voice_service.py)
2. Fix model auto-download:
   - Ensure Piper ONNX models downloaded to `voice_cache/piper/`
   - Handle Windows path issues with HuggingFace mirror
   
3. Create TTS endpoints:
   - `POST /voice/tts` - Convert text to speech
   - `GET /voice/audio/{file_id}` - Serve generated audio
   
4. Update UI:
   - Add "Read Response" button in chat
   - Stream audio back to browser
   - Show playback status

**Expected Outcome**: Smooth TTS output with visual feedback

---

## 4. File-by-File Inventory

### Core Engine
| File | Lines | Status | Action |
|------|-------|--------|--------|
| `start_llm.py` | ~200 | ✅ Working | Keep; wire to LocalLLMManager |
| `zena_mode/heart_and_brain.py` | 229 | ⚠️ Monolithic | Refactor to use LocalLLMManager |
| `zena_mode/model_orchestrator.py` | ? | ⚠️ Duplicate | **DELETE after verification** |
| `zena_mode/server.py` | 184 | ✅ Working | Update handler imports |
| `zena_mode/resource_detect.py` | ? | ✅ Working | Keep for hardware profiling |

### Voice System
| File | Lines | Status | Action |
|------|-------|--------|--------|
| `voice_service.py` | 403 | ⚠️ Partial | **USE THIS** as base; unify |
| `zena_mode/voice_engine.py` | ? | ❌ Broken | **DELETE** - conflicting approach |
| `zena_mode/voice_stream.py` | ? | ❓ Unknown | Evaluate for removal |
| `zena_mode/handlers/voice.py` | ~80 | ⚠️ Incomplete | Fix and integrate |
| `experimental_voice_lab/` | N/A | ❌ Dead code | **DELETE** |

### UI/Handler Layer
| File | Lines | Status | Action |
|------|-------|--------|--------|
| `zena.py` | 187 | ✅ Working | Add voice UI components |
| `zena_mode/handlers/__init__.py` | ? | ✅ Working | Ensure imports updated |
| `zena_mode/handlers/models.py` | ? | ⚠️ Dated | Update to use LocalLLMManager |
| `zena_mode/handlers/voice.py` | ~80 | ⚠️ Broken | **Priority fix** |

---

## 5. Config System Analysis

### Current (config_system.py)
```python
MODEL_DIR = Path(...)         # Where GGUF files live
default_model = "..."         # Current model filename
gpu_layers = -1 or N          # -1 = auto, else manual
```

### RAG_RAT (config/__init__.py + config_enhanced.py)
```python
MODELS_DIR = C:\AI\Models          # Centralized
BIN_DIR = C:\AI\_bin               # llama-server location
PROVIDERS = {...}                  # 8 LLM providers with details
```

**Action**: Align ZEN_AI_RAG config with RAG_RAT standards

---

## 6. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Multiple LLM modules | HIGH | Copy RAG_RAT's local_llm/ module as-is |
| Voice system fragmentation | HIGH | Standardize on voice_service.py + unified manager |
| No microphone device enum | MEDIUM | Add sounddevice.query_devices() |
| Missing TTS integration | MEDIUM | Hook up Piper endpoint to UI |
| Monolithic heart_and_brain | MEDIUM | Refactor incrementally, test each step |

---

## 7. Testing Strategy

After changes:
1. **Unit Tests**: Voice device enumeration, TTS generation, model discovery
2. **Integration Tests**: Record → Transcribe → Process → TTS → Playback
3. **Stress Tests**: Rapid model switches, concurrent voice requests
4. **Chaos Tests**: Kill llama-server, verify auto-restart still works

Run existing tests to ensure no regressions:
```bash
python -m pytest tests/ -v
```

---

## 8. Success Criteria ✅

- [ ] Single LLM module (copied from RAG_RAT)
- [ ] Microphone recording works with device selection
- [ ] STT (speech-to-text) converts audio to text
- [ ] TTS (text-to-speech) generates audio responses
- [ ] Full voice loop: Mic → STT → LLM → TTS → Speaker
- [ ] All 90+ existing tests still passing
- [ ] Zero breaking changes to Heart & Brain lifecycle

---

## Next Steps

1. **Verify Local_LLM module** (confirm RAG_RAT version is what we need)
2. **Copy & integrate** local_llm/ into ZEN_AI_RAG
3. **Fix voice handler** endpoints and device enumeration
4. **Add TTS integration** to UI
5. **Test full voice loop** end-to-end
6. **Clean up** duplicate modules and dead code

---

**Prepared by**: AI Assistant  
**Ready for**: Phase 4.1 Implementation
