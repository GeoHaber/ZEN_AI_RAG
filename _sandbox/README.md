# ZenAI - AI Assistant with RAG and Multilingual Support

## Overview
ZenAI is a clean, focused AI assistant inspired by hospital chatbot UX patterns, featuring:
- ZenAI-style UI (guided task chips, visual persona, floating popup mode)
- Multilingual support (auto-detect + translate)
- Local RAG from website scanning
- Voice interaction (Whisper STT + piper TTS)

## Quick Start

### Prerequisites
- Python 3.14
- llama.cpp binaries in `_bin/`
- AI model in `C:\AI\Models\`

### Installation
```bash
cd C:\Users\dvdze\Documents\_Python\Dev\ZenAI
pip install -r requirements.txt  # (create this from Local_LLM if needed)
```

### Run
```bash
python start_llm.py  # Starts backend + UI on port 8080
```

## Project Structure
```
ZenAI/
├── zena.py              # Main NiceGUI application
├── start_llm.py         # Backend orchestrator
├── utils.py             # Shared utilities
├── config.json          # Configuration
├── _bin/                # llama.cpp binaries
└── tests/               # Active tests (4 files)
```

## Features Implemented
- ✅ Chat with streaming responses
- ✅ File upload with smart formatting
- ✅ Model selection (Hub API)
- ✅ Model download
- ✅ Voice input (mic button)
- ✅ Guided task chips
- ✅ AI avatar (robot icon)
- ✅ RAG popup (dialog ready)
- ✅ TTS output button
- ✅ llama.cpp version check

## Features Planned (ZenAI Mode)
- [ ] Floating popup UI (bottom-right)
- [ ] Pulsing "Assistance" trigger
- [ ] Multilingual support (auto-detect)
- [ ] Website RAG pipeline
- [ ] Voice multilingual (Whisper + piper)

## Testing
```bash
python -m pytest tests/  # Run all 4 tests
```

## Configuration
Edit `config.json` to enable ZenAI mode:
```json
{
  "zena_mode": {
    "enabled": true,
    "language": "auto",
    "rag_source": "website",
    "website_url": "https://example.com"
  }
}
```

## Development
This repository is a clean migration from `Local_LLM`, excluding:
- Legacy Flet code
- Archived tests
- Development artifacts

**Result**: 85% file reduction, focused codebase

## Next Steps
1. Add ZenAI to VSCode workspace
2. Implement floating popup UI
3. Build RAG pipeline
4. Add multilingual support

## License
[Your License Here]
