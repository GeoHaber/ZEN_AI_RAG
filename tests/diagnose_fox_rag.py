import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from zena_mode.scraper import WebsiteScraper
from zena_mode.rag_pipeline import LocalRAG

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DiagnoseFox")

def diagnose_fox():
    # A recent/relevant Davos article from Fox News
    url = "https://www.foxnews.com/world/world-economic-forum-kick-off-davos-switzerland-global-elites-likely-face-flak-private-jets"
    
    logger.info(f"--- 1. SCRAPING {url} ---")
    scraper = WebsiteScraper(url)
    docs = scraper.scrape(max_pages=1)
    
    if not docs:
        logger.error("Scraping failed: No documents returned.")
        return
    
    doc = docs[0]
    logger.info(f"Scraped Title: {doc['title']}")
    logger.info(f"Content length: {len(doc['content'])} chars")
    logger.info(f"Snippet: {doc['content'][:500]}...")
    
    # Check if 'Davos' is in content
    if 'Davos' in doc['content'] or 'DAVOS' in doc['content']:
        logger.info("✅ 'Davos' found in scraped content.")
    else:
        logger.warning("❌ 'Davos' NOT found in scraped content! Checking raw HTML decomposition...")

    logger.info("--- 2. INDEXING ---")
    rag = LocalRAG(cache_dir=Path("tmp_diag_rag"))
    rag.build_index(docs, filter_junk=True)
    
    logger.info(f"Index built: {len(rag.chunks)} chunks.")
    
    logger.info("--- 3. QUERYING ---")
    query = "What is Davos?"
    results = rag.search(query, k=3)
    
    if not results:
        logger.error("Query failed: No results returned.")
    else:
        logger.info(f"✅ Found {len(results)} results.")
        for i, res in enumerate(results):
            logger.info(f"Result {i+1} (Score: {res['score']:.4f}): {res['text'][:200]}...")

if __name__ == "__main__":
    diagnose_fox()
