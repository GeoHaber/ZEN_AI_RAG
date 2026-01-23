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

logger = logging.getLogger(__name__)

class WebsiteScraper:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.visited = set()
        self.documents = []
        self.domain = urlparse(base_url).netloc
    
    def is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain."""
        return urlparse(url).netloc == self.domain
    
    def clean_html(self, soup: BeautifulSoup) -> str:
        """Remove scripts, styles, navigation, and extract clean text."""
        # 1. Try to find main content container first
        content_container = None
        for selector in ['article', 'main', '[role="main"]', '.article-body', '.entry-content', '.post-content']:
            content_container = soup.select_one(selector)
            if content_container:
                # Use this sub-tree instead of the whole body
                soup = content_container
                break
        
        # 2. Remove unwanted tags
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'form', 'button']):
            tag.decompose()
        
        # 3. Get text
        # Use a more sophisticated text extraction if possible
        text = soup.get_text(separator=' ')
        
        # 4. Clean whitespace
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
        start_time = time.time()
        queue = [self.base_url]
        
        while queue and len(self.visited) < max_pages:
            url = queue.pop(0)
            if url in self.visited:
                continue
            
            try:
                page_start = time.time()
                logger.info(f"[Scraper] Fetching: {url}")
                response = requests.get(url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                fetch_time = time.time() - page_start
                
                if response.status_code != 200:
                    logger.warning(f"[Scraper] ❌ Failed to fetch {url}: Status {response.status_code}")
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
                else:
                    logger.warning(f"[Scraper] ⚠️ Content too short for {url} ({len(text)} chars). Skipped.")
                
                # Find links
                for link in soup.find_all('a', href=True):
                    full_url = urljoin(url, link['href'])
                    # Only follow same-domain HTTP(S) links
                    if self.is_same_domain(full_url) and full_url.startswith('http'):
                        queue.append(full_url)
                
                self.visited.add(url)
                
                # Update progress
                if progress_callback:
                    progress_callback(len(self.visited), max_pages, url)
                
            except Exception as e:
                logger.error(f"[Scraper] Error scraping {url}: {e}")
        
        total_time = time.time() - start_time
        avg_time = total_time / len(self.documents) if self.documents else 0
        logger.info(f"[Scraper] ✅ Completed: {len(self.documents)} pages in {total_time:.2f}s ({avg_time:.2f}s/page)")
        return self.documents
