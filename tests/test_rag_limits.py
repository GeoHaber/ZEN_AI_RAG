import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zena_mode.rag_pipeline import generate_rag_response, LocalRAG


class TestRAGLimits:
    """
    Verification Test for RAG Context Safety Cap.
    Ensures that massive context does not overflow the 4096-token limit (causing 400 Errors).
    """

    def test_context_truncation(self):
        """Test that context is truncated to MAX_CTX_CHARS (12000)."""

        # 1. Setup Mock RAG
        rag = MagicMock(spec=LocalRAG)

        # Create massive chunks that would definitely overflow
        # 5 chunks of 5000 chars each = 25,000 chars > 12,000 limit
        massive_chunk = "A" * 5000
        rag.hybrid_search.return_value = [
            {"text": massive_chunk, "url": "doc1", "title": "Doc 1"},
            {"text": massive_chunk, "url": "doc2", "title": "Doc 2"},
            {"text": massive_chunk, "url": "doc3", "title": "Doc 3"},
            {"text": massive_chunk, "url": "doc4", "title": "Doc 4"},
            {"text": massive_chunk, "url": "doc5", "title": "Doc 5"},
        ]
        rag.rerank.return_value = rag.hybrid_search.return_value  # Pass through rerank

        # 2. Setup Mock Backend
        backend = MagicMock()
        backend.send_message.return_value = ["Response"]

        # 3. Execution
        generator = generate_rag_response("test query", rag, backend)
        list(generator)  # Consume generator to trigger logic

        # 4. Verification
        # Capture the prompt sent to backend
        args, _ = backend.send_message.call_args
        prompt = args[0]

        # Check context length
        context_part = prompt.split("Question:")[0]
        context_len = len(context_part)

        # [X-Ray auto-fix] print(f"\n[DEBUG] Context Length sent to LLM: {context_len} chars")
        # Assertions
        assert context_len < 13000, f"Context overflow! Length {context_len} > 13000"
        assert context_len > 1000, "Context too short!"

        # Verify it contains at least the first 2 chunks (10,000 chars + overhead fits in 12k)
        # But 3 chunks (15,000) should be truncated
        assert "Source [1]" in prompt
        assert "Source [2]" in prompt
        # Source 3 might be partial or missing depending on implementation details

    def test_empty_context_safe(self):
        """Test handles empty context gracefully."""
        rag = MagicMock(spec=LocalRAG)
        rag.hybrid_search.return_value = []
        rag.rerank.return_value = []

        backend = MagicMock()

        gen = generate_rag_response("query", rag, backend)
        response = "".join(list(gen))

        assert "don't have enough information" in response
        backend.send_message.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
