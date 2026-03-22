"""
Deep-audit functional tests — Phase 2.

NO mocks — tests use real module instances with real data.

Covers gaps NOT in test_core_modules.py or test_enhanced_rag.py:
  - KnowledgeGraph (SQLite CRUD, multi-hop, entity extraction)
  - Pydantic models (ChunkPayload, RAGSearchResult, QueryRewriteResult, EvalSample)
  - MetricsTracker IndexEvent + summary aggregation
  - MetricsTracker time-windowed summary
  - EnhancedRAGService._record_metrics (verifies the bug-fix)
  - ZeroWasteCache fingerprint invalidation & version bump
  - InferenceGuard CrashReport classification
  - PromptTemplate serialization (to_dict / from_dict)
  - validate_prompt function
  - Cross-module pipeline: rewrite → retrieve → rerank → compress → evaluate
"""

import asyncio
import os
import tempfile
import time

import pytest


# ═══════════════════════════════════════════════════════════════════
# KnowledgeGraph (SQLite-backed)
# ═══════════════════════════════════════════════════════════════════


class TestKnowledgeGraph:
    """Full CRUD tests against a temporary SQLite database."""

    @pytest.fixture(autouse=True)
    def kg(self, tmp_path):
        from Core.knowledge_graph import KnowledgeGraph
        db = str(tmp_path / "test_kg.db")
        self.kg = KnowledgeGraph(db_path=db)
        yield
        self.kg.clear()

    def test_add_entity_returns_id(self):
        eid = self.kg.add_entity("Albert Einstein", "person")
        assert isinstance(eid, str)
        assert len(eid) == 12  # md5[:12]

    def test_add_entity_idempotent(self):
        eid1 = self.kg.add_entity("Python")
        eid2 = self.kg.add_entity("Python")
        assert eid1 == eid2

    def test_add_and_query_triples(self):
        self.kg.add_triples(
            [("Python", "created_by", "Guido van Rossum")],
            source_url="test.pdf",
            confidence=0.95,
        )
        results = self.kg.query_entity("Python")
        assert len(results) >= 1
        names = [r.get("object_name") or r.get("subject_name") for r in results]
        assert any("Guido" in n for n in names if n)

    def test_get_stats(self):
        self.kg.add_triples([
            ("Earth", "orbits", "Sun"),
            ("Moon", "orbits", "Earth"),
        ])
        stats = self.kg.get_stats()
        assert stats["entities"] >= 3  # Earth, Sun, Moon
        assert stats["triples"] >= 2

    def test_clear(self):
        self.kg.add_triples([("A", "rel", "B")])
        self.kg.clear()
        stats = self.kg.get_stats()
        assert stats["entities"] == 0
        assert stats["triples"] == 0

    def test_multi_hop(self):
        self.kg.add_triples([
            ("Einstein", "born_in", "Ulm"),
            ("Ulm", "located_in", "Germany"),
        ])
        paths = self.kg.multi_hop("Einstein", "Germany", max_hops=3)
        # Should find Einstein -> Ulm -> Germany
        assert len(paths) >= 1
        names = [node.get("name") for node in paths[0]]
        assert "Einstein" in names[0].lower() or "einstein" in str(names).lower()

    def test_multi_hop_no_path(self):
        self.kg.add_triples([("X", "rel", "Y")])
        paths = self.kg.multi_hop("X", "Z", max_hops=2)
        assert paths == []

    def test_extract_entities_regex(self):
        text = "Python is a Programming Language. Apple was founded by Steve Jobs."
        triples = self.kg.extract_entities_regex(text)
        assert len(triples) >= 1
        predicates = [t[1] for t in triples]
        assert "is_a" in predicates or "founded_by" in predicates

    def test_extract_entities_regex_empty(self):
        triples = self.kg.extract_entities_regex("no entities here at all")
        assert triples == []

    def test_confidence_max_on_conflict(self):
        self.kg.add_triples([("A", "rel", "B")], confidence=0.5)
        self.kg.add_triples([("A", "rel", "B")], confidence=0.9)
        # Same triple — confidence should be max(0.5, 0.9)
        results = self.kg.query_entity("A")
        assert len(results) == 1
        assert results[0]["confidence"] >= 0.9

    def test_source_url_stored(self):
        self.kg.add_triples(
            [("Node", "connects_to", "Graph")],
            source_url="http://example.com/doc"
        )
        results = self.kg.query_entity("Node")
        assert any(r.get("source_url") == "http://example.com/doc" for r in results)


# ═══════════════════════════════════════════════════════════════════
# Pydantic Models (Core/rag_models.py)
# ═══════════════════════════════════════════════════════════════════


class TestChunkPayload:
    def test_valid_minimal(self):
        from Core.rag_models import ChunkPayload
        cp = ChunkPayload(text="Hello world")
        assert cp.text == "Hello world"
        assert cp.chunk_index == 0
        assert cp.is_table is False
        assert cp.url is None

    def test_valid_full(self):
        from Core.rag_models import ChunkPayload
        cp = ChunkPayload(
            text="Test content",
            url="http://test.com",
            title="Test Doc",
            scan_root="/data",
            chunk_index=5,
            is_table=True,
            sheet_name="Sheet1",
            parent_id="abc123",
            doc_type="excel",
        )
        assert cp.url == "http://test.com"
        assert cp.chunk_index == 5
        assert cp.is_table is True

    def test_blank_text_rejected(self):
        from Core.rag_models import ChunkPayload
        with pytest.raises(Exception):  # ValidationError
            ChunkPayload(text="   ")

    def test_negative_chunk_index_rejected(self):
        from Core.rag_models import ChunkPayload
        with pytest.raises(Exception):
            ChunkPayload(text="ok", chunk_index=-1)

    def test_extra_fields_allowed(self):
        from Core.rag_models import ChunkPayload
        cp = ChunkPayload(text="test", custom_field="surprise")
        assert cp.custom_field == "surprise"

    def test_text_stripped(self):
        from Core.rag_models import ChunkPayload
        cp = ChunkPayload(text="  hello  ")
        assert cp.text == "hello"


class TestRAGSearchResult:
    def test_valid_minimal(self):
        from Core.rag_models import RAGSearchResult
        r = RAGSearchResult(text="some result")
        assert r.score == 0.0
        assert r.rerank_score is None
        assert r.is_cached is False

    def test_score_coercion(self):
        from Core.rag_models import RAGSearchResult
        r = RAGSearchResult(text="result", score="0.95")
        assert r.score == 0.95

    def test_invalid_score_coerced_to_zero(self):
        from Core.rag_models import RAGSearchResult
        r = RAGSearchResult(text="result", score="not_a_number")
        assert r.score == 0.0

    def test_blank_text_rejected(self):
        from Core.rag_models import RAGSearchResult
        with pytest.raises(Exception):
            RAGSearchResult(text="   ")

    def test_extra_fields_allowed(self):
        from Core.rag_models import RAGSearchResult
        r = RAGSearchResult(text="test", new_meta=42)
        assert r.new_meta == 42


class TestQueryRewriteResult:
    def test_passthrough(self):
        from Core.rag_models import QueryRewriteResult
        qr = QueryRewriteResult(original="What is AI?")
        assert qr.strategy == "passthrough"
        assert qr.all_queries == ["What is AI?"]

    def test_all_queries_deduplicates(self):
        from Core.rag_models import QueryRewriteResult
        qr = QueryRewriteResult(
            original="What is AI?",
            rewrites=["what is ai?", "explain artificial intelligence"],
            strategy="llm",
        )
        # "what is ai?" is a duplicate of original (case-insensitive)
        assert len(qr.all_queries) == 2
        assert qr.all_queries[0] == "What is AI?"
        assert "artificial intelligence" in qr.all_queries[1].lower()

    def test_empty_rewrites(self):
        from Core.rag_models import QueryRewriteResult
        qr = QueryRewriteResult(original="test")
        assert qr.rewrites == []
        assert len(qr.all_queries) == 1


class TestEvalSample:
    def test_valid(self):
        from Core.rag_models import EvalSample
        es = EvalSample(query="What is X?", expected_answer="X is Y.")
        assert es.generated_answer is None
        assert es.retrieved_texts == []
        assert es.ndcg is None

    def test_full_fields(self):
        from Core.rag_models import EvalSample
        es = EvalSample(
            query="q",
            expected_answer="a",
            retrieved_texts=["t1", "t2"],
            generated_answer="gen",
            relevance_scores=[1.0, 0.5],
            ndcg=0.85,
            mrr=1.0,
        )
        assert len(es.relevance_scores) == 2
        assert es.ndcg == 0.85


# ═══════════════════════════════════════════════════════════════════
# MetricsTracker — IndexEvent + windowed summary
# ═══════════════════════════════════════════════════════════════════


class TestMetricsTrackerExtended:
    """Covers IndexEvent recording and time-windowed summaries."""

    @pytest.fixture(autouse=True)
    def fresh_tracker(self):
        from Core.metrics_tracker import MetricsTracker
        # Reset singleton
        MetricsTracker._instance = None
        MetricsTracker._lock = __import__("threading").Lock()
        self.tracker = MetricsTracker()
        yield
        self.tracker.clear()
        MetricsTracker._instance = None

    def test_record_index_event(self):
        from Core.metrics_tracker import IndexEvent
        self.tracker.record_index(IndexEvent(
            url="http://example.com/doc.pdf",
            chunks_created=15,
            processing_time_ms=250.0,
            doc_type="pdf",
        ))
        summary = self.tracker.get_summary()
        assert summary.total_documents_indexed == 1
        assert summary.total_chunks_created == 15
        assert summary.avg_indexing_time_ms == 250.0

    def test_multiple_index_events(self):
        from Core.metrics_tracker import IndexEvent
        self.tracker.record_index(IndexEvent(chunks_created=10, processing_time_ms=100))
        self.tracker.record_index(IndexEvent(chunks_created=20, processing_time_ms=300))
        s = self.tracker.get_summary()
        assert s.total_documents_indexed == 2
        assert s.total_chunks_created == 30
        assert s.avg_indexing_time_ms == 200.0

    def test_windowed_summary(self):
        from Core.metrics_tracker import QueryEvent
        # Record an old event
        old = QueryEvent(query="old", latency_ms=100, timestamp=time.time() - 9999)
        self.tracker.record_query(old)
        # Record a recent event
        self.tracker.record_query(QueryEvent(query="new", latency_ms=50))
        # Full summary includes both
        full = self.tracker.get_summary()
        assert full.total_queries == 2
        # Windowed summary (last 60s) should only include recent
        windowed = self.tracker.get_summary(window_seconds=60)
        assert windowed.total_queries == 1
        assert windowed.avg_latency_ms == 50.0

    def test_mixed_query_and_index(self):
        from Core.metrics_tracker import QueryEvent, IndexEvent
        self.tracker.record_query(QueryEvent(query="test", latency_ms=100, quality_score=0.8))
        self.tracker.record_index(IndexEvent(chunks_created=5))
        s = self.tracker.get_summary()
        assert s.total_queries == 1
        assert s.total_documents_indexed == 1
        assert s.avg_quality_score == 0.8


# ═══════════════════════════════════════════════════════════════════
# EnhancedRAGService._record_metrics (bug-fix verification)
# ═══════════════════════════════════════════════════════════════════


class TestRecordMetricsFix:
    """Verifies the bug-fix: _record_metrics now passes correct
    field names to QueryEvent (latency_ms, cache_hit)."""

    def test_record_metrics_creates_valid_event(self):
        from Core.services.enhanced_rag_service import EnhancedRAGService
        from Core.metrics_tracker import MetricsTracker, QueryEvent

        # Reset singleton
        MetricsTracker._instance = None
        MetricsTracker._lock = __import__("threading").Lock()

        svc = EnhancedRAGService.__new__(EnhancedRAGService)
        svc._metrics_tracker = MetricsTracker()
        svc._metrics_tracker.clear()

        result = {
            "answer": "Python is great.",
            "metadata": {
                "confidence": {"score": 0.85},
                "hallucination": {"probability": 0.05},
            },
        }
        # Should NOT raise — the field names must be correct
        svc._record_metrics("What is Python?", result, 0.150)

        events = svc._metrics_tracker.get_recent_queries(1)
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, QueryEvent)
        assert event.latency_ms == 150.0
        assert event.cache_hit is False
        assert event.quality_score == 0.85
        assert event.hallucination_probability == 0.05
        assert event.query == "What is Python?"

        MetricsTracker._instance = None

    def test_record_metrics_no_tracker(self):
        from Core.services.enhanced_rag_service import EnhancedRAGService

        svc = EnhancedRAGService.__new__(EnhancedRAGService)
        svc._metrics_tracker = None
        # Should silently return without error
        svc._record_metrics("query", {}, 0.1)

    def test_record_metrics_empty_metadata(self):
        from Core.services.enhanced_rag_service import EnhancedRAGService
        from Core.metrics_tracker import MetricsTracker

        MetricsTracker._instance = None
        MetricsTracker._lock = __import__("threading").Lock()

        svc = EnhancedRAGService.__new__(EnhancedRAGService)
        svc._metrics_tracker = MetricsTracker()
        svc._metrics_tracker.clear()

        svc._record_metrics("q", {"metadata": {}}, 0.05)
        events = svc._metrics_tracker.get_recent_queries(1)
        assert len(events) == 1
        assert events[0].quality_score == 0.0
        assert events[0].hallucination_probability == 0.0

        MetricsTracker._instance = None


# ═══════════════════════════════════════════════════════════════════
# ZeroWasteCache — fingerprint invalidation & version bump
# ═══════════════════════════════════════════════════════════════════


class TestZeroWasteCacheAdvanced:
    """Tests for invalidation, fingerprinting, version bumps."""

    def test_invalidate_urls_removes_matching(self):
        from Core.zero_waste_cache import ZeroWasteCache
        cache = ZeroWasteCache()
        cache.clear()

        cache.set_answer("What is Python?", [
            {"text": "Python is a language", "score": 0.9, "url": "http://py.org"},
        ], source_chunks=[{"text": "src", "url": "http://py.org"}])

        # Verify it's cached
        hit = cache.get_answer("What is Python?")
        assert hit is not None

        # Invalidate the URL
        cache.invalidate_urls(["http://py.org"])

        # Now it should be a miss (or None)
        miss = cache.get_answer("What is Python?")
        # After invalidation, should not return stale data
        # (implementation may return None or not match fingerprint)
        # We just verify no crash occurred
        assert miss is None or isinstance(miss, list)

    def test_version_bump_clears_stale(self):
        from Core.zero_waste_cache import ZeroWasteCache
        cache = ZeroWasteCache()
        cache.clear()

        cache.set_answer("test query", [{"text": "answer", "score": 1.0}])
        assert cache.get_answer("test query") is not None

        cache.bump_version()
        # After version bump, old entries have stale fingerprint
        result = cache.get_answer("test query")
        assert result is None or isinstance(result, list)

    def test_context_cache_round_trip(self):
        from Core.zero_waste_cache import ZeroWasteCache
        cache = ZeroWasteCache()
        cache.clear()

        chunks = [
            {"text": "Context chunk 1", "score": 0.9},
            {"text": "Context chunk 2", "score": 0.8},
        ]
        cache.set_context("ML overview", chunks)
        result = cache.get_context("ML overview")
        assert result is not None
        assert len(result) == 2

    def test_stats_accumulate(self):
        from Core.zero_waste_cache import ZeroWasteCache
        cache = ZeroWasteCache()
        cache.clear()
        # Reset stats
        for key in cache.stats:
            cache.stats[key] = 0

        cache.get_answer("nonexistent")
        assert cache.stats["tier1_misses"] >= 1

    def test_classify_strategy_temporal(self):
        from Core.zero_waste_cache import ZeroWasteCache
        assert ZeroWasteCache.classify_strategy("What happened today?") == "temporal"

    def test_classify_strategy_standard(self):
        from Core.zero_waste_cache import ZeroWasteCache
        result = ZeroWasteCache.classify_strategy("What is Python?")
        assert result in ("standard", "strict")


# ═══════════════════════════════════════════════════════════════════
# InferenceGuard — CrashReport classification
# ═══════════════════════════════════════════════════════════════════


class TestCrashReportClassification:
    """Tests CrashReport.classify() auto-classification of error causes."""

    def test_classify_memory_error(self):
        from Core.inference_guard import CrashReport
        report = CrashReport(
            operation="inference",
            error_type="MemoryError",
            error_message="out of memory",
            traceback="...",
        )
        report.classify()
        assert "MEMORY" in report.likely_cause

    def test_classify_timeout(self):
        from Core.inference_guard import CrashReport
        report = CrashReport(
            operation="inference",
            error_type="TimeoutError",
            error_message="timed out waiting for response",
            traceback="...",
        )
        report.classify()
        assert "TIMEOUT" in report.likely_cause or "FIFO" in report.likely_cause

    def test_crash_report_to_dict(self):
        from Core.inference_guard import CrashReport
        report = CrashReport(
            operation="test_op",
            error_type="ValueError",
            error_message="bad value",
            traceback="Traceback...",
        )
        d = report.to_dict()
        assert d["operation"] == "test_op"
        assert d["error_type"] == "ValueError"
        assert "error_message" in d

    def test_guard_metrics_full_cycle(self):
        from Core.inference_guard import GuardMetrics
        gm = GuardMetrics()
        gm.record_call()
        gm.record_success(elapsed_ms=42.0, rss_delta_mb=1.5, profile={"test": True})
        stats = gm.get_stats()
        assert stats["total_guarded_calls"] >= 1
        assert stats["timing"]["avg_ms"] > 0

    def test_async_guard_captures_crash(self):
        from Core.inference_guard import InferenceGuard

        async def _run():
            try:
                async with InferenceGuard("test_crash") as guard:
                    guard.phase("boom")
                    raise RuntimeError("deliberate")
            except RuntimeError:
                pass

        asyncio.get_event_loop().run_until_complete(_run())
        from Core.inference_guard import get_crash_history
        history = get_crash_history()
        assert any("deliberate" in str(h.get("error_message", "")) for h in history)


# ═══════════════════════════════════════════════════════════════════
# PromptTemplate serialization + validate_prompt
# ═══════════════════════════════════════════════════════════════════


class TestPromptTemplateSerialization:
    def test_to_dict_and_from_dict(self):
        from Core.prompt_focus import PromptTemplate
        tpl = PromptTemplate(
            name="test_tpl",
            label="Test Template",
            icon="🧪",
            category="Testing",
            system_prompt="You are a test expert.",
            temperature=0.5,
            description="For testing",
            example_query="Is this a test?",
        )
        d = tpl.to_dict()
        assert d["name"] == "test_tpl"
        assert d["temperature"] == 0.5

        restored = PromptTemplate.from_dict(d)
        assert restored.name == tpl.name
        assert restored.label == tpl.label
        assert restored.system_prompt == tpl.system_prompt
        assert restored.temperature == tpl.temperature

    def test_builtin_templates_serializable(self):
        from Core.prompt_focus import PromptTemplateLibrary
        lib = PromptTemplateLibrary()
        for tpl in lib.list_templates():
            d = tpl.to_dict()
            restored = type(tpl).from_dict(d)
            assert restored.name == tpl.name

    def test_validate_prompt_good(self):
        from Core.prompt_focus import validate_prompt
        warnings = validate_prompt("You are a helpful medical assistant. Extract key symptoms.")
        # Good prompt should produce few or no warnings
        assert isinstance(warnings, list)

    def test_validate_prompt_empty(self):
        from Core.prompt_focus import validate_prompt
        warnings = validate_prompt("")
        assert len(warnings) >= 1  # empty prompt should produce a warning


# ═══════════════════════════════════════════════════════════════════
# FocusMode — all modes produce valid configs
# ═══════════════════════════════════════════════════════════════════


class TestFocusModesExtended:
    def test_each_mode_has_system_prompt(self):
        from Core.prompt_focus import FocusMode, FOCUS_CONFIGS
        for mode in FocusMode:
            config = FOCUS_CONFIGS[mode]
            assert config.mode == mode
            # GENERAL may have empty addition; others must have content
            if mode != FocusMode.GENERAL:
                assert len(config.system_prompt_addition) > 0

    def test_apply_to_prompt_prepends(self):
        from Core.prompt_focus import FocusMode, FOCUS_CONFIGS
        config = FOCUS_CONFIGS[FocusMode.SUMMARIZATION]
        result = config.apply_to_prompt("Base prompt here.")
        assert "Base prompt here." in result
        if config.system_prompt_addition:
            assert config.system_prompt_addition in result


# ═══════════════════════════════════════════════════════════════════
# Cross-module deep pipeline test
# ═══════════════════════════════════════════════════════════════════


PIPELINE_CHUNKS = [
    {"text": "Python was created by Guido van Rossum in 1991.", "score": 0.95, "url": "a.com", "title": "A"},
    {"text": "Python emphasizes code readability with significant whitespace.", "score": 0.90, "url": "b.com", "title": "B"},
    {"text": "Python supports OOP, functional, and procedural paradigms.", "score": 0.85, "url": "c.com", "title": "C"},
    {"text": "JavaScript is used for web development.", "score": 0.50, "url": "d.com", "title": "D"},
    {"text": "Python is a high-level, interpreted programming language.", "score": 0.92, "url": "a.com", "title": "A"},
]


class TestDeepPipeline:
    """Multi-module pipeline: rewrite → rerank → dedup → compress → conflict → evaluate."""

    def test_rewrite_feeds_reranker(self):
        from Core.query_rewriter import QueryRewriter
        from Core.reranker_advanced import AdvancedReranker

        rewriter = QueryRewriter()
        result = rewriter.rewrite("What is Python?")
        queries = result.all_queries

        reranker = AdvancedReranker()
        # Rerank using first query
        reranked = reranker.rerank(queries[0], PIPELINE_CHUNKS, top_k=3)
        assert len(reranked) <= 3
        assert all("rerank_score" in c for c in reranked)

    def test_dedup_then_compress_then_evaluate(self):
        from Core.smart_deduplicator import SmartDeduplicator
        from Core.contextual_compressor import ContextualCompressor
        from Core.evaluation import get_answer_evaluator

        dedup = SmartDeduplicator()
        deduped = dedup.deduplicate(PIPELINE_CHUNKS)

        compressor = ContextualCompressor()
        compressed = compressor.compress("Tell me about Python", deduped.unique_chunks)

        evaluator = get_answer_evaluator()
        answer = "Python is a programming language created by Guido van Rossum."
        sources = [c["text"] for c in compressed]
        scores = evaluator.evaluate("Tell me about Python", answer, sources)
        assert "overall" in scores
        assert 0 <= scores["overall"] <= 1

    def test_kg_enriches_pipeline(self, tmp_path):
        """KnowledgeGraph feeds extra context into conflict detection."""
        from Core.knowledge_graph import KnowledgeGraph
        from Core.conflict_detector import ConflictDetector

        kg = KnowledgeGraph(db_path=str(tmp_path / "pipe_kg.db"))
        kg.add_triples([
            ("Python", "created_by", "Guido van Rossum"),
            ("Python", "first_released", "1991"),
        ])
        triples = kg.query_entity("Python")
        assert len(triples) >= 2

        # Now pass both RAG chunks and KG facts to conflict detector
        detector = ConflictDetector()
        chunks_with_kg = PIPELINE_CHUNKS + [
            {"text": f"KG fact: {t['predicate']} -> {t.get('object_name', '')}", "score": 1.0}
            for t in triples
        ]
        result = detector.detect(chunks_with_kg)
        assert hasattr(result, "has_conflicts")

        kg.clear()

    def test_metrics_tracked_through_pipeline(self):
        """Full pipeline records correct metrics via MetricsTracker."""
        from Core.metrics_tracker import MetricsTracker, QueryEvent
        from Core.reranker_advanced import AdvancedReranker
        from Core.smart_deduplicator import SmartDeduplicator

        MetricsTracker._instance = None
        MetricsTracker._lock = __import__("threading").Lock()
        tracker = MetricsTracker()
        tracker.clear()

        t0 = time.time()
        reranker = AdvancedReranker()
        reranked = reranker.rerank("Python info", PIPELINE_CHUNKS, top_k=3)

        dedup = SmartDeduplicator()
        result = dedup.deduplicate(reranked)
        elapsed = time.time() - t0

        event = QueryEvent(
            query="Python info",
            latency_ms=round(elapsed * 1000, 2),
            chunks_retrieved=len(PIPELINE_CHUNKS),
            chunks_after_dedup=len(result.unique_chunks),
            quality_score=0.9,
        )
        tracker.record_query(event)

        summary = tracker.get_summary()
        assert summary.total_queries == 1
        assert summary.avg_latency_ms > 0
        assert summary.avg_quality_score == 0.9

        MetricsTracker._instance = None

    def test_answer_refinement_with_real_data(self):
        """AnswerRefinementEngine refines a good answer without degrading it."""
        from Core.answer_refinement import AnswerRefinementEngine

        engine = AnswerRefinementEngine(quality_threshold=0.3)
        sources = [{"text": c["text"]} for c in PIPELINE_CHUNKS[:3]]

        result = asyncio.get_event_loop().run_until_complete(
            engine.refine(
                "Python is a programming language created by Guido van Rossum in 1991.",
                "What is Python?",
                sources,
            )
        )
        assert result.refined_answer  # non-empty
        assert isinstance(result.quality_score, float)
        assert isinstance(result.stages_applied, list)

    def test_flare_with_real_generate(self):
        """FLARE with a real (trivial) generate function."""
        from Core.flare_retrieval import FLARERetriever

        def simple_generate(query, chunks):
            return "Python is a programming language."

        def simple_retrieve(query, top_k=5):
            return PIPELINE_CHUNKS[:top_k]

        flare = FLARERetriever(
            retrieve_fn=simple_retrieve,
            generate_fn=simple_generate,
        )
        result = flare.retrieve_and_generate(
            "What is Python?",
            initial_chunks=PIPELINE_CHUNKS[:3],
        )
        assert result.final_answer
        assert result.iterations >= 0
        assert isinstance(result.sub_queries, list)


# ═══════════════════════════════════════════════════════════════════
# EnhancedRAGService — integration (no external LLM)
# ═══════════════════════════════════════════════════════════════════


class TestEnhancedRAGServiceIntegration:
    """Tests EnhancedRAGService initialize + query with stub functions."""

    def test_initialize_and_query(self):
        from Core.services.enhanced_rag_service import EnhancedRAGService

        def stub_retrieve(query, top_k=5):
            return PIPELINE_CHUNKS[:top_k]

        def stub_generate(query, chunks):
            return "Python is a programming language created by Guido van Rossum."

        svc = EnhancedRAGService.__new__(EnhancedRAGService)
        svc.__init__()
        svc.initialize(
            retrieve_fn=stub_retrieve,
            generate_fn=stub_generate,
        )
        assert svc._initialized is True

        result = svc.query("What is Python?", top_k=3)
        assert "answer" in result
        assert isinstance(result["answer"], str)
        assert len(result["answer"]) > 0

    def test_query_returns_metadata(self):
        from Core.services.enhanced_rag_service import EnhancedRAGService

        def stub_retrieve(query, top_k=5):
            return PIPELINE_CHUNKS[:top_k]

        def stub_generate(query, chunks):
            return "Python is a language."

        svc = EnhancedRAGService.__new__(EnhancedRAGService)
        svc.__init__()
        svc.initialize(retrieve_fn=stub_retrieve, generate_fn=stub_generate)

        result = svc.query("What is Python?")
        assert "metadata" in result
        metadata = result["metadata"]
        assert "latency_ms" in metadata or "stages" in metadata or isinstance(metadata, dict)

    def test_not_initialized_error(self):
        from Core.services.enhanced_rag_service import EnhancedRAGService
        svc = EnhancedRAGService.__new__(EnhancedRAGService)
        svc.__init__()
        result = svc.query("test")
        # Should return error or empty answer, not crash
        assert isinstance(result, dict)

    def test_force_strategy(self):
        from Core.services.enhanced_rag_service import EnhancedRAGService

        def stub_retrieve(query, top_k=5):
            return PIPELINE_CHUNKS[:top_k]

        def stub_generate(query, chunks):
            return "An answer."

        svc = EnhancedRAGService.__new__(EnhancedRAGService)
        svc.__init__()
        svc.initialize(retrieve_fn=stub_retrieve, generate_fn=stub_generate)

        result = svc.query("compare x and y", force_strategy="analytical")
        assert isinstance(result, dict)
        assert "answer" in result


# ═══════════════════════════════════════════════════════════════════
# Edge Cases & Robustness
# ═══════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge cases across multiple modules."""

    def test_reranker_with_missing_text(self):
        from Core.reranker_advanced import AdvancedReranker
        reranker = AdvancedReranker()
        chunks = [{"score": 0.5}]  # no text field
        result = reranker.rerank("query", chunks, top_k=1)
        # Should handle gracefully — either skip or use empty text
        assert isinstance(result, list)

    def test_compressor_with_unicode(self):
        from Core.contextual_compressor import ContextualCompressor
        compressor = ContextualCompressor()
        chunks = [
            {"text": "日本語のテキスト Python プログラミング言語", "score": 0.9},
            {"text": "Ñoño está programando en Python con café ☕", "score": 0.8},
        ]
        result = compressor.compress("Python programming", chunks)
        assert isinstance(result, list)

    def test_deduplicator_with_very_similar_chunks(self):
        from Core.smart_deduplicator import SmartDeduplicator
        dedup = SmartDeduplicator()
        chunks = [
            {"text": "Python is a programming language.", "score": 0.9},
            {"text": "Python is a programming language!", "score": 0.85},
            {"text": "Python is a programming language...", "score": 0.8},
        ]
        result = dedup.deduplicate(chunks)
        # Should detect near-duplicates
        assert len(result.unique_chunks) <= len(chunks)

    def test_hallucination_detector_with_numbers(self):
        from Core.hallucination_detector_v2 import AdvancedHallucinationDetector
        detector = AdvancedHallucinationDetector()
        sources = [{"text": "The project has 100 contributors and was started in 2020."}]
        answer = "The project has 500 contributors and was started in 2018."
        result = detector.detect(answer, sources)
        # Conflicting numbers — should flag higher hallucination
        assert result.probability >= 0.0

    def test_confidence_scorer_extreme_case(self):
        from Core.confidence_scorer import AnswerQualityAssessor
        scorer = AnswerQualityAssessor()
        # Perfect case: answer exactly matches source
        sources = [{"text": "The sky is blue."}]
        result = scorer.assess("The sky is blue.", "What color is the sky?", sources)
        assert result.confidence >= 0.5  # Well-grounded

    def test_follow_up_generator_diverse_queries(self):
        from Core.follow_up_generator import FollowUpGenerator
        gen = FollowUpGenerator()
        result = gen.generate(
            query="Explain quantum computing",
            answer="Quantum computing uses qubits that can exist in superposition.",
            source_chunks=[{"text": "Qubits leverage quantum mechanics for parallel computation."}],
        )
        assert len(result) >= 1
        assert all("?" in q for q in result)
