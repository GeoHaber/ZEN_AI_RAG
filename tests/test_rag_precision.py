import unittest
import sys
import os
import numpy as np
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock dependencies BEFORE importing modules
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["qdrant_client"] = MagicMock()
sys.modules["qdrant_client.models"] = MagicMock()
sys.modules["faiss"] = MagicMock()
sys.modules["numpy"] = np  # Use real numpy for math
sys.modules["sentence_transformers"].__version__ = "2.2.2"

from zena_mode.rag_pipeline import LocalRAG
from zena_mode.arbitrage import SwarmArbitrator


class TestRAGPrecision(unittest.TestCase):
    """TestRAGPrecision class."""

    def setUp(self):
        """Setup."""
        # Reset mocks
        sys.modules["sentence_transformers"].reset_mock()
        sys.modules["qdrant_client"].reset_mock()

        # Ensure CrossEncoder returns a FRESH mock each time
        config_mock = MagicMock()
        sys.modules["sentence_transformers"].CrossEncoder = config_mock
        config_mock.return_value = MagicMock()  # New instance per test run if re-imported

        # Setup RAG with mocked SentenceTransformer
        with (
            patch("zena_mode.rag_pipeline.SentenceTransformer") as mock_st,
            patch("zena_mode.rag_pipeline.QdrantClient") as mock_qc,
        ):
            self.rag = LocalRAG(cache_dir=None)
            self.rag.model = mock_st.return_value
            self.rag.qdrant = mock_qc.return_value

        self.arbitrator = SwarmArbitrator()

    def test_rag_reranking_complex(self):
        """
        Test re-ranking with 'distractor' chunks.
        Scenario: Query 'Capital of France'
        Chunks:
        1. 'Paris is the capital of France.' (Target)
        2. 'The capital of Texas is Austin.' (Distractor - shares keywords)
        3. 'France is in Europe.' (Related)
        """
        from zena_mode.rag_pipeline import CrossEncoder as MockCrossEncoder

        mock_instance = MagicMock()
        MockCrossEncoder.return_value = mock_instance

        chunks = [
            {"text": "The capital of Texas is Austin.", "id": "distractor"},
            {"text": "Paris is the capital of France.", "id": "target"},
            {"text": "France is in Europe.", "id": "related"},
        ]

        # Define side_effect to score based on content relevance to "Capital of France"
        def predict_side_effect(pairs):
            """Predict side effect."""
            scores = []
            for query, text in pairs:
                if "Paris" in text:
                    scores.append(0.95)  # High
                elif "Texas" in text:
                    scores.append(0.1)  # Low (Distractor)
                elif "Europe" in text:
                    scores.append(0.5)  # Medium
                else:
                    scores.append(0.0)
            return np.array(scores)

        mock_instance.predict.side_effect = predict_side_effect

        # Act
        reranked = self.rag.rerank("Capital of France", chunks, top_k=3)

        # Assert
        self.assertEqual(len(reranked), 3)
        self.assertEqual(reranked[0]["text"], "Paris is the capital of France.")
        self.assertEqual(reranked[1]["text"], "France is in Europe.")
        self.assertEqual(reranked[2]["text"], "The capital of Texas is Austin.")
        self.assertTrue(reranked[0]["rerank_score"] > reranked[1]["rerank_score"])


def _test_hallucination_verification_mixed_part1(self):
    """Test hallucination verification mixed part 1."""

    # Response has 2 distinct sentences
    response = "Apples are red. Bananas are purple."

    result = self.arbitrator.verify_hallucination(response, context_chunks)

    print(f"DEBUG RESULT: {result}", file=sys.stderr, flush=True)
    # Should be 0.5 because "Apples are red" is supported, "Bananas are purple" is not
    self.assertAlmostEqual(result["score"], 0.5)
    self.assertEqual(len(result["unsupported"]), 1)
    self.assertIn("purple", result["unsupported"][0])

    def test_hallucination_verification_mixed(self):
        """
        Test verification with a mixed response (partially supported).
        Context: 'Apples are red. Bananas are yellow.'
        Response: 'Apples are red. Bananas are purple.'
        Expectation: 50% score.
        """
        import sentence_transformers

        MockCrossEncoder = sentence_transformers.CrossEncoder

        mock_nli = MagicMock()
        MockCrossEncoder.return_value = mock_nli

        # Dynamic scoring logic for NLI
        # Pairs are [ [chunk, sentence], ... ]
        # We need to return logits [Contradiction, Entailment, Neutral]
        def nli_side_effect(pairs):
            """Nli side effect."""
            # We predict for a BATCH of pairs (one sentence vs all chunks)
            # We check if ANY chunk entails the sentence

            # Since we iterate sentence by sentence in the implementation code,
            # this `predict` call corresponds to ONE sentence against ALL context chunks.

            batch_logits = []

            # Check the sentence (hypothesis) from the first pair
            # (All pairs in this batch share the same sentence)
            sentence = pairs[0][1]

            for chunk, _ in pairs:
                # Simple keyword matching logic for the mock
                if "Apples are red" in sentence and "Apples are red" in chunk:
                    # ENTAILMENT (Index 1 high)
                    batch_logits.append([-5.0, 5.0, -5.0])
                elif "Bananas" in sentence and "Bananas are yellow" in chunk:
                    if "purple" in sentence:
                        # CONTRADICTION (Index 0 high)
                        batch_logits.append([5.0, -5.0, -5.0])
                    else:
                        # ENTAILMENT
                        batch_logits.append([-5.0, 5.0, -5.0])
                else:
                    # NEUTRAL (Index 2 high) - e.g. unrelated chunk
                    batch_logits.append([-5.0, -5.0, 5.0])

            return np.array(batch_logits)

        mock_nli.predict.side_effect = nli_side_effect

        _test_hallucination_verification_mixed_part1(self)

    def test_hallucination_verification_perfect(self):
        """
        Test perfect entailment.
        """
        import sentence_transformers

        MockCrossEncoder = sentence_transformers.CrossEncoder
        mock_nli = MockCrossEncoder.return_value

        def nli_side_effect(pairs):
            """Nli side effect."""
            pairs[0][1]
            batch_logits = []
            for chunk, _ in pairs:
                # Always entail for this test
                batch_logits.append([-5.0, 5.0, -5.0])
            return np.array(batch_logits)

        mock_nli.predict.side_effect = nli_side_effect

        result = self.arbitrator.verify_hallucination("Everything is true.", ["Context"])
        self.assertEqual(result["score"], 1.0, f"Failed Perfect Verification: {result}")
        self.assertEqual(len(result["unsupported"]), 0)


if __name__ == "__main__":
    unittest.main()
