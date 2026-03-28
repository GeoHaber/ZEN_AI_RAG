"""
tests/test_contextual_compression.py - Test Contextual Compression

Tests for the contextual compression functionality
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from Core.contextual_compressor import ContextualCompressor, get_contextual_compressor


class TestContextualCompressor(unittest.TestCase):
    """Test contextual compression functionality"""

    def setUp(self):
        self.compressor = ContextualCompressor(max_tokens_per_chunk=200)

    def test_basic_compression(self):
        """Test basic compression functionality"""
        query = "What is machine learning?"
        chunks = [
            "Machine learning is a subset of artificial intelligence. It enables computers to learn from data without being explicitly programmed. Common algorithms include decision trees and neural networks.",
            "Weather forecasting uses various models. Temperature and humidity are important factors. Meteorologists use satellite data for predictions.",
        ]

        compressed, stats = self.compressor.compress_chunks(query, chunks, use_llm=False)

        self.assertEqual(len(compressed), 2)
        self.assertTrue(len(compressed[0]) <= len(chunks[0]))
        # First chunk should have ML content, second shouldn't be as relevant
        self.assertIn("machine learning", compressed[0].lower())

    def test_empty_chunks(self):
        """Test with empty chunks"""
        compressed, stats = self.compressor.compress_chunks("test", [], use_llm=False)
        self.assertEqual(compressed, [])

    def test_compression_stats(self):
        """Test that compression stats are tracked"""
        query = "test query"
        chunks = ["This is a test chunk with some content about testing."]

        compressed, stats = self.compressor.compress_chunks(query, chunks, use_llm=False)

        self.assertIn("total_compressions", stats)
        self.assertIn("compression_ratio", stats)
        self.assertGreater(stats["total_compressions"], 0)

    def test_sentence_splitting(self):
        """Test sentence splitting"""
        text = "First sentence. Second sentence! Third sentence? Fourth sentence."
        sentences = self.compressor._split_sentences(text)

        self.assertEqual(len(sentences), 4)

    def test_token_estimation(self):
        """Test token estimation"""
        text = "This is a test"
        tokens = self.compressor._estimate_tokens(text)
        self.assertGreater(tokens, 0)

    def test_heuristic_compression(self):
        """Test heuristic compression with keyword matching"""
        query = "neural networks deep learning"
        chunk = """
        Neural networks are computing systems inspired by biological neural networks.
        Deep learning is a subset of machine learning based on artificial neural networks.
        The weather today is sunny and warm.
        Stock markets fluctuated today.
        """

        compressed = self.compressor._heuristic_compress(query, chunk)

        # Should keep relevant sentences about neural networks
        self.assertIn("neural", compressed.lower())
        # Should skip irrelevant sentences
        self.assertNotIn("weather", compressed.lower())
        self.assertNotIn("stock", compressed.lower())

    def test_global_instance(self):
        """Test that global instance works"""
        comp1 = get_contextual_compressor()
        comp2 = get_contextual_compressor()

        self.assertIs(comp1, comp2)


if __name__ == "__main__":
    unittest.main()
