# Medical Scenarios — RAG Use Case

This folder implements a **focused use case**: generate medical scenario documents, index them into the vector database, verify indexing, and run predefined prompts (e.g. via a local Llama server) to produce a simple report.

## Workflow

1. **Generate** — `generate_scenarios.py` creates medical scenario documents (synthetic guidelines, Q&A, procedures).
2. **Index & verify** — `index_and_verify.py` loads scenarios into the RAG vector DB, checks success, and prints one vector DB entry as a structure example.
3. **Query & report** — `run_queries_report.py` runs predefined real-case prompts against the indexed data (and optional Llama server), and writes a simple text report.

## Prerequisites

- Project dependencies installed (sentence-transformers, qdrant-client, etc.).
- For **query report with LLM**: Llama server (or Ollama) running, e.g. `python scripts/start_llama_server.py` or Ollama on port 11434.

## Usage

From project root:

```bash
# 1. Generate scenario documents (writes to medical_scenarios/data/)
python -m medical_scenarios.generate_scenarios

# 2. Index into vector DB and verify (uses rag_storage in project root)
python -m medical_scenarios.index_and_verify

# 3. Run predefined queries and generate report
python -m medical_scenarios.run_queries_report
```

Report is written to `medical_scenarios/report.txt`.

### Optional: use Llama server or Ollama for answers

- **Llama server** (OpenAI-compatible, e.g. `python scripts/start_llama_server.py`):
  - `MEDICAL_LLM_ENDPOINT=http://localhost:8001 MEDICAL_LLM_PROVIDER="Local (llama-cpp)" MEDICAL_LLM_MODEL=llama3.2 python -m medical_scenarios.run_queries_report`
- **Ollama**:
  - `MEDICAL_LLM_ENDPOINT=http://localhost:11434 MEDICAL_LLM_PROVIDER=Ollama MEDICAL_LLM_MODEL=llama3.2 python -m medical_scenarios.run_queries_report`
- **RAG-only** (no LLM call; report shows retrieved chunks only):
  - `MEDICAL_USE_LLM=0 python -m medical_scenarios.run_queries_report`
