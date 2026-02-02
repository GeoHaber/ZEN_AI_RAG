"""
scraper.py - Website scraping for RAG pipeline
"""
import requests
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
from urllib.parse import urljoin, urlparse
import logging
from .web_scanner import WebCrawlScanner

logger = logging.getLogger(__name__)

class WebsiteScraper:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.visited = set()
        self.documents = []
        self.domain = urlparse(base_url).netloc
        self.scanner = WebCrawlScanner()
        self.crawl_report = None
    
    def is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain."""
        return urlparse(url).netloc == self.domain
    
    def clean_html(self, soup: BeautifulSoup) -> str:
        """Remove scripts, styles, navigation, and extract clean text."""
        # Remove unwanted tags
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
            tag.decompose()
        
        # --- NEW: Strip Cookie Banners & Modals ---
        cookie_keywords = ["cookie", "consent", "privacy policy", "terms of use", "gdpr"]
        for element in soup.find_all(['div', 'section', 'aside']):
            classes = " ".join(element.get('class', [])) if element.get('class') else ""
            ids = str(element.get('id', ""))
            
            # Check if this looks like a banner/modal
            if any(kw in (classes + ids).lower() for kw in ["banner", "modal", "popup", "consent", "cookie"]):
                # Confirmation: Does it also have policy keywords?
                text_content = element.get_text().lower()
                if any(kw in text_content for kw in cookie_keywords):
                    # logger.debug(f"[Scraper] Stripping suspected banner: {classes} {ids}")
                    element.decompose()
        
        # Get text
        text = soup.get_text(separator='\n')
        
        # Clean whitespace
        lines = [line.strip() for line in text.splitlines()]
        text = '\n'.join(line for line in lines if line)
        
        return text
    
    def scrape(self, max_pages: int = 50, progress_callback=None) -> list:
        """
        Crawl website and extract text content.
        
        Args:
            max_pages: Maximum number of pages to scrape
            progress_callback: Optional callable(count, max_pages, url) for UI updates
        """
        if BeautifulSoup is None:
            raise ImportError("BeautifulSoup4 is required for web scraping. Install with: pip install beautifulsoup4")
        
        import time
        import random
        import asyncio
        
        # Pre-flight ethical scan
        self.crawl_report = asyncio.run(self.scanner.scan(self.base_url))
        if not self.crawl_report.can_crawl:
            logger.error(f"[Scraper] 🛑 Scrape aborted: {self.crawl_report.reason}")
            return []
            
        if self.crawl_report.bot_protection:
            logger.warning(f"[Scraper] ⚠️ Target site has {self.crawl_report.bot_protection} protection. Results may be limited.")

        start_time = time.time()
        queue = [self.base_url]
        
        # Rotation of User-Agents to avoid pattern detection
        USER_AGENTS = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1'
        ]
        
        def get_headers():
            return {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.google.com/',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        
        while queue and len(self.visited) < max_pages:
            url = queue.pop(0)
            if url in self.visited:
                continue
            
            try:
                # Add a small random jitter to mimic human browsing
                if self.visited:
                    time.sleep(random.uniform(1.0, 3.0))

                page_start = time.time()
                logger.debug(f"[Scraper] Fetching: {url}")
                
                # Exponential Backoff Retry Logic
                response = None
                retries = 3
                backoff = 2
                
                for attempt in range(retries):
                    try:
                        response = requests.get(url, timeout=15, headers=get_headers())
                        
                        # Handle 429 (Rate Limit) or 999 (Blocked)
                        if response.status_code in [429, 999]:
                            wait_time = backoff ** (attempt + 1) + random.uniform(1, 3)
                            logger.warning(f"[Scraper] ⚠️ Blocked ({response.status_code}) at {url}. Retrying in {wait_time:.1f}s...")
                            time.sleep(wait_time)
                            continue
                        
                        if response.status_code == 200:
                            break
                        else:
                            logger.warning(f"[Scraper] ⚠️ Failed {url} (Status: {response.status_code})")
                            break # Don't retry other errors
                    except Exception as e:
                        if attempt < retries - 1:
                            time.sleep(backoff ** (attempt + 1))
                        else:
                            raise e
                
                if not response or response.status_code != 200:
                    self.visited.add(url)
                    continue

                fetch_time = time.time() - page_start
                
                # Check for common "Forbidden" or "Bot detected" content
                lower_text = response.text.lower()
                if any(kw in lower_text for kw in ["security check", "bot detection", "captcha", "cloudflare"]):
                     logger.error(f"[Scraper] ❌ Anti-bot triggered at {url}")
                     self.visited.add(url)
                     continue

                parse_start = time.time()
                soup = BeautifulSoup(response.text, 'html.parser')
                parse_time = time.time() - parse_start
                
                # Extract text
                clean_start = time.time()
                text = self.clean_html(soup)
                clean_time = time.time() - clean_start
                
                if len(text) > 100:  # Only save pages with substantial content
                    self.documents.append({
                        "url": url,
                        "title": soup.title.string if soup.title else url,
                        "content": text
                    })
                    logger.info(f"[Scraper] ✅ Saved: {url} ({len(text)} chars) | Fetch: {fetch_time:.2f}s, Parse: {parse_time:.2f}s, Clean: {clean_time:.2f}s")
                
                # Find links
                for link in soup.find_all('a', href=True):
                    full_url = urljoin(url, link['href'])
                    # Only follow same-domain HTTP(S) links
                    if self.is_same_domain(full_url) and full_url.startswith('http'):
                        if full_url not in self.visited and full_url not in queue:
                            queue.append(full_url)
                
                self.visited.add(url)
                
                # Update progress
                if progress_callback:
                    progress_callback(len(self.visited), max_pages, url)
                
            except Exception as e:
                logger.error(f"[Scraper] Error scraping {url}: {e}")
                self.visited.add(url)
        
        total_time = time.time() - start_time
        avg_time = total_time / len(self.documents) if self.documents else 0
        logger.info(f"[Scraper] ✅ Completed: {len(self.documents)} pages in {total_time:.2f}s ({avg_time:.2f}s/page)")
        return self.documents
