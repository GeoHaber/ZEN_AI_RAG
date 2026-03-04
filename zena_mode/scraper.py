"""
scraper.py - Website scraping for RAG pipeline with production-grade resilience

Enhanced Features (v2.0):
- Pre-flight web scanning (robots.txt, bot protection detection)
- Exponential backoff retry logic
- User-Agent rotation
- Cookie banner removal
- Polite delays (1-3s jitter)
- Anti-bot content detection
- Comprehensive user feedback
"""
import requests
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
from urllib.parse import urljoin, urlparse
import logging
import time
import random
import asyncio

logger = logging.getLogger(__name__)

# Import web scanner for pre-flight checks
try:
    from .web_scanner import WebCrawlScanner
    WEB_SCANNER_AVAILABLE = True
except ImportError:
    WEB_SCANNER_AVAILABLE = False
    logger.warning("[Scraper] web_scanner not available - pre-flight checks disabled")


# User-Agent rotation to avoid fingerprinting
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1'
]


def get_headers():
    """Generate realistic browser headers with rotating User-Agent."""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.google.com/',
        'DNT': '1',  # Do Not Track
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }


from utils import normalize_input

class WebsiteScraper:
    """WebsiteScraper class."""
    def __init__(self, base_url: str):
        """Initialize instance."""
        # Normalize: "example.com" -> "https://example.com"
        self.base_url = normalize_input(base_url)
        self.visited = set()
        self.documents = []
        self.domain = urlparse(self.base_url).netloc

        # Initialize web scanner for pre-flight checks
        if WEB_SCANNER_AVAILABLE:
            self.scanner = WebCrawlScanner()
            self.crawl_report = None
        else:
            self.scanner = None
            self.crawl_report = None

    def is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain."""
        return urlparse(url).netloc == self.domain

    def clean_html(self, soup: BeautifulSoup) -> str:
        """
        Remove scripts, styles, navigation, cookie banners, and extract clean text.

        Enhanced with:
        - Content container prioritization (article, main, etc.)
        - Cookie banner removal
        - Multi-layer junk removal
        """
        # 1. (Removed aggressive container selection to ensure we catch all sections like "Meet the Team")
        # Pre-process images to preserve ALT text and SRC
        for img in soup.find_all('img', src=True):
            alt_text = img.get('alt', '').strip()
            src = img['src']
            # Convert to absolute URL if needed (using soup's base or logic if available, but here we might need to handle it later or rely on src being mostly valid)
            # Better: let's rely on the scraper's URL joining if possible, but here we are in clean_html. 
            # We'll just generic markdown.
            img.replace_with(f" ![{alt_text}]({src}) ")

        # 2. Remove unwanted tags
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'form', 'button']):
            tag.decompose()

        # 3. Strip Cookie Banners & Modals (IMPROVEMENT #1)
        cookie_keywords = ["cookie", "consent", "privacy policy", "terms of use", "gdpr"]
        for element in soup.find_all(['div', 'section', 'aside']):
            classes = " ".join(element.get('class', [])) if element.get('class') else ""
            ids = str(element.get('id', ""))

            # Check if this looks like a banner/modal (class/ID check)
            if any(kw in (classes + ids).lower() for kw in ["banner", "modal", "popup", "consent", "cookie"]):
                # Confirmation: Does it also have policy keywords? (content check)
                text_content = element.get_text().lower()
                if any(kw in text_content for kw in cookie_keywords):
                    logger.debug(f"[Scraper] Stripping cookie banner: {classes} {ids}")
                    element.decompose()

        # 4. Get text
        text = soup.get_text(separator=' ')

        # 5. Clean whitespace
        lines = [line.strip() for line in text.splitlines()]
        text = '\n'.join(line for line in lines if line)

        return text

def _do_scrape_setup_part1_part2():
    """Do scrape setup part1 part 2."""

    # FINAL SUMMARY
    total_time = time.time() - start_time
    avg_time = total_time / len(self.documents) if self.documents else 0

    logger.info(
        f"[Scraper] ✅ Completed: {len(self.documents)} pages in {total_time:.2f}s "
        f"({avg_time:.2f}s/page)"
    )

    if failed_urls:
        logger.warning(f"[Scraper] ⚠️ Failed to scrape {len(failed_urls)} URLs")
        for url, reason in failed_urls[:5]:  # Show first 5 failures
            logger.warning(f"  - {url}: {reason}")

    # Return structured result
    result = {
        "success": len(self.documents) > 0,
        "documents": self.documents,
        "stats": {
            "total_visited": len(self.visited),
            "total_saved": len(self.documents),
            "total_failed": len(failed_urls),
            "total_time": total_time,
            "avg_time_per_page": avg_time
        }
    }

    # Add warnings if applicable
    if failed_urls:
        result["warning"] = f"{len(failed_urls)} URLs failed to scrape"
        result["failed_urls"] = failed_urls

    if self.crawl_report and self.crawl_report.bot_protection:
        result["warning"] = f"Site has {self.crawl_report.bot_protection} protection - results may be incomplete"

    if self.crawl_report:
        result["report"] = self.crawl_report

    return result


def _do_scrape_setup_part1():
    """Do scrape setup part 1."""


    while queue and len(self.visited) < max_pages:
        url = queue.pop(0)
        if url in self.visited:
            continue

        try:
            # IMPROVEMENT #3: Polite delay (mimic human browsing)
            if self.visited:
                delay = random.uniform(1.0, 3.0)
                logger.debug(f"[Scraper] Polite delay: {delay:.1f}s")
                time.sleep(delay)

            page_start = time.time()
            logger.debug(f"[Scraper] Fetching: {url}")

            # IMPROVEMENT #4: Exponential Backoff Retry Logic
            response = None
            retries = 3
            backoff = 2

            for attempt in range(retries):
                try:
                    response = requests.get(url, timeout=15, headers=get_headers())

                    # Handle recoverable errors (rate limits, transient blocks)
                    if response.status_code in [429, 999]:
                        wait_time = backoff ** (attempt + 1) + random.uniform(1, 3)
                        logger.warning(
                            f"[Scraper] ⚠️ Blocked ({response.status_code}) at {url}. "
                            f"Retrying in {wait_time:.1f}s... (Attempt {attempt + 1}/{retries})"
                        )
                        time.sleep(wait_time)
                        continue

                    if response.status_code == 200:
                        break
                    else:
                        logger.warning(f"[Scraper] ⚠️ Failed {url} (Status: {response.status_code})")
                        failed_urls.append((url, response.status_code))
                        break  # Don't retry unrecoverable errors

                except requests.exceptions.Timeout:
                    if attempt < retries - 1:
                        wait_time = backoff ** (attempt + 1)
                        logger.warning(f"[Scraper] ⏱️ Timeout at {url}. Retrying in {wait_time:.1f}s...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"[Scraper] ❌ Timeout at {url} after {retries} attempts")
                        failed_urls.append((url, "timeout"))
                        break

                except Exception as e:
                    if attempt < retries - 1:
                        wait_time = backoff ** (attempt + 1)
                        logger.warning(f"[Scraper] ⚠️ Error at {url}: {e}. Retrying in {wait_time:.1f}s...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"[Scraper] ❌ Failed {url} after {retries} attempts: {e}")
                        failed_urls.append((url, str(e)))
                        break

            # Check if we got a valid response
            if not response or response.status_code != 200:
                self.visited.add(url)
                continue

            fetch_time = time.time() - page_start

            # IMPROVEMENT #5: Anti-Bot Content Detection
            lower_text = response.text.lower()
            if any(kw in lower_text for kw in ["security check", "bot detection", "captcha", "cloudflare"]):
                logger.error(f"[Scraper] ❌ Anti-bot protection triggered at {url}")
                failed_urls.append((url, "anti-bot"))
                self.visited.add(url)
                continue

            # Parse HTML
            parse_start = time.time()
            soup = BeautifulSoup(response.text, 'html.parser')
            parse_time = time.time() - parse_start

            # Extract clean text (with cookie banner removal)
            clean_start = time.time()
            text = self.clean_html(soup)
            clean_time = time.time() - clean_start

            # Only save pages with substantial content
            if len(text) > 100:
                self.documents.append({
                    "url": url,
                    "title": soup.title.string if soup.title else url,
                    "content": text
                })
                logger.info(
                    f"[Scraper] ✅ Saved: {url} ({len(text)} chars) | "
                    f"Fetch: {fetch_time:.2f}s, Parse: {parse_time:.2f}s, Clean: {clean_time:.2f}s"
                )
            else:
                logger.warning(f"[Scraper] ⚠️ Content too short for {url} ({len(text)} chars). Skipped.")

            # Find links to continue crawling
            for link in soup.find_all('a', href=True):
                full_url = urljoin(url, link['href'])
                # Only follow same-domain HTTP(S) links
                if self.is_same_domain(full_url) and full_url.startswith('http'):
                    if full_url not in self.visited and full_url not in queue:
                        queue.append(full_url)

            self.visited.add(url)

            # Update progress callback
            if progress_callback:
                progress_callback(len(self.visited), max_pages, url)

        except Exception as e:
            logger.error(f"[Scraper] Error scraping {url}: {e}")
            failed_urls.append((url, str(e)))
            self.visited.add(url)

    _do_scrape_setup_part1_part2()


def _do_scrape_setup():
    """Helper: setup phase for scrape."""

    if BeautifulSoup is None:
        return {
            "success": False,
            "error": "BeautifulSoup4 is required for web scraping. Install with: pip install beautifulsoup4",
            "documents": []
        }

    # PRE-FLIGHT SCAN (IMPROVEMENT #2: Early failure detection)
    if self.scanner:
        try:
            logger.info(f"[Scraper] Running pre-flight scan for {self.base_url}...")
            self.crawl_report = asyncio.run(self.scanner.scan(self.base_url))

            # Check if we can crawl
            if not self.crawl_report.can_crawl:
                logger.error(f"[Scraper] 🛑 Scrape aborted: {self.crawl_report.reason}")
                return {
                    "success": False,
                    "error": f"Scrape blocked: {self.crawl_report.reason}",
                    "protection": self.crawl_report.bot_protection,
                    "documents": [],
                    "report": self.crawl_report
                }

            # Warn if bot protection detected (may succeed with limitations)
            if self.crawl_report.bot_protection:
                logger.warning(
                    f"[Scraper] ⚠️ Target site has {self.crawl_report.bot_protection} protection. "
                    "Results may be limited."
                )
        except Exception as e:
            logger.warning(f"[Scraper] Pre-flight scan failed: {e}. Continuing anyway...")
            self.crawl_report = None



    def scrape(self, max_pages: int = 50, progress_callback=None) -> dict:
        """
        Crawl website and extract text content with production-grade resilience.

        Args:
            max_pages: Maximum number of pages to scrape
            progress_callback: Optional callable(count, max_pages, url) for UI updates

        Returns:
            dict with:
                - success: bool
                - documents: list of scraped documents
                - error: str (if failed)
                - warning: str (if partial success)
                - report: CrawlabilityReport (if scanner available)
        """
        _do_scrape_setup()
        # MAIN SCRAPING LOOP
        time.time()
    _do_scrape_setup_part1()
