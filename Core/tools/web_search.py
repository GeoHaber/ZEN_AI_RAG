"""
Web Search Tool — Multi-provider wrapper
=========================================
Supports DuckDuckGo (default, no API key), Google (via googlesearch-python,
no API key), and Bing (scraping fallback). Tries providers in order until
results are found.

Usage:
    from Core.tools.web_search import search_web, search_with_fallback

    results = search_web("latest python version", max_results=5)
    for r in results:
        print(r["title"], r["url"])
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Provider availability ──────────────────────────────────────────────────

try:
    from duckduckgo_search import DDGS

    _DDG_AVAILABLE = True
except ImportError:
    _DDG_AVAILABLE = False
    logger.debug("duckduckgo-search not installed: pip install duckduckgo-search")

try:
    from googlesearch import search as _google_search  # googlesearch-python

    _GOOGLE_AVAILABLE = True
except ImportError:
    _GOOGLE_AVAILABLE = False
    logger.debug("googlesearch-python not installed: pip install googlesearch-python")

try:
    import requests as _requests

    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False

# Provider constants
PROVIDER_DDG = "duckduckgo"
PROVIDER_GOOGLE = "google"
PROVIDER_BING = "bing"

PROVIDERS_ORDERED = [PROVIDER_DDG, PROVIDER_GOOGLE, PROVIDER_BING]


# =============================================================================
# INDIVIDUAL PROVIDER IMPLEMENTATIONS
# =============================================================================


def _search_duckduckgo(query: str, max_results: int = 5) -> List[Dict]:
    """DuckDuckGo search — no API key required."""
    if not _DDG_AVAILABLE:
        logger.debug("DuckDuckGo not available")
        return []
    try:
        with DDGS() as ddgs:
            results = []
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    {
                        "url": r.get("href") or r.get("link", ""),
                        "title": r.get("title", ""),
                        "snippet": r.get("body") or r.get("snippet", ""),
                        "provider": PROVIDER_DDG,
                    }
                )
            return results
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")
        return []


def _search_google(query: str, max_results: int = 5) -> List[Dict]:
    """Google search via googlesearch-python — no API key required."""
    if not _GOOGLE_AVAILABLE:
        logger.debug("googlesearch-python not available")
        return []
    try:
        results = []
        for url in _google_search(query, num_results=max_results, advanced=True):
            # advanced=True returns SearchResult objects with url, title, description
            if hasattr(url, "url"):
                results.append(
                    {
                        "url": url.url,
                        "title": getattr(url, "title", url.url),
                        "snippet": getattr(url, "description", ""),
                        "provider": PROVIDER_GOOGLE,
                    }
                )
            else:
                results.append(
                    {
                        "url": str(url),
                        "title": str(url),
                        "snippet": "",
                        "provider": PROVIDER_GOOGLE,
                    }
                )
        return results
    except Exception as e:
        logger.warning(f"Google search failed: {e}")
        return []


def _search_bing(query: str, max_results: int = 5) -> List[Dict]:
    """
    Bing search via HTML scraping (no API key).
    Uses requests + basic HTML parsing — lightweight fallback.
    """
    if not _REQUESTS_AVAILABLE:
        logger.debug("requests not available for Bing fallback")
        return []
    try:
        from urllib.parse import quote_plus
        from html.parser import HTMLParser

        class BingParser(HTMLParser):
            """Minimal HTML parser for Bing result titles and URLs."""

            def __init__(self):
                super().__init__()
                self.results: List[Dict] = []
                self._current_url = ""
                self._current_title = ""
                self._in_title = False

            def handle_starttag(self, tag, attrs):
                if tag == "h2":
                    self._in_title = True
                if tag == "a" and self._in_title:
                    attrs_dict = dict(attrs)
                    href = attrs_dict.get("href", "")
                    if href.startswith("http") and "bing.com" not in href:
                        self._current_url = href

            def handle_data(self, data):
                if self._in_title and data.strip():
                    self._current_title += data

            def handle_endtag(self, tag):
                if tag == "h2" and self._in_title:
                    if self._current_url and self._current_title.strip():
                        self.results.append(
                            {
                                "url": self._current_url,
                                "title": self._current_title.strip(),
                                "snippet": "",
                                "provider": PROVIDER_BING,
                            }
                        )
                    self._in_title = False
                    self._current_url = ""
                    self._current_title = ""

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        url = f"https://www.bing.com/search?q={quote_plus(query)}&count={max_results * 2}"
        resp = _requests.get(url, headers=headers, timeout=8)
        resp.raise_for_status()

        parser = BingParser()
        parser.feed(resp.text)
        return parser.results[:max_results]

    except Exception as e:
        logger.warning(f"Bing search failed: {e}")
        return []


# =============================================================================
# PUBLIC API
# =============================================================================


def search_web(
    query: str,
    max_results: int = 5,
    provider: str = PROVIDER_DDG,
) -> List[Dict]:
    """
    Search the web using the specified provider.

    Args:
        query:       Search query string
        max_results: Maximum number of results
        provider:    "duckduckgo" | "google" | "bing"

    Returns:
        List of dicts with keys: url, title, snippet, provider
    """
    if not query or not query.strip():
        logger.warning("Empty search query")
        return []

    query = query.strip()

    dispatch = {
        PROVIDER_DDG: _search_duckduckgo,
        PROVIDER_GOOGLE: _search_google,
        PROVIDER_BING: _search_bing,
    }

    fn = dispatch.get(provider, _search_duckduckgo)
    try:
        return fn(query, max_results)
    except Exception as e:
        logger.error(f"search_web({provider}) unexpected error: {e}")
        return []


def search_with_fallback(
    query: str,
    max_results: int = 5,
    providers: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Search with automatic fallback through multiple providers.

    Tries providers in order (DDG → Google → Bing) until results are found.

    Args:
        query:       Search query string
        max_results: Maximum number of results
        providers:   Override default provider order

    Returns:
        List of dicts with keys: url, title, snippet, provider
    """
    order = providers or PROVIDERS_ORDERED

    for provider in order:
        results = search_web(query, max_results=max_results, provider=provider)
        if results:
            logger.info(f"Search succeeded with provider: {provider} ({len(results)} results)")
            return results
        logger.debug(f"Provider {provider} returned 0 results, trying next…")

    logger.warning(f"All providers failed for query: {query!r}")
    return []


def get_available_providers() -> List[str]:
    """Return list of currently available search providers."""
    available = []
    if _DDG_AVAILABLE:
        available.append(PROVIDER_DDG)
    if _GOOGLE_AVAILABLE:
        available.append(PROVIDER_GOOGLE)
    if _REQUESTS_AVAILABLE:
        available.append(PROVIDER_BING)
    return available or [PROVIDER_BING]  # Bing scraping always last resort
