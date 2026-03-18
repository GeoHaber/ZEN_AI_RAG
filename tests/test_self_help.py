import unittest
import sys
import os
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from zena_mode.rag_pipeline import LocalRAG
from zena_mode.arbitrage import SwarmArbitrator


class TestSelfHelpRAG(unittest.TestCase):
    """TestSelfHelpRAG class."""

    def setUp(self):
        """Setup."""
        # Use a temporary cache for testing
        self.test_cache = Path("./test_self_help_cache")
        if self.test_cache.exists():
            shutil.rmtree(self.test_cache)
        self.test_cache.mkdir()

        self.rag = LocalRAG(cache_dir=self.test_cache)
        self.arbitrator = SwarmArbitrator()

        # Load Manual Content
        self.manual_path = Path("USER_MANUAL.md")
        # In actual app, this is C:\Users\dvdze\.gemini\antigravity\brain\...\USER_MANUAL.md
        # For this test, we might need to locate it or mock it.
        # I will look for it in the current dir or expected locations.

        content = ""
        candidates = [
            Path("USER_MANUAL.md"),
            Path(__file__).resolve().parent.parent / "USER_MANUAL.md",
        ]

        for p in candidates:
            if not p.exists():
                continue
            content = p.read_text(encoding="utf-8")
            break

        if not content:
            # Fallback mock for CI/CD safety
            content = """# ZenAI User Manual\n## 2. Model Manager\nExpand this section to view and manage your local LLMs.\n- Catalog: Shows a list of popular models."""

        # Ingest Manual
        doc = {"url": "internal://USER_MANUAL.md", "title": "ZenAI User Manual", "content": content}
        self.rag.build_index([doc], filter_junk=False)

    def tearDown(self):
        """Teardown."""
        self.rag.close()
        # Clean up
        if self.test_cache.exists():
            try:
                shutil.rmtree(self.test_cache)
            except Exception:
                pass

    def test_manual_retrieval(self):
        """Test if 'how to switch models' retrieves the Model Manager section."""
        query = "How do I switch models?"
        results = self.rag.search(query, k=3)

        # Check if we got results
        self.assertTrue(len(results) > 0, "No results found for manual query")

        # Check content relevance
        top_text = results[0]["text"].lower()
        # [X-Ray auto-fix] print(f"DEBUG: Top Result: {top_text}")
        # We expect 'model manager' or 'catalog' or 'download' logic
        self.assertTrue(
            any(x in top_text for x in ["model", "catalog", "manager", "download"]),
            f"Top result did not contain expected keywords. Got: {top_text}",
        )

    def test_troubleshooting_retrieval(self):
        """Test if 'audio not working' hits troubleshooting."""
        query = "My audio is not working"
        results = self.rag.search(query, k=3)

        found_troubleshooting = False
        for res in results:
            if not (
                "troubleshooting" in res["text"].lower()
                or "microphone" in res["text"].lower()
                or "audio" in res["text"].lower()
            ):
                continue
            found_troubleshooting = True
            break

        self.assertTrue(found_troubleshooting, "Did not find troubleshooting info for audio issue")

    def test_verification_shield(self):
        """Verify that the Arbitrator confirms the answer matches the manual."""
        # Simulated RAG Context
        context = ["The Model Manager allows you to switch local LLMs from the catalog."]

        # Good Answer
        ans_good = "You can switch models using the Model Manager."
        res_good = self.arbitrator.verify_hallucination(ans_good, context)
        self.assertGreaterEqual(res_good["score"], 0.6, "Good answer should pass verification")

        # Bad Answer
        ans_bad = "You switch models by restarting your computer 10 times."
        res_bad = self.arbitrator.verify_hallucination(ans_bad, context)
        self.assertLess(res_bad["score"], 0.6, "Hallucination should fail verification")


if __name__ == "__main__":
    unittest.main()
