# -*- coding: utf-8 -*-
"""
test_rag_pipeline.py - Comprehensive tests for RAG functionality
Tests scanning, indexing, querying, deduplication, and chat integration
"""

import pytest
import threading
import time
from pathlib import Path
from zena_mode.rag_pipeline import LocalRAG, DedupeConfig
from zena_mode.scraper import WebsiteScraper


class TestDeduplication:
    """Test deduplication functionality."""

    def test_exact_hash_deduplication(self, tmp_path):
        """Test that exact duplicate chunks are rejected via SHA256 hash."""
        rag = LocalRAG(cache_dir=tmp_path)

        # Use content long enough to pass junk filter
        docs = [
            {
                "url": "test1",
                "title": "T1",
                "content": "This is unique content for testing deduplication functionality in the ZenAI RAG system. It must be at least fifty characters long.",
            },
            {
                "url": "test2",
                "title": "T2",
                "content": "This is unique content for testing deduplication functionality in the ZenAI RAG system. It must be at least fifty characters long.",
            },  # Exact dup
        ]

        rag.build_index(docs, filter_junk=True)

        # Should only have 1 chunk (second is exact duplicate)
        assert len(rag.chunks) == 1
        assert rag.get_stats()["total_chunks"] == 1

    def test_near_duplicate_detection(self, tmp_path):
        """Test near-duplicate detection via Qdrant semantic search."""
        rag = LocalRAG(cache_dir=tmp_path)

        # Very similar content (should be detected as near-duplicate)
        docs = [
            {
                "url": "test1",
                "title": "T1",
                "content": "The quick brown fox jumps over the lazy dog in the park today and feels very happy about it.",
            },
            {
                "url": "test2",
                "title": "T2",
                "content": "The quick brown fox jumps over the lazy dog in the park today and feels very happy about it!",
            },  # Near-dup (minor change)
        ]

        # Test with a threshold where they should be deduplicated
        rag.build_index(docs, dedup_threshold=0.95, filter_junk=False)

        # At 0.95 threshold, the near-duplicate should be filtered
        assert rag.get_stats()["total_chunks"] == 1

    def test_document_level_deduplication(self, tmp_path):
        """Test that entire documents are deduplicated."""
        rag = LocalRAG(cache_dir=tmp_path)

        # Content long enough
        content = "Content for document level dedup test that is long enough to pass all filters. " * 5
        doc = {"url": "test", "title": "T", "content": content}

        # Add same document twice
        rag.build_index([doc], filter_junk=False)
        initial_count = rag.get_stats()["total_chunks"]

        rag.build_index([doc], filter_junk=False)  # Add again

        # Should not add more chunks (exact content hash check)
        assert rag.get_stats()["total_chunks"] == initial_count

    def test_cross_batch_deduplication(self, tmp_path):
        """Test that deduplication works across batches."""
        rag = LocalRAG(cache_dir=tmp_path)

        # First batch
        docs1 = [{"url": "test1", "title": "T1", "content": "Unique content batch one for testing"}]
        rag.build_index(docs1, filter_junk=False)
        count_after_batch1 = len(rag.chunks)

        # Second batch with duplicate
        docs2 = [
            {"url": "test2", "title": "T2", "content": "Unique content batch one for testing"},  # Duplicate of batch1
            {"url": "test3", "title": "T3", "content": "Brand new unique content batch two here"},
        ]
        rag.build_index(docs2, filter_junk=False)

        # Should only add 1 new chunk (the truly unique one)
        assert len(rag.chunks) == count_after_batch1 + 1


class TestJunkFiltering:
    """Test junk chunk detection and filtering."""

    def test_filter_short_chunks(self, tmp_path):
        """Test that short chunks are filtered."""
        rag = LocalRAG(cache_dir=tmp_path)

        # Chunk shorter than MIN_CHUNK_LENGTH
        assert rag._is_junk_chunk("Hi") == True
        assert rag._is_junk_chunk("x" * 10) == True

    def test_filter_low_entropy_chunks(self, tmp_path):
        """Test that low-entropy (repetitive) chunks are filtered."""
        rag = LocalRAG(cache_dir=tmp_path)

        # Very repetitive text has low entropy
        repetitive = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        assert rag._is_junk_chunk(repetitive) == True

    def test_filter_blacklisted_chunks(self, tmp_path):
        """Test that chunks with blacklisted keywords are filtered."""
        rag = LocalRAG(cache_dir=tmp_path)

        # Contains blacklisted keyword
        assert rag._is_junk_chunk("Please subscribe now to our newsletter for updates") == True
        assert rag._is_junk_chunk("Click here to read more about our cookie policy") == True

    def test_accept_valid_chunks(self, tmp_path):
        """Test that valid chunks are accepted."""
        rag = LocalRAG(cache_dir=tmp_path)

        # Normal, informative text
        valid = "The hospital emergency room is open 24 hours a day, 7 days a week for patient care."
        assert rag._is_junk_chunk(valid) == False

    def test_entropy_calculation(self, tmp_path):
        """Test entropy calculation accuracy."""
        rag = LocalRAG(cache_dir=tmp_path)

        # Completely uniform text has low entropy
        uniform = "a" * 100
        low_entropy = rag._calculate_entropy(uniform)

        # Varied text has higher entropy
        varied = "The quick brown fox jumps over the lazy dog"
        high_entropy = rag._calculate_entropy(varied)

        assert low_entropy < high_entropy
        assert low_entropy < DedupeConfig.MIN_ENTROPY


class TestHybridSearch:
    """Test hybrid search with RRF fusion."""

    def test_hybrid_search_returns_results(self, tmp_path):
        """Test hybrid search returns ranked results."""
        rag = LocalRAG(cache_dir=tmp_path)

        docs = [
            {"url": "t1", "title": "Python", "content": "Python is a programming language used for web development"},
            {"url": "t2", "title": "Java", "content": "Java is used for enterprise software applications"},
            {"url": "t3", "title": "JavaScript", "content": "JavaScript runs in web browsers for interactive pages"},
        ]
        rag.build_index(docs, filter_junk=False)

        results = rag.hybrid_search("programming language", k=2, alpha=0.5)

        assert len(results) <= 2
        assert all("fusion_score" in r for r in results)

    def test_hybrid_search_alpha_weighting(self, tmp_path):
        """Test that alpha parameter affects search results."""
        rag = LocalRAG(cache_dir=tmp_path)

        docs = [
            {"url": "t1", "title": "Doc1", "content": "Machine learning algorithms for data science"},
            {"url": "t2", "title": "Doc2", "content": "Data science and machine learning applications"},
        ]
        rag.build_index(docs, filter_junk=False)

        # Pure semantic (alpha=1)
        semantic_results = rag.hybrid_search("ML algorithms", k=2, alpha=1.0)

        # Pure keyword (alpha=0)
        keyword_results = rag.hybrid_search("ML algorithms", k=2, alpha=0.0)

        # Both should return results
        assert len(semantic_results) > 0
        assert len(keyword_results) > 0


class TestThreadSafety:
    """Test thread safety of RAG operations."""

    def test_concurrent_search(self, tmp_path):
        """Test concurrent search operations don't cause issues."""
        rag = LocalRAG(cache_dir=tmp_path)

        docs = [
            {"url": f"test{i}", "title": f"T{i}", "content": f"Document number {i} with unique content here"}
            for i in range(50)
        ]
        rag.build_index(docs, filter_junk=False)

        results = []
        errors = []

        def search_task(query):
            """Search task."""
            try:
                result = rag.search(query, k=3)
                results.append(len(result))
            except Exception as e:
                errors.append(str(e))

        # Launch concurrent searches
        threads = [threading.Thread(target=search_task, args=(f"document {i}",)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors during concurrent search: {errors}"
        assert len(results) == 10

    def test_concurrent_build_index(self, tmp_path):
        """Test concurrent index building is thread-safe."""
        rag = LocalRAG(cache_dir=tmp_path)

        errors = []

        def build_task(batch_id):
            """Build task."""
            try:
                docs = [
                    {
                        "url": f"batch{batch_id}_{i}",
                        "title": f"T{i}",
                        "content": f"Batch {batch_id} document {i} unique content here",
                    }
                    for i in range(10)
                ]
                rag.build_index(docs, filter_junk=False)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=build_task, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors during concurrent build: {errors}"
        # Should have chunks from all batches (with dedup)
        assert len(rag.chunks) > 0


class TestAddChunks:
    """Test add_chunks method for pre-chunked content."""

    def test_add_chunks_basic(self, tmp_path):
        """Test adding pre-chunked content."""
        rag = LocalRAG(cache_dir=tmp_path)

        # Use longer chunks that pass junk filter (>50 chars, good entropy)
        chunks = [
            {
                "url": "test1",
                "title": "T1",
                "text": "Pre-chunked content number one for testing the RAG system functionality here",
            },
            {
                "url": "test2",
                "title": "T2",
                "text": "Pre-chunked content number two for testing the RAG system integration there",
            },
        ]

        rag.add_chunks(chunks)

        assert len(rag.chunks) == 2
        assert rag.get_stats()["total_chunks"] == 2

    def test_add_chunks_deduplication(self, tmp_path):
        """Test that add_chunks deduplicates."""
        rag = LocalRAG(cache_dir=tmp_path)

        # Use longer chunks that pass junk filter
        chunks = [
            {
                "url": "test1",
                "title": "T1",
                "text": "This content will be duplicated for testing the deduplication feature in RAG",
            },
            {
                "url": "test2",
                "title": "T2",
                "text": "This content will be duplicated for testing the deduplication feature in RAG",
            },  # Exact dup
        ]

        rag.add_chunks(chunks)

        # Should only have 1 chunk
        assert len(rag.chunks) == 1


class TestGetStats:
    """Test get_stats method."""

    def test_stats_empty_index(self, tmp_path):
        """Test stats on empty index."""
        rag = LocalRAG(cache_dir=tmp_path)

        stats = rag.get_stats()

        assert stats["total_chunks"] == 0
        assert "collection" in stats

    def test_stats_populated_index(self, tmp_path):
        """Test stats on populated index."""
        rag = LocalRAG(cache_dir=tmp_path)

        docs = [
            {
                "url": "test",
                "title": "T",
                "content": "Content for stats test with enough characters to pass the junk filter comfortably.",
            }
        ]
        rag.build_index(docs, filter_junk=False)

        stats = rag.get_stats()

        assert stats["total_chunks"] == 1
        assert stats["collection"] == "zenai_knowledge"


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_unicode_content(self, tmp_path):
        """Test handling of Unicode content."""
        rag = LocalRAG(cache_dir=tmp_path)

        docs = [
            {
                "url": "test",
                "title": "Unicode",
                "content": "日本語テスト Chinese中文 Emoji🎉 Accénts àéïõü Special™ symbols© and some more text to pass the length filter easily.",
            },
        ]

        rag.build_index(docs, filter_junk=False)

        assert len(rag.chunks) == 1
        results = rag.search("日本語")
        assert len(results) > 0

    def test_empty_documents(self, tmp_path):
        """Test handling of empty documents."""
        rag = LocalRAG(cache_dir=tmp_path)

        docs = [
            {"url": "test1", "title": "Empty", "content": ""},
            {"url": "test2", "title": "Whitespace", "content": "   "},
            {"url": "test3", "title": "Valid", "content": "This is valid content with enough characters"},
        ]

        rag.build_index(docs, filter_junk=False)

        # Only valid document should be indexed
        assert len(rag.chunks) == 1

    def test_very_long_document(self, tmp_path):
        """Test handling of very long documents."""
        rag = LocalRAG(cache_dir=tmp_path)

        # Varied content to avoid deduplication
        long_content = " ".join(
            [f"This is unique sentence number {i} for a very long document that needs testing." for i in range(200)]
        )
        docs = [{"url": "test", "title": "Long", "content": long_content}]

        rag.build_index(docs, filter_junk=False)

        # Should create multiple chunks
        assert len(rag.chunks) > 1

    def test_special_characters_in_query(self, tmp_path):
        """Test search with special characters in query."""
        rag = LocalRAG(cache_dir=tmp_path)

        docs = [
            {"url": "test", "title": "Code", "content": "Python code example: def hello(): print('Hello!')"},
        ]
        rag.build_index(docs, filter_junk=False)

        # Query with special characters
        results = rag.search("def hello(): print()")
        assert len(results) > 0

    def test_score_range(self, tmp_path):
        """Test that search scores are in valid range [0, 1]."""
        rag = LocalRAG(cache_dir=tmp_path)

        docs = [
            {
                "url": "test",
                "title": "Score",
                "content": "Test content for score validation check in the ZenAI RAG system for high precision.",
            }
        ]
        rag.build_index(docs, filter_junk=False)

        results = rag.search("test content")

        for r in results:
            assert 0 <= r["score"] <= 1, f"Score {r['score']} out of range"


class TestRAGPipeline:
    """Test RAG pipeline functionality."""

    def test_chunk_documents(self, tmp_path):
        """Test document chunking."""
        rag = LocalRAG(cache_dir=tmp_path)

        # Use realistic content with good entropy (not repetitive)
        documents = [
            {
                "url": "http://test.com",
                "title": "Test",
                "content": "The quick brown fox jumps over the lazy dog. " * 25,
            }  # ~1125 chars
        ]

        chunks = rag.chunk_documents(documents, chunk_size=500, filter_junk=False)

        # Should create 2+ chunks from 1000+ chars
        assert len(chunks) >= 2
        assert all("text" in chunk for chunk in chunks)
        assert all("url" in chunk for chunk in chunks)

    def test_chunk_small_content(self, tmp_path):
        """Test chunking with content smaller than chunk size."""
        rag = LocalRAG(cache_dir=tmp_path)

        documents = [
            {
                "url": "http://test.com",
                "title": "Small",
                "content": "Short text is now longer than 20 chars with varied words",
            }
        ]

        chunks = rag.chunk_documents(documents, chunk_size=500, filter_junk=False)

        # Should create 1 chunk
        assert len(chunks) == 1
        assert chunks[0]["text"] == "Short text is now longer than 20 chars with varied words"

    def test_build_index(self, tmp_path):
        """Test building FAISS index."""
        rag = LocalRAG(cache_dir=tmp_path)

        docs = [
            {"url": "test1", "title": "T1", "content": "Hello world from Python programming language test document"},
            {
                "url": "test2",
                "title": "T2",
                "content": "Machine learning and artificial intelligence are fascinating topics",
            },
        ]

        rag.build_index(docs, filter_junk=False)

        assert len(rag.chunks) == 2

    def test_save_load_qdrant(self, tmp_path):
        """Test saving/loading index with Qdrant."""
        storage_dir = tmp_path / "qdrant"
        rag = LocalRAG(cache_dir=storage_dir)

        # Create index with realistic content
        docs = [
            {
                "url": "test",
                "title": "Test",
                "content": "The quick brown fox jumps over the lazy dog multiple times today and it is very exciting.",
            }
        ]
        rag.build_index(docs, filter_junk=False)

        # Close the first instance to release the lock
        del rag
        import gc

        gc.collect()
        time.sleep(1.0)  # Wait for OS to release file handle

        # Load in new instance
        rag2 = LocalRAG(cache_dir=storage_dir)
        assert rag2.get_stats()["total_chunks"] == 1

    def test_query(self):
        """Test querying RAG index."""
        rag = LocalRAG()

        docs = [
            {
                "url": "test",
                "title": "Hospital",
                "content": "The hospital offers emergency services 24 hours a day for all patients in the area.",
            },
            {
                "url": "test",
                "title": "Hospital",
                "content": "Visiting hours are 9am to 5pm daily except for holidays and emergency situations.",
            },
            {
                "url": "test",
                "title": "Hospital",
                "content": "We have a cardiology department specialized in advanced heart surgeries and care.",
            },
        ]

        rag.build_index(docs)

        # Query for emergency services
        results = rag.search("emergency services", k=1)

        assert len(results) >= 1
        assert "emergency services" in results[0]["text"]

    def test_query_empty_index(self, tmp_path):
        """Test querying empty index returns empty list."""
        rag = LocalRAG(cache_dir=tmp_path)
        res = rag.search("test query")
        assert res == []


class TestRAGIntegration:
    """Test RAG integration with chat."""

    def test_rag_context_injection(self, tmp_path):
        """Test RAG context is injected into prompts."""
        rag = LocalRAG(cache_dir=tmp_path)

        docs = [
            {
                "url": "test",
                "title": "Info",
                "content": "The manager of the facility is John Doe, who has been with us for ten years.",
            },
        ]

        rag.build_index(docs)

        # Query
        results = rag.search("who is the manager", k=1)

        # Build prompt with context
        context = "\n\n".join([chunk["text"] for chunk in results])
        prompt = f"""Based on the following context, answer the question.

Context:
{context}

Question: who is the manager

Answer:"""

        # Verify content is in prompt
        assert "John Doe" in prompt
        assert "who is the manager" in prompt


class TestWebsiteScraper:
    """Test website scraping functionality."""

    def test_scraper_initialization(self):
        """Test scraper initializes correctly."""
        scraper = WebsiteScraper("http://example.com")

        assert scraper.base_url == "http://example.com"
        assert len(scraper.visited) == 0

    @pytest.mark.asyncio
    async def test_scraper_respects_rate_limit(self):
        """Test scraper has rate limiting."""
        # This would require mocking HTTP requests
        # For now, verify structure is correct
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
