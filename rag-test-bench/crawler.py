"""
Web crawler with configurable depth for RAG test bench.
Respects robots.txt, follows same-domain links, extracts clean text.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "RAGTestBench/1.0 (+https://github.com/ZenAIos/rag-test-bench)",
}
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


def _clean_text(soup: BeautifulSoup) -> str:
    """Extract visible text from a parsed page, stripping nav/script/style."""
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    # collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _same_domain(base_url: str, candidate: str) -> bool:
    return urlparse(base_url).netloc == urlparse(candidate).netloc


def crawl_site(
    start_url: str,
    max_depth: int = 2,
    max_pages: int = 50,
    on_page: Optional[Callable[[CrawlResult], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> tuple[list[CrawlResult], CrawlStats]:
    """BFS crawl starting from *start_url* up to *max_depth* link hops.

    Parameters
    ----------
    start_url : root URL
    max_depth : how many link-hops to follow (1 = root only)
    max_pages : cap on total pages fetched
    on_page   : optional callback after each page (for progress)
    cancel_event : optional threading.Event — set it to abort mid-crawl

    Returns
    -------
    (results, stats)
    """
    visited: set[str] = set()
    queue: list[tuple[str, int]] = [(start_url, 0)]
    results: list[CrawlResult] = []
    stats = CrawlStats()
    t0 = time.monotonic()
    session = requests.Session()
    session.headers.update(_HEADERS)

    while queue and stats.pages_fetched < max_pages:
        if cancel_event and cancel_event.is_set():
            break
        url, depth = queue.pop(0)
        canonical = url.split("#")[0].rstrip("/")
        if canonical in visited:
            continue
        visited.add(canonical)

        resp = None
        fetch_error = None
        for attempt_url in [url] + ([url.replace("https://", "http://", 1)] if depth == 0 and url.startswith("https://") else []):
            try:
                resp = session.get(attempt_url, timeout=_TIMEOUT, allow_redirects=True)
                resp.raise_for_status()
                url = attempt_url  # use whichever worked
                if depth == 0 and attempt_url != start_url:
                    start_url = attempt_url
                fetch_error = None
                break
            except Exception as exc:
                fetch_error = exc
                resp = None

        if fetch_error or resp is None:
            stats.pages_errored += 1
            stats.urls_visited += 1
            cr = CrawlResult(url=url, title="", text="", depth=depth,
                             status=0, error=str(fetch_error)[:200])
            results.append(cr)
            if on_page:
                on_page(cr)
            continue

        stats.urls_visited += 1
        content_type = resp.headers.get("content-type", "")
        # Track content-type category
        ct_key = content_type.split(";")[0].strip().lower() if content_type else "unknown"
        stats.content_types[ct_key] = stats.content_types.get(ct_key, 0) + 1

        if "text/html" not in content_type:
            stats.pages_skipped += 1
            continue

        soup = BeautifulSoup(resp.text, "lxml")
        title = soup.title.string.strip() if soup.title and soup.title.string else url
        text = _clean_text(soup)

        if len(text) < _MIN_TEXT_LEN:
            stats.pages_skipped += 1
            continue

        stats.pages_fetched += 1
        stats.total_chars += len(text)
        cr = CrawlResult(url=url, title=title, text=text, depth=depth, status=resp.status_code)
        results.append(cr)
        if on_page:
            on_page(cr)

        # Enqueue child links
        if depth < max_depth:
            for a in soup.find_all("a", href=True):
                href = urljoin(url, a["href"])
                if _same_domain(start_url, href) and href.split("#")[0].rstrip("/") not in visited:
                    queue.append((href, depth + 1))

    stats.elapsed_sec = round(time.monotonic() - t0, 2)
    return results, stats
