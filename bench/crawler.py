"""
Web crawler with configurable depth for RAG test bench.
Respects robots.txt, follows same-domain links, extracts clean text.
Backed by zen_core_libs WebCrawler.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional
from urllib.parse import urlparse

from zen_core_libs.acquire.crawler import WebCrawler

logger = logging.getLogger(__name__)

_TIMEOUT = 15
_MIN_TEXT_LEN = 50  # skip pages with less useful text than this


@dataclass
class CrawlResult:
    url: str
    title: str
    text: str
    depth: int
    status: int = 200
    error: Optional[str] = None


@dataclass
class CrawlStats:
    pages_fetched: int = 0
    pages_skipped: int = 0
    pages_errored: int = 0
    total_chars: int = 0
    elapsed_sec: float = 0.0
    urls_visited: int = 0
    content_types: dict = field(default_factory=dict)  # e.g. {"text/html": 42, "image/jpeg": 5}


def _same_domain(base_url: str, candidate: str) -> bool:
    return urlparse(base_url).netloc == urlparse(candidate).netloc


def crawl_site(
    start_url: str,
    max_depth: int = 2,
    max_pages: int = 50,
    on_page: Optional[Callable[[CrawlResult], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> tuple[list[CrawlResult], CrawlStats]:
    """BFS crawl starting from *start_url* up to *max_depth* link hops using WebCrawler."""
    visited: set[str] = set()
    queue: list[tuple[str, int]] = [(start_url, 0)]
    results: list[CrawlResult] = []
    stats = CrawlStats()
    t0 = time.monotonic()
    
    crawler = WebCrawler(timeout=_TIMEOUT, extract_links=True)

    while queue and stats.urls_visited < max_pages:
        if cancel_event and cancel_event.is_set():
            break
        url, depth = queue.pop(0)
        canonical = url.split("#")[0].rstrip("/")
        if canonical in visited:
            continue
        visited.add(canonical)

        # Try to crawl the URL
        try:
            zen_result = crawler.crawl_sync(url)
        except Exception as exc:
             stats.pages_errored += 1
             stats.urls_visited += 1
             cr = CrawlResult(url=url, title="", text="", depth=depth,
                              status=0, error=str(exc)[:200])
             results.append(cr)
             if on_page:
                 on_page(cr)
             continue

        stats.urls_visited += 1
        
        ct_key = "text/markdown" if zen_result.content else "unknown"
        stats.content_types[ct_key] = stats.content_types.get(ct_key, 0) + 1

        if zen_result.error or not zen_result.content:
             if "All crawl engines failed" in (zen_result.error or ""):
                 stats.pages_errored += 1
                 cr = CrawlResult(url=url, title="", text="", depth=depth, status=zen_result.status_code, error=zen_result.error)
                 results.append(cr)
                 if on_page:
                     on_page(cr)
             else:
                 stats.pages_skipped += 1
             continue

        text = zen_result.content
        title = zen_result.title

        if len(text) < _MIN_TEXT_LEN:
            stats.pages_skipped += 1
            continue

        stats.pages_fetched += 1
        stats.total_chars += len(text)
        cr = CrawlResult(url=url, title=title, text=text, depth=depth, status=zen_result.status_code)
        results.append(cr)
        if on_page:
            on_page(cr)

        # Enqueue child links
        if depth < max_depth:
            for href in zen_result.links:
                if _same_domain(start_url, href) and href.split("#")[0].rstrip("/") not in visited:
                    queue.append((href, depth + 1))

    stats.elapsed_sec = round(time.monotonic() - t0, 2)
    return results, stats
