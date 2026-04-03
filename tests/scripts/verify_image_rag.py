import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from zena_mode.scraper import WebsiteScraper
from bs4 import BeautifulSoup


def mock_html_with_images():
    """Mock html with images."""
    return """
    <html>
        <head><title>Test Page with Images</title></head>
        <body>
            <h1>Welcome to the extraction test</h1>
            <p>Here is a cute cat:</p>
            <img src="https://example.com/cat.jpg" alt="A cute kitten sleeping">
            <p>And a chart:</p>
            <img src="https://example.com/chart.png" alt="Sales Chart 2024">
            <div class="footer">Footer content</div>
        </body>
    </html>
    """


async def verify_image_extraction():
    """Verify image extraction."""
    print("🔍 Starting Image Extraction Verification...")

    scraper = WebsiteScraper("https://mock.test")
    soup = BeautifulSoup(mock_html_with_images(), "html.parser")

    # Test clean_html logic directly
    clean_text = scraper.clean_html(soup)

    print("\n--- Extracted Content ---")
    print(clean_text)
    print("-------------------------")

    # Validation
    if "![A cute kitten sleeping](https://example.com/cat.jpg)" in clean_text:
        print("✅ SUCCESS: Image 1 preserved as Markdown")
    else:
        print("❌ FAIL: Image 1 missing or malformed")

    if "![Sales Chart 2024](https://example.com/chart.png)" in clean_text:
        print("✅ SUCCESS: Image 2 preserved as Markdown")
    else:
        print("❌ FAIL: Image 2 missing or malformed")


if __name__ == "__main__":
    asyncio.run(verify_image_extraction())
