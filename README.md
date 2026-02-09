# ZEN_AI_RAG — Zena AI with RAG & Local LLM

Full-stack AI assistant with **Retrieval-Augmented Generation**, local LLM inference via **llama-cpp**, and a Streamlit web UI — designed to run entirely offline.

## Features

- **Local LLM inference** — llama-cpp server with auto-model discovery and GPU/CPU selection
- **RAG pipeline** — BGE embeddings, semantic chunking, Qdrant vector search, layout-aware PDF parsing
- **Reranker** — cross-encoder reranking for improved retrieval precision
- **Multi-format ingestion** — PDF, DOCX, XLSX, web pages, code files (30+ types)
- **Streamlit UI** — dark mode, RAG badges, chat interface, settings sidebar
- **Pre-flight validation** — auto-checks binary, models, and dependencies on startup
- **Multi-model support** — auto-discovers GGUF models, switch models live
- **Zena AI personality** — customizable AI assistant with enhanced capabilities

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Launch (auto-validates and starts llama-cpp server + Streamlit UI)
python start_llm.py
```

See [QUICK_START.md](QUICK_START.md) for detailed setup instructions.

## Architecture

```
├── start_llm.py          # Entry point — pre-flight + server + UI
├── app.py                # Streamlit chat application
├── rag_engine.py         # RAG pipeline (indexing, retrieval, reranking)
├── content_extractor.py  # Multi-format document parser
├── llm_backend.py        # LLM provider abstraction
├── config.py             # Configuration management
└── pip_spy_max.py        # Dependency analyzer
```

## Dependencies

- `llama-cpp-python` — local GGUF model inference
- `streamlit` — web UI
- `sentence-transformers` — BGE embeddings
- `qdrant-client` — vector database
- `beautifulsoup4`, `PyMuPDF` — document parsing
- `cross-encoder` — reranking

## License

MIT
