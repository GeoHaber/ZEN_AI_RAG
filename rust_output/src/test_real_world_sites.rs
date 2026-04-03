/// Real-world site testing for RAG scraper resilience.
/// 
/// Tests against actual sites:
/// - LinkedIn (high protection)
/// - Facebook (high protection)
/// - SEC.gov (government, should allow)
/// - Investopedia (financial advice)
/// - Bloomberg (financial news)
/// - Wikipedia (open access)

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;
use tokio;

/// Test scraper against real-world sites and document results.
#[derive(Debug, Clone)]
pub struct RealWorldTester {
    pub results: Vec<serde_json::Value>,
    pub timestamp: String /* datetime::now.strftime */,
}

impl RealWorldTester {
    pub fn new() -> Self {
        Self {
            results: vec![],
            timestamp: datetime::now().strftime("%Y-%m-%d %H:%M:%S".to_string()),
        }
    }
}

/// Test site part1 part2 part 4.
pub fn _test_site_part1_part2_part4(r#self: String) -> () {
    // Test site part1 part2 part 4.
    let mut scan_matches_expected = result.get(&"scan".to_string()).cloned().unwrap_or(HashMap::new()).get(&"can_crawl".to_string()).cloned() == expected_crawlable;
    if scan_matches_expected {
        println!("   ✅ Scanner prediction CORRECT");
        result["evaluation".to_string()] = "correct".to_string();
    } else {
        println!("   ⚠️  Scanner prediction UNEXPECTED");
        result["evaluation".to_string()] = "unexpected".to_string();
    }
    println!("\n💡 User Guidance");
    println!("{}", ("-".to_string() * 40));
    if !result.get(&"scan".to_string()).cloned().unwrap_or(HashMap::new()).get(&"can_crawl".to_string()).cloned().unwrap_or(true) {
        let mut reason = result.get(&"scan".to_string()).cloned().unwrap_or(HashMap::new()).get(&"reason".to_string()).cloned().unwrap_or("".to_string());
        let mut protection = result.get(&"scan".to_string()).cloned().unwrap_or(HashMap::new()).get(&"bot_protection".to_string()).cloned();
        if reason.contains(&"robots.txt".to_string()) {
            println!("{}", "   📋 This site blocks automated access via robots.txt".to_string());
            println!("{}", "   💡 Recommendation: Use manual copy-paste or API access".to_string());
        } else if protection == "Cloudflare".to_string() {
            println!("{}", "   🛡️  Cloudflare protection detected".to_string());
            println!("{}", "   💡 Recommendation: Use browser automation (Playwright/Selenium)".to_string());
        } else if (protection && protection.contains(&"LinkedIn".to_string())) {
            println!("{}", "   🛡️  LinkedIn high-precision filtering".to_string());
            println!("{}", "   💡 Recommendation: Use LinkedIn API or export data manually".to_string());
        } else if (reason.contains(&"403".to_string()) || reason.contains(&"Forbidden".to_string())) {
            println!("{}", "   🚫 Site returns 403 Forbidden".to_string());
            println!("{}", "   💡 Recommendation: Check if login is required or use alternative source".to_string());
        } else if (reason.contains(&"429".to_string()) || reason.contains(&"Rate".to_string())) {
            println!("{}", "   ⏱️  Rate limit detected".to_string());
            println!("{}", "   💡 Recommendation: Try again later or slow down requests".to_string());
        } else {
            println!("   ⚠️  Blocked: {}", reason);
            println!("{}", "   💡 Recommendation: Manual content extraction or authenticated access".to_string());
        }
    } else if result.get(&"scrape".to_string()).cloned().unwrap_or(HashMap::new()).get(&"success".to_string()).cloned() {
        println!("{}", "   ✅ Site successfully scraped!".to_string());
        println!("{}", "   💡 Content indexed and ready for RAG queries".to_string());
    } else {
        println!("{}", "   ⚠️  Scraping encountered issues".to_string());
        if result.get(&"scrape".to_string()).cloned().unwrap_or(HashMap::new()).get(&"warning".to_string()).cloned() {
            println!("   Warning: {}", result["scrape".to_string()]["warning".to_string()]);
        }
    }
    self.results.push(result);
    result
}

/// Test site part1 part 2.
pub fn _test_site_part1_part2(r#self: String, url: String) -> Result<()> {
    // Test site part1 part 2.
    let test_site = |url, expected_crawlable, category| {
        // Test a single site and document results.
        // 
        // Args:
        // url: Site URL to test
        // expected_crawlable: Whether we expect to be able to scrape
        // category: Site category (social, financial, government, etc.)
        println!("\n{}", ("=".to_string() * 80));
        println!("🔍 TESTING: {}", url);
        println!("   Category: {}", category);
        println!("   Expected: {}", if expected_crawlable { "✅ Crawlable".to_string() } else { "🛑 Blocked".to_string() });
        println!("{}\n", ("=".to_string() * 80));
        let mut result = HashMap::from([("url".to_string(), url), ("category".to_string(), category), ("expected_crawlable".to_string(), expected_crawlable), ("timestamp".to_string(), self.timestamp)]);
        println!("{}", "📡 Phase 1: Pre-flight Scan".to_string());
        println!("{}", ("-".to_string() * 40));
        let mut scanner = WebCrawlScanner();
        // try:
        {
            let mut scan_report = scanner.scan(url).await;
            result["scan".to_string()] = HashMap::from([("can_crawl".to_string(), scan_report.can_crawl), ("reason".to_string(), scan_report.reason), ("bot_protection".to_string(), scan_report.bot_protection), ("requires_js".to_string(), scan_report.requires_js), ("delay_suggestion".to_string(), scan_report.delay_suggestion), ("metadata".to_string(), scan_report.metadata)]);
            println!("   Can Crawl: {}", if scan_report.can_crawl { "✅ YES".to_string() } else { "🛑 NO".to_string() });
            println!("   Reason: {}", scan_report.reason);
            if scan_report.bot_protection {
                println!("   🛡️  Protection: {}", scan_report.bot_protection);
            }
            if scan_report.requires_js {
                println!("   ⚡ Requires JavaScript");
                // pass
            }
            if scan_report.metadata {
                println!("   📋 Metadata: {}", scan_report.metadata);
            }
        }
        // except Exception as e:
        println!("\n📝 Phase 2: Scraping Attempt");
        println!("{}", ("-".to_string() * 40));
        _test_site_part1(self, url);
    };
    Ok(_test_site_part1_part2_part4(self))
}

/// Test site part1 part 3.
pub fn _test_site_part1_part3(r#self: String) -> Result<()> {
    // Test site part1 part 3.
    let generate_report = || {
        // Generate comprehensive test report.
        println!("\n\n{}", ("=".to_string() * 80));
        println!("📊 COMPREHENSIVE TEST REPORT");
        println!("{}\n", ("=".to_string() * 80));
        println!("🕒 Test Run: {}", self.timestamp);
        println!("📈 Total Sites Tested: {}\n", self.results.len());
        let mut categories = HashMap::new();
        for r in self.results.iter() {
            let mut cat = r["category".to_string()];
            if !categories.contains(&cat) {
                categories[cat] = HashMap::from([("total".to_string(), 0), ("crawlable".to_string(), 0), ("blocked".to_string(), 0)]);
            }
            categories[&cat]["total".to_string()] += 1;
            if r.get(&"scan".to_string()).cloned().unwrap_or(HashMap::new()).get(&"can_crawl".to_string()).cloned().unwrap_or(false) {
                categories[&cat]["crawlable".to_string()] += 1;
            } else {
                categories[&cat]["blocked".to_string()] += 1;
            }
        }
        println!("{}", "📊 Summary by Category:".to_string());
        println!("{}", ("-".to_string() * 40));
        for (cat, stats) in categories.iter().iter() {
            println!("   {}:", cat);
            println!("      Total: {}", stats["total".to_string()]);
            println!("      ✅ Crawlable: {}", stats["crawlable".to_string()]);
            println!("      🛑 Blocked: {}", stats["blocked".to_string()]);
            // pass
        }
        println!("\n📋 Individual Site Results:");
        println!("{}", ("-".to_string() * 80));
        for (i, r) in self.results.iter().enumerate().iter() {
            let mut can_crawl = r.get(&"scan".to_string()).cloned().unwrap_or(HashMap::new()).get(&"can_crawl".to_string()).cloned().unwrap_or(false);
            let mut status = if can_crawl == r["expected_crawlable".to_string()] { "✅ PASS".to_string() } else { "⚠️  UNEXPECTED".to_string() };
            println!("\n{}. {}", i, r["url".to_string()]);
            println!("   Category: {}", r["category".to_string()]);
            println!("   Expected: {}", if r["expected_crawlable".to_string()] { "✅ Crawlable".to_string() } else { "🛑 Blocked".to_string() });
            println!("   Actual: {}", if can_crawl { "✅ Crawlable".to_string() } else { "🛑 Blocked".to_string() });
            println!("   Result: {}", status);
            if r.get(&"scan".to_string()).cloned().unwrap_or(HashMap::new()).get(&"bot_protection".to_string()).cloned() {
                println!("   Protection: {}", r["scan".to_string()]["bot_protection".to_string()]);
                // pass
            }
            if r.get(&"scrape".to_string()).cloned().unwrap_or(HashMap::new()).get(&"success".to_string()).cloned() {
                let mut docs = r["scrape".to_string()]["documents_count".to_string()];
                println!("   Scraped: {} pages", docs);
            }
        }
        let mut report_file = PathBuf::from("test_results_real_world.json".to_string());
        let mut f = File::create(report_file)?;
        {
            json::dump(HashMap::from([("timestamp".to_string(), self.timestamp), ("summary".to_string(), HashMap::from([("total_tested".to_string(), self.results.len()), ("by_category".to_string(), categories)])), ("results".to_string(), self.results)]), f, /* indent= */ 2);
        }
        println!("\n💾 Full results saved to: {}", report_file);
        self.results
    Ok(})
}

/// Test site part 1.
pub fn _test_site_part1(r#self: String, url: String) -> Result<()> {
    // Test site part 1.
    if (scan_report && !scan_report.can_crawl) {
        println!("   ⏭️  SKIPPED - Pre-flight scan blocked");
        result["scrape".to_string()] = HashMap::from([("skipped".to_string(), true), ("reason".to_string(), "pre-flight_blocked".to_string())]);
    } else {
        let mut scraper = WebsiteScraper(url);
        // try:
        {
            let mut scrape_result = scraper::scrape(/* max_pages= */ 3);
            result["scrape".to_string()] = HashMap::from([("success".to_string(), scrape_result["success".to_string()]), ("documents_count".to_string(), scrape_result.get(&"documents".to_string()).cloned().unwrap_or(vec![]).len()), ("stats".to_string(), scrape_result.get(&"stats".to_string()).cloned().unwrap_or(HashMap::new())), ("error".to_string(), scrape_result.get(&"error".to_string()).cloned()), ("warning".to_string(), scrape_result.get(&"warning".to_string()).cloned()), ("failed_urls_count".to_string(), scrape_result.get(&"failed_urls".to_string()).cloned().unwrap_or(vec![]).len())]);
            if scrape_result["success".to_string()] {
                let mut stats = scrape_result["stats".to_string()];
                println!("   ✅ SUCCESS");
                println!("   📄 Pages Saved: {}/{}", stats["total_saved".to_string()], stats["total_visited".to_string()]);
                println!("   ⏱️  Total Time: {:.2}s", stats["total_time".to_string()]);
                println!("   ⚡ Avg/Page: {:.2}s", stats["avg_time_per_page".to_string()]);
                if scrape_result.get(&"warning".to_string()).cloned() {
                    println!("   ⚠️  Warning: {}", scrape_result["warning".to_string()]);
                }
                if scrape_result["documents".to_string()] {
                    let mut first_doc = scrape_result["documents".to_string()][0];
                    let mut content_preview = first_doc["content".to_string()][..200];
                    println!("\n   📄 Sample Content:");
                    println!("      Title: {}", first_doc.get(&"title".to_string()).cloned().unwrap_or("N/A".to_string()));
                    println!("      Preview: {}...", content_preview);
                }
            } else {
                println!("   ❌ FAILED");
                println!("   Reason: {}", scrape_result.get(&"error".to_string()).cloned().unwrap_or("Unknown".to_string()));
                if scrape_result.get(&"protection".to_string()).cloned() {
                    println!("   🛡️  Protection: {}", scrape_result["protection".to_string()]);
                    // pass
                }
            }
        }
        // except Exception as e:
    }
    println!("\n📊 Evaluation");
    println!("{}", ("-".to_string() * 40));
    _test_site_part1_part2(self, url);
    Ok(_test_site_part1_part3(self))
}

/// Run all real-world tests.
pub async fn main() -> Result<()> {
    // Run all real-world tests.
    let mut tester = RealWorldTester();
    let mut test_cases = vec![("https://www.linkedin.com/in/williamhgates/".to_string(), false, "Social Media - LinkedIn".to_string()), ("https://www.facebook.com/zuck".to_string(), false, "Social Media - Facebook".to_string()), ("https://www.sec.gov/edgar/searchedgar/companysearch".to_string(), true, "Government - SEC EDGAR".to_string()), ("https://www.sec.gov/news/pressreleases".to_string(), true, "Government - SEC News".to_string()), ("https://www.investopedia.com/terms/s/stock.asp".to_string(), true, "Financial - Investopedia".to_string()), ("https://www.investopedia.com/financial-advisor-4427709".to_string(), true, "Financial - Investopedia Advisor".to_string()), ("https://www.bloomberg.com/markets".to_string(), false, "Financial News - Bloomberg".to_string()), ("https://en::wikipedia.org/wiki/Stock_market".to_string(), true, "Reference - Wikipedia".to_string())];
    for (url, expected_crawlable, category) in test_cases.iter() {
        // try:
        {
            tester.test_site(url, expected_crawlable, category).await;
        }
        // except KeyboardInterrupt as _e:
        // except Exception as _e:
    }
    Ok(tester.generate_report())
}
