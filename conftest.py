import sys
import types
from pathlib import Path

# Add project root and src to sys.path for all tests
root = Path(__file__).parent
src = root / "src"

for path in [root, src]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# ── Stub out rag_core if not installed so zena_mode can be imported ──────────
if "rag_core" not in sys.modules:
    _rc = types.ModuleType("rag_core")
    _rc.__path__ = []  # make it a package
    _rc.__package__ = "rag_core"
    sys.modules["rag_core"] = _rc
    for _sub in (
        "bm25_index", "cache", "chunker", "dedup", "embeddings",
        "fusion", "models", "pipeline", "reranker", "retriever",
        "text_chunker",
    ):
        _m = types.ModuleType(f"rag_core.{_sub}")
        _m.__dict__.update({
            "BM25Index": type("BM25Index", (), {}),
            "SemanticCache": type("SemanticCache", (), {"__init__": lambda self, **kw: None}),
            "TextChunker": type("TextChunker", (), {}),
            "ChunkerConfig": type("ChunkerConfig", (), {}),
            "DeduplicationManager": type("DeduplicationManager", (), {}),
            "SmartDeduplicator": type("SmartDeduplicator", (), {}),
            "EmbeddingManager": type("EmbeddingManager", (), {}),
            "RerankerManager": type("RerankerManager", (), {}),
            "reciprocal_rank_fusion": lambda *a, **kw: [],
        })
        sys.modules[f"rag_core.{_sub}"] = _m
        setattr(_rc, _sub, _m)
