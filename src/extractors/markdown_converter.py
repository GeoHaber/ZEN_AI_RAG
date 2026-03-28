import re
import logging
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


def _rows_to_markdown_table(rows: list, max_body_rows: int = 0) -> str:
    """Convert a list of row-lists into a Markdown table string."""
    if not rows:
        return ""
    max_cols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < max_cols:
            r.append("")
    lines = [
        "| " + " | ".join(rows[0]) + " |",
        "| " + " | ".join(["---"] * max_cols) + " |",
    ]
    body = rows[1:]
    if max_body_rows and len(body) > max_body_rows:
        body = body[:max_body_rows]
        for row in body:
            lines.append("| " + " | ".join(row) + " |")
        lines.append(f"*... {len(rows) - 1 - max_body_rows} more rows ...*")
    else:
        for row in body:
            lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _sanitize_text(text: str) -> str:
    """Remove surrogate chars, WP shortcodes, and widget artifacts."""
    if not text:
        return ""
    text = text.encode("utf-8", errors="surrogateescape").decode("utf-8", errors="replace")
    # Strip WordPress/VC shortcodes like [rev_slider_vc alias="..."]
    text = re.sub(r"\[/?[a-zA-Z_][a-zA-Z0-9_]*(?:\s[^\]]*)?]", "", text)
    # Strip common widget/plugin artifacts
    text = re.sub(r"(?i)^ZenAIos Widget.*$", "", text, flags=re.MULTILINE)
    # Collapse resulting blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


class HTMLToStructuredMarkdown:
    """
    Converts HTML soup into structured Markdown that preserves:
    - Heading hierarchy (# H1 → ###### H6)
    - Tables as Markdown tables
    - Ordered and unordered lists
    - Blockquotes
    - Code blocks (fenced)
    - Links with URLs
    - Bold/italic emphasis
    - Horizontal rules
    """

    NOISE_TAGS = {
        "nav",
        "footer",
        "header",
        "aside",
        "script",
        "style",
        "noscript",
        "svg",
        "form",
        "iframe",
    }
    NOISE_ATTR_KEYWORDS = {
        "menu",
        "sidebar",
        "banner",
        "footer",
        "nav",
        "social",
        "cookie",
        "advert",
        "sponsored",
        "widget",
    }

    _NOISE_PATTERNS = None
    _COMMENT_ARTEFACT_RE = re.compile(r"^(?:close\s+\w|end\s+\w|/\*|<!--|\[if\s)", re.IGNORECASE)

    def convert(self, soup: BeautifulSoup) -> str:
        """Convert a BeautifulSoup document into structured Markdown with boilerplate removal."""
        if not soup:
            return ""

        for tag in soup.find_all(self.NOISE_TAGS):
            tag.decompose()

        for tag in soup.find_all(attrs={"style": re.compile(r"display\s*:\s*none", re.I)}):
            tag.decompose()
        for tag in soup.find_all(attrs={"hidden": True}):
            tag.decompose()

        parts = []
        main = soup.find("main") or soup.find("article") or soup.find("body") or soup
        self._walk(main, parts)

        text = "\n".join(parts)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _is_noise_element(self, element: Tag) -> bool:
        if element.name in ("body", "html"):
            return False

        if HTMLToStructuredMarkdown._NOISE_PATTERNS is None:
            HTMLToStructuredMarkdown._NOISE_PATTERNS = [
                re.compile(r"(?:^|[\s_-])" + re.escape(kw) + r"(?:$|[\s_-])", re.I) for kw in self.NOISE_ATTR_KEYWORDS
            ]

        classes = element.get("class", [])
        for cls_token in classes:
            cls_lower = cls_token.lower()
            if cls_lower in self.NOISE_ATTR_KEYWORDS:
                return True
            for pat in HTMLToStructuredMarkdown._NOISE_PATTERNS:
                if pat.search(cls_lower):
                    return True

        eid = str(element.get("id", "")).lower()
        if eid:
            if eid in self.NOISE_ATTR_KEYWORDS:
                return True
            for pat in HTMLToStructuredMarkdown._NOISE_PATTERNS:
                if pat.search(eid):
                    return True

        return False

    def _walk(self, element, parts: list, depth: int = 0):
        if isinstance(element, str):
            stripped = element.strip()
            if stripped and not self._COMMENT_ARTEFACT_RE.match(stripped):
                parts.append(stripped)
            return

        if not isinstance(element, Tag):
            return

        if self._is_noise_element(element):
            return

        tag = element.name

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            text = element.get_text(strip=True)
            if text:
                parts.append(f"\n{'#' * level} {text}\n")
            return

        if tag == "table":
            md_table = self._table_to_markdown(element)
            if md_table:
                parts.append(f"\n{md_table}\n")
            return

        if tag in ("ul", "ol"):
            self._list_to_markdown(element, parts, ordered=(tag == "ol"), indent=depth)
            return

        if tag == "blockquote":
            text = element.get_text(strip=True)
            if text:
                lines = text.split("\n")
                quoted = "\n".join(f"> {line}" for line in lines)
                parts.append(f"\n{quoted}\n")
            return

        if tag == "pre":
            code = element.find("code")
            lang = ""
            if code:
                classes = code.get("class", [])
                for cls in classes:
                    if cls.startswith("language-") or cls.startswith("lang-"):
                        lang = cls.split("-", 1)[1]
                        break
                text = code.get_text()
            else:
                text = element.get_text()
            parts.append(f"\n```{lang}\n{text}\n```\n")
            return

        if tag == "code" and element.parent and element.parent.name != "pre":
            parts.append(f"`{element.get_text()}`")
            return

        if tag == "p":
            text = self._inline_text(element)
            if text.strip():
                parts.append(f"\n{text}\n")
            return

        if tag == "hr":
            parts.append("\n---\n")
            return

        if tag == "br":
            parts.append("\n")
            return

        if tag == "img":
            alt = element.get("alt", "").strip()
            if alt:
                parts.append(f"[Image: {alt}]")
            return

        if tag in ("strong", "b"):
            text = element.get_text(strip=True)
            if text:
                parts.append(f"**{text}**")
            return

        if tag in ("em", "i"):
            text = element.get_text(strip=True)
            if text:
                parts.append(f"*{text}*")
            return

        if tag == "a":
            href = element.get("href", "")
            text = element.get_text(strip=True)
            if text and href and href.startswith("http"):
                parts.append(f"[{text}]({href})")
            elif text:
                parts.append(text)
            return

        if tag == "dl":
            for child in element.children:
                if isinstance(child, Tag):
                    if child.name == "dt":
                        parts.append(f"\n**{child.get_text(strip=True)}**")
                    elif child.name == "dd":
                        parts.append(f": {child.get_text(strip=True)}")
            return

        for child in element.children:
            self._walk(child, parts, depth)

    def _inline_text(self, element) -> str:
        parts = []
        for child in element.children:
            if isinstance(child, str):
                parts.append(child)
            elif isinstance(child, Tag):
                if child.name in ("strong", "b"):
                    parts.append(f"**{child.get_text()}**")
                elif child.name in ("em", "i"):
                    parts.append(f"*{child.get_text()}*")
                elif child.name == "a":
                    href = child.get("href", "")
                    text = child.get_text()
                    if href.startswith("http"):
                        parts.append(f"[{text}]({href})")
                    else:
                        parts.append(text)
                elif child.name == "code":
                    parts.append(f"`{child.get_text()}`")
                elif child.name == "br":
                    parts.append("\n")
                else:
                    parts.append(child.get_text())
        return "".join(parts)

    def _table_to_markdown(self, table: Tag) -> str:
        rows = []
        for tr in table.find_all("tr"):
            cells = []
            for td in tr.find_all(["th", "td"]):
                text = td.get_text(strip=True).replace("|", "\\|")
                text = re.sub(r"\s+", " ", text)
                cells.append(text)
            if cells:
                rows.append(cells)
        if not rows:
            return ""
        return _rows_to_markdown_table(rows)

    def _list_to_markdown(self, element: Tag, parts: list, ordered: bool = False, indent: int = 0):
        prefix_space = "  " * indent
        counter = 1
        for li in element.find_all("li", recursive=False):
            nested = li.find(["ul", "ol"])
            text = ""
            for child in li.children:
                if isinstance(child, Tag) and child.name in ("ul", "ol"):
                    continue
                elif isinstance(child, Tag):
                    text += child.get_text(strip=True)
                elif isinstance(child, str):
                    text += child.strip()
            if text:
                marker = f"{counter}." if ordered else "-"
                parts.append(f"{prefix_space}{marker} {text}")
                counter += 1
            if nested:
                self._list_to_markdown(nested, parts, ordered=(nested.name == "ol"), indent=indent + 1)
