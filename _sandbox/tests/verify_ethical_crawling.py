# -*- coding: utf-8 -*-
"""
verify_ethical_crawling.py - Demonstration of Intelligent & Ethical Web Crawling
Tests the new WebCrawlScanner integration in both sync and async scrapers.
"""
import asyncio
import logging
from zena_mode.async_scraper import SafeAsyncScraper
from zena_mode.scraper import WebsiteScraper

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("EthicalVerify")

async def verify_async_politeness():
    logger.info("\n--- 🔍 VERIFYING ASYNC SCRAPER (POLITE MODE) ---")
    
    # Target 1: A blocked site (Google Search)
    url_blocked = "https://www.google.com/search?q=zenai"
    logger.info(f"Testing blocked URL: {url_blocked}")
    scraper = SafeAsyncScraper(url_blocked)
    results = await scraper.scrape_website(max_pages=1)
    if not results:
        logger.info(f"✅ ASYNC: Successfully respected robots.txt/blocking for {url_blocked}")

    # Target 2: An allowed site (GitHub Trending)
    url_allowed = "https://github.com/trending"
    logger.info(f"Testing allowed URL: {url_allowed}")
    scraper = SafeAsyncScraper(url_allowed)
    results = await scraper.scrape_website(max_pages=1)
    if results:
        logger.info(f"✅ ASYNC: Successfully crawled allowed URL: {results[0]['url']}")

def verify_sync_politeness():
    logger.info("\n--- 🔍 VERIFYING SYNC SCRAPER (POLITE MODE) ---")
    
    # Target 1: A blocked site
    url_blocked = "https://www.google.com/search?q=zenai"
    logger.info(f"Testing blocked URL: {url_blocked}")
    scraper = WebsiteScraper(url_blocked)
    results = scraper.scrape(max_pages=1)
    if not results:
        logger.info(f"✅ SYNC: Successfully respected robots.txt/blocking for {url_blocked}")

    # Target 2: An allowed site
    url_allowed = "https://github.com/trending"
    logger.info(f"Testing allowed URL: {url_allowed}")
    scraper = WebsiteScraper(url_allowed)
    results = scraper.scrape(max_pages=1)
    if results:
        logger.info(f"✅ SYNC: Successfully crawled allowed URL: {results[0]['url']}")

if __name__ == "__main__":
    # Run async tests
    asyncio.run(verify_async_politeness())
    
    # Run sync tests
    verify_sync_politeness()
    
    logger.info("\n✨ Ethical Web Crawling verification complete!")
