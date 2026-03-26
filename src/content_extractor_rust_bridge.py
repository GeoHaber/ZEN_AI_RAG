"""
Bridge between Python content_extractor and optimized Rust implementations.

This module provides fallback logic:
1. Try to import and use Rust implementations (faster)
2. Fallback to Python implementations if Rust unavailable
3. Transparent API compatibility
"""

import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

# Track Rust availability
RUST_AVAILABLE = False
RUST_ERROR = None

try:
    # Try to import the compiled Rust extension
    import rag_rat_rust

    # Test that required functions exist
    assert hasattr(rag_rat_rust, "parse_image_dimension"), "Missing parse_image_dimension"
    assert hasattr(rag_rat_rust, "decode_response_text"), "Missing decode_response_text"
    assert hasattr(rag_rat_rust, "extract_images"), "Missing extract_images"

    RUST_AVAILABLE = True
    logger.info("✅ Rust extensions loaded (content_extractor optimizations available)")

except ImportError as e:
    RUST_ERROR = str(e)
    logger.warning(f"⚠️  Rust extensions not available: {e}")
    logger.info("   Falling back to pure Python implementations")
except (AssertionError, AttributeError) as e:
    RUST_ERROR = str(e)
    logger.warning(f"⚠️  Rust extension missing required functions: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# WRAPPER FUNCTIONS: Transparent fallback to Python
# ═══════════════════════════════════════════════════════════════════════════


def parse_image_dimension(value: str) -> Optional[int]:
    """
    Parse image width/height attribute safely.

    BUGFIX: Prevents "invalid literal for int()" on corrupted HTML attributes.

    Args:
        value: Attribute value (e.g., "100", "100px", "3dX\x19^\x03")

    Returns:
        Parsed integer or None if invalid/unreadable
    """
    if RUST_AVAILABLE:
        try:
            return rag_rat_rust.parse_image_dimension(value)
        except Exception as e:
            logger.warning(f"Rust parse_image_dimension failed: {e}, using Python fallback")

    # Python fallback: safe dimension parsing
    try:
        value_str = str(value).strip()
        # Extract leading digits only
        digits = "".join(c for c in value_str if c.isdigit())
        if not digits:
            return None
        return int(digits)
    except (ValueError, AttributeError, TypeError):
        return None


def decode_response_text(response_bytes: bytes, charset_hint: Optional[str] = None) -> str:
    """
    Decode HTTP response with robust encoding detection.

    BUGFIX: Handles malformed/binary responses with fallback chain.

    Args:
        response_bytes: Raw response body
        charset_hint: Charset from Content-Type header

    Returns:
        Decoded text with corruption replaced or filtered
    """
    if RUST_AVAILABLE:
        try:
            return rag_rat_rust.decode_response_text(response_bytes, charset_hint)
        except Exception as e:
            logger.warning(f"Rust decode_response_text failed: {e}, using Python fallback")

    # Python fallback: safe decoding with multiple strategies
    try:
        # Try explicit charset first
        if charset_hint:
            try:
                return response_bytes.decode(charset_hint, errors="replace")
            except (LookupError, TypeError):
                pass

        # Try UTF-8
        try:
            text = response_bytes.decode("utf-8", errors="strict")
            if len(text) > 0:
                return text
        except UnicodeDecodeError as exc:
            logger.debug("%s", exc)

        # UTF-8 with replacement
        text = response_bytes.decode("utf-8", errors="replace")
        if len(text) > 0 and text.count("\ufffd") < len(text) / 10:
            return text

        # Last resort: ISO-8859-1 (accepts all bytes)
        return response_bytes.decode("iso-8859-1", errors="replace")

    except Exception as e:
        logger.error(f"All decode strategies failed: {e}")
        # Absolute fallback: lossy decode ignoring all errors
        return response_bytes.decode("utf-8", errors="ignore")


def extract_images(html: str, page_url: str) -> List[Dict[str, str]]:
    """
    Extract image URLs from HTML with robust dimension handling.

    BUGFIX: Safely parses width/height attributes, filters corrupted data.

    Args:
        html: HTML content
        page_url: Base URL for relative link resolution

    Returns:
        List of image dicts with url, alt, source, width, height
    """
    if RUST_AVAILABLE:
        try:
            images = rag_rat_rust.extract_images(html, page_url)
            logger.debug(f"Rust extract_images found {len(images)} images")
            return images
        except Exception as e:
            logger.warning(f"Rust extract_images failed: {e}, using Python fallback")

    # Python fallback: regex-based image extraction
    import re
    from urllib.parse import urljoin

    images = []
    seen_srcs = set()

    # Find all img tags (simple regex that handles both quote types)
    for img_match in re.finditer(r'<img[^>]*src=["\']([^"\']+)["\']', html, re.IGNORECASE):
        src = img_match.group(1)
        if not src:
            continue

        # Normalize URL
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            src = urljoin(page_url, src)
        elif not src.startswith("http"):
            src = urljoin(page_url, src)

        # Skip junk patterns
        src_lower = src.lower()
        if any(
            x in src_lower
            for x in [
                "pixel",
                "tracking",
                "1x1",
                "spacer",
                "analytics",
                "beacon",
                "logo",
                "favicon",
            ]
        ):
            continue

        # Dedup
        if src in seen_srcs:
            continue
        seen_srcs.add(src)

        # Extract attributes from full match
        full_match = img_match.group(0)

        # Get width/height using safe parsing
        width_match = re.search(r'\swidth=["\']*([^\s=>]+)', full_match, re.IGNORECASE)
        width = width_match.group(1) if width_match else ""

        height_match = re.search(r'\sheight=["\']*([^\s=>]+)', full_match, re.IGNORECASE)
        height = height_match.group(1) if height_match else ""

        alt_match = re.search(r'\salt=["\']([^"\']*)["\']', full_match, re.IGNORECASE)
        alt = alt_match.group(1) if alt_match else ""

        # BUGFIX: Skip tiny images with safe dimension parsing
        if width:
            dim = parse_image_dimension(width)
            if dim and dim < 32:
                continue

        if height:
            dim = parse_image_dimension(height)
            if dim and dim < 32:
                continue

        images.append(
            {
                "url": src,
                "alt": alt,
                "source": page_url,
                "width": width,
                "height": height,
            }
        )

    return images[:500]  # Cap at 500 images


# ═══════════════════════════════════════════════════════════════════════════
# STATUS & DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════


def get_rust_status() -> Dict[str, any]:
    """Get status of Rust extensions."""
    return {
        "available": RUST_AVAILABLE,
        "error": RUST_ERROR,
        "version": rag_rat_rust.__version__ if RUST_AVAILABLE else None,
    }


def benchmark_parse_image_dimension():
    """Benchmark dimension parsing."""
    import time

    test_values = [
        "100",
        "100px",
        "   50  ",
        "invalid",
        "3dX\x19^\x03",  # Corrupted
        "none",
        "",
    ]

    print("\n" + "=" * 70)
    print("BENCHMARKING: parse_image_dimension()")
    print("=" * 70)

    # Rust version
    if RUST_AVAILABLE:
        start = time.perf_counter()
        for _ in range(1000):
            for val in test_values:
                rag_rat_rust.parse_image_dimension(val)
        rust_time = time.perf_counter() - start
        # [X-Ray auto-fix] print(f"✓ Rust (1000 iterations):   {rust_time * 1000:.2f}ms")
    else:
        rust_time = None
        print("✗ Rust not available")

    # Python version
    start = time.perf_counter()
    for _ in range(1000):
        for val in test_values:
            parse_image_dimension(val)
    py_time = time.perf_counter() - start
    # [X-Ray auto-fix] print(f"✓ Python (1000 iterations): {py_time * 1000:.2f}ms")
    if rust_time:
        speedup = py_time / rust_time
        # [X-Ray auto-fix] print(f"\n✓ Speedup: {speedup:.1f}x faster with Rust")
    print()


if __name__ == "__main__":
    # Test the bridge
    # [X-Ray auto-fix] print(f"Rust status: {get_rust_status()}")
    # Test dimension parsing
    print("\nTesting parse_image_dimension():")
    for val in ["100", "100px", "invalid", "3dX\x19^\x03", ""]:
        result = parse_image_dimension(val)
        # [X-Ray auto-fix] print(f"  {val!r:20} → {result}")
    # Run benchmark
    benchmark_parse_image_dimension()
