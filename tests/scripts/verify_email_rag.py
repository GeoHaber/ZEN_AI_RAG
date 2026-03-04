import sys
import os
import shutil
import mailbox
from email.message import EmailMessage
from pathlib import Path
import asyncio

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from zena_mode.email_ingestor import EmailIngestor
from zena_mode.rag_pipeline import LocalRAG
from config_system import config

def _do_test_email_rag_flow_setup():
    """Helper: setup phase for test_email_rag_flow."""

    print("📧 Starting Email RAG Verification...")

    # 1. Setup Temporary Artifacts
    tmp_dir = Path("temp_email_test")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir()

    mbox_path = tmp_dir / "legacy_archive.mbox"
    rag_storage = tmp_dir / "rag_db"
    return mbox_path, rag_storage, tmp_dir


async def test_email_rag_flow():
    """Test email rag flow."""
    mbox_path, rag_storage, tmp_dir = _do_test_email_rag_flow_setup()
    
    try:
        # 2. Create Dummy MBOX
        print(f"📦 Creating MBOX at {mbox_path}...")
        mbox = mailbox.mbox(str(mbox_path))
        
        # Email 1: Old date
        msg1 = EmailMessage()
        msg1['Subject'] = 'Project Alpha Kickoff'
        msg1['From'] = 'ceo@zenacorp.com'
        msg1['Date'] = 'Mon, 1 Jan 1990 09:00:00 -0500'
        msg1.set_content("Welcome to Project Alpha. We start today, 1990.")
        mbox.add(msg1)
        
        # Email 2: Request
        msg2 = EmailMessage()
        msg2['Subject'] = 'Urgent: Server Down'
        msg2['From'] = 'admin@zenacorp.com'
        msg2['Date'] = 'Fri, 31 Dec 1999 23:59:00 -0500'
        msg2.set_content("The server is melting! Y2K is coming!")
        mbox.add(msg2)
        
        mbox.flush()
        mbox.close()
        
        # 3. Ingest
        print("📥 Ingesting emails...")
        ingestor = EmailIngestor()
        docs = ingestor.ingest(str(mbox_path))
        print(f"   found {len(docs)} emails.")
        
        # 4. Index into RAG
        print("🧠 Indexing to RAG...")
        # Use a fresh, temporary RAG instance
        rag = LocalRAG(cache_dir=rag_storage)
        rag.build_index(docs)
        
        # 5. Query
        print("\n🔍 Query 1: 'When did Project Alpha start?'")
        results = rag.search("When did Project Alpha start?")
        if results:
            top = results[0]
            print(f"   Answer Source: {top['text'][:50]}...")
            print(f"   Metadata Date: {top.get('metadata', {}).get('date')}")
            if "1990" in top['text'] or "1990" in top.get('metadata', {}).get('date', ''):
                print("   ✅ SUCCESS: Retrieved 1990 date.")
            else:
                print("   ❌ FAILURE: Did not find 1990 context.")
        else:
             print("   ❌ FAILURE: No results found.")

        print("\n🔍 Query 2: 'Who warned about Y2K?'")
        results = rag.search("Who warned about Y2K server melting?")
        if results:
            top = results[0]
            print(f"   Answer Source: {top['text'][:50]}...")
            print(f"   Metadata Sender: {top.get('metadata', {}).get('sender')}")
            if "admin@zenacorp.com" in str(top):
                print("   ✅ SUCCESS: Retrieved correct sender.")
            else:
                print("   ❌ FAILURE: Wrong sender.")
        else:
             print("   ❌ FAILURE: No results found.")

    finally:
        # Cleanup
        if tmp_dir.exists():
            try:
                # Force close RAG to release locks
                if 'rag' in locals():
                    rag.close()
                shutil.rmtree(tmp_dir)
                print("\n🧹 Cleanup complete.")
            except Exception as e:
                print(f"Cleanup warning: {e}")

if __name__ == "__main__":
    asyncio.run(test_email_rag_flow())
