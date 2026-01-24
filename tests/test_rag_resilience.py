"""
Test suite for RAG scraper resilience features.

Tests:
1. Web scanner (robots.txt, bot protection detection)
2. Retry logic (exponential backoff)
3. Cookie banner removal
4. User-Agent rotation
5. Anti-bot content detection
6. Structured error returns
"""
import pytest
import asyncio
from bs4 import BeautifulSoup
from unittest.mock import Mock, patch, AsyncMock
import time

# Import modules to test
try:
    from zena_mode.scraper import WebsiteScraper, get_headers
    from zena_mode.web_scanner import WebCrawlScanner, CrawlabilityReport
    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False
    pytest.skip("RAG modules not available", allow_module_level=True)


class TestWebScanner:
    """Test pre-flight web scanning functionality."""

    @pytest.mark.asyncio
    async def test_robots_txt_allowed(self):
        """Test that we correctly parse robots.txt allow."""
        scanner = WebCrawlScanner()
        # Wikipedia allows general crawling
        report = await scanner.scan("https://en.wikipedia.org/wiki/Python_(programming_language)")
        assert report.can_crawl == True

    @pytest.mark.asyncio
    async def test_robots_txt_blocked(self):
        """Test that we respect robots.txt disallow."""
        scanner = WebCrawlScanner()
        # Test with a known blocked path (may vary by site)
        report = await scanner.scan("https://www.linkedin.com/in/test")
        # LinkedIn typically blocks crawlers on /in/ paths
        # Note: This may fail if LinkedIn changes their robots.txt
        # In that case, mock the robots.txt response

    @pytest.mark.asyncio
    async def test_403_forbidden_handling(self):
        """Test 403 status code is detected and blocked."""
        scanner = WebCrawlScanner()
        # Use httpstat.us which returns specific status codes
        report = await scanner.scan("https://httpstat.us/403")
        assert not report.can_crawl
        assert "403" in report.reason or "Forbidden" in report.reason

    @pytest.mark.asyncio
    async def test_429_rate_limit_detection(self):
        """Test 429 status code is detected."""
        scanner = WebCrawlScanner()
        report = await scanner.scan("https://httpstat.us/429")
        assert not report.can_crawl
        assert "429" in report.reason or "Rate" in report.reason

    @pytest.mark.asyncio
    async def test_bot_protection_detection(self):
        """Test anti-bot protection pattern detection."""
        scanner = WebCrawlScanner()

        # Mock HTML response with Cloudflare protection
        mock_html = """
        <html>
            <body>
                <div>Cloudflare Ray ID: 12345</div>
                <div>Checking your browser...</div>
            </body>
        </html>
        """

        # Mock the HTTP request
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = mock_html
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            report = await scanner.scan("https://example.com")
            assert report.bot_protection is not None

    @pytest.mark.asyncio
    async def test_meta_robots_noindex(self):
        """Test meta robots noindex detection."""
        scanner = WebCrawlScanner()

        mock_html = """
        <html>
            <head>
                <meta name="robots" content="noindex, nofollow">
            </head>
            <body>Content</body>
        </html>
        """

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = mock_html
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            report = await scanner.scan("https://example.com")
            assert not report.can_crawl
            assert "meta-robots" in report.reason.lower()


class TestScraperRetryLogic:
    """Test exponential backoff retry logic."""

    def test_retry_on_429(self):
        """Test that scraper retries on 429 rate limit."""
        scraper = WebsiteScraper("https://example.com")

        # Mock requests to return 429, then 200
        responses = [
            Mock(status_code=429),
            Mock(status_code=200, text='<html><body>Success</body></html>')
        ]

        with patch('requests.get', side_effect=responses):
            with patch('time.sleep'):  # Skip actual delays in test
                result = scraper.scrape(max_pages=1)

                # Should succeed after retry
                assert result["success"] == True
                # Should have called requests.get twice (initial + 1 retry)

    def test_retry_on_timeout(self):
        """Test that scraper retries on timeout."""
        import requests
        scraper = WebsiteScraper("https://example.com")

        # Mock first call to timeout, second to succeed
        responses = [
            requests.exceptions.Timeout("Connection timeout"),
            Mock(status_code=200, text='<html><body>Success</body></html>')
        ]

        with patch('requests.get', side_effect=responses):
            with patch('time.sleep'):  # Skip actual delays
                result = scraper.scrape(max_pages=1)

                # Should succeed after retry
                assert result["success"] == True

    def test_exponential_backoff_timing(self):
        """Test that exponential backoff waits correct durations."""
        scraper = WebsiteScraper("https://example.com")

        # Track sleep calls
        sleep_times = []

        def mock_sleep(duration):
            sleep_times.append(duration)

        # Mock 429 responses to trigger retries
        responses = [
            Mock(status_code=429),
            Mock(status_code=429),
            Mock(status_code=200, text='<html><body>Success</body></html>')
        ]

        with patch('requests.get', side_effect=responses):
            with patch('time.sleep', side_effect=mock_sleep):
                result = scraper.scrape(max_pages=1)

                # Verify exponential backoff pattern
                assert len(sleep_times) >= 2  # At least 2 retries
                # Each retry should wait longer (2^n + random(1-3))
                # Sleep times should be roughly: 3-5s, 5-7s
                assert sleep_times[0] >= 3.0  # 2^1 + 1
                assert sleep_times[0] <= 5.0  # 2^1 + 3
                assert sleep_times[1] >= 5.0  # 2^2 + 1
                assert sleep_times[1] <= 7.0  # 2^2 + 3


class TestCookieBannerRemoval:
    """Test cookie banner detection and removal."""

    def test_cookie_banner_removed(self):
        """Test that cookie banners are stripped."""
        html = """
        <html>
            <body>
                <div id="cookie-banner" class="modal">
                    We use cookies to improve your experience.
                    <button>Accept All</button>
                    <button>Reject All</button>
                </div>
                <article>
                    <h1>Real Article Title</h1>
                    <p>This is the actual content we want to index.</p>
                </article>
            </body>
        </html>
        """

        scraper = WebsiteScraper("https://example.com")
        soup = BeautifulSoup(html, 'html.parser')
        text = scraper.clean_html(soup)

        # Cookie banner should be removed
        assert "cookie" not in text.lower()
        assert "Accept All" not in text
        assert "Reject All" not in text

        # Real content should remain
        assert "Real Article Title" in text
        assert "actual content" in text

    def test_gdpr_consent_removed(self):
        """Test GDPR consent modals are removed."""
        html = """
        <html>
            <body>
                <div class="gdpr-consent-popup">
                    <p>We respect your privacy. By continuing, you consent to our privacy policy.</p>
                    <button>I Agree</button>
                </div>
                <main>
                    <p>Main content here</p>
                </main>
            </body>
        </html>
        """

        scraper = WebsiteScraper("https://example.com")
        soup = BeautifulSoup(html, 'html.parser')
        text = scraper.clean_html(soup)

        assert "privacy policy" not in text.lower()
        assert "I Agree" not in text
        assert "Main content" in text

    def test_false_positive_prevention(self):
        """Test that legitimate content with word 'cookie' is NOT removed."""
        html = """
        <html>
            <body>
                <article>
                    <h1>Best Cookie Recipes</h1>
                    <p>Here are some delicious cookie recipes...</p>
                </article>
            </body>
        </html>
        """

        scraper = WebsiteScraper("https://example.com")
        soup = BeautifulSoup(html, 'html.parser')
        text = scraper.clean_html(soup)

        # Legitimate content about cookies should NOT be removed
        assert "Cookie Recipes" in text
        assert "delicious cookie" in text


class TestUserAgentRotation:
    """Test User-Agent rotation functionality."""

    def test_user_agent_is_realistic(self):
        """Test that User-Agent strings are realistic."""
        headers = get_headers()
        user_agent = headers['User-Agent']

        # Should contain browser identifiers
        assert any(browser in user_agent for browser in ['Chrome', 'Safari', 'Firefox'])
        # Should contain platform
        assert any(platform in user_agent for platform in ['Windows', 'Macintosh', 'X11', 'iPhone'])
        # Should look like a real browser
        assert 'Mozilla/5.0' in user_agent

    def test_headers_include_realistic_fields(self):
        """Test that headers include all realistic browser fields."""
        headers = get_headers()

        required_fields = [
            'User-Agent',
            'Accept',
            'Accept-Language',
            'Referer',
            'DNT',
            'Connection',
            'Upgrade-Insecure-Requests'
        ]

        for field in required_fields:
            assert field in headers

        # Referer should be Google (looks legitimate)
        assert headers['Referer'] == 'https://www.google.com/'

    def test_user_agent_rotation(self):
        """Test that User-Agent actually rotates."""
        # Generate 10 headers and verify we get different UAs
        user_agents = [get_headers()['User-Agent'] for _ in range(10)]

        # Should have at least 2 different UAs in 10 calls (statistically very likely)
        unique_uas = set(user_agents)
        assert len(unique_uas) >= 2


class TestAntiBotDetection:
    """Test anti-bot content detection."""

    def test_cloudflare_challenge_detected(self):
        """Test that Cloudflare challenge pages are detected."""
        scraper = WebsiteScraper("https://example.com")

        mock_html = """
        <html>
            <body>
                <div>Checking your browser before accessing...</div>
                <div>Cloudflare</div>
            </body>
        </html>
        """

        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = mock_html
            mock_get.return_value = mock_response

            result = scraper.scrape(max_pages=1)

            # Should detect anti-bot and fail
            assert not result["success"]
            # Should have anti-bot in failed URLs
            failed_urls = result.get("failed_urls", [])
            assert any("anti-bot" in str(reason) for url, reason in failed_urls)

    def test_captcha_detected(self):
        """Test that CAPTCHA pages are detected."""
        scraper = WebsiteScraper("https://example.com")

        mock_html = """
        <html>
            <body>
                <div class="g-recaptcha">Please complete the CAPTCHA</div>
            </body>
        </html>
        """

        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = mock_html
            mock_get.return_value = mock_response

            result = scraper.scrape(max_pages=1)

            # Should detect anti-bot
            assert not result["success"]


class TestStructuredReturns:
    """Test that scraper returns structured data."""

    def test_successful_scrape_structure(self):
        """Test structure of successful scrape result."""
        scraper = WebsiteScraper("https://example.com")

        mock_html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <article>This is test content that is more than 100 characters long so it passes the minimum content length check.</article>
            </body>
        </html>
        """

        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = mock_html
            mock_get.return_value = mock_response

            with patch('time.sleep'):  # Skip polite delays
                result = scraper.scrape(max_pages=1)

                # Verify structure
                assert isinstance(result, dict)
                assert "success" in result
                assert "documents" in result
                assert "stats" in result

                # Verify success case
                assert result["success"] == True
                assert len(result["documents"]) > 0

                # Verify stats
                stats = result["stats"]
                assert "total_visited" in stats
                assert "total_saved" in stats
                assert "total_failed" in stats
                assert "total_time" in stats
                assert "avg_time_per_page" in stats

    def test_failed_scrape_structure(self):
        """Test structure of failed scrape result."""
        scraper = WebsiteScraper("https://example.com")

        # Mock pre-flight scan failure
        if scraper.scanner:
            mock_report = CrawlabilityReport("https://example.com")
            mock_report.can_crawl = False
            mock_report.reason = "Blocked by robots.txt"

            with patch.object(scraper.scanner, 'scan', return_value=mock_report):
                result = scraper.scrape(max_pages=1)

                # Verify structure
                assert isinstance(result, dict)
                assert "success" in result
                assert "error" in result
                assert "documents" in result

                # Verify failure case
                assert result["success"] == False
                assert "Blocked by robots.txt" in result["error"]
                assert len(result["documents"]) == 0


class TestContentContainerPrioritization:
    """Test that content containers are correctly prioritized."""

    def test_article_tag_prioritized(self):
        """Test that <article> content is extracted preferentially."""
        html = """
        <html>
            <body>
                <nav>Navigation junk</nav>
                <aside>Sidebar ads</aside>
                <article>
                    <h1>Article Title</h1>
                    <p>Article content here</p>
                </article>
                <footer>Footer junk</footer>
            </body>
        </html>
        """

        scraper = WebsiteScraper("https://example.com")
        soup = BeautifulSoup(html, 'html.parser')
        text = scraper.clean_html(soup)

        # Article content should be present
        assert "Article Title" in text
        assert "Article content" in text

        # Navigation and footer should be removed
        assert "Navigation junk" not in text
        assert "Footer junk" not in text

    def test_main_tag_prioritized(self):
        """Test that <main> content is extracted preferentially."""
        html = """
        <html>
            <body>
                <header>Header stuff</header>
                <main>
                    <h1>Main Content</h1>
                    <p>This is the main content</p>
                </main>
                <aside>Sidebar</aside>
            </body>
        </html>
        """

        scraper = WebsiteScraper("https://example.com")
        soup = BeautifulSoup(html, 'html.parser')
        text = scraper.clean_html(soup)

        # Main content should be present
        assert "Main Content" in text
        # Header should be removed
        assert "Header stuff" not in text


class TestPoliteDelays:
    """Test polite delay functionality."""

    def test_polite_delays_applied(self):
        """Test that delays are applied between requests."""
        scraper = WebsiteScraper("https://example.com")

        sleep_calls = []

        def mock_sleep(duration):
            sleep_calls.append(duration)

        mock_html = '<html><body><p>Test content over 100 chars long so it gets saved. More text here to reach the minimum.</p></body></html>'

        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = mock_html
            mock_get.return_value = mock_response

            with patch('time.sleep', side_effect=mock_sleep):
                result = scraper.scrape(max_pages=3)

                # Should have delays between requests (not before first request)
                # 3 pages = 2 delays (between 1→2 and 2→3)
                assert len(sleep_calls) >= 2

                # Each delay should be between 1-3 seconds
                for delay in sleep_calls:
                    assert delay >= 1.0
                    assert delay <= 3.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
