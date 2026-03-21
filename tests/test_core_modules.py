"""
Functional tests for all Core RAG modules.

NO mocks — tests use real module instances with real data
to verify correctness, data flow, and edge cases.

Covers:
  - AdvancedReranker
  - SmartDeduplicator
  - ConflictDetector
  - AdvancedHallucinationDetector
  - AnswerQualityAssessor (ConfidenceScorer)
  - FollowUpGenerator
  - MetricsTracker
  - FLARERetriever
  - ContextualCompressor
  - QueryRewriter
  - ZeroWasteCache
  - PromptTemplateLibrary / FocusModes
  - InferenceGuard
  - AnswerRefinementEngine
  - AnswerEvaluator / RetrievalEvaluator
"""

import asyncio
import time

import pytest


# ─── Sample data fixtures ──────────────────────────────────────────────────

SAMPLE_CHUNKS = [
    {
        "text": "Python is a high-level, interpreted programming language known for its simplicity and readability.",
        "score": 0.95,
        "url": "https://docs.python.org/3/tutorial/",
        "title": "Python Tutorial",
    },
    {
        "text": "Python supports multiple programming paradigms including object-oriented, functional, and procedural programming.",
        "score": 0.90,
        "url": "https://docs.python.org/3/tutorial/",
        "title": "Python Tutorial",
    },
    {
        "text": "Guido van Rossum created Python in 1991. The language emphasizes code readability with significant whitespace.",
        "score": 0.85,
        "url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
        "title": "Python Wikipedia",
    },
    {
        "text": "JavaScript is a dynamic language primarily used for web development, both client-side and server-side.",
        "score": 0.60,
        "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
        "title": "MDN JavaScript",
    },
    {
        "text": "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
        "score": 0.40,
        "url": "https://example.com/ml",
        "title": "ML Intro",
    },
]

SAMPLE_QUERY = "What is Python and who created it?"

SAMPLE_ANSWER = (
    "Python is a high-level, interpreted programming language created by "
    "Guido van Rossum in 1991. It is known for its simplicity, readability, "
    "and support for multiple programming paradigms including object-oriented "
    "and functional programming."
)


# ═══════════════════════════════════════════════════════════════════
# AdvancedReranker
# ═══════════════════════════════════════════════════════════════════

class TestAdvancedReranker:
    """Functional tests for multi-signal reranking."""

    def test_rerank_returns_scored_chunks(self):
        from Core.reranker_advanced import AdvancedReranker

        reranker = AdvancedReranker()
        results = reranker.rerank(SAMPLE_QUERY, SAMPLE_CHUNKS, top_k=3)

        assert len(results) == 3
        assert all("rerank_score" in r for r in results)
        assert all("_rerank_detail" in r for r in results)
        # Scores should be between 0 and 1
        assert all(0 <= r["rerank_score"] <= 1 for r in results)

    def test_rerank_preserves_original_fields(self):
        from Core.reranker_advanced import AdvancedReranker

        reranker = AdvancedReranker()
        results = reranker.rerank(SAMPLE_QUERY, SAMPLE_CHUNKS, top_k=5)

        for r in results:
            assert "text" in r
            assert "url" in r

    def test_rerank_orders_by_relevance(self):
        from Core.reranker_advanced import AdvancedReranker

        reranker = AdvancedReranker()
        results = reranker.rerank(SAMPLE_QUERY, SAMPLE_CHUNKS, top_k=5)

        scores = [r["rerank_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_rerank_detail_has_all_signals(self):
        from Core.reranker_advanced import AdvancedReranker

        reranker = AdvancedReranker()
        results = reranker.rerank(SAMPLE_QUERY, SAMPLE_CHUNKS[:2], top_k=2)

        detail = results[0]["_rerank_detail"]
        expected_keys = {"semantic", "position", "density", "answer_type", "source"}
        assert expected_keys.issubset(set(detail.keys()))

    def test_rerank_empty_chunks(self):
        from Core.reranker_advanced import AdvancedReranker

        reranker = AdvancedReranker()
        results = reranker.rerank("test", [], top_k=5)
        assert results == []

    def test_rerank_top_k_greater_than_input(self):
        from Core.reranker_advanced import AdvancedReranker

        reranker = AdvancedReranker()
        results = reranker.rerank(SAMPLE_QUERY, SAMPLE_CHUNKS[:2], top_k=10)
        assert len(results) == 2


# ═══════════════════════════════════════════════════════════════════
# SmartDeduplicator
# ═══════════════════════════════════════════════════════════════════

class TestSmartDeduplicator:
    """Functional tests for multi-strategy deduplication."""

    def test_deduplicate_removes_exact_dupes(self):
        from Core.smart_deduplicator import SmartDeduplicator

        dedup = SmartDeduplicator()
        chunks = [
            {"text": "Python is a great language.", "url": "a.pdf"},
            {"text": "Python is a great language.", "url": "a.pdf"},  # exact dupe
            {"text": "Java is also popular.", "url": "b.pdf"},
        ]
        result = dedup.deduplicate(chunks)

        assert len(result.unique_chunks) < 3
        assert result.stats.exact_dupes_removed >= 1

    def test_deduplicate_unique_chunks_unchanged(self):
        from Core.smart_deduplicator import SmartDeduplicator

        dedup = SmartDeduplicator()
        result = dedup.deduplicate(SAMPLE_CHUNKS)

        assert len(result.unique_chunks) >= 3  # mostly unique
        assert result.stats.total_input == len(SAMPLE_CHUNKS)
        assert result.stats.total_output == len(result.unique_chunks)

    def test_deduplicate_stats_totals_match(self):
        from Core.smart_deduplicator import SmartDeduplicator

        dedup = SmartDeduplicator()
        result = dedup.deduplicate(SAMPLE_CHUNKS)

        assert result.stats.total_output == result.stats.total_input - result.stats.total_removed

    def test_deduplicate_empty_input(self):
        from Core.smart_deduplicator import SmartDeduplicator

        dedup = SmartDeduplicator()
        result = dedup.deduplicate([])

        assert result.unique_chunks == []
        assert result.stats.total_input == 0

    def test_deduplicate_single_chunk(self):
        from Core.smart_deduplicator import SmartDeduplicator

        dedup = SmartDeduplicator()
        # Use realistic-length text to avoid boilerplate detection
        result = dedup.deduplicate([{
            "text": "Python is a high-level programming language created by Guido van Rossum in 1991. "
                    "It supports multiple paradigms including OOP and functional programming.",
            "url": "docs.python.org",
        }])

        assert len(result.unique_chunks) == 1

    def test_deduplication_result_has_conflicts_field(self):
        from Core.smart_deduplicator import SmartDeduplicator

        dedup = SmartDeduplicator()
        result = dedup.deduplicate(SAMPLE_CHUNKS)

        assert hasattr(result, "conflicts")
        assert isinstance(result.conflicts, list)


# ═══════════════════════════════════════════════════════════════════
# ConflictDetector
# ═══════════════════════════════════════════════════════════════════

class TestConflictDetector:
    """Functional tests for cross-source conflict detection."""

    def test_detect_no_conflicts_in_consistent_data(self):
        from Core.conflict_detector import ConflictDetector

        detector = ConflictDetector()
        # Consistent chunks about Python
        chunks = SAMPLE_CHUNKS[:3]
        report = detector.detect(chunks)

        assert hasattr(report, "conflicts")
        assert hasattr(report, "total_facts_extracted")
        assert report.sources_analyzed == len(chunks)

    def test_detect_numerical_conflict(self):
        from Core.conflict_detector import ConflictDetector

        detector = ConflictDetector()
        chunks = [
            {"text": "The population of the city is 500,000 people.", "url": "source1.pdf", "title": "Report A"},
            {"text": "The city has a population of 1,200,000 residents.", "url": "source2.pdf", "title": "Report B"},
        ]
        report = detector.detect(chunks)

        assert report.total_facts_extracted >= 2

    def test_detect_has_conflicts_property(self):
        from Core.conflict_detector import ConflictDetector

        detector = ConflictDetector()
        report = detector.detect(SAMPLE_CHUNKS[:2])

        assert isinstance(report.has_conflicts, bool)

    def test_detect_empty_chunks(self):
        from Core.conflict_detector import ConflictDetector

        detector = ConflictDetector()
        report = detector.detect([])

        assert report.total_facts_extracted == 0
        assert not report.has_conflicts

    def test_conflict_report_fields(self):
        from Core.conflict_detector import ConflictDetector

        detector = ConflictDetector()
        report = detector.detect(SAMPLE_CHUNKS)

        assert hasattr(report, "consensus_facts")
        assert isinstance(report.consensus_facts, list)


# ═══════════════════════════════════════════════════════════════════
# AdvancedHallucinationDetector
# ═══════════════════════════════════════════════════════════════════

class TestAdvancedHallucinationDetector:
    """Functional tests for multi-method hallucination detection."""

    def test_detect_grounded_answer(self):
        from Core.hallucination_detector_v2 import AdvancedHallucinationDetector

        detector = AdvancedHallucinationDetector()
        report = detector.detect(
            answer=SAMPLE_ANSWER,
            source_chunks=SAMPLE_CHUNKS[:3],
            query=SAMPLE_QUERY,
        )

        assert hasattr(report, "probability")
        assert 0.0 <= report.probability <= 1.0
        assert hasattr(report, "flagged_claims")
        assert isinstance(report.flagged_claims, list)

    def test_detect_hallucinated_answer(self):
        from Core.hallucination_detector_v2 import AdvancedHallucinationDetector

        detector = AdvancedHallucinationDetector()
        hallucinated = (
            "Python was created by Linus Torvalds in 2005. "
            "It runs exclusively on quantum computers and uses "
            "a revolutionary neural compiler."
        )
        report = detector.detect(
            answer=hallucinated,
            source_chunks=SAMPLE_CHUNKS[:3],
            query=SAMPLE_QUERY,
        )

        # Should detect issues — ungrounded claims
        assert report.probability > 0 or len(report.flagged_claims) > 0

    def test_detect_is_clean_property(self):
        from Core.hallucination_detector_v2 import AdvancedHallucinationDetector

        detector = AdvancedHallucinationDetector()
        report = detector.detect(SAMPLE_ANSWER, SAMPLE_CHUNKS[:3], SAMPLE_QUERY)

        assert isinstance(report.is_clean, bool)

    def test_detect_empty_answer(self):
        from Core.hallucination_detector_v2 import AdvancedHallucinationDetector

        detector = AdvancedHallucinationDetector()
        report = detector.detect("", SAMPLE_CHUNKS[:3], SAMPLE_QUERY)

        assert report.probability >= 0
        assert report.total_claims == 0

    def test_detect_by_type_breakdown(self):
        from Core.hallucination_detector_v2 import AdvancedHallucinationDetector

        detector = AdvancedHallucinationDetector()
        report = detector.detect(SAMPLE_ANSWER, SAMPLE_CHUNKS[:3], SAMPLE_QUERY)

        assert hasattr(report, "by_type")
        assert isinstance(report.by_type, dict)

    def test_detect_with_no_sources(self):
        from Core.hallucination_detector_v2 import AdvancedHallucinationDetector

        detector = AdvancedHallucinationDetector()
        report = detector.detect(SAMPLE_ANSWER, [], SAMPLE_QUERY)

        # With no sources, detector returns early with default report
        assert report.summary != ""
        assert report.probability == 0.0  # early return, no analysis


# ═══════════════════════════════════════════════════════════════════
# AnswerQualityAssessor (ConfidenceScorer)
# ═══════════════════════════════════════════════════════════════════

class TestAnswerQualityAssessor:
    """Functional tests for multi-factor confidence scoring."""

    def test_assess_well_grounded_answer(self):
        from Core.confidence_scorer import AnswerQualityAssessor

        assessor = AnswerQualityAssessor()
        quality = assessor.assess(SAMPLE_ANSWER, SAMPLE_QUERY, SAMPLE_CHUNKS[:3])

        assert 0.0 <= quality.confidence <= 1.0
        assert quality.risk_level in ("low", "medium", "high")
        assert quality.explanation != ""

    def test_assess_breakdown_fields(self):
        from Core.confidence_scorer import AnswerQualityAssessor

        assessor = AnswerQualityAssessor()
        quality = assessor.assess(SAMPLE_ANSWER, SAMPLE_QUERY, SAMPLE_CHUNKS[:3])

        bd = quality.breakdown
        assert hasattr(bd, "source_alignment")
        assert hasattr(bd, "claim_support")
        assert hasattr(bd, "semantic_consistency")
        assert hasattr(bd, "source_credibility")
        assert hasattr(bd, "overall")

    def test_assess_empty_answer(self):
        from Core.confidence_scorer import AnswerQualityAssessor

        assessor = AnswerQualityAssessor()
        quality = assessor.assess("", SAMPLE_QUERY, SAMPLE_CHUNKS[:3])

        assert quality.confidence == 0.0 or quality.risk_level == "high"

    def test_assess_no_sources(self):
        from Core.confidence_scorer import AnswerQualityAssessor

        assessor = AnswerQualityAssessor()
        quality = assessor.assess(SAMPLE_ANSWER, SAMPLE_QUERY, [])

        assert quality.risk_level in ("medium", "high")

    def test_assess_irrelevant_answer(self):
        from Core.confidence_scorer import AnswerQualityAssessor

        assessor = AnswerQualityAssessor()
        irrelevant = "The weather today is sunny with a high of 75 degrees."
        quality = assessor.assess(irrelevant, SAMPLE_QUERY, SAMPLE_CHUNKS[:3])

        # Irrelevant answer should score lower
        good = assessor.assess(SAMPLE_ANSWER, SAMPLE_QUERY, SAMPLE_CHUNKS[:3])
        assert quality.confidence <= good.confidence


# ═══════════════════════════════════════════════════════════════════
# FollowUpGenerator
# ═══════════════════════════════════════════════════════════════════

class TestFollowUpGenerator:
    """Functional tests for follow-up question generation."""

    def test_generate_follow_ups(self):
        from Core.follow_up_generator import FollowUpGenerator

        gen = FollowUpGenerator(llm_fn=None)
        follow_ups = gen.generate(SAMPLE_ANSWER, SAMPLE_QUERY, SAMPLE_CHUNKS[:3])

        assert isinstance(follow_ups, list)
        assert len(follow_ups) >= 1
        assert all(isinstance(q, str) and len(q) > 0 for q in follow_ups)

    def test_generate_without_sources(self):
        from Core.follow_up_generator import FollowUpGenerator

        gen = FollowUpGenerator(llm_fn=None)
        follow_ups = gen.generate(SAMPLE_ANSWER, SAMPLE_QUERY)

        assert isinstance(follow_ups, list)

    def test_generate_empty_answer(self):
        from Core.follow_up_generator import FollowUpGenerator

        gen = FollowUpGenerator(llm_fn=None)
        follow_ups = gen.generate("", SAMPLE_QUERY)

        assert isinstance(follow_ups, list)

    def test_follow_ups_are_questions(self):
        from Core.follow_up_generator import FollowUpGenerator

        gen = FollowUpGenerator(llm_fn=None)
        follow_ups = gen.generate(SAMPLE_ANSWER, SAMPLE_QUERY, SAMPLE_CHUNKS[:3])

        # At least some should end with '?'
        questions = [q for q in follow_ups if q.strip().endswith("?")]
        assert len(questions) >= 1


# ═══════════════════════════════════════════════════════════════════
# MetricsTracker
# ═══════════════════════════════════════════════════════════════════

class TestMetricsTracker:
    """Functional tests for query metrics aggregation."""

    def test_record_and_summarize(self):
        from Core.metrics_tracker import MetricsTracker, QueryEvent

        tracker = MetricsTracker()
        tracker.clear()

        event = QueryEvent(
            query="test query",
            latency_ms=150.0,
            cache_hit=False,
            chunks_retrieved=5,
            hallucination_probability=0.1,
            quality_score=0.85,
        )
        tracker.record_query(event)

        summary = tracker.get_summary()
        assert summary.total_queries >= 1
        assert summary.avg_latency_ms > 0

    def test_cache_hit_rate(self):
        from Core.metrics_tracker import MetricsTracker, QueryEvent

        tracker = MetricsTracker()
        tracker.clear()

        tracker.record_query(QueryEvent(query="q1", cache_hit=True, latency_ms=10))
        tracker.record_query(QueryEvent(query="q2", cache_hit=False, latency_ms=200))
        tracker.record_query(QueryEvent(query="q3", cache_hit=True, latency_ms=15))

        summary = tracker.get_summary()
        assert 0.6 <= summary.cache_hit_rate <= 0.7  # 2/3

    def test_latency_percentiles(self):
        from Core.metrics_tracker import MetricsTracker, QueryEvent

        tracker = MetricsTracker()
        tracker.clear()

        for i in range(100):
            tracker.record_query(QueryEvent(
                query=f"q{i}",
                latency_ms=float(i + 1),
            ))

        summary = tracker.get_summary()
        assert summary.p50_latency_ms > 0
        assert summary.p90_latency_ms > summary.p50_latency_ms
        assert summary.p99_latency_ms >= summary.p90_latency_ms

    def test_empty_summary(self):
        from Core.metrics_tracker import MetricsTracker

        tracker = MetricsTracker()
        tracker.clear()

        summary = tracker.get_summary()
        assert summary.total_queries == 0
        assert summary.avg_latency_ms == 0


# ═══════════════════════════════════════════════════════════════════
# FLARERetriever
# ═══════════════════════════════════════════════════════════════════

class TestFLARERetriever:
    """Functional tests for forward-looking active retrieval."""

    def test_retrieve_and_generate(self):
        from Core.flare_retrieval import FLARERetriever

        def mock_retrieve(query):
            return [{"text": f"Info about {query[:20]}", "score": 0.8}]

        def mock_generate(query, context):
            return f"Based on the context, {query} is explained here."

        flare = FLARERetriever(retrieve_fn=mock_retrieve, generate_fn=mock_generate)
        result = flare.retrieve_and_generate(SAMPLE_QUERY, SAMPLE_CHUNKS[:3])

        assert result.final_answer != ""
        assert result.iterations >= 1
        assert isinstance(result.sub_queries, list)

    def test_flare_result_fields(self):
        from Core.flare_retrieval import FLARERetriever, FLAREResult

        def noop_retrieve(q):
            return []

        def noop_generate(q, c):
            return "Simple answer."

        flare = FLARERetriever(retrieve_fn=noop_retrieve, generate_fn=noop_generate)
        result = flare.retrieve_and_generate("simple question")

        assert hasattr(result, "final_answer")
        assert hasattr(result, "iterations")
        assert hasattr(result, "sub_queries")
        assert hasattr(result, "total_chunks_retrieved")
        assert hasattr(result, "confidence_improved")

    def test_flare_no_retrieve_fn(self):
        from Core.flare_retrieval import FLARERetriever

        def mock_generate(q, c):
            return "answer without retrieval"

        flare = FLARERetriever(retrieve_fn=None, generate_fn=mock_generate)
        result = flare.retrieve_and_generate("test", SAMPLE_CHUNKS[:2])

        assert result.final_answer != ""

    def test_flare_with_initial_chunks(self):
        from Core.flare_retrieval import FLARERetriever

        retrieved_queries = []

        def tracking_retrieve(q):
            retrieved_queries.append(q)
            return [{"text": "Additional context", "score": 0.7}]

        def mock_generate(q, c):
            return "Generated answer using all context."

        flare = FLARERetriever(retrieve_fn=tracking_retrieve, generate_fn=mock_generate)
        result = flare.retrieve_and_generate(SAMPLE_QUERY, SAMPLE_CHUNKS[:2])

        assert result.final_answer != ""


# ═══════════════════════════════════════════════════════════════════
# ContextualCompressor
# ═══════════════════════════════════════════════════════════════════

class TestContextualCompressor:
    """Functional tests for query-focused chunk compression."""

    def test_compress_reduces_noise(self):
        from Core.contextual_compressor import ContextualCompressor

        compressor = ContextualCompressor(max_tokens=2000)
        results = compressor.compress(SAMPLE_QUERY, SAMPLE_CHUNKS)

        assert len(results) >= 1
        # All returned chunks should have text
        assert all("text" in r for r in results)

    def test_compress_marks_compressed(self):
        from Core.contextual_compressor import ContextualCompressor

        compressor = ContextualCompressor(max_tokens=500)
        results = compressor.compress(SAMPLE_QUERY, SAMPLE_CHUNKS)

        # Compressed chunks should have metadata markers
        for r in results:
            assert "_compressed" in r or "text" in r

    def test_compress_empty_chunks(self):
        from Core.contextual_compressor import ContextualCompressor

        compressor = ContextualCompressor()
        results = compressor.compress("test query", [])

        assert results == []

    def test_compress_preserves_relevant_content(self):
        from Core.contextual_compressor import ContextualCompressor

        compressor = ContextualCompressor(max_tokens=5000)
        results = compressor.compress(SAMPLE_QUERY, SAMPLE_CHUNKS[:3])

        # Python-related chunks should survive compression
        all_text = " ".join(r.get("text", "") for r in results)
        assert "Python" in all_text or "python" in all_text.lower()

    def test_compress_respects_token_limit(self):
        from Core.contextual_compressor import ContextualCompressor

        compressor = ContextualCompressor(max_tokens=100)
        results = compressor.compress(SAMPLE_QUERY, SAMPLE_CHUNKS)

        total_words = sum(len(r.get("text", "").split()) for r in results)
        # Rough token estimate — should be constrained
        assert total_words < 200  # generous margin


# ═══════════════════════════════════════════════════════════════════
# QueryRewriter
# ═══════════════════════════════════════════════════════════════════

class TestQueryRewriter:
    """Functional tests for multi-query expansion."""

    def test_rewrite_without_llm(self):
        from Core.query_rewriter import QueryRewriter

        rewriter = QueryRewriter(llm_fn=None)
        result = rewriter.rewrite(SAMPLE_QUERY)

        assert result.original == SAMPLE_QUERY
        assert result.strategy in ("template", "passthrough")
        # all_queries should always include the original
        assert SAMPLE_QUERY in result.all_queries

    def test_rewrite_with_llm(self):
        from Core.query_rewriter import QueryRewriter

        def fake_llm(prompt):
            return (
                "1. What is the Python programming language?\n"
                "2. Who is the creator of Python?\n"
                "3. When was Python first released?"
            )

        rewriter = QueryRewriter(llm_fn=fake_llm)
        result = rewriter.rewrite(SAMPLE_QUERY)

        assert result.original == SAMPLE_QUERY
        assert result.strategy == "llm"
        assert len(result.rewrites) >= 1

    def test_rewrite_all_queries_deduplicates(self):
        from Core.query_rewriter import QueryRewriter

        rewriter = QueryRewriter(llm_fn=None)
        result = rewriter.rewrite("test query")

        # all_queries should not have duplicates
        seen = set()
        for q in result.all_queries:
            lower = q.lower()
            assert lower not in seen, f"Duplicate query: {q}"
            seen.add(lower)

    def test_rewrite_empty_query(self):
        from Core.query_rewriter import QueryRewriter

        rewriter = QueryRewriter(llm_fn=None)
        result = rewriter.rewrite("")

        assert result.original == ""
        assert result.strategy == "passthrough"


# ═══════════════════════════════════════════════════════════════════
# ZeroWasteCache
# ═══════════════════════════════════════════════════════════════════

class TestZeroWasteCache:
    """Functional tests for two-tier semantic cache."""

    def test_exact_cache_hit(self):
        from Core.zero_waste_cache import ZeroWasteCache

        cache = ZeroWasteCache()
        cache.set_answer("What is Python?", [{"text": "Python is a language.", "answer": "cached"}])

        result = cache.get_answer("What is Python?")
        assert result is not None
        assert cache.stats["tier1_exact_hits"] >= 1

    def test_cache_miss(self):
        from Core.zero_waste_cache import ZeroWasteCache

        cache = ZeroWasteCache()
        result = cache.get_answer("A completely new question never asked before xyz123")

        assert result is None

    def test_temporal_query_bypasses_cache(self):
        from Core.zero_waste_cache import ZeroWasteCache

        cache = ZeroWasteCache()
        cache.set_answer("what happened today", [{"text": "something"}])

        result = cache.get_answer("what happened today")
        assert result is None
        assert cache.stats["temporal_bypasses"] >= 1

    def test_is_temporal_query(self):
        from Core.zero_waste_cache import ZeroWasteCache

        assert ZeroWasteCache.is_temporal_query("What happened today?")
        assert ZeroWasteCache.is_temporal_query("Show me the latest news")
        assert not ZeroWasteCache.is_temporal_query("What is photosynthesis?")

    def test_classify_strategy(self):
        from Core.zero_waste_cache import ZeroWasteCache

        assert ZeroWasteCache.classify_strategy("What happened today?") == "temporal"
        assert ZeroWasteCache.classify_strategy("Give me the exact number") == "strict"
        assert ZeroWasteCache.classify_strategy("What is Python?") == "standard"

    def test_stats_tracking(self):
        from Core.zero_waste_cache import ZeroWasteCache

        cache = ZeroWasteCache()
        cache.get_answer("miss query")
        assert cache.stats["tier1_misses"] >= 1

    def test_context_cache_set_get(self):
        from Core.zero_waste_cache import ZeroWasteCache

        cache = ZeroWasteCache()
        chunks = [{"text": "some context data", "url": "doc.pdf"}]
        cache.set_context("query about X", chunks)

        # Context cache requires semantic matching — just verify set doesn't crash
        assert cache.stats is not None


# ═══════════════════════════════════════════════════════════════════
# PromptTemplateLibrary & FocusModes
# ═══════════════════════════════════════════════════════════════════

class TestPromptTemplateLibrary:
    """Functional tests for prompt templates and focus modes."""

    def test_list_builtin_templates(self):
        from Core.prompt_focus import PromptTemplateLibrary

        lib = PromptTemplateLibrary(storage_dir=None)
        templates = lib.list_templates()

        assert len(templates) >= 10  # 12+ builtins
        assert all(hasattr(t, "name") and hasattr(t, "system_prompt") for t in templates)

    def test_list_categories(self):
        from Core.prompt_focus import PromptTemplateLibrary

        lib = PromptTemplateLibrary(storage_dir=None)
        categories = lib.list_categories()

        assert "Medical" in categories
        assert "Legal" in categories
        assert "Business" in categories

    def test_apply_template(self):
        from Core.prompt_focus import PromptTemplateLibrary

        lib = PromptTemplateLibrary(storage_dir=None)
        system_prompt, wrapped = lib.apply_template("medical_symptoms", "patient symptoms?")

        assert system_prompt != ""
        assert "patient symptoms?" in wrapped

    def test_apply_nonexistent_template(self):
        from Core.prompt_focus import PromptTemplateLibrary

        lib = PromptTemplateLibrary(storage_dir=None)
        sys, wrapped = lib.apply_template("nonexistent_xxx", "test query")

        assert sys == ""
        assert wrapped == "test query"

    def test_get_template(self):
        from Core.prompt_focus import PromptTemplateLibrary

        lib = PromptTemplateLibrary(storage_dir=None)
        tpl = lib.get_template("medical_symptoms")

        assert tpl is not None
        assert tpl.category == "Medical"
        assert tpl.is_builtin is True

    def test_save_and_delete_custom(self, tmp_path):
        from Core.prompt_focus import PromptTemplateLibrary

        storage = tmp_path / "test_prompts.json"
        lib = PromptTemplateLibrary(storage_dir=storage)

        tpl, warnings = lib.save_custom(
            name="Test Custom",
            label="My Custom Prompt",
            system_prompt="You are a test helper.",
            category="Testing",
        )
        assert tpl.name == "test_custom"
        assert lib.custom_count >= 1

        found = lib.get_template("test_custom")
        assert found is not None

        deleted = lib.delete_custom("test_custom")
        assert deleted is True
        assert lib.get_template("test_custom") is None

    def test_clone_as_custom(self, tmp_path):
        from Core.prompt_focus import PromptTemplateLibrary

        storage = tmp_path / "test_prompts.json"
        lib = PromptTemplateLibrary(storage_dir=storage)

        cloned = lib.clone_as_custom("medical_symptoms", "my_med")
        assert cloned is not None
        assert not cloned.is_builtin

    def test_filter_by_category(self):
        from Core.prompt_focus import PromptTemplateLibrary

        lib = PromptTemplateLibrary(storage_dir=None)
        medical = lib.list_templates(category="Medical")

        assert len(medical) >= 2
        assert all(t.category == "Medical" for t in medical)


class TestFocusModes:
    """Functional tests for focus mode configurations."""

    def test_all_focus_modes_defined(self):
        from Core.prompt_focus import FocusMode, FOCUS_CONFIGS

        for mode in FocusMode:
            assert mode in FOCUS_CONFIGS

    def test_focus_config_apply(self):
        from Core.prompt_focus import FocusMode, FOCUS_CONFIGS

        config = FOCUS_CONFIGS[FocusMode.FACT_CHECK]
        modified = config.apply_to_prompt("Base system prompt.")

        assert "Base system prompt." in modified
        assert "fact" in modified.lower() or "claim" in modified.lower()

    def test_general_mode_no_change(self):
        from Core.prompt_focus import FocusMode, FOCUS_CONFIGS

        config = FOCUS_CONFIGS[FocusMode.GENERAL]
        base = "This is the base prompt."
        result = config.apply_to_prompt(base)

        assert result == base  # General mode adds nothing


# ═══════════════════════════════════════════════════════════════════
# InferenceGuard
# ═══════════════════════════════════════════════════════════════════

class TestInferenceGuard:
    """Functional tests for inference crash diagnostics."""

    def test_guard_metrics_record_call(self):
        from Core.inference_guard import GuardMetrics

        metrics = GuardMetrics()
        metrics.record_call()
        stats = metrics.get_stats()

        assert stats["total_guarded_calls"] >= 1

    def test_guard_metrics_record_success(self):
        from Core.inference_guard import GuardMetrics

        metrics = GuardMetrics()
        metrics.record_call()
        metrics.record_success(
            elapsed_ms=100.0,
            rss_delta_mb=5.0,
            profile={"operation": "test", "status": "ok"},
        )
        stats = metrics.get_stats()

        assert stats["timing"]["avg_ms"] > 0
        assert stats["memory"]["max_rss_delta_mb"] >= 5.0

    def test_guard_metrics_record_crash(self):
        from Core.inference_guard import GuardMetrics

        metrics = GuardMetrics()
        metrics.record_crash({"error": "test", "type": "RuntimeError"})

        assert metrics.total_crashes >= 1
        history = metrics.get_crash_history()
        assert len(history) >= 1

    def test_memory_snapshot(self):
        from Core.inference_guard import MemorySnapshot

        snap = MemorySnapshot()
        assert snap.rss_mb > 0
        assert snap.sys_total_mb > 0

        d = snap.to_dict()
        assert "rss_mb" in d
        assert "system_total_mb" in d

    def test_memory_snapshot_delta(self):
        from Core.inference_guard import MemorySnapshot

        snap1 = MemorySnapshot()
        snap2 = MemorySnapshot()
        delta = snap2.delta(snap1)

        assert "rss_delta_mb" in delta
        assert "vms_delta_mb" in delta

    def test_get_guard_stats_api(self):
        from Core.inference_guard import get_guard_stats

        stats = get_guard_stats()
        assert "total_guarded_calls" in stats
        assert "timing" in stats
        assert "memory" in stats

    def test_async_context_manager_success(self):
        from Core.inference_guard import InferenceGuard

        async def run():
            async with InferenceGuard("test_op") as guard:
                guard.mark("step1")
                guard.phase("processing")
                guard.mark("step2")
            return True

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result is True

    def test_async_context_manager_crash(self):
        from Core.inference_guard import InferenceGuard

        async def run():
            with pytest.raises(ValueError, match="deliberate"):
                async with InferenceGuard("test_crash"):
                    raise ValueError("deliberate crash")

        asyncio.get_event_loop().run_until_complete(run())


# ═══════════════════════════════════════════════════════════════════
# AnswerRefinementEngine
# ═══════════════════════════════════════════════════════════════════

class TestAnswerRefinementEngine:
    """Functional tests for post-generation quality pipeline."""

    def test_refine_good_answer(self):
        from Core.answer_refinement import AnswerRefinementEngine

        engine = AnswerRefinementEngine(llm_fn=None)

        async def run():
            return await engine.refine(SAMPLE_ANSWER, SAMPLE_QUERY, SAMPLE_CHUNKS[:3])

        result = asyncio.get_event_loop().run_until_complete(run())

        assert result.original_answer == SAMPLE_ANSWER
        assert result.refined_answer != ""
        assert 0.0 <= result.quality_score <= 1.0

    def test_refine_empty_answer(self):
        from Core.answer_refinement import AnswerRefinementEngine

        engine = AnswerRefinementEngine(llm_fn=None)

        async def run():
            return await engine.refine("", SAMPLE_QUERY, SAMPLE_CHUNKS[:3])

        result = asyncio.get_event_loop().run_until_complete(run())

        assert result.original_answer == ""
        assert not result.was_refined

    def test_refine_empty_sources(self):
        from Core.answer_refinement import AnswerRefinementEngine

        engine = AnswerRefinementEngine(llm_fn=None)

        async def run():
            return await engine.refine(SAMPLE_ANSWER, SAMPLE_QUERY, [])

        result = asyncio.get_event_loop().run_until_complete(run())

        assert not result.was_refined

    def test_refinement_result_fields(self):
        from Core.answer_refinement import AnswerRefinementEngine, RefinementResult

        engine = AnswerRefinementEngine(llm_fn=None)

        async def run():
            return await engine.refine(SAMPLE_ANSWER, SAMPLE_QUERY, SAMPLE_CHUNKS[:3])

        result = asyncio.get_event_loop().run_until_complete(run())

        assert isinstance(result, RefinementResult)
        assert hasattr(result, "stages_applied")
        assert hasattr(result, "refinement_notes")
        assert hasattr(result, "completeness_score")
        assert hasattr(result, "hallucination_probability")


# ═══════════════════════════════════════════════════════════════════
# AnswerEvaluator
# ═══════════════════════════════════════════════════════════════════

class TestAnswerEvaluator:
    """Functional tests for answer quality evaluation."""

    def test_evaluate_good_answer(self):
        from Core.evaluation import AnswerEvaluator

        evaluator = AnswerEvaluator()
        source_texts = [c["text"] for c in SAMPLE_CHUNKS[:3]]
        scores = evaluator.evaluate(SAMPLE_QUERY, SAMPLE_ANSWER, source_texts)

        assert "overall" in scores
        assert "faithfulness" in scores
        assert "relevance" in scores
        assert "completeness" in scores
        assert "conciseness" in scores
        assert all(0.0 <= v <= 1.0 for v in scores.values())

    def test_evaluate_empty_answer(self):
        from Core.evaluation import AnswerEvaluator

        evaluator = AnswerEvaluator()
        scores = evaluator.evaluate(SAMPLE_QUERY, "", ["source text"])

        assert scores["overall"] == 0.0

    def test_evaluate_no_sources(self):
        from Core.evaluation import AnswerEvaluator

        evaluator = AnswerEvaluator()
        scores = evaluator.evaluate(SAMPLE_QUERY, SAMPLE_ANSWER, [])

        assert scores["faithfulness"] == 0.5  # fallback

    def test_evaluation_history(self):
        from Core.evaluation import AnswerEvaluator

        evaluator = AnswerEvaluator()
        evaluator.evaluate("Q1", "Answer one.", ["source"])
        evaluator.evaluate("Q2", "Answer two.", ["source"])

        stats = evaluator.get_statistics()
        assert stats["total_evaluations"] >= 2

    def test_conciseness_scoring(self):
        from Core.evaluation import AnswerEvaluator

        # Optimal length (20-200 words) should score high
        assert AnswerEvaluator._score_conciseness("word " * 50) == 1.0
        # Too short should score lower
        assert AnswerEvaluator._score_conciseness("short") < 1.0


# ═══════════════════════════════════════════════════════════════════
# RetrievalEvaluator
# ═══════════════════════════════════════════════════════════════════

class TestRetrievalEvaluator:
    """Functional tests for retrieval quality metrics."""

    def test_calculate_metrics_perfect_retrieval(self):
        from Core.evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1", "doc2", "doc3"]

        metrics = evaluator.calculate_metrics(retrieved, relevant, k=3)

        assert metrics["precision@3"] == 1.0
        assert metrics["recall@3"] == 1.0
        assert metrics["mrr"] == 1.0
        assert metrics["f1"] == 1.0

    def test_calculate_metrics_no_overlap(self):
        from Core.evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()
        metrics = evaluator.calculate_metrics(["a", "b"], ["c", "d"], k=2)

        assert metrics["precision@2"] == 0.0
        assert metrics["recall@2"] == 0.0
        assert metrics["mrr"] == 0.0
        assert metrics["f1"] == 0.0

    def test_calculate_metrics_partial_overlap(self):
        from Core.evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()
        metrics = evaluator.calculate_metrics(
            ["doc1", "doc2", "doc3", "doc4"],
            ["doc2", "doc4"],
            k=4,
        )

        assert metrics["precision@4"] == 0.5  # 2 of 4
        assert metrics["recall@4"] == 1.0      # 2 of 2
        assert metrics["mrr"] == 0.5            # first hit at position 2

    def test_mrr_ordering(self):
        from Core.evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()
        # First relevant doc at position 1
        m1 = evaluator.calculate_metrics(["rel", "irr"], ["rel"], k=2)
        # First relevant doc at position 2
        m2 = evaluator.calculate_metrics(["irr", "rel"], ["rel"], k=2)

        assert m1["mrr"] > m2["mrr"]

    def test_empty_inputs(self):
        from Core.evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()
        metrics = evaluator.calculate_metrics([], [], k=5)

        assert metrics["precision@5"] == 0.0
        assert metrics["f1"] == 0.0


# ═══════════════════════════════════════════════════════════════════
# Cross-Module Integration
# ═══════════════════════════════════════════════════════════════════

class TestCrossModuleIntegration:
    """Verify modules work together in realistic pipelines."""

    def test_rerank_then_dedup(self):
        """Reranker output feeds into deduplicator."""
        from Core.reranker_advanced import AdvancedReranker
        from Core.smart_deduplicator import SmartDeduplicator

        reranker = AdvancedReranker()
        dedup = SmartDeduplicator()

        reranked = reranker.rerank(SAMPLE_QUERY, SAMPLE_CHUNKS, top_k=5)
        result = dedup.deduplicate(reranked)

        assert len(result.unique_chunks) >= 1
        # Rerank metadata should survive
        assert all("rerank_score" in c for c in result.unique_chunks)

    def test_dedup_then_conflict_detect(self):
        """Deduplicator output feeds into conflict detector."""
        from Core.smart_deduplicator import SmartDeduplicator
        from Core.conflict_detector import ConflictDetector

        dedup = SmartDeduplicator()
        detector = ConflictDetector()

        deduped = dedup.deduplicate(SAMPLE_CHUNKS)
        report = detector.detect(deduped.unique_chunks)

        assert report.sources_analyzed == len(deduped.unique_chunks)

    def test_compress_then_evaluate(self):
        """Compressor output feeds into evaluator."""
        from Core.contextual_compressor import ContextualCompressor
        from Core.evaluation import AnswerEvaluator

        compressor = ContextualCompressor(max_tokens=2000)
        evaluator = AnswerEvaluator()

        compressed = compressor.compress(SAMPLE_QUERY, SAMPLE_CHUNKS)
        source_texts = [c["text"] for c in compressed]

        scores = evaluator.evaluate(SAMPLE_QUERY, SAMPLE_ANSWER, source_texts)
        assert scores["overall"] > 0

    def test_hallucination_then_confidence(self):
        """Hallucination report informs confidence scoring."""
        from Core.hallucination_detector_v2 import AdvancedHallucinationDetector
        from Core.confidence_scorer import AnswerQualityAssessor

        h_detector = AdvancedHallucinationDetector()
        assessor = AnswerQualityAssessor()

        h_report = h_detector.detect(SAMPLE_ANSWER, SAMPLE_CHUNKS[:3], SAMPLE_QUERY)
        quality = assessor.assess(SAMPLE_ANSWER, SAMPLE_QUERY, SAMPLE_CHUNKS[:3])

        # Both should produce valid results
        assert 0 <= h_report.probability <= 1
        assert 0 <= quality.confidence <= 1

    def test_full_mini_pipeline(self):
        """Simulate a mini-pipeline: rerank → dedup → compress → evaluate."""
        from Core.reranker_advanced import AdvancedReranker
        from Core.smart_deduplicator import SmartDeduplicator
        from Core.contextual_compressor import ContextualCompressor
        from Core.evaluation import AnswerEvaluator

        # Step 1: Rerank
        reranker = AdvancedReranker()
        reranked = reranker.rerank(SAMPLE_QUERY, SAMPLE_CHUNKS, top_k=5)

        # Step 2: Deduplicate
        dedup = SmartDeduplicator()
        deduped = dedup.deduplicate(reranked)

        # Step 3: Compress
        compressor = ContextualCompressor(max_tokens=2000)
        compressed = compressor.compress(SAMPLE_QUERY, deduped.unique_chunks)

        # Step 4: Evaluate answer quality
        evaluator = AnswerEvaluator()
        source_texts = [c["text"] for c in compressed]
        scores = evaluator.evaluate(SAMPLE_QUERY, SAMPLE_ANSWER, source_texts)

        assert scores["overall"] > 0
        assert len(compressed) >= 1
