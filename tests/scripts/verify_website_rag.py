import asyncio
import logging
import sys
import os

# Setup Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config_system import config

# Ensure we use specific config for test
config.rag.enabled = True

from zena_mode.scraper import WebsiteScraper
from zena_mode.rag_pipeline import AsyncLocalRAG

# Configure Logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("VerifyRAG")


async def run_verification():
    """Run verification."""
    print("=" * 60)
    print("🕷️  WEBSITE RAG VERIFICATION START")
    print("=" * 60)

    # 1. Initialize RAG
    print("\n[1] Initializing Vector DB...")
    rag = AsyncLocalRAG()
    # [X-Ray auto-fix] print(f"✅ RAG Initialized. Collection: {rag.collection_name}")
    # 2. Scrape Website (Real Scraper!)
    target_url = "https://example.com"
    # [X-Ray auto-fix] print(f"\n[2] Scraping {target_url}...")
    scraper = WebsiteScraper(target_url)
    # Run in thread as per UI logic
    result = await asyncio.to_thread(scraper.scrape, max_pages=1)

    if not result["success"]:
        # [X-Ray auto-fix] print(f"❌ Scraping Failed: {result.get('error')}")
        return

    docs = result["documents"]
    # [X-Ray auto-fix] print(f"✅ Scraped {len(docs)} documents.")
    # [X-Ray auto-fix] print(f"   - Title: {docs[0]['title']}")
    # [X-Ray auto-fix] print(f"   - Content Preview: {docs[0]['content'][:50]}...")
    # 3. Index Content
    print("\n[3] Ingesting to Qdrant...")
    await rag.build_index_async(docs)
    print("✅ Indexing Complete")

    # 4. Prove It (Search)
    print("\n[4] Searching for content...")
    query = "What is this domain for?"
    results = await rag.search_async(query, k=3)

    # [X-Ray auto-fix] print(f"✅ Found {len(results)} matches.")
    for i, r in enumerate(results):
        # [X-Ray auto-fix] print(f"   [{i + 1}] Score: {r['score']:.3f} | Text: {r['text'][:60]}...")
        pass
    if any("example" in r["text"].lower() for r in results):
        print("\n🎉 SUCCESS: Website content retrieved from RAG!")
    else:
        print("\n⚠️ WARNING: Content mismatch.")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_verification())
