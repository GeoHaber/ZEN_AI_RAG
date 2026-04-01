import requests
import logging
from bs4 import BeautifulSoup

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LinkedInDiagnose")


def diagnose_url(url):
    """Diagnose url."""
    print(f"\n🔍 Diagnosing URL: {url}")
    print("-" * 50)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"📡 HTTP Status: {response.status_code}")
        print(f"📏 Response Length: {len(response.text)} bytes")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.title.string if soup.title else "No title"
            print(f"📑 Page Title: {title}")
            # Check for common bot detection patterns
            if "authwall" in response.url or "security-check" in response.text.lower():
                print("⚠️  DETECTED: Redirected to Authwall/Security check.")

            text = soup.get_text()
            print(f"📝 Extracted Text Preview (first 200 chars):\n{text.strip()[:200]}...")
            if len(text.strip()) < 100:
                print("❌ ERROR: Very little text extracted. JavaScript rendering might be required.")
        else:
            print(f"❌ ERROR: Received non-200 status code.")
            if response.status_code == 403:
                print("💡 Suggestion: Site is blocking basic requests (Forbidden).")
            elif response.status_code == 999:
                print("💡 Suggestion: LinkedIn specific request rejection code.")

    except Exception:
        print(f"❌ EXCEPTION: {e}")
        pass


if __name__ == "__main__":
    url = "https://www.linkedin.com/in/georgehaber/"
    diagnose_url(url)
