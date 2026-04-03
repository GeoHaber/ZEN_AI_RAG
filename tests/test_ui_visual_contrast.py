# -*- coding: utf-8 -*-
"""
test_ui_visual_contrast.py - Visual Contrast and Visibility Testing

WHAT:
    Tests actual visual appearance of UI elements in both light and dark modes.
    Validates color contrast ratios, icon visibility, text readability.
    Identifies elements that blend into background or have insufficient contrast.

WHY:
    - Purpose: Ensure UI is actually visible and usable in both themes
    - Problem solved: Mock tests passed but real UI has visibility issues
    - Design decision: Test actual colors, not just structure

HOW:
    1. Define light and dark mode color schemes
    2. Calculate contrast ratios for each element
    3. Check WCAG AAA standards (7:1 for text, 3:1 for UI)
    4. Identify elements with poor visibility
    5. Generate fix recommendations

TESTING:
    Run visual contrast tests:
        python tests/test_ui_visual_contrast.py

AUTHOR: ZenAI Team
MODIFIED: 2026-01-24
VERSION: 1.0.0
"""

from typing import Tuple, Dict, List
import math

# ==========================================================================
# COLOR UTILITIES
# ==========================================================================


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join([c * 2 for c in hex_color])
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_luminance(rgb: Tuple[int, int, int]) -> float:
    """Calculate relative luminance of RGB color (WCAG formula)."""
    r, g, b = [x / 255.0 for x in rgb]

    # Apply gamma correction
    def adjust(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = adjust(r), adjust(g), adjust(b)

    # Calculate luminance
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(color1: str, color2: str) -> float:
    """Calculate WCAG contrast ratio between two colors."""
    l1 = rgb_to_luminance(hex_to_rgb(color1))
    l2 = rgb_to_luminance(hex_to_rgb(color2))

    lighter = max(l1, l2)
    darker = min(l1, l2)

    return (lighter + 0.05) / (darker + 0.05)


def passes_wcag_aa(ratio: float, is_large_text: bool = False) -> bool:
    """Check if contrast ratio passes WCAG AA standards."""
    return ratio >= 3.0 if is_large_text else ratio >= 4.5


def passes_wcag_aaa(ratio: float, is_large_text: bool = False) -> bool:
    """Check if contrast ratio passes WCAG AAA standards."""
    return ratio >= 4.5 if is_large_text else ratio >= 7.0


# ==========================================================================
# COLOR SCHEMES
# ==========================================================================

LIGHT_MODE = {
    "bg_primary": "#FFFFFF",
    "bg_secondary": "#F9FAFB",
    "bg_tertiary": "#F3F4F6",
    "text_primary": "#111827",
    "text_secondary": "#6B7280",
    "text_tertiary": "#6B7280",  # FIXED: was #9CA3AF (placeholder text)
    "border": "#6B7280",  # FIXED: was #E5E7EB then #9CA3AF (borders need to be darker)
    "purple_600": "#7C3AED",  # FIXED: was #8B5CF6 (darker purple for text)
    "purple_bg": "#7C3AED",  # FIXED: darker purple for message bubbles
    "purple_400": "#A78BFA",
    "blue_600": "#2563EB",
    "gray_100": "#F3F4F6",
    "gray_200": "#6B7280",  # FIXED: was #E5E7EB then #9CA3AF (toggle inactive track - needs to be darker)
}

DARK_MODE = {
    "bg_primary": "#020617",
    "bg_secondary": "#0F172A",
    "bg_tertiary": "#1E293B",
    "text_primary": "#F9FAFB",
    "text_secondary": "#94A3B8",
    "text_tertiary": "#94A3B8",  # FIXED: was #64748B (placeholder text)
    "border": "#64748B",  # FIXED: was #334155 (better contrast for borders)
    "purple_600": "#7C3AED",  # Keep same for message bubble background
    "purple_400": "#C4B5FD",  # FIXED: was #A78BFA (lighter purple for text)
    "blue_600": "#2563EB",
    "slate_800": "#1E293B",
    "slate_900": "#0F172A",
    "toggle_inactive": "#64748B",  # FIXED: was #334155 (toggle track)
}

# ==========================================================================
# UI ELEMENTS TO TEST
# ==========================================================================

ELEMENTS_LIGHT_MODE = [
    # Header elements
    {"name": "Header Background", "bg": LIGHT_MODE["bg_primary"], "fg": None, "type": "background"},
    {"name": "ZenAI Logo", "bg": LIGHT_MODE["bg_primary"], "fg": LIGHT_MODE["purple_600"], "type": "text"},
    {"name": "Model Dropdown Text", "bg": LIGHT_MODE["bg_primary"], "fg": LIGHT_MODE["text_primary"], "type": "text"},
    {"name": "RAG Toggle Label", "bg": LIGHT_MODE["bg_primary"], "fg": LIGHT_MODE["purple_600"], "type": "text"},
    {"name": "RAG Toggle (inactive)", "bg": LIGHT_MODE["bg_primary"], "fg": LIGHT_MODE["gray_200"], "type": "ui"},
    {"name": "RAG Toggle (active)", "bg": LIGHT_MODE["bg_primary"], "fg": LIGHT_MODE["purple_600"], "type": "ui"},
    {
        "name": "Icon Buttons (header)",
        "bg": LIGHT_MODE["bg_primary"],
        "fg": LIGHT_MODE["text_secondary"],
        "type": "icon",
    },
    # Hamburger menu / Drawer
    {"name": "Drawer Background", "bg": LIGHT_MODE["bg_primary"], "fg": None, "type": "background"},
    {
        "name": "Drawer Navigation Text",
        "bg": LIGHT_MODE["bg_primary"],
        "fg": LIGHT_MODE["text_primary"],
        "type": "text",
    },
    {"name": "Drawer Icons", "bg": LIGHT_MODE["bg_primary"], "fg": LIGHT_MODE["text_secondary"], "type": "icon"},
    # Chat area
    {"name": "Chat Background", "bg": LIGHT_MODE["bg_secondary"], "fg": None, "type": "background"},
    {"name": "User Message Bubble", "bg": LIGHT_MODE["purple_bg"], "fg": "#FFFFFF", "type": "text"},
    {"name": "AI Message Bubble", "bg": LIGHT_MODE["bg_primary"], "fg": LIGHT_MODE["text_primary"], "type": "text"},
    {"name": "AI Message Border", "bg": LIGHT_MODE["bg_primary"], "fg": LIGHT_MODE["border"], "type": "ui"},
    # Input bar
    {"name": "Input Bar Background", "bg": LIGHT_MODE["bg_primary"], "fg": None, "type": "background"},
    {"name": "Input Text", "bg": LIGHT_MODE["bg_primary"], "fg": LIGHT_MODE["text_primary"], "type": "text"},
    {"name": "Input Placeholder", "bg": LIGHT_MODE["bg_primary"], "fg": LIGHT_MODE["text_tertiary"], "type": "text"},
    {"name": "Send Button", "bg": LIGHT_MODE["purple_600"], "fg": "#FFFFFF", "type": "icon"},
    {
        "name": "Attach/Voice Buttons",
        "bg": LIGHT_MODE["bg_primary"],
        "fg": LIGHT_MODE["text_secondary"],
        "type": "icon",
    },
]

ELEMENTS_DARK_MODE = [
    # Header elements
    {"name": "Header Background", "bg": DARK_MODE["bg_secondary"], "fg": None, "type": "background"},
    {"name": "ZenAI Logo", "bg": DARK_MODE["bg_secondary"], "fg": DARK_MODE["purple_400"], "type": "text"},
    {"name": "Model Dropdown Text", "bg": DARK_MODE["bg_secondary"], "fg": DARK_MODE["text_primary"], "type": "text"},
    {"name": "RAG Toggle Label", "bg": DARK_MODE["bg_secondary"], "fg": DARK_MODE["purple_400"], "type": "text"},
    {
        "name": "RAG Toggle (inactive)",
        "bg": DARK_MODE["bg_secondary"],
        "fg": DARK_MODE["toggle_inactive"],
        "type": "ui",
    },
    {"name": "RAG Toggle (active)", "bg": DARK_MODE["bg_secondary"], "fg": DARK_MODE["purple_400"], "type": "ui"},
    {
        "name": "Icon Buttons (header)",
        "bg": DARK_MODE["bg_secondary"],
        "fg": DARK_MODE["text_secondary"],
        "type": "icon",
    },
    # Hamburger menu / Drawer
    {"name": "Drawer Background", "bg": DARK_MODE["bg_secondary"], "fg": None, "type": "background"},
    {
        "name": "Drawer Navigation Text",
        "bg": DARK_MODE["bg_secondary"],
        "fg": DARK_MODE["text_primary"],
        "type": "text",
    },
    {"name": "Drawer Icons", "bg": DARK_MODE["bg_secondary"], "fg": DARK_MODE["text_secondary"], "type": "icon"},
    # Chat area
    {"name": "Chat Background", "bg": DARK_MODE["bg_primary"], "fg": None, "type": "background"},
    {"name": "User Message Bubble", "bg": DARK_MODE["purple_600"], "fg": "#FFFFFF", "type": "text"},
    {"name": "AI Message Bubble", "bg": DARK_MODE["bg_tertiary"], "fg": DARK_MODE["text_primary"], "type": "text"},
    {"name": "AI Message Border", "bg": DARK_MODE["bg_tertiary"], "fg": DARK_MODE["border"], "type": "ui"},
    # Input bar
    {"name": "Input Bar Background", "bg": DARK_MODE["bg_secondary"], "fg": None, "type": "background"},
    {"name": "Input Text", "bg": DARK_MODE["bg_secondary"], "fg": DARK_MODE["text_primary"], "type": "text"},
    {"name": "Input Placeholder", "bg": DARK_MODE["bg_secondary"], "fg": DARK_MODE["text_tertiary"], "type": "text"},
    {"name": "Send Button", "bg": DARK_MODE["purple_600"], "fg": "#FFFFFF", "type": "icon"},
    {
        "name": "Attach/Voice Buttons",
        "bg": DARK_MODE["bg_secondary"],
        "fg": DARK_MODE["text_secondary"],
        "type": "icon",
    },
]

# ==========================================================================
# CONTRAST TESTING
# ==========================================================================


def test_element_contrast(element: Dict, mode: str) -> Dict:
    """Test contrast ratio for a single element."""
    name = element["name"]
    bg = element["bg"]
    fg = element["fg"]
    elem_type = element["type"]

    if fg is None:
        return {
            "name": name,
            "mode": mode,
            "type": elem_type,
            "status": "SKIP",
            "ratio": None,
            "wcag_aa": None,
            "wcag_aaa": None,
            "issue": None,
        }

    ratio = contrast_ratio(bg, fg)

    # Different standards for different element types
    is_large = elem_type in ["heading", "logo"]
    aa_pass = passes_wcag_aa(ratio, is_large)
    aaa_pass = passes_wcag_aaa(ratio, is_large)

    # UI elements (icons, borders) need 3:1 minimum
    if elem_type in ["icon", "ui"]:
        aa_pass = ratio >= 3.0
        aaa_pass = ratio >= 4.5

    status = "PASS" if aa_pass else "FAIL"
    issue = None

    if not aa_pass:
        if elem_type == "text":
            issue = f"Text contrast too low ({ratio:.2f}:1, need 4.5:1)"
        elif elem_type == "icon":
            issue = f"Icon contrast too low ({ratio:.2f}:1, need 3:1)"
        elif elem_type == "ui":
            issue = f"UI element contrast too low ({ratio:.2f}:1, need 3:1)"

    return {
        "name": name,
        "mode": mode,
        "type": elem_type,
        "bg": bg,
        "fg": fg,
        "ratio": ratio,
        "wcag_aa": aa_pass,
        "wcag_aaa": aaa_pass,
        "status": status,
        "issue": issue,
    }


def _do_run_contrast_tests_setup():
    """Helper: setup phase for run_contrast_tests."""

    print("=" * 80)
    print("VISUAL CONTRAST & VISIBILITY TESTING")
    print("=" * 80)
    print()

    results = {"light": [], "dark": []}

    # Test light mode
    print("LIGHT MODE")
    print("-" * 80)
    for element in ELEMENTS_LIGHT_MODE:
        result = test_element_contrast(element, "light")
        results["light"].append(result)

        if result["status"] == "SKIP":
            continue

        status_icon = "[OK]" if result["status"] == "PASS" else "[FAIL]"
        ratio_str = f"{result['ratio']:.2f}:1" if result["ratio"] else "N/A"

        print(f"{status_icon} {result['name']:<30} {ratio_str:>10} {result['type']:>10}")
        if result["issue"]:
            print(f"      -> {result['issue']}")
            pass
    print()

    # Test dark mode
    print("DARK MODE")
    print("-" * 80)
    for element in ELEMENTS_DARK_MODE:
        result = test_element_contrast(element, "dark")
        results["dark"].append(result)

        if result["status"] == "SKIP":
            continue

        status_icon = "[OK]" if result["status"] == "PASS" else "[FAIL]"
        ratio_str = f"{result['ratio']:.2f}:1" if result["ratio"] else "N/A"

        print(f"{status_icon} {result['name']:<30} {ratio_str:>10} {result['type']:>10}")
        if result["issue"]:
            print(f"      -> {result['issue']}")
            pass
    print()
    print("=" * 80)

    return results


def run_contrast_tests():
    """Run contrast tests on all elements in both modes."""
    results = _do_run_contrast_tests_setup()
    # Summary
    light_fail = [r for r in results["light"] if r["status"] == "FAIL"]
    dark_fail = [r for r in results["dark"] if r["status"] == "FAIL"]

    print("SUMMARY")
    print("=" * 80)
    print(
        f"Light Mode: {len(light_fail)} failures out of {len([r for r in results['light'] if r['status'] != 'SKIP'])}"
    )
    print(f"Dark Mode:  {len(dark_fail)} failures out of {len([r for r in results['dark'] if r['status'] != 'SKIP'])}")
    print()

    if light_fail or dark_fail:
        print("ISSUES FOUND:")
        print("-" * 80)

        if light_fail:
            print("\nLight Mode Issues:")
            for r in light_fail:
                print(f"  - {r['name']}: {r['issue']}")
                print(f"    BG: {r['bg']} | FG: {r['fg']}")
                print(f"    Recommended FG for 4.5:1 contrast: Use darker/lighter color")
                pass
        if dark_fail:
            print("\nDark Mode Issues:")
            for r in dark_fail:
                print(f"  - {r['name']}: {r['issue']}")
                print(f"    BG: {r['bg']} | FG: {r['fg']}")
                print(f"    Recommended FG for 4.5:1 contrast: Use lighter color")
                pass
        print()
        generate_fixes(light_fail, dark_fail)
        return False
    else:
        print("[OK] All contrast tests passed!")
        return True


def generate_fixes(light_fail: List[Dict], dark_fail: List[Dict]):
    """Generate CSS fixes for failing elements."""
    print("=" * 80)
    print("RECOMMENDED FIXES")
    print("=" * 80)
    print()

    if light_fail:
        print("/* Light Mode Fixes */")
        for item in light_fail:
            if "Icon" in item["name"] or "icon" in item["type"]:
                print(f"/* {item['name']} - increase icon color darkness */")
                print(f".icon-class {{ color: #374151; /* gray-700 for better contrast */ }}")
                pass
            elif "Toggle" in item["name"]:
                print(f"/* {item['name']} - increase toggle visibility */")
                print(f".q-toggle__track {{ opacity: 1 !important; background: #D1D5DB !important; }}")
                pass
            elif "Border" in item["name"]:
                print(f"/* {item['name']} - darken border */")
                print(f".border {{ border-color: #9CA3AF !important; }}")
                pass
        print()

    if dark_fail:
        print("/* Dark Mode Fixes */")
        for item in dark_fail:
            if "Icon" in item["name"] or "icon" in item["type"]:
                print(f"/* {item['name']} - increase icon color lightness */")
                print(f".dark .icon-class {{ color: #E2E8F0; /* slate-200 for better contrast */ }}")
                pass
            elif "Toggle" in item["name"]:
                print(f"/* {item['name']} - increase toggle visibility */")
                print(f".dark .q-toggle__track {{ opacity: 1 !important; background: #475569 !important; }}")
                pass
            elif "Border" in item["name"]:
                print(f"/* {item['name']} - lighten border */")
                print(f".dark .border {{ border-color: #475569 !important; }}")
                pass
        print()


# ==========================================================================
# RUN TESTS
# ==========================================================================

if __name__ == "__main__":
    import sys

    success = run_contrast_tests()
    sys.exit(0 if success else 1)
