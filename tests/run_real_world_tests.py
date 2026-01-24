"""
Simple real-world test script (Windows-compatible, no emojis).
"""
import asyncio
import json
from datetime import datetime
import sys
sys.path.insert(0, '.')

from zena_mode.scraper import WebsiteScraper
from zena_mode.web_scanner import WebCrawlScanner


async def test_all_sites():
    """Test all real-world sites."""
    scanner = WebCrawlScanner()

    test_cases = [
        ("LinkedIn Profile", "https://www.linkedin.com/in/williamhgates/", False),
        ("Facebook Profile", "https://www.facebook.com/zuck", False),
        ("SEC EDGAR Search", "https://www.sec.gov/edgar/searchedgar/companysearch", True),
        ("SEC News", "https://www.sec.gov/news/pressreleases", True),
        ("Investopedia Article", "https://www.investopedia.com/terms/s/stock.asp", True),
        ("Investopedia Advisor", "https://www.investopedia.com/financial-advisor-4427709", True),
        ("Bloomberg Markets", "https://www.bloomberg.com/markets", False),
        ("Wikipedia Article", "https://en.wikipedia.org/wiki/Stock_market", True),
    ]

    results = []
    print("\n" + "="*80)
    print("RAG SCRAPER - REAL WORLD TEST RESULTS")
    print("="*80 + "\n")

    for name, url, expected_crawlable in test_cases:
        print(f"\nTesting: {name}")
        print(f"URL: {url}")
        print(f"Expected: {'ALLOW' if expected_crawlable else 'BLOCK'}")
        print("-" * 40)

        try:
            # Pre-flight scan
            report = await scanner.scan(url)

            result = {
                "name": name,
                "url": url,
                "expected_crawlable": expected_crawlable,
                "can_crawl": report.can_crawl,
                "reason": report.reason,
                "bot_protection": report.bot_protection,
                "requires_js": report.requires_js,
                "metadata": report.metadata
            }

            print(f"Result: {'ALLOW' if report.can_crawl else 'BLOCK'}")
            print(f"Reason: {report.reason}")
            if report.bot_protection:
                print(f"Protection Detected: {report.bot_protection}")
            if report.requires_js:
                print(f"Requires JavaScript: Yes")

            # Verify expectation
            if report.can_crawl == expected_crawlable:
                print("Status: PASS (matches expectation)")
                result["test_status"] = "PASS"
            else:
                print("Status: UNEXPECTED (differs from expectation)")
                result["test_status"] = "UNEXPECTED"

            # User guidance
            if not report.can_crawl:
                if "robots.txt" in report.reason:
                    print("Recommendation: Use manual copy-paste or API access")
                elif "Cloudflare" in str(report.bot_protection):
                    print("Recommendation: Use browser automation (Playwright/Selenium)")
                elif "LinkedIn" in str(report.bot_protection):
                    print("Recommendation: Use LinkedIn API or export data manually")
                elif "403" in report.reason:
                    print("Recommendation: Check if login required or use alternative source")
                elif "429" in report.reason:
                    print("Recommendation: Try again later or slow down requests")
                else:
                    print("Recommendation: Manual extraction or authenticated access")

            results.append(result)

        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                "name": name,
                "url": url,
                "error": str(e),
                "test_status": "ERROR"
            })

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    total = len(results)
    passed = sum(1 for r in results if r.get("test_status") == "PASS")
    unexpected = sum(1 for r in results if r.get("test_status") == "UNEXPECTED")
    errors = sum(1 for r in results if r.get("test_status") == "ERROR")

    print(f"\nTotal Sites Tested: {total}")
    print(f"Passed (Matched Expectation): {passed}")
    print(f"Unexpected Results: {unexpected}")
    print(f"Errors: {errors}")

    crawlable = sum(1 for r in results if r.get("can_crawl"))
    blocked = sum(1 for r in results if not r.get("can_crawl") and r.get("test_status") != "ERROR")

    print(f"\nCrawlability:")
    print(f"  Allowed: {crawlable}/{total}")
    print(f"  Blocked: {blocked}/{total}")

    # Protection types detected
    protections = {}
    for r in results:
        prot = r.get("bot_protection")
        if prot:
            protections[prot] = protections.get(prot, 0) + 1

    if protections:
        print(f"\nBot Protections Detected:")
        for prot, count in protections.items():
            print(f"  {prot}: {count} site(s)")

    # Save results
    output_file = "test_results_real_world.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": total,
                "passed": passed,
                "unexpected": unexpected,
                "errors": errors,
                "crawlable": crawlable,
                "blocked": blocked
            },
            "protections_detected": protections,
            "results": results
        }, f, indent=2)

    print(f"\nFull results saved to: {output_file}")

    return results


if __name__ == "__main__":
    print("Starting real-world site tests...")
    print("This may take 30-60 seconds...\n")
    asyncio.run(test_all_sites())
    print("\nTests complete!")
