"""
Tests for Core/reranker_advanced.py — AdvancedReranker 5-factor scoring

Tests cover:
  - Factor calculations (semantic, position, density, answer-type, source)
  - rerank() public API
  - Weight override
  - Edge cases (empty chunks, no model)
"""

import pytest
from unittest.mock import MagicMock
import numpy as np


# ─── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def mock_model():
    """Mock SentenceTransformer returning predictable embeddings."""
    model = MagicMock()

    def encode_fn(texts, **kwargs):
        results = []
        for t in texts:
            vec = np.zeros(384)
            idx = hash(t) % 384
            vec[idx] = 1.0
            results.append(vec / (np.linalg.norm(vec) + 1e-10))
        return np.array(results)

    model.encode = encode_fn
    return model


@pytest.fixture
def reranker(mock_model):
    """Create AdvancedReranker with mocked model, no CrossEncoder."""
    from Core.reranker_advanced import AdvancedReranker

    # Bypass __init__ to avoid downloading real CrossEncoder model
    r = AdvancedReranker.__new__(AdvancedReranker)
    r.model = mock_model
    r.cross_encoder = None
    return r


@pytest.fixture
def sample_chunks():
    """Small set of realistic chunks."""
    return [
        {
            "text": "Python was created by Guido van Rossum and first released in 1991. "
            "It emphasizes code readability and supports multiple programming paradigms.",
            "url": "https://en.wikipedia.org/wiki/Python",
            "source": "wikipedia",
            "title": "Python (programming language)",
        },
        {
            "text": "Subscribe to our tech newsletter for weekly Python tips and tricks!",
            "url": "https://example-blog.com/newsletter",
            "source": "blog",
            "title": "Newsletter",
        },
        {
            "text": "Step 1: Install Python from python.org. Step 2: Verify with python --version. "
            "Step 3: Set up a virtual environment.",
            "url": "https://docs.python.org/install",
            "source": "official",
            "title": "Installation Guide",
        },
        {
            "text": "A study published in IEEE found that Python adoption grew 25% in 2025, "
            "surpassing JavaScript in data science applications.",
            "url": "https://research.ieee.org/paper123",
            "source": "academic",
            "title": "Language Adoption Trends",
        },
    ]


# ─── Import ────────────────────────────────────────────────────────────────


def test_import():
    from Core.reranker_advanced import AdvancedReranker

    assert AdvancedReranker is not None


# ─── Basic rerank() ────────────────────────────────────────────────────────


def test_rerank_returns_tuple(reranker, sample_chunks):
    """rerank() should return (chunks, scores) tuple."""
    ranked, scores = reranker.rerank("What is Python?", sample_chunks, top_k=3)
    assert isinstance(ranked, list)
    assert isinstance(scores, list)
    assert len(ranked) == 3
    assert len(scores) == 3


def test_rerank_scores_sorted(reranker, sample_chunks):
    """Scores should be in descending order."""
    _, scores = reranker.rerank("How to install Python?", sample_chunks, top_k=4)
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1], "Scores not sorted descending"


def test_rerank_top_k_limit(reranker, sample_chunks):
    """Should respect top_k parameter."""
    ranked, scores = reranker.rerank("Python history", sample_chunks, top_k=2)
    assert len(ranked) == 2
    assert len(scores) == 2


def test_rerank_top_k_larger_than_chunks(reranker, sample_chunks):
    """top_k > len(chunks) should return all chunks."""
    ranked, scores = reranker.rerank("Python", sample_chunks, top_k=100)
    assert len(ranked) == len(sample_chunks)


# ─── Weight Override ──────────────────────────────────────────────────────


def test_rerank_custom_weights(reranker, sample_chunks):
    """Custom weights should still produce valid results."""
    weights = {
        "semantic": 0.80,
        "position": 0.0,
        "density": 0.0,
        "answer_type": 0.10,
        "source": 0.10,
    }
    ranked, scores = reranker.rerank("What is Python?", sample_chunks, weights=weights)
    assert len(ranked) > 0
    assert all(isinstance(s, (int, float)) for s in scores)


# ─── Source Credibility ──────────────────────────────────────────────────


def test_source_credibility_ordering(reranker):
    """Official sources should rank higher than blogs."""
    from Core.reranker_advanced import AdvancedReranker

    assert AdvancedReranker.SOURCE_CREDIBILITY["official"] > AdvancedReranker.SOURCE_CREDIBILITY["blog"]
    assert AdvancedReranker.SOURCE_CREDIBILITY["academic"] > AdvancedReranker.SOURCE_CREDIBILITY["forum"]
    assert AdvancedReranker.SOURCE_CREDIBILITY["gov"] > AdvancedReranker.SOURCE_CREDIBILITY["reddit"]


# ─── Query Type Detection ─────────────────────────────────────────────────


def test_query_type_patterns_exist(reranker):
    """All expected query types should be defined."""
    expected = {
        "definition",
        "procedure",
        "comparison",
        "location",
        "temporal",
        "quantitative",
        "causal",
    }
    from Core.reranker_advanced import AdvancedReranker

    assert expected.issubset(set(AdvancedReranker.QUERY_TYPE_PATTERNS.keys()))


def test_definition_query_detected(reranker):
    """'What is X' should match definition pattern."""
    from Core.reranker_advanced import AdvancedReranker

    pattern = AdvancedReranker.QUERY_TYPE_PATTERNS["definition"]
    assert pattern.search("What is Python?")


def test_procedure_query_detected(reranker):
    """'How to ...' should match procedure pattern."""
    from Core.reranker_advanced import AdvancedReranker

    pattern = AdvancedReranker.QUERY_TYPE_PATTERNS["procedure"]
    assert pattern.search("How to install Python?")


# ─── Edge Cases ────────────────────────────────────────────────────────────


def test_empty_chunks(reranker):
    """Empty chunk list should return empty results."""
    ranked, scores = reranker.rerank("anything", [], top_k=5)
    assert ranked == []
    assert scores == []


def test_single_chunk(reranker):
    """Single chunk should be returned as-is."""
    chunk = [{"text": "The only chunk available about tropical forests."}]
    ranked, scores = reranker.rerank("tropical forests", chunk, top_k=5)
    assert len(ranked) == 1


def test_chunk_missing_optional_fields(reranker):
    """Chunks without url/source/title should still work."""
    chunks = [
        {"text": "First chunk with content about algorithms."},
        {"text": "Second chunk about data structures in computer science."},
    ]
    ranked, scores = reranker.rerank("algorithms", chunks, top_k=2)
    assert len(ranked) == 2
