
# ZenAI Test Suite

## Standard Tests
Run the core unit tests to verify logic:
```powershell
python -m unittest tests/test_rag_precision.py
```

## Performance Benchmarks
Run the latency benchmark to measure RAG pipeline speed:
```powershell
python tests/benchmark_pipeline.py
```

## Voice Lab Integration
To test the emotional voice engine:
```powershell
python experimental_voice_lab/test_voice_stack.py
```
