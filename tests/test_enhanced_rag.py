"""
Tests for industry-best RAG enhancements.

Tests cover:
  - Contextual Retrieval (Anthropic-style)
  - HyDE (Hypothetical Document Embeddings)
  - Corrective RAG (CRAG)
  - Query Router / Intent Classifier
  - Parent Document Retrieval
  - Graph RAG (Community Detection)
  - Enhanced RAG Service (pipeline orchestration)
"""

import pytest
from unittest.mock import MagicMock, patch


# ═══════════════════════════════════════════════════════════════════
# Contextual Retrieval
# ═══════════════════════════════════════════════════════════════════

class TestContextualRetrieval:
    """Tests for Anthropic-style contextual chunk enrichment."""

    def test_contextualize_chunks_with_llm(self):
        from Core.contextual_retrieval import ContextualRetrieval

        mock_llm = MagicMock(return_value="This chunk discusses neural network architectures from a ML textbook.")
        cr = ContextualRetrieval(llm_fn=mock_llm)

        chunks = [
            {"text": "Transformers use self-attention mechanisms to process sequences in parallel."},
            {"text": "The learning rate should be tuned carefully for optimal convergence."},
        ]
        results = cr.contextualize_chunks(chunks, "Full ML textbook content...", "ML Textbook")

        assert len(results) == 2
        assert results[0].context_prefix != ""
        assert "Transformers" in results[0].contextualized_text
        assert results[0].document_title == "ML Textbook"

    def test_contextualize_chunks_without_llm(self):
        from Core.contextual_retrieval import ContextualRetrieval

        cr = ContextualRetrieval(llm_fn=None)
        chunks = [{"text": "Some content here."}]
        results = cr.contextualize_chunks(chunks, "Doc text", "My Document")

        assert len(results) == 1
        assert "My Document" in results[0].context_prefix
        assert "Some content here." in results[0].contextualized_text

    def test_contextualize_empty_chunks(self):
        from Core.contextual_retrieval import ContextualRetrieval

        cr = ContextualRetrieval()
        assert cr.contextualize_chunks([], "doc text") == []

    def test_caching(self):
        from Core.contextual_retrieval import ContextualRetrieval

        call_count = 0
        def counting_llm(prompt):
            nonlocal call_count
            call_count += 1
            return "Context about the chunk."

        cr = ContextualRetrieval(llm_fn=counting_llm, enable_caching=True)
        chunks = [{"text": "Test content alpha."}]

        # First call
        cr.contextualize_chunks(chunks, "doc", "title")
        first_count = call_count

        # Second call (same chunk) should use cache
        cr.contextualize_chunks(chunks, "doc", "title")
        assert call_count == first_count  # No additional LLM call

    def test_heuristic_context_positions(self):
        from Core.contextual_retrieval import ContextualRetrieval

        cr = ContextualRetrieval(llm_fn=None)
        chunks = [{"text": f"Chunk {i}"} for i in range(10)]
        results = cr.contextualize_chunks(chunks, "doc", "Title")

        assert "beginning" in results[0].context_prefix
        assert "end" in results[9].context_prefix
        assert "middle" in results[5].context_prefix


# ═══════════════════════════════════════════════════════════════════
# HyDE Retrieval
# ═══════════════════════════════════════════════════════════════════

class TestHyDERetrieval:
    """Tests for Hypothetical Document Embeddings."""

    def test_retrieve_with_hyde(self):
        from Core.hyde_retrieval import HyDERetriever

        mock_llm = MagicMock(return_value="Aurora borealis is caused by charged solar particles.")
        mock_embed = MagicMock(return_value=[0.1, 0.2, 0.3])
        mock_search = MagicMock(return_value=[
            {"text": "Solar wind particles cause auroras", "score": 0.9},
            {"text": "Northern lights are visible at high latitudes", "score": 0.8},
        ])

        hyde = HyDERetriever(
            llm_fn=mock_llm,
            embed_fn=mock_embed,
            search_fn=mock_search,
        )
        result = hyde.retrieve("What causes aurora borealis?")

        assert result.strategy_used == "hyde"
        assert not result.fallback_used
        assert len(result.search_results) == 2
        assert "Aurora" in result.hypothetical_document or "aurora" in result.hypothetical_document

    def test_retrieve_fallback_no_llm(self):
        from Core.hyde_retrieval import HyDERetriever

        hyde = HyDERetriever(llm_fn=None)
        result = hyde.retrieve("test query")
        assert result.fallback_used

    def test_fusion_with_standard_results(self):
        from Core.hyde_retrieval import HyDERetriever

        mock_llm = MagicMock(return_value="Hypothetical answer about topic X.")
        mock_embed = MagicMock(return_value=[0.1, 0.2])
        mock_search = MagicMock(return_value=[
            {"text": "HyDE result about X", "score": 0.85},
        ])

        hyde = HyDERetriever(llm_fn=mock_llm, embed_fn=mock_embed, search_fn=mock_search)
        standard = [
            {"text": "Standard result about X", "score": 0.9},
            {"text": "Another standard result", "score": 0.7},
        ]

        fused = hyde.retrieve_with_fusion("query about X", standard, top_k=5)
        assert len(fused) >= 2
        # Verify fusion scores are present
        assert all("fusion_score" in r for r in fused)

    def test_classify_query_type(self):
        from Core.hyde_retrieval import HyDERetriever

        assert HyDERetriever.classify_query_type("how to implement binary search") == "technical"
        assert HyDERetriever.classify_query_type("why is the sky blue") == "analytical"
        assert HyDERetriever.classify_query_type("what is the capital of France") == "factual"


# ═══════════════════════════════════════════════════════════════════
# Corrective RAG (CRAG)
# ═══════════════════════════════════════════════════════════════════

class TestCorrectiveRAG:
    """Tests for self-healing retrieval with quality grading."""

    def test_correct_grade(self):
        from Core.corrective_rag import CorrectiveRAG, RetrievalGrade

        mock_generate = MagicMock(return_value="Python is a programming language.")
        crag = CorrectiveRAG(generate_fn=mock_generate)

        chunks = [
            {"text": "Python is a high-level programming language known for its simplicity.", "score": 0.9},
            {"text": "Python supports multiple paradigms including OOP.", "score": 0.85},
        ]
        result = crag.retrieve_and_generate("What is Python?", initial_chunks=chunks)

        assert result.answer != ""
        assert result.grade in (RetrievalGrade.CORRECT, RetrievalGrade.AMBIGUOUS)

    def test_incorrect_grade_triggers_correction(self):
        from Core.corrective_rag import CorrectiveRAG, RetrievalGrade

        mock_retrieve = MagicMock(return_value=[
            {"text": "Relevant answer about quantum computing", "score": 0.8},
        ])
        mock_generate = MagicMock(return_value="Answer about quantum computing.")

        crag = CorrectiveRAG(
            retrieve_fn=mock_retrieve,
            generate_fn=mock_generate,
        )

        # Chunks with no keyword overlap (should grade as incorrect/ambiguous)
        chunks = [
            {"text": "The weather today is sunny and warm", "score": 0.2},
        ]
        result = crag.retrieve_and_generate(
            "Explain quantum computing", initial_chunks=chunks,
        )

        assert result.answer != ""
        assert len(result.corrections_applied) > 0

    def test_empty_chunks(self):
        from Core.corrective_rag import CorrectiveRAG, RetrievalGrade

        mock_generate = MagicMock(return_value="Fallback answer.")
        crag = CorrectiveRAG(generate_fn=mock_generate)

        result = crag.retrieve_and_generate("test query", initial_chunks=[])
        assert result.grade == RetrievalGrade.INCORRECT

    def test_decompose_query(self):
        from Core.corrective_rag import CorrectiveRAG

        crag = CorrectiveRAG()
        # "and" decomposition
        subs = crag._decompose_query("Explain machine learning and deep learning")
        assert len(subs) >= 2


# ═══════════════════════════════════════════════════════════════════
# Query Router
# ═══════════════════════════════════════════════════════════════════

class TestQueryRouter:
    """Tests for adaptive intent-based pipeline routing."""

    def test_route_simple_query(self):
        from Core.query_router import QueryRouter, QueryIntent

        router = QueryRouter()
        decision = router.route("What is machine learning?")
        assert decision.intent == QueryIntent.SIMPLE
        assert not decision.use_hyde
        assert not decision.use_flare

    def test_route_analytical_query(self):
        from Core.query_router import QueryRouter, QueryIntent

        router = QueryRouter()
        decision = router.route("Compare Python and JavaScript for machine learning applications")
        assert decision.intent in (QueryIntent.ANALYTICAL, QueryIntent.SIMPLE)
        # Analytical queries should get more elaborate pipeline
        if decision.intent == QueryIntent.ANALYTICAL:
            assert decision.use_hyde

    def test_route_multi_hop_query(self):
        from Core.query_router import QueryRouter, QueryIntent

        router = QueryRouter()
        decision = router.route("What is the relationship between climate change and ocean acidification?")
        assert decision.intent in (QueryIntent.MULTI_HOP, QueryIntent.ANALYTICAL, QueryIntent.SIMPLE)

    def test_route_aggregate_query(self):
        from Core.query_router import QueryRouter, QueryIntent

        router = QueryRouter()
        decision = router.route("Summarize the main themes in this document")
        assert decision.intent == QueryIntent.AGGREGATE

    def test_route_temporal_query(self):
        from Core.query_router import QueryRouter, QueryIntent

        router = QueryRouter()
        decision = router.route("What happened in the latest 2024 election results?")
        assert decision.intent == QueryIntent.TEMPORAL

    def test_route_conversational_query(self):
        from Core.query_router import QueryRouter, QueryIntent

        router = QueryRouter()
        decision = router.route("Hi, hello there")
        assert decision.intent == QueryIntent.CONVERSATIONAL

    def test_route_empty_query(self):
        from Core.query_router import QueryRouter, QueryIntent

        router = QueryRouter()
        decision = router.route("")
        assert decision.intent == QueryIntent.CONVERSATIONAL

    def test_pipeline_config_per_intent(self):
        from Core.query_router import QueryRouter, QueryIntent

        config = QueryRouter.get_pipeline_for_intent(QueryIntent.ANALYTICAL)
        assert "pipeline" in config
        assert config["use_hyde"] is True

    def test_routing_confidence(self):
        from Core.query_router import QueryRouter

        router = QueryRouter()
        decision = router.route("What is the capital of France?")
        assert 0.0 <= decision.confidence <= 1.0


# ═══════════════════════════════════════════════════════════════════
# Parent Document Retrieval
# ═══════════════════════════════════════════════════════════════════

class TestParentDocumentRetrieval:
    """Tests for hierarchical small-to-big retrieval."""

    def test_create_hierarchy(self):
        from Core.parent_document_retrieval import ParentDocumentRetriever

        pdr = ParentDocumentRetriever(parent_size=200, child_size=50, child_overlap=10)
        text = "A" * 500  # 500 chars

        parents, children = pdr.create_hierarchy(text, {"url": "test.pdf"})

        assert len(parents) >= 2
        assert len(children) > len(parents)
        assert all("parent_id" in c for c in children)

    def test_expand_to_parents(self):
        from Core.parent_document_retrieval import ParentDocumentRetriever

        pdr = ParentDocumentRetriever(parent_size=200, child_size=50)
        text = "Section one content here. " * 20 + "Section two content here. " * 20

        parents, children = pdr.create_hierarchy(text)

        # Simulate matching 2 children from same parent
        if len(children) >= 2:
            matched = [children[0], children[1]]
        else:
            matched = children[:1]
        result = pdr.expand_to_parents(matched)

        assert len(result.parent_chunks) >= 1
        assert result.total_parent_chars > 0

    def test_get_parent_context(self):
        from Core.parent_document_retrieval import ParentDocumentRetriever

        pdr = ParentDocumentRetriever(parent_size=100, child_size=30)
        text = "Alpha beta gamma. " * 10 + "Delta epsilon zeta. " * 10

        parents, children = pdr.create_hierarchy(text)

        # Simulate search results with parent_id
        search_results = [
            {**children[0], "score": 0.9},
            {**children[2], "score": 0.7},
        ]

        expanded = pdr.get_parent_context(search_results)
        # Should have expanded to parent text
        assert len(expanded) >= 1
        assert any(r.get("_expanded_from_child") for r in expanded)

    def test_empty_text(self):
        from Core.parent_document_retrieval import ParentDocumentRetriever

        pdr = ParentDocumentRetriever()
        parents, children = pdr.create_hierarchy("")
        assert parents == []
        assert children == []

    def test_clear_store(self):
        from Core.parent_document_retrieval import ParentDocumentRetriever

        pdr = ParentDocumentRetriever(parent_size=100, child_size=30)
        pdr.create_hierarchy("Some text content for testing.")
        assert len(pdr._parent_store) > 0
        pdr.clear()
        assert len(pdr._parent_store) == 0


# ═══════════════════════════════════════════════════════════════════
# Graph RAG
# ═══════════════════════════════════════════════════════════════════

class TestGraphRAG:
    """Tests for community detection and global Q&A."""

    @pytest.fixture
    def kg_with_data(self, tmp_path):
        from Core.knowledge_graph import KnowledgeGraph

        db_path = str(tmp_path / "test_kg.db")
        kg = KnowledgeGraph(db_path=db_path)

        # Build a small graph with two communities
        # Community 1: ML/AI
        kg.add_triples([
            ("Machine Learning", "is_part_of", "Artificial Intelligence"),
            ("Deep Learning", "is_part_of", "Machine Learning"),
            ("Neural Networks", "used_in", "Deep Learning"),
            ("Transformers", "is_type_of", "Neural Networks"),
        ], source_url="ml_doc.pdf")

        # Community 2: Web Dev
        kg.add_triples([
            ("JavaScript", "used_in", "Web Development"),
            ("React", "is_framework_for", "JavaScript"),
            ("HTML", "used_with", "JavaScript"),
        ], source_url="web_doc.pdf")

        return kg

    def test_build_communities(self, kg_with_data):
        from Core.graph_rag import GraphRAG

        graph_rag = GraphRAG(
            knowledge_graph=kg_with_data,
            min_community_size=2,
        )
        communities = graph_rag.build_communities()

        assert len(communities) >= 1
        # At least one community should have entities
        assert any(c.size >= 2 for c in communities)

    def test_global_query(self, kg_with_data):
        from Core.graph_rag import GraphRAG

        mock_llm = MagicMock(return_value="The dataset covers AI/ML and Web Development topics.")
        graph_rag = GraphRAG(
            knowledge_graph=kg_with_data,
            llm_fn=mock_llm,
            min_community_size=2,
        )
        graph_rag.build_communities()

        result = graph_rag.query("What are the main themes?", strategy="global")
        assert result.strategy == "global"

    def test_local_query(self, kg_with_data):
        from Core.graph_rag import GraphRAG

        graph_rag = GraphRAG(knowledge_graph=kg_with_data, min_community_size=2)
        graph_rag.build_communities()

        result = graph_rag.query("How does Machine Learning relate to Deep Learning?", strategy="local")
        assert result.strategy == "local"

    def test_auto_strategy_detection(self):
        from Core.graph_rag import GraphRAG

        assert GraphRAG._detect_strategy("What are the main themes?") == "global"
        assert GraphRAG._detect_strategy("How does X work?") == "local"
        assert GraphRAG._detect_strategy("Summarize the key topics") == "global"

    def test_empty_graph(self):
        from Core.graph_rag import GraphRAG

        graph_rag = GraphRAG(knowledge_graph=None)
        communities = graph_rag.build_communities()
        assert communities == []

    def test_extract_query_entities(self):
        from Core.graph_rag import GraphRAG

        entities = GraphRAG._extract_query_entities("How does Machine Learning relate to Deep Learning?")
        assert "Machine Learning" in entities or "Deep Learning" in entities


# ═══════════════════════════════════════════════════════════════════
# Enhanced RAG Service (Integration)
# ═══════════════════════════════════════════════════════════════════

class TestEnhancedRAGService:
    """Tests for the orchestrated pipeline."""

    def test_initialize(self):
        from Core.services.enhanced_rag_service import EnhancedRAGService

        service = EnhancedRAGService()
        service.initialize(
            retrieve_fn=lambda q, k: [],
            generate_fn=lambda q, c: "answer",
            llm_fn=lambda p: "response",
        )
        assert service._initialized

    def test_simple_query_routing(self):
        from Core.services.enhanced_rag_service import EnhancedRAGService

        mock_retrieve = MagicMock(return_value=[
            {"text": "Python is a programming language", "score": 0.9, "url": "doc.pdf"},
        ])
        mock_generate = MagicMock(return_value="Python is a versatile programming language.")

        service = EnhancedRAGService()
        service.initialize(
            retrieve_fn=mock_retrieve,
            generate_fn=mock_generate,
            llm_fn=lambda p: "response",
        )

        result = service.query("What is Python?")
        assert "answer" in result
        assert "metadata" in result
        assert result["metadata"]["latency_ms"] >= 0

    def test_force_strategy(self):
        from Core.services.enhanced_rag_service import EnhancedRAGService

        service = EnhancedRAGService()
        service.initialize(
            retrieve_fn=lambda q, k: [{"text": "chunk", "score": 0.9}],
            generate_fn=lambda q, c: "answer",
        )

        result = service.query("test", force_strategy="simple")
        assert result["metadata"]["routing"]["intent"] == "simple"

    def test_not_initialized_returns_error(self):
        from Core.services.enhanced_rag_service import EnhancedRAGService

        service = EnhancedRAGService()
        result = service.query("test")
        assert result["metadata"]["error"] == "not_initialized"

    def test_pipeline_stages_tracked(self):
        from Core.services.enhanced_rag_service import EnhancedRAGService

        service = EnhancedRAGService()
        service.initialize(
            retrieve_fn=lambda q, k: [{"text": "data", "score": 0.8}],
            generate_fn=lambda q, c: "result",
        )

        result = service.query("What is X?", force_strategy="simple")
        assert "stages" in result["metadata"]
        assert len(result["metadata"]["stages"]) > 0
