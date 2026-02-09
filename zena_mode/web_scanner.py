# -*- coding: utf-8 -*-
"""
web_scanner.py - Intelligent Web Crawlability & Ethics Scanner
Checks robots.txt, anti-bot protection, and permission meta-tags.
"""
import httpx
import asyncio
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse, urljoin
import logging
import socket
from bs4 import BeautifulSoup

from utils import safe_print

logger = logging.getLogger("WebScanner")

class CrawlabilityReport:
    def __init__(self, url: str):
        self.url = url
        self.domain = urlparse(url).netloc
        self.can_crawl = True
        self.reason = "Ready to crawl"
        self.requires_js = False
        self.bot_protection = None # e.g., 'Cloudflare', 'Captcha'
        self.delay_suggestion = 1.0
        self.metadata = {}

    def __repr__(self):
        status = "✅ ALLOWED" if self.can_crawl else "❌ BLOCKED"
        return f"[{status}] {self.url} - {self.reason} (Protection: {self.bot_protection})"

class WebCrawlScanner:
    """
    Scans a target URL to determine if it is ethical and technically 
    possible to crawl using lightweight techniques.
    """
    
    def __init__(self, user_agent: str = "ZenAI-Bot/1.0"):
        self.user_agent = user_agent
        self.robot_parsers = {} # Cache for RobotFileParser objects

    async def get_robots_parser(self, domain: str) -> RobotFileParser:
        """Fetch and parse robots.txt for a given domain."""
        if domain in self.robot_parsers:
            return self.robot_parsers[domain]
        
        rp = RobotFileParser()
        robots_url = f"https://{domain}/robots.txt"
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(robots_url, timeout=5.0)
                if resp.status_code == 200:
                    rp.parse(resp.text.splitlines())
                else:
                    # If robots.txt doesn't exist, assume allowed
                    rp.allow_all = True
        except Exception as e:
            logger.warning(f"Failed to fetch robots.txt for {domain}: {e}")
            rp.allow_all = True
            
        self.robot_parsers[domain] = rp
        return rp

    async def scan(self, url: str) -> CrawlabilityReport:
        """
        Perform a comprehensive scan of the URL for crawlability.
        """
        report = CrawlabilityReport(url)
        
        # 1. Check robots.txt
        rp = await self.get_robots_parser(report.domain)
        if not rp.can_fetch(self.user_agent, url):
            report.can_crawl = False
            report.reason = "Blocked by robots.txt"
            return report

        # 2. Lightweight "Pre-flight" request
        try:
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(url, headers=headers, timeout=10.0)
                
                # Check status code
                high_difficulty_codes = [403, 429, 999, 1020, 406]
                if resp.status_code in high_difficulty_codes:
                    report.can_crawl = False
                    report.metadata["high_difficulty"] = True
                    if resp.status_code == 403: report.reason = "Forbidden (403)"
                    elif resp.status_code == 429: report.reason = "Rate Limited (429)"
                    elif resp.status_code == 999: report.reason = "Bot Block (LinkedIn/Generic)"
                    elif resp.status_code == 1020: report.reason = "Access Denied (Cloudflare 1020)"
                    else: report.reason = f"Block Status ({resp.status_code})"
                    return report
                
                # Check for anti-bot content & platform-specific filters
                html = resp.text.lower()
                
                # Broad Anti-Bot Detection Patterns (Improvement)
                protection_patterns = {
                    "cloudflare": "Cloudflare Ray ID",
                    "datadome": "DataDome Bot Protection",
                    "perimeterx": "PerimeterX Security",
                    "akamai": "Akamai Edge Computing",
                    "incapsula": "Imperva Incapsula",
                    "captcha": "CHALLENGE_CAPTCHA",
                    "g-recaptcha": "Google ReCaptcha",
                    "security check": "Generic AI/Bot Firewall",
                    "access denied": "Generic Gateway Filter"
                }
                
                for pattern, label in protection_patterns.items():
                    if pattern in html:
                        report.bot_protection = label
                        # Cloudflare doesn't always block, but Akamai/DataDome usually do for RAG
                        if pattern not in ["cloudflare", "access denied"]:
                            report.metadata["high_difficulty"] = True

                if "linkedin.com" in report.domain:
                    report.bot_protection = "LinkedIn High-Precision Filter"
                    if "/in/" in url:
                        report.metadata["high_difficulty"] = True
                        report.reason = "LinkedIn Profile (Highly Protected)"
                    else:
                        # General LinkedIn pages are typically Cloudflare-protected
                        report.bot_protection = "Cloudflare"
                        report.requires_js = True
                elif "captcha" in html or "g-recaptcha" in html:
                    report.bot_protection = "Captcha"
                    report.can_crawl = False
                    report.reason = "Captcha detected"
                elif "security check" in html:
                    report.bot_protection = "Generic Security"
                
                # Check for Cookie Banners (Improvement)
                cookie_keywords = ["cookie consent", "refuse all", "reject all", "allow all", "manage cookies"]
                if any(kw in html for kw in cookie_keywords):
                    report.metadata["cookie_banner_detected"] = True
                
                # Parse meta tags for robots instructions
                soup = BeautifulSoup(resp.text, 'html.parser')
                meta_robots = soup.find("meta", attrs={"name": "robots"})
                if meta_robots and meta_robots.get("content"):
                    content = meta_robots["content"].lower()
                    if "noindex" in content or "nocrawl" in content:
                        report.can_crawl = False
                        report.reason = "Blocked by meta-robots tag"
                
                # Check for legal/ack requirements
                acknowledgments = ["terms of service", "user agreement", "privacy policy", "do not scrape"]
                for ack in acknowledgments:
                    if ack in html:
                        report.metadata[f"found_{ack.replace(' ', '_')}"] = True

        except socket.gaierror:
            report.can_crawl = False
            report.reason = "Domain not found (Check for typos)"
        except httpx.ConnectError:
             report.can_crawl = False
             report.reason = "Connection failed (Server offline or invalid URL)"
        except Exception as e:
            report.can_crawl = False
            report.reason = f"Connection error: {str(e)}"
            
        return report

async def test_scanner():
    scanner = WebCrawlScanner()
    urls = [
        "https://www.google.com/search?q=test",
        "https://en.wikipedia.org/wiki/Python_(programming_language)",
        "https://github.com/trending"
    ]
    for url in urls:
        report = await scanner.scan(url)
        safe_print(report)

if __name__ == "__main__":
    asyncio.run(test_scanner())
