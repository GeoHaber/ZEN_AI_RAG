import pytest
import shutil
import mailbox
from email.message import EmailMessage
from pathlib import Path
import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from zena_mode.email_ingestor import EmailIngestor
from zena_mode.rag_pipeline import LocalRAG


class TestEmailRAGE2E:
    """TestEmailRAGE2E class."""

    @pytest.fixture
    def rag_environment(self, tmp_path):
        """Setup temporary RAG environment."""
        rag_dir = tmp_path / "rag_db"
        rag_dir.mkdir()
        rag = LocalRAG(cache_dir=rag_dir)
        yield rag, tmp_path
        rag.close()

    def test_email_retrieval_flow(self, rag_environment):
        """Test email retrieval flow."""
        rag, tmp_path = rag_environment
        mbox_path = tmp_path / "legacy_archive.mbox"

        # 1. Create Dummy MBOX
        mbox = mailbox.mbox(str(mbox_path))

        msg1 = EmailMessage()
        msg1["Subject"] = "Project Alpha Kickoff"
        msg1["From"] = "ceo@zenacorp.com"
        msg1["Date"] = "Mon, 1 Jan 1990 09:00:00 -0500"
        msg1.set_content("Welcome to Project Alpha. We start today, 1990.")
        mbox.add(msg1)

        msg2 = EmailMessage()
        msg2["Subject"] = "Urgent: Server Down"
        msg2["From"] = "admin@zenacorp.com"
        msg2["Date"] = "Fri, 31 Dec 1999 23:59:00 -0500"
        msg2.set_content("The server is melting! Y2K is coming!")
        mbox.add(msg2)

        mbox.flush()
        mbox.close()

        # 2. Ingest
        ingestor = EmailIngestor()
        docs = ingestor.ingest(str(mbox_path))
        assert len(docs) == 2

        # 3. Index
        rag.build_index(docs)

        # 4. Query: Date
        results = rag.search("When did Project Alpha start?", k=3)
        assert len(results) > 0
        top = results[0]
        assert "1990" in top["text"]
        assert "1990" in top["metadata"]["date"]

        # 5. Query: Sender
        # "Who warned about Y2K?" might be ambiguous if documents are small/sparse
        results = rag.search("Who warned about Y2K server melting?", k=3)
        assert len(results) > 0

        # Check if correct email is in top results (ranking varies by model)
        found = False
        for res in results:
            if "admin@zenacorp.com" not in res["metadata"]["sender"]:
                continue
            found = True
            break
        assert found, f"Did not find admin email in results: {results}"


if __name__ == "__main__":
    pytest.main([__file__])
