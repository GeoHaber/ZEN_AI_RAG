import pytest
import mailbox
import email
from email.message import EmailMessage
from pathlib import Path
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from zena_mode.email_ingestor import EmailIngestor


class TestEmailIngestor:
    """TestEmailIngestor class."""

    @pytest.fixture
    def mbox_file(self, tmp_path):
        """Create a dummy MBOX file"""
        mbox_path = tmp_path / "test_archive.mbox"
        mbox = mailbox.mbox(str(mbox_path))

        # Email 1
        msg1 = EmailMessage()
        msg1["Subject"] = "Meeting Update"
        msg1["From"] = "boss@company.com"
        msg1["To"] = "me@company.com"
        msg1["Date"] = "Fri, 21 Nov 1997 09:55:06 -0600"
        msg1.set_content("The meeting is moved to Monday.")
        mbox.add(msg1)

        # Email 2
        msg2 = EmailMessage()
        msg2["Subject"] = "Project Launch"
        msg2["From"] = "marketing@company.com"
        msg2["Date"] = "Tue, 1 Jan 2000 12:00:00 +0000"
        msg2.set_content("Launch is successful!")
        mbox.add(msg2)

        mbox.flush()
        mbox.close()
        return mbox_path

    def test_mbox_ingestion(self, mbox_file):
        """Test mbox ingestion."""
        ingestor = EmailIngestor()
        docs = ingestor.ingest(str(mbox_file))

        assert len(docs) == 2

        # Verify Email 1
        doc1 = next(d for d in docs if "Meeting Update" in d["title"])
        assert "1997" in doc1["metadata"]["date"]
        assert "boss@company.com" in doc1["metadata"]["sender"]
        assert "Meeting Update" in doc1["title"]
        assert "The meeting is moved to Monday" in doc1["content"]

        # Verify Email 2
        doc2 = next(d for d in docs if "Project Launch" in d["title"])
        assert "2000" in doc2["metadata"]["date"]

    def test_unsupported_format(self, tmp_path):
        """Test unsupported format."""
        ingestor = EmailIngestor()
        bad_file = tmp_path / "archive.xyz"
        bad_file.touch()
        docs = ingestor.ingest(str(bad_file))
        assert len(docs) == 0


if __name__ == "__main__":
    pytest.main([__file__])
