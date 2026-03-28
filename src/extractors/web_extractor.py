import logging
import time
import requests
from typing import List, Dict, Tuple, Optional, Callable
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

from .markdown_converter import HTMLToStructuredMarkdown, _sanitize_text

logger = logging.getLogger(__name__)

# Rust optimizations if available
try:
    from content_extractor_rust_bridge import (
        decode_response_text,
        parse_image_dimension,
        extract_images as extract_images_rust,
        RUST_AVAILABLE,
    )
except ImportError:
    RUST_AVAILABLE = False
    decode_response_text = None
    parse_image_dimension = None
    extract_images_rust = None

_html_converter = HTMLToStructuredMarkdown()


def _extract_page_metadata(soup: BeautifulSoup, url: str) -> Dict:
    """Extract rich metadata from an HTML page."""
    meta = {"url": url}
    if soup.title and soup.title.string:
        meta["title"] = _sanitize_text(soup.title.string.strip())
    else:
        og = soup.find("meta", attrs={"property": "og:title"})
        meta["title"] = og["content"].strip() if og and og.get("content") else url

    desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if desc and desc.get("content"):
        meta["description"] = _sanitize_text(desc["content"].strip()[:500])

    author = soup.find("meta", attrs={"name": "author"})
    if author and author.get("content"):
        meta["author"] = author["content"].strip()

    for attr in ["article:published_time", "datePublished", "date"]:
        tag = soup.find("meta", attrs={"property": attr}) or soup.find("meta", attrs={"name": attr})
        if tag and tag.get("content"):
            meta["date"] = tag["content"].strip()
            break

    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        meta["language"] = html_tag["lang"]

    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical and canonical.get("href"):
        meta["canonical"] = canonical["href"]

    return meta


class WebScanner:
    """World-class web crawler with structure-preserving extraction."""

    JUNK_IMG_PATTERNS = [
        "pixel",
        "tracking",
        "1x1",
        "spacer",
        "blank",
        ".gif",
        "data:image",
        "advertisement",
        "ad-",
        "analytics",
        "beacon",
        "logo",
        "favicon",
        "icon",
    ]

    def __init__(
        self,
        timeout: int = 15,
        user_agent: str = None,
        max_retries: int = 2,
        max_chars_per_page: int = 50_000,
    ):
        self.timeout = timeout
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 RAG_RAT/2.0"
        )
        self.max_retries = max_retries
        self.max_chars_per_page = max_chars_per_page
        self._seen_hashes = set()

    def scan(
        self,
        start_url: str,
        max_pages: int = 1,
        progress_callback: Optional[Callable] = None,
        page_callback: Optional[Callable[[str, Dict], None]] = None,
        completed_items: List[str] = None,
    ) -> Tuple[str, List[Dict], List[Dict]]:
        visited = set()
        queue = [start_url]
        base_domain = urlparse(start_url).netloc

        all_text = []
        all_images = []
        all_sources = []
        pages_crawled = 0

        while queue and pages_crawled < max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            is_completed = completed_items and url in completed_items
            if progress_callback:
                status = f"Resuming: {url}" if is_completed else f"Scanning: {url}"
                try:
                    progress_callback(pages_crawled, max_pages, status, completed_item=url)
                except TypeError:
                    progress_callback(pages_crawled, max_pages)

            if is_completed:
                html = self._fetch_with_retry(url)
                if html is not None:
                    try:
                        soup = BeautifulSoup(html, "html.parser")
                        add_budget = max(0, max_pages - pages_crawled)
                        if add_budget > 0:
                            added = 0
                            for a in soup.find_all("a", href=True):
                                if added >= add_budget:
                                    break
                                link = self._normalize_link(a["href"], url, base_domain)
                                if link and link not in visited and link not in queue:
                                    queue.append(link)
                                    added += 1
                    except Exception as exc:
                        logger.debug("%s", exc)
                continue

            pages_crawled += 1
            html = self._fetch_with_retry(url)
            if html is None:
                continue

            try:
                soup = BeautifulSoup(html, "html.parser")
                meta = _extract_page_metadata(soup, url)
                page_images = self._extract_images(soup, url)
                all_images.extend(page_images)
                structured_text = _html_converter.convert(soup)
                structured_text = _sanitize_text(structured_text)
            except Exception as parse_err:
                logger.warning(f"Error parsing HTML from {url}: {parse_err}")
                continue

            content_hash = hash(structured_text[:2000])
            if content_hash in self._seen_hashes:
                continue
            self._seen_hashes.add(content_hash)

            if len(structured_text) > self.max_chars_per_page:
                structured_text = structured_text[: self.max_chars_per_page] + "\n\n[... truncated ...]"

            header = f"=== PAGE: {meta.get('title', url)} ===\nURL: {url}\n"
            if meta.get("description"):
                header += f"Description: {meta['description']}\n"
            header += "-" * 60 + "\n"

            page_block = header + structured_text
            all_text.append(page_block)

            source_entry = {
                "type": "web",
                "path": url,
                "title": meta.get("title", url),
                "chars": len(structured_text),
                "images": len(page_images),
            }
            all_sources.append(source_entry)

            if page_callback and not is_completed:
                try:
                    page_callback(page_block, source_entry)
                except Exception as exc:
                    logger.debug("%s", exc)

            if pages_crawled < max_pages:
                for a in soup.find_all("a", href=True):
                    link = self._normalize_link(a["href"], url, base_domain)
                    if link and link not in visited and link not in queue:
                        queue.append(link)

        return "\n\n".join(all_text), all_images[:500], all_sources

    def _fetch_with_retry(self, url: str) -> Optional[str]:
        for attempt in range(self.max_retries + 1):
            try:
                r = requests.get(url, timeout=self.timeout, headers={"User-Agent": self.user_agent})
                if r.status_code == 200:
                    if RUST_AVAILABLE and decode_response_text:
                        text = decode_response_text(r.content, r.encoding)
                        if text:
                            return text
                    return r.text
                elif r.status_code in (429, 503):
                    time.sleep(2 ** (attempt + 1))
                    continue
                return None
            except Exception as exc:
                logger.debug("%s", exc)
        return None

    def _extract_images(self, soup: BeautifulSoup, page_url: str) -> List[Dict]:
        if RUST_AVAILABLE and extract_images_rust:
            try:
                return extract_images_rust(str(soup), page_url)
            except Exception as exc:
                logger.debug("%s", exc)

        images = []
        seen_srcs = set()
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if not src:
                continue
            src = urljoin(page_url, src)
            if any(x in src.lower() for x in self.JUNK_IMG_PATTERNS):
                continue
            if src in seen_srcs:
                continue
            seen_srcs.add(src)
            images.append({"url": src, "alt": img.get("alt", ""), "source": page_url})
        return images

    def _normalize_link(self, href: str, current_url: str, base_domain: str) -> Optional[str]:
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            return None
        href = urljoin(current_url, href)
        parsed = urlparse(href)
        if parsed.netloc != base_domain:
            return None
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
