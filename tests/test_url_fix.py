import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from zena_mode.scraper import WebsiteScraper

def test_scraper_normalizes_url():
    """Verify scraper adds https:// to bare domains."""
    # 1. Bare domain
    scraper = WebsiteScraper("example.com")
    assert scraper.base_url == "https://example.com"
    assert scraper.domain == "example.com"

    # 2. Localhost (should be http)
    scraper_local = WebsiteScraper("localhost:8000")
    assert scraper_local.base_url == "http://localhost:8000"

    # 3. Already valid
    scraper_valid = WebsiteScraper("http://test.com")
    assert scraper_valid.base_url == "http://test.com"
    
    # 4. Input with spaces
    scraper_spaces = WebsiteScraper("  google.com  ")
    assert scraper_spaces.base_url == "https://google.com"

if __name__ == "__main__":
    test_scraper_normalizes_url()
    print("✅ URL Normalization Verified")
