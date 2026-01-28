"""
Real-world site testing for RAG scraper resilience.

Tests against actual sites:
- LinkedIn (high protection)
- Facebook (high protection)
- SEC.gov (government, should allow)
- Investopedia (financial advice)
- Bloomberg (financial news)
- Wikipedia (open access)
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime

try:
    from zena_mode.scraper import WebsiteScraper
    from zena_mode.web_scanner import WebCrawlScanner
    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False
    print("❌ RAG modules not available")
    exit(1)


class RealWorldTester:
    """Test scraper against real-world sites and document results."""

    def __init__(self):
        self.results = []
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async def test_site(self, url: str, expected_crawlable: bool, category: str):
        """
        Test a single site and document results.

        Args:
            url: Site URL to test
            expected_crawlable: Whether we expect to be able to scrape
            category: Site category (social, financial, government, etc.)
        """
        print(f"\n{'='*80}")
        print(f"🔍 TESTING: {url}")
        print(f"   Category: {category}")
        print(f"   Expected: {'✅ Crawlable' if expected_crawlable else '🛑 Blocked'}")
        print(f"{'='*80}\n")

        result = {
            "url": url,
            "category": category,
            "expected_crawlable": expected_crawlable,
            "timestamp": self.timestamp
        }

        # Phase 1: Pre-flight scan
        print("📡 Phase 1: Pre-flight Scan")
        print("-" * 40)

        scanner = WebCrawlScanner()
        try:
            scan_report = await scanner.scan(url)

            result["scan"] = {
                "can_crawl": scan_report.can_crawl,
                "reason": scan_report.reason,
                "bot_protection": scan_report.bot_protection,
                "requires_js": scan_report.requires_js,
                "delay_suggestion": scan_report.delay_suggestion,
                "metadata": scan_report.metadata
            }

            print(f"   Can Crawl: {'✅ YES' if scan_report.can_crawl else '🛑 NO'}")
            print(f"   Reason: {scan_report.reason}")
            if scan_report.bot_protection:
                print(f"   🛡️  Protection: {scan_report.bot_protection}")
            if scan_report.requires_js:
                print(f"   ⚡ Requires JavaScript")
            if scan_report.metadata:
                print(f"   📋 Metadata: {scan_report.metadata}")

        except Exception as e:
            print(f"   ❌ Scan failed: {e}")
            result["scan"] = {"error": str(e)}
            scan_report = None

        # Phase 2: Actual scraping attempt (only if scan passed or we want to test anyway)
        print(f"\n📝 Phase 2: Scraping Attempt")
        print("-" * 40)

        if scan_report and not scan_report.can_crawl:
            print(f"   ⏭️  SKIPPED - Pre-flight scan blocked")
            result["scrape"] = {"skipped": True, "reason": "pre-flight_blocked"}
        else:
            scraper = WebsiteScraper(url)
            try:
                scrape_result = scraper.scrape(max_pages=3)  # Just 3 pages for testing

                result["scrape"] = {
                    "success": scrape_result["success"],
                    "documents_count": len(scrape_result.get("documents", [])),
                    "stats": scrape_result.get("stats", {}),
                    "error": scrape_result.get("error"),
                    "warning": scrape_result.get("warning"),
                    "failed_urls_count": len(scrape_result.get("failed_urls", []))
                }

                if scrape_result["success"]:
                    stats = scrape_result["stats"]
                    print(f"   ✅ SUCCESS")
                    print(f"   📄 Pages Saved: {stats['total_saved']}/{stats['total_visited']}")
                    print(f"   ⏱️  Total Time: {stats['total_time']:.2f}s")
                    print(f"   ⚡ Avg/Page: {stats['avg_time_per_page']:.2f}s")

                    if scrape_result.get("warning"):
                        print(f"   ⚠️  Warning: {scrape_result['warning']}")

                    # Show sample content
                    if scrape_result["documents"]:
                        first_doc = scrape_result["documents"][0]
                        content_preview = first_doc["content"][:200]
                        print(f"\n   📄 Sample Content:")
                        print(f"      Title: {first_doc.get('title', 'N/A')}")
                        print(f"      Preview: {content_preview}...")
                else:
                    print(f"   ❌ FAILED")
                    print(f"   Reason: {scrape_result.get('error', 'Unknown')}")
                    if scrape_result.get("protection"):
                        print(f"   🛡️  Protection: {scrape_result['protection']}")

            except Exception as e:
                print(f"   ❌ Scraping exception: {e}")
                result["scrape"] = {"error": str(e)}

        # Evaluation
        print(f"\n📊 Evaluation")
        print("-" * 40)

        scan_matches_expected = (
            result.get("scan", {}).get("can_crawl") == expected_crawlable
        )

        if scan_matches_expected:
            print(f"   ✅ Scanner prediction CORRECT")
            result["evaluation"] = "correct"
        else:
            print(f"   ⚠️  Scanner prediction UNEXPECTED")
            result["evaluation"] = "unexpected"

        # User guidance
        print(f"\n💡 User Guidance")
        print("-" * 40)

        if not result.get("scan", {}).get("can_crawl", True):
            reason = result.get("scan", {}).get("reason", "")
            protection = result.get("scan", {}).get("bot_protection")

            if "robots.txt" in reason:
                print("   📋 This site blocks automated access via robots.txt")
                print("   💡 Recommendation: Use manual copy-paste or API access")
            elif protection == "Cloudflare":
                print("   🛡️  Cloudflare protection detected")
                print("   💡 Recommendation: Use browser automation (Playwright/Selenium)")
            elif protection and "LinkedIn" in protection:
                print("   🛡️  LinkedIn high-precision filtering")
                print("   💡 Recommendation: Use LinkedIn API or export data manually")
            elif "403" in reason or "Forbidden" in reason:
                print("   🚫 Site returns 403 Forbidden")
                print("   💡 Recommendation: Check if login is required or use alternative source")
            elif "429" in reason or "Rate" in reason:
                print("   ⏱️  Rate limit detected")
                print("   💡 Recommendation: Try again later or slow down requests")
            else:
                print(f"   ⚠️  Blocked: {reason}")
                print("   💡 Recommendation: Manual content extraction or authenticated access")

        elif result.get("scrape", {}).get("success"):
            print("   ✅ Site successfully scraped!")
            print("   💡 Content indexed and ready for RAG queries")
        else:
            print("   ⚠️  Scraping encountered issues")
            if result.get("scrape", {}).get("warning"):
                print(f"   Warning: {result['scrape']['warning']}")

        self.results.append(result)
        return result

    def generate_report(self):
        """Generate comprehensive test report."""
        print(f"\n\n{'='*80}")
        print(f"📊 COMPREHENSIVE TEST REPORT")
        print(f"{'='*80}\n")

        print(f"🕒 Test Run: {self.timestamp}")
        print(f"📈 Total Sites Tested: {len(self.results)}\n")

        # Summary by category
        categories = {}
        for r in self.results:
            cat = r["category"]
            if cat not in categories:
                categories[cat] = {"total": 0, "crawlable": 0, "blocked": 0}
            categories[cat]["total"] += 1
            if r.get("scan", {}).get("can_crawl", False):
                categories[cat]["crawlable"] += 1
            else:
                categories[cat]["blocked"] += 1

        print("📊 Summary by Category:")
        print("-" * 40)
        for cat, stats in categories.items():
            print(f"   {cat}:")
            print(f"      Total: {stats['total']}")
            print(f"      ✅ Crawlable: {stats['crawlable']}")
            print(f"      🛑 Blocked: {stats['blocked']}")

        # Individual site results
        print(f"\n📋 Individual Site Results:")
        print("-" * 80)

        for i, r in enumerate(self.results, 1):
            can_crawl = r.get("scan", {}).get("can_crawl", False)
            status = "✅ PASS" if can_crawl == r["expected_crawlable"] else "⚠️  UNEXPECTED"

            print(f"\n{i}. {r['url']}")
            print(f"   Category: {r['category']}")
            print(f"   Expected: {'✅ Crawlable' if r['expected_crawlable'] else '🛑 Blocked'}")
            print(f"   Actual: {'✅ Crawlable' if can_crawl else '🛑 Blocked'}")
            print(f"   Result: {status}")

            if r.get("scan", {}).get("bot_protection"):
                print(f"   Protection: {r['scan']['bot_protection']}")

            if r.get("scrape", {}).get("success"):
                docs = r['scrape']['documents_count']
                print(f"   Scraped: {docs} pages")

        # Save to JSON
        report_file = Path("test_results_real_world.json")
        with open(report_file, "w") as f:
            json.dump({
                "timestamp": self.timestamp,
                "summary": {
                    "total_tested": len(self.results),
                    "by_category": categories
                },
                "results": self.results
            }, f, indent=2)

        print(f"\n💾 Full results saved to: {report_file}")

        return self.results


async def main():
    """Run all real-world tests."""
    tester = RealWorldTester()

    # Test sites
    test_cases = [
        # Social Media (HIGH PROTECTION)
        ("https://www.linkedin.com/in/williamhgates/", False, "Social Media - LinkedIn"),
        ("https://www.facebook.com/zuck", False, "Social Media - Facebook"),

        # Government / SEC (SHOULD ALLOW)
        ("https://www.sec.gov/edgar/searchedgar/companysearch", True, "Government - SEC EDGAR"),
        ("https://www.sec.gov/news/pressreleases", True, "Government - SEC News"),

        # Financial Advice (MAY ALLOW)
        ("https://www.investopedia.com/terms/s/stock.asp", True, "Financial - Investopedia"),
        ("https://www.investopedia.com/financial-advisor-4427709", True, "Financial - Investopedia Advisor"),

        # Financial News (MIXED)
        ("https://www.bloomberg.com/markets", False, "Financial News - Bloomberg"),  # Paywall expected

        # Open Access (SHOULD ALLOW)
        ("https://en.wikipedia.org/wiki/Stock_market", True, "Reference - Wikipedia"),
    ]

    for url, expected_crawlable, category in test_cases:
        try:
            await tester.test_site(url, expected_crawlable, category)
        except KeyboardInterrupt:
            print("\n\n⚠️  Test interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()

    # Generate final report
    tester.generate_report()


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    RAG SCRAPER - REAL WORLD TEST SUITE                       ║
║                                                                              ║
║  Testing against:                                                            ║
║  • LinkedIn & Facebook (High Protection)                                     ║
║  • SEC.gov (Government Sites)                                                ║
║  • Investopedia (Financial Advice)                                           ║
║  • Bloomberg (Financial News - Paywall)                                      ║
║  • Wikipedia (Open Access)                                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

    asyncio.run(main())
