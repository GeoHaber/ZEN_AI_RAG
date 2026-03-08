# -*- coding: utf-8 -*-
"""
async_scraper.py - Safe parallel async web scraper for RAG
Implements polite scraping practices to avoid DoS detection
"""

import aiohttp
import asyncio
from asyncio import Semaphore
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
import time
from .web_scanner import WebCrawlScanner

logger = logging.getLogger(__name__)


class SafeAsyncScraper:
    """
    Safe parallel async website scraper with anti-DoS measures.

    Safety Features:
    - Rate limiting (max 5 concurrent requests)
    - Delays between requests (0.5s minimum)
    - Proper User-Agent header
    - Timeout handling
    - Polite retry logic
    """

    def __init__(
        self,
        base_url: str,
        max_concurrent: int = 5,  # Conservative limit
        delay_between_requests: float = 0.5,  # 500ms delay
        timeout: int = 10,
    ):
        """Initialize instance."""
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.max_concurrent = max_concurrent
        self.delay = delay_between_requests
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.visited = set()
        self.documents = []

        # Polite User-Agent
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

        self.scanner = WebCrawlScanner(user_agent=self.headers["User-Agent"])
        self.crawl_report = None

        logger.info(
            f"[SafeScraper] Initialized: max {max_concurrent} concurrent, "
            f"{delay_between_requests}s delay between requests"
        )

    async def scrape_page(self, session: aiohttp.ClientSession, url: str, semaphore: Semaphore):
        """
        Scrape a single page with safety measures.

        Args:
            session: aiohttp session
            url: URL to scrape
            semaphore: Rate limiting semaphore

        Returns:
            Document dict or None if failed
        """
        async with semaphore:
            if url in self.visited:
                return None

            self.visited.add(url)

            try:
                # Polite delay before request
                await asyncio.sleep(self.delay)

                start_time = time.time()

                # Fetch HTML with polite headers
                fetch_start = time.time()
                async with session.get(url, headers=self.headers, timeout=self.timeout) as response:
                    # Check for rate limiting
                    if response.status == 429:  # Too Many Requests
                        logger.warning(f"[SafeScraper] ⏸️ Rate limited by server: {url}")
                        await asyncio.sleep(5)  # Back off for 5 seconds
                        return None

                    if response.status != 200:
                        logger.warning(f"[SafeScraper] ❌ {url} returned {response.status}")
                        return None

                    html = await response.text()
                fetch_time = time.time() - fetch_start

                # Parse HTML
                parse_start = time.time()
                soup = BeautifulSoup(html, "html.parser")

                # Extract title
                title = soup.find("title")
                title_text = title.get_text().strip() if title else url

                # Remove unwanted elements
                for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    element.decompose()

                # Extract text
                text = soup.get_text(separator=" ", strip=True)
                parse_time = time.time() - parse_start

                # Clean text
                clean_start = time.time()
                text = " ".join(text.split())
                time.time() - clean_start

                total_time = time.time() - start_time

                logger.info(
                    f"[SafeScraper] ✅ {url} ({len(text)} chars) | "
                    f"Fetch: {fetch_time:.2f}s, Parse: {parse_time:.2f}s, Total: {total_time:.2f}s"
                )

                return {"url": url, "title": title_text, "content": text}

            except asyncio.TimeoutError:
                logger.warning(f"[SafeScraper] ⏱️ Timeout: {url}")
                return None

            except aiohttp.ClientError as e:
                logger.error(f"[SafeScraper] ❌ Network error: {url} - {e}")
                return None

            except Exception as e:
                logger.error(f"[SafeScraper] ❌ Error scraping {url}: {e}")
                return None

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and belongs to same domain."""
        try:
            parsed = urlparse(url)
            return (
                parsed.scheme in ["http", "https"]
                and parsed.netloc == self.domain
                and not url.endswith((".pdf", ".jpg", ".png", ".gif", ".zip", ".exe"))
            )
        except Exception:
            return False

    async def discover_urls(self, session: aiohttp.ClientSession, start_url: str, max_pages: int) -> list:
        """
        Discover URLs using BFS (sequential to be polite).

        Args:
            session: aiohttp session
            start_url: Starting URL
            max_pages: Maximum pages to discover

        Returns:
            List of URLs to scrape
        """
        discovered = set()
        queue = [start_url]

        while queue and len(discovered) < max_pages:
            url = queue.pop(0)

            if url in discovered or not self._is_valid_url(url):
                continue

            discovered.add(url)

            try:
                # Polite delay
                await asyncio.sleep(self.delay)

                async with session.get(url, headers=self.headers, timeout=self.timeout) as response:
                    if response.status != 200:
                        continue

                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # Find all links
                    for link in soup.find_all("a", href=True):
                        absolute_url = urljoin(url, link["href"])
                        if self._is_valid_url(absolute_url) and absolute_url not in discovered:
                            queue.append(absolute_url)

            except Exception as e:
                logger.debug(f"[SafeScraper] Error discovering from {url}: {e}")
                continue

        logger.info(f"[SafeScraper] 🔍 Discovered {len(discovered)} URLs")
        return list(discovered)
        return list(discovered)

    async def scrape_website(self, max_pages: int = 50, progress_callback=None) -> list:
        """
        Scrape website with parallel requests and safety measures.

        Args:
            max_pages: Maximum pages to scrape
            progress_callback: Optional callback(current, total, url)

        Returns:
            List of scraped documents
        """
        start_time = time.time()

        logger.info(
            f"[SafeScraper] 🚀 Starting safe parallel scrape: "
            f"max {max_pages} pages, {self.max_concurrent} concurrent, "
            f"{self.delay}s delay"
        )

        # Pre-flight ethical scan
        self.crawl_report = await self.scanner.scan(self.base_url)
        if not self.crawl_report.can_crawl:
            logger.error(f"[SafeScraper] 🛑 Scrape aborted: {self.crawl_report.reason}")
            return []

        if self.crawl_report.bot_protection:
            logger.warning(
                f"[SafeScraper] ⚠️ Target site has {self.crawl_report.bot_protection} protection. Results may be limited."
            )

        # Create session with connection pooling
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Discover URLs (polite, sequential)
            urls_to_scrape = await self.discover_urls(session, self.base_url, max_pages)
            total_urls = len(urls_to_scrape)

            if total_urls == 0:
                logger.warning("[SafeScraper] No URLs discovered")
                return []

            # Create semaphore for rate limiting
            semaphore = Semaphore(self.max_concurrent)

            # Scrape all URLs in parallel (with rate limiting)
            tasks = [self.scrape_page(session, url, semaphore) for url in urls_to_scrape]

            # Track progress
            completed = 0
            for coro in asyncio.as_completed(tasks):
                result = await coro
                if result:
                    self.documents.append(result)

                completed += 1
                if progress_callback:
                    progress_callback(completed, total_urls, result["url"] if result else "")

        total_time = time.time() - start_time
        avg_time = total_time / total_urls if total_urls > 0 else 0

        logger.info(
            f"[SafeScraper] ✅ Completed: {len(self.documents)} pages in {total_time:.2f}s ({avg_time:.2f}s/page avg)"
        )

        return self.documents
