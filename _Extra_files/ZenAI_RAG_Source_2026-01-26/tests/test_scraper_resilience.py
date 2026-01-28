import pytest
from unittest.mock import patch, MagicMock
from zena_mode.scraper import WebsiteScraper
import requests

def test_scraper_exponential_backoff():
    """Verify that the scraper retries on 999/429 status codes."""
    scraper = WebsiteScraper("https://example.com")
    
    # Mock responses: 999, 429, then 200
    mock_responses = [
        MagicMock(status_code=999),
        MagicMock(status_code=429),
        MagicMock(status_code=200, text="<html><title>Success</title><body>This is a substantial piece of content that exceeds the 100 character threshold to ensure the scraper actually saves it as a valid document for RAG indexing. It needs to be long enough to pass the filters.</body></html>")
    ]
    
    with patch('requests.get', side_effect=mock_responses) as mock_get:
        # Mock time.sleep to avoid waiting in tests
        with patch('time.sleep'):
            docs = scraper.scrape(max_pages=1)
            
            # Verify 3 calls were made (2 retries + 1 success)
            assert mock_get.call_count == 3
            assert len(docs) == 1
            assert docs[0]['title'] == "Success"

def test_scraper_antibot_detection():
    """Verify that common anti-bot keywords trigger a failure."""
    scraper = WebsiteScraper("https://example.com")
    
    # Mock response with "cloudflare" keyword
    mock_response = MagicMock(status_code=200, text="<html><body>Please complete the security check by cloudflare</body></html>")
    
    with patch('requests.get', return_value=mock_response):
        docs = scraper.scrape(max_pages=1)
        
        # Should not save the document
        assert len(docs) == 0

def test_scraper_different_domain_filtered():
    """Verify that links to other domains are not followed."""
    scraper = WebsiteScraper("https://example.com")
    assert scraper.is_same_domain("https://example.com/page") is True
    assert scraper.is_same_domain("https://other.com/page") is False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
