/// Simple real-world test script (Windows-compatible, no emojis).

use anyhow::{Result, Context};
use crate::scraper::{WebsiteScraper};
use crate::web_scanner::{WebCrawlScanner};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use tokio;

/// Test all sites part 1.
pub fn _test_all_sites_part1() -> Result<()> {
    // Test all sites part 1.
    println!("{}", ("\n".to_string() + ("=".to_string() * 80)));
    println!("{}", "SUMMARY".to_string());
    println!("{}", ("=".to_string() * 80));
    let mut total = results.len();
    let mut passed = results.iter().filter(|r| r.get(&"test_status".to_string()).cloned() == "PASS".to_string()).map(|r| 1).collect::<Vec<_>>().iter().sum::<i64>();
    let mut unexpected = results.iter().filter(|r| r.get(&"test_status".to_string()).cloned() == "UNEXPECTED".to_string()).map(|r| 1).collect::<Vec<_>>().iter().sum::<i64>();
    let mut errors = results.iter().filter(|r| r.get(&"test_status".to_string()).cloned() == "ERROR".to_string()).map(|r| 1).collect::<Vec<_>>().iter().sum::<i64>();
    println!("\nTotal Sites Tested: {}", total);
    println!("Passed (Matched Expectation): {}", passed);
    println!("Unexpected Results: {}", unexpected);
    println!("Errors: {}", errors);
    let mut crawlable = results.iter().filter(|r| r.get(&"can_crawl".to_string()).cloned()).map(|r| 1).collect::<Vec<_>>().iter().sum::<i64>();
    let mut blocked = results.iter().filter(|r| (!r.get(&"can_crawl".to_string()).cloned() && r.get(&"test_status".to_string()).cloned() != "ERROR".to_string())).map(|r| 1).collect::<Vec<_>>().iter().sum::<i64>();
    println!("\nCrawlability:");
    println!("  Allowed: {}/{}", crawlable, total);
    println!("  Blocked: {}/{}", blocked, total);
    let mut protections = HashMap::new();
    for r in results.iter() {
        let mut prot = r.get(&"bot_protection".to_string()).cloned();
        if prot {
            protections[prot] = (protections.get(&prot).cloned().unwrap_or(0) + 1);
        }
    }
    if protections {
        println!("\nBot Protections Detected:");
        for (prot, count) in protections.iter().iter() {
            println!("  {}: {} site(s)", prot, count);
            // pass
        }
    }
    let mut output_file = "test_results_real_world.json".to_string();
    let mut f = File::create(output_file)?;
    {
        json::dump(HashMap::from([("timestamp".to_string(), datetime::now().isoformat()), ("summary".to_string(), HashMap::from([("total".to_string(), total), ("passed".to_string(), passed), ("unexpected".to_string(), unexpected), ("errors".to_string(), errors), ("crawlable".to_string(), crawlable), ("blocked".to_string(), blocked)])), ("protections_detected".to_string(), protections), ("results".to_string(), results)]), f, /* indent= */ 2);
    }
}

/// Test all real-world sites.
pub async fn test_all_sites() -> Result<()> {
    // Test all real-world sites.
    let mut scanner = WebCrawlScanner();
    let mut test_cases = vec![("LinkedIn Profile".to_string(), "https://www.linkedin.com/in/williamhgates/".to_string(), false), ("Facebook Profile".to_string(), "https://www.facebook.com/zuck".to_string(), false), ("SEC EDGAR Search".to_string(), "https://www.sec.gov/edgar/searchedgar/companysearch".to_string(), true), ("SEC News".to_string(), "https://www.sec.gov/news/pressreleases".to_string(), true), ("Investopedia Article".to_string(), "https://www.investopedia.com/terms/s/stock.asp".to_string(), true), ("Investopedia Advisor".to_string(), "https://www.investopedia.com/financial-advisor-4427709".to_string(), true), ("Bloomberg Markets".to_string(), "https://www.bloomberg.com/markets".to_string(), false), ("Wikipedia Article".to_string(), "https://en::wikipedia.org/wiki/Stock_market".to_string(), true)];
    let mut results = vec![];
    println!("{}", ("\n".to_string() + ("=".to_string() * 80)));
    println!("{}", "RAG SCRAPER - REAL WORLD TEST RESULTS".to_string());
    println!("{}", (("=".to_string() * 80) + "\n".to_string()));
    for (name, url, expected_crawlable) in test_cases.iter() {
        println!("\nTesting: {}", name);
        println!("URL: {}", url);
        println!("Expected: {}", if expected_crawlable { "ALLOW".to_string() } else { "BLOCK".to_string() });
        println!("{}", ("-".to_string() * 40));
        // try:
        {
            let mut report = scanner.scan(url).await;
            let mut result = HashMap::from([("name".to_string(), name), ("url".to_string(), url), ("expected_crawlable".to_string(), expected_crawlable), ("can_crawl".to_string(), report.can_crawl), ("reason".to_string(), report.reason), ("bot_protection".to_string(), report.bot_protection), ("requires_js".to_string(), report.requires_js), ("metadata".to_string(), report.metadata)]);
            println!("Result: {}", if report.can_crawl { "ALLOW".to_string() } else { "BLOCK".to_string() });
            println!("Reason: {}", report.reason);
            if report.bot_protection {
                println!("Protection Detected: {}", report.bot_protection);
            }
            if report.requires_js {
                println!("Requires JavaScript: Yes");
                // pass
            }
            if report.can_crawl == expected_crawlable {
                println!("{}", "Status: PASS (matches expectation)".to_string());
                result["test_status".to_string()] = "PASS".to_string();
            } else {
                println!("{}", "Status: UNEXPECTED (differs from expectation)".to_string());
                result["test_status".to_string()] = "UNEXPECTED".to_string();
            }
            if !report.can_crawl {
                if report.reason.contains(&"robots.txt".to_string()) {
                    println!("{}", "Recommendation: Use manual copy-paste or API access".to_string());
                } else if report.bot_protection.to_string().contains(&"Cloudflare".to_string()) {
                    println!("{}", "Recommendation: Use browser automation (Playwright/Selenium)".to_string());
                } else if report.bot_protection.to_string().contains(&"LinkedIn".to_string()) {
                    println!("{}", "Recommendation: Use LinkedIn API or export data manually".to_string());
                } else if report.reason.contains(&"403".to_string()) {
                    println!("{}", "Recommendation: Check if login required or use alternative source".to_string());
                } else if report.reason.contains(&"429".to_string()) {
                    println!("{}", "Recommendation: Try again later or slow down requests".to_string());
                } else {
                    println!("{}", "Recommendation: Manual extraction or authenticated access".to_string());
                }
            }
            results.push(result);
        }
        // except Exception as e:
    }
    _test_all_sites_part1();
    println!("\nFull results saved to: {}", output_file);
    Ok(results)
}
