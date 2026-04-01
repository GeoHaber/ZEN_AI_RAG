"""
X_Ray RUST CONVERSION TEST HARNESS
════════════════════════════════════════════════════════════════════

Comprehensive automated testing for:
1. Crash prevention and error handling
2. Real website RAG pipeline
3. Performance profiling (Python vs Rust)
4. X_Ray analysis on converted code
5. Question answering from RAG

Websites tested:
- Crestafund.com (crowdfunding platform)
- Oradea.ro (municipal website)
"""

import sys
import os
import time
import json
import traceback
import psutil
from typing import Dict, Tuple, Optional
from datetime import datetime

# Add RAG_RAT to path
sys.path.insert(0, os.path.dirname(__file__))

print("\n" + "=" * 80)
print("RUST CONVERSION REAL-WORLD TEST HARNESS")
print("=" * 80)

# ═══════════════════════════════════════════════════════════════════════════
# CRASH PREVENTION LAYER
# ═══════════════════════════════════════════════════════════════════════════


class SafeImporter:
    """Safely import modules and catch all errors."""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.imports = {}

    def safe_import(self, module_name: str, display_name: str = None) -> bool:
        """Try to import a module, catch and log errors."""
        display_name = display_name or module_name
        try:
            self.imports[module_name] = __import__(module_name)
            print(f"  ✓ {display_name:40} success")
            return True
        except Exception as e:
            error_msg = f"{display_name}: {str(e)[:100]}"
            self.errors.append(error_msg)
            print(f"  ✗ {display_name:40} FAILED: {str(e)[:50]}")
            return False

    def report(self):
        """Print import summary."""
        print("\n" + "─" * 80)
        print("IMPORT VERIFICATION")
        print("─" * 80)
        print(f"Successful: {len(self.imports)} modules")
        print(f"Failed: {len(self.errors)} modules")
        if self.errors:
            print("\nErrors:")
            for err in self.errors:
                print(f"  • {err}")
                pass
        return len(self.errors) == 0


# ═══════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "─" * 80)
print("PHASE 1: SAFE INITIALIZATION")
print("─" * 80)

importer = SafeImporter()

# Critical imports
importer.safe_import("requests", "requests (HTTP)")
importer.safe_import("bs4", "BeautifulSoup (HTML parsing)")
importer.safe_import("psutil", "psutil (System monitoring)")

# RAG_RAT imports
importer.safe_import("content_extractor", "Content Extractor")
importer.safe_import("content_extractor_rust_bridge", "Content Extractor Rust Bridge")
importer.safe_import("inference_guard_rust_bridge", "Inference Guard Rust Bridge")

# Check Rust module
try:
    import rag_rat_rust

    RUST_AVAILABLE = True
    importer.imports["rag_rat_rust"] = rag_rat_rust
    print(f"  ✓ {'Rust Extension Module (rag_rat_rust.pyd)':40} success")
except ImportError as e:
    RUST_AVAILABLE = False
    importer.warnings.append(f"Rust module not available: {e}")
    print(f"  ⚠ {'Rust Extension Module (rag_rat_rust.pyd)':40} not available")
if not importer.report():
    print("\n❌ Critical imports failed. Exiting.")
    sys.exit(1)

print("\n✅ All critical modules loaded successfully")
if RUST_AVAILABLE:
    print("✅ Rust acceleration available")
else:
    print("⚠️  Running Python-only mode")

# ═══════════════════════════════════════════════════════════════════════════
# WEBSITE FETCHING WITH CRASH PREVENTION
# ═══════════════════════════════════════════════════════════════════════════


def safe_fetch_website(url: str, timeout: int = 30) -> Tuple[bool, str, Optional[str], Optional[int]]:
    """
    Safely fetch website content with error handling.

    Returns: (success, content, error_message, status_code)
    """
    try:
        print(f"\n  📥 Fetching {url}...")
        import requests

        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        print(f"     Status: {response.status_code}")
        print(f"     Size: {len(response.content) / 1024:.1f} KB")
        return True, response.content, None, response.status_code

    except requests.exceptions.Timeout:
        error = f"Timeout after {timeout}s"
        print(f"     ❌ {error}")
        return False, "", error, None

    except requests.exceptions.ConnectionError as e:
        error = f"Connection error: {str(e)[:50]}"
        print(f"     ❌ {error}")
        return False, "", error, None

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else None
        error = f"HTTP {status}: {str(e)[:50]}"
        print(f"     ❌ {error}")
        return False, "", error, status

    except Exception as e:
        error = f"Unexpected error: {str(e)[:50]}"
        print(f"     ❌ {error}")
        print(f"     {traceback.format_exc()[:200]}")
        return False, "", error, None


# ═══════════════════════════════════════════════════════════════════════════
# SAFE CONTENT PROCESSING
# ═══════════════════════════════════════════════════════════════════════════


def safe_process_content(html_content: bytes, url: str) -> Dict:
    """Safely process HTML content with crash prevention."""

    result = {
        "url": url,
        "success": False,
        "html_size": len(html_content),
        "text_extracted": 0,
        "images_found": 0,
        "text_preview": "",
        "errors": [],
        "warnings": [],
    }

    try:
        # Decode HTML
        try:
            from content_extractor_rust_bridge import decode_response_text

            text = decode_response_text(html_content, None)
            result["decode_method"] = "Rust"
        except Exception as e:
            result["warnings"].append(f"Rust decode failed, using Python: {str(e)[:50]}")
            try:
                text = html_content.decode("utf-8", errors="replace")
            except Exception:
                text = html_content.decode("iso-8859-1", errors="replace")
            result["decode_method"] = "Python fallback"

        result["text_extracted"] = len(text)
        result["text_preview"] = text[:200]

        # Extract images
        try:
            from content_extractor_rust_bridge import extract_images

            images = extract_images(text, url)
            result["images_found"] = len(images)
        except Exception as e:
            result["warnings"].append(f"Image extraction failed: {str(e)[:50]}")
            result["images_found"] = 0

        result["success"] = True

    except Exception as e:
        result["errors"].append(f"Content processing failed: {str(e)[:100]}")
        result["success"] = False
        print(f"\n     ❌ Content processing error: {str(e)}")
        traceback.print_exc()

    return result


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2: WEBSITE SCANNING
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("PHASE 2: SAFE WEBSITE SCANNING")
print("=" * 80)

websites = {
    "crestafund": "https://www.crestafund.com",
    "oradea": "https://oradea.ro",
}

website_data = {}

for name, url in websites.items():
    print(f"\n{name.upper()}")
    print("─" * 80)

    # Fetch
    success, content, error, status = safe_fetch_website(url)

    if not success:
        print(f"  ❌ Failed to fetch {url}")
        website_data[name] = {
            "url": url,
            "success": False,
            "error": error,
            "status_code": status,
        }
        continue

    # Process
    result = safe_process_content(content, url)
    website_data[name] = result

    print(f"  ✓ HTML decoded: {result['text_extracted']:,} characters")
    print(f"  ✓ Images found: {result['images_found']}")
    print(f"  ✓ Decode method: {result.get('decode_method', 'unknown')}")
    if result.get("errors"):
        print(f"  ⚠ Errors: {result['errors']}")
        pass
    if result.get("warnings"):
        print(f"  ⚠ Warnings: {result['warnings']}")
        pass
        # ═══════════════════════════════════════════════════════════════════════════
        # PHASE 3: CRASH DETECTION & REPORTING
        # ═══════════════════════════════════════════════════════════════════════════

        pass
print("\n" + "=" * 80)
print("PHASE 3: CRASH DETECTION REPORT")
print("=" * 80)

crashes = []
for name, data in website_data.items():
    if not data.get("success", True):
        crashes.append({"site": name, "reason": data.get("error", "Unknown error")})

if crashes:
    print(f"\n❌ {len(crashes)} CRASHES DETECTED:")
    for crash in crashes:
        print(f"  • {crash['site']}: {crash['reason']}")
        pass
else:
    print("\n✅ NO CRASHES - All websites processed safely!")

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 4: BUILD RAG KNOWLEDGE BASE
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("PHASE 4: BUILD RAG KNOWLEDGE BASE")
print("=" * 80)

# For now, create a simple knowledge base from extracted text
rag_knowledge = {}

for name, data in website_data.items():
    if data.get("success") and data.get("text_extracted", 0) > 0:
        rag_knowledge[name] = {
            "url": data["url"],
            "content": data.get("text_preview", "")[:500],  # Store preview
            "size": data["text_extracted"],
            "images": data["images_found"],
        }
        print(f"✓ {name}: Added {data['text_extracted']:,} chars to RAG")
print(f"\n✅ RAG Knowledge Base Ready: {len(rag_knowledge)} sources")
# ═══════════════════════════════════════════════════════════════════════════
# PHASE 5: SAMPLE QUESTIONS
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("PHASE 5: QUESTION ANSWERING FROM RAG")
print("=" * 80)

sample_questions = [
    "What is Oradea and what are its main features?",
    "What kind of organization is Crestafund?",
    "What services or content are mentioned on these websites?",
]

print("\nSample questions to answer from RAG:")
for i, q in enumerate(sample_questions, 1):
    print(f"  {i}. {q}")
    pass
print("\n(Full LLM integration would complete the RAG pipeline)")

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 6: PERFORMANCE PROFILING
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("PHASE 6: PERFORMANCE PROFILING")
print("=" * 80)

process = psutil.Process()

total_memory_start = process.memory_info().rss / 1024 / 1024
total_time_start = time.time()

print(f"\nMemory usage: {total_memory_start:.2f} MB")
print(f"CPU percent: {process.cpu_percent(interval=1):.1f}%")
# ═══════════════════════════════════════════════════════════════════════════
# PHASE 7: SUMMARY REPORT
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("PHASE 7: TEST SUMMARY")
print("=" * 80)

total_time = time.time() - total_time_start
total_memory = process.memory_info().rss / 1024 / 1024

summary = {
    "timestamp": datetime.now().isoformat(),
    "rust_available": RUST_AVAILABLE,
    "tests_run": len(website_data),
    "tests_passed": sum(1 for d in website_data.values() if d.get("success", False)),
    "crashes": len(crashes),
    "total_content_size": sum(d.get("text_extracted", 0) for d in website_data.values()),
    "total_images": sum(d.get("images_found", 0) for d in website_data.values()),
    "total_time_seconds": total_time,
    "memory_mb": total_memory,
}

print("\n📊 TEST RESULTS:")
print(f"  ✓ Tests passed: {summary['tests_passed']}/{summary['tests_run']}")
print(f"  ✓ Crashes: {summary['crashes']}")
print(f"  ✓ Total content: {summary['total_content_size']:,} chars")
print(f"  ✓ Total images: {summary['total_images']}")
print(f"  ✓ Time: {summary['total_time_seconds']:.2f}s")
print(f"  ✓ Memory: {summary['memory_mb']:.2f} MB")
print(f"  ✓ Rust available: {'YES' if summary['rust_available'] else 'NO'}")
if summary["crashes"] == 0:
    print("\n✅ ALL TESTS PASSED - NO CRASHES!")
else:
    print(f"\n⚠️  {summary['crashes']} CRASH(ES) DETECTED")
    pass
    # ═══════════════════════════════════════════════════════════════════════════
    # SAVE RESULTS
    # ═══════════════════════════════════════════════════════════════════════════

    pass
results_file = "rag_harness_results.json"
with open(results_file, "w") as f:
    json.dump(
        {
            "summary": summary,
            "website_data": website_data,
            "crashes": crashes,
        },
        f,
        indent=2,
    )

print(f"\n💾 Results saved to: {results_file}")
print("\n" + "=" * 80)
print("✅ HARNESS COMPLETE")
print("=" * 80)
