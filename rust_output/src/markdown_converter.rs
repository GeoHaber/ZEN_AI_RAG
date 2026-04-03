use anyhow::{Result, Context};
use regex::Regex;
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Converts HTML soup into structured Markdown that preserves:
/// - Heading hierarchy (# H1 → ###### H6)
/// - Tables as Markdown tables
/// - Ordered and unordered lists
/// - Blockquotes
/// - Code blocks (fenced)
/// - Links with URLs
/// - Bold/italic emphasis
/// - Horizontal rules
#[derive(Debug, Clone)]
pub struct HTMLToStructuredMarkdown {
}

impl HTMLToStructuredMarkdown {
    /// Convert a BeautifulSoup document into structured Markdown with boilerplate removal.
    pub fn convert(&mut self, soup: BeautifulSoup) -> String {
        // Convert a BeautifulSoup document into structured Markdown with boilerplate removal.
        if !soup {
            "".to_string()
        }
        for tag in soup.find_all(self.NOISE_TAGS).iter() {
            tag.decompose();
        }
        for tag in soup.find_all(/* attrs= */ HashMap::from([("style".to_string(), regex::Regex::new(&"display\\s*:\\s*none".to_string()).unwrap())])).iter() {
            tag.decompose();
        }
        for tag in soup.find_all(/* attrs= */ HashMap::from([("hidden".to_string(), true)])).iter() {
            tag.decompose();
        }
        let mut parts = vec![];
        let mut main = (soup.find(&*"main".to_string()).map(|i| i as i64).unwrap_or(-1) || soup.find(&*"article".to_string()).map(|i| i as i64).unwrap_or(-1) || soup.find(&*"body".to_string()).map(|i| i as i64).unwrap_or(-1) || soup);
        self._walk(main, parts);
        let mut text = parts.join(&"\n".to_string());
        let mut text = regex::Regex::new(&"\\n{3,}".to_string()).unwrap().replace_all(&"\n\n".to_string(), text).to_string();
        text.trim().to_string()
    }
    pub fn _is_noise_element(&mut self, element: Tag) -> bool {
        if ("body".to_string(), "html".to_string()).contains(&element.name) {
            false
        }
        if HTMLToStructuredMarkdown._NOISE_PATTERNS.is_none() {
            HTMLToStructuredMarkdown._NOISE_PATTERNS = self.NOISE_ATTR_KEYWORDS.iter().map(|kw| regex::Regex::new(&(("(?:^|[\\s_-])".to_string() + re::escape(kw)) + "(?:$|[\\s_-])".to_string())).unwrap()).collect::<Vec<_>>();
        }
        let mut classes = element.get(&"class".to_string()).cloned().unwrap_or(vec![]);
        for cls_token in classes.iter() {
            let mut cls_lower = cls_token.to_lowercase();
            if self.NOISE_ATTR_KEYWORDS.contains(&cls_lower) {
                true
            }
            for pat in HTMLToStructuredMarkdown._NOISE_PATTERNS.iter() {
                if pat.search(cls_lower) {
                    true
                }
            }
        }
        let mut eid = element.get(&"id".to_string()).cloned().unwrap_or("".to_string()).to_string().to_lowercase();
        if eid {
            if self.NOISE_ATTR_KEYWORDS.contains(&eid) {
                true
            }
            for pat in HTMLToStructuredMarkdown._NOISE_PATTERNS.iter() {
                if pat.search(eid) {
                    true
                }
            }
        }
        false
    }
    pub fn _walk(&mut self, element: String, parts: Vec<serde_json::Value>, depth: i64) -> () {
        if /* /* isinstance(element, str) */ */ true {
            let mut stripped = element.trim().to_string();
            if (stripped && !self._COMMENT_ARTEFACT_RE.match(stripped)) {
                parts.push(stripped);
            }
            return;
        }
        if !/* /* isinstance(element, Tag) */ */ true {
            return;
        }
        if self._is_noise_element(element) {
            return;
        }
        let mut tag = element.name;
        if ("h1".to_string(), "h2".to_string(), "h3".to_string(), "h4".to_string(), "h5".to_string(), "h6".to_string()).contains(&tag) {
            let mut level = tag[1].to_string().parse::<i64>().unwrap_or(0);
            let mut text = element.get_text(/* strip= */ true);
            if text {
                parts.push(format!("\n{} {}\n", ("#".to_string() * level), text));
            }
            return;
        }
        if tag == "table".to_string() {
            let mut md_table = self._table_to_markdown(element);
            if md_table {
                parts.push(format!("\n{}\n", md_table));
            }
            return;
        }
        if ("ul".to_string(), "ol".to_string()).contains(&tag) {
            self._list_to_markdown(element, parts, /* ordered= */ tag == "ol".to_string(), /* indent= */ depth);
            return;
        }
        if tag == "blockquote".to_string() {
            let mut text = element.get_text(/* strip= */ true);
            if text {
                let mut lines = text.split("\n".to_string()).map(|s| s.to_string()).collect::<Vec<String>>();
                let mut quoted = lines.iter().map(|line| format!("> {}", line)).collect::<Vec<_>>().join(&"\n".to_string());
                parts.push(format!("\n{}\n", quoted));
            }
            return;
        }
        if tag == "pre".to_string() {
            let mut code = element.find(&*"code".to_string()).map(|i| i as i64).unwrap_or(-1);
            let mut lang = "".to_string();
            if code {
                let mut classes = code.get(&"class".to_string()).cloned().unwrap_or(vec![]);
                for cls in classes.iter() {
                    if (cls.starts_with(&*"language-".to_string()) || cls.starts_with(&*"lang-".to_string())) {
                        let mut lang = cls.split("-".to_string(), 1)[1];
                        break;
                    }
                }
                let mut text = code.get_text();
            } else {
                let mut text = element.get_text();
            }
            parts.push(format!("\n```{}\n{}\n```\n", lang, text));
            return;
        }
        if (tag == "code".to_string() && element.parent().unwrap_or(std::path::Path::new("")) && element.parent().unwrap_or(std::path::Path::new("")).name != "pre".to_string()) {
            parts.push(format!("`{}`", element.get_text()));
            return;
        }
        if tag == "p".to_string() {
            let mut text = self._inline_text(element);
            if text.trim().to_string() {
                parts.push(format!("\n{}\n", text));
            }
            return;
        }
        if tag == "hr".to_string() {
            parts.push("\n---\n".to_string());
            return;
        }
        if tag == "br".to_string() {
            parts.push("\n".to_string());
            return;
        }
        if tag == "img".to_string() {
            let mut alt = element.get(&"alt".to_string()).cloned().unwrap_or("".to_string()).trim().to_string();
            if alt {
                parts.push(format!("[Image: {}]", alt));
            }
            return;
        }
        if ("strong".to_string(), "b".to_string()).contains(&tag) {
            let mut text = element.get_text(/* strip= */ true);
            if text {
                parts.push(format!("**{}**", text));
            }
            return;
        }
        if ("em".to_string(), "i".to_string()).contains(&tag) {
            let mut text = element.get_text(/* strip= */ true);
            if text {
                parts.push(format!("*{}*", text));
            }
            return;
        }
        if tag == "a".to_string() {
            let mut href = element.get(&"href".to_string()).cloned().unwrap_or("".to_string());
            let mut text = element.get_text(/* strip= */ true);
            if (text && href && href.starts_with(&*"http".to_string())) {
                parts.push(format!("[{}]({})", text, href));
            } else if text {
                parts.push(text);
            }
            return;
        }
        if tag == "dl".to_string() {
            for child in element.children.iter() {
                if /* /* isinstance(child, Tag) */ */ true {
                    if child.name == "dt".to_string() {
                        parts.push(format!("\n**{}**", child.get_text(/* strip= */ true)));
                    } else if child.name == "dd".to_string() {
                        parts.push(format!(": {}", child.get_text(/* strip= */ true)));
                    }
                }
            }
            return;
        }
        for child in element.children.iter() {
            self._walk(child, parts, depth);
        }
    }
    pub fn _inline_text(&self, element: String) -> String {
        let mut parts = vec![];
        for child in element.children.iter() {
            if /* /* isinstance(child, str) */ */ true {
                parts.push(child);
            } else if /* /* isinstance(child, Tag) */ */ true {
                if ("strong".to_string(), "b".to_string()).contains(&child.name) {
                    parts.push(format!("**{}**", child.get_text()));
                } else if ("em".to_string(), "i".to_string()).contains(&child.name) {
                    parts.push(format!("*{}*", child.get_text()));
                } else if child.name == "a".to_string() {
                    let mut href = child.get(&"href".to_string()).cloned().unwrap_or("".to_string());
                    let mut text = child.get_text();
                    if href.starts_with(&*"http".to_string()) {
                        parts.push(format!("[{}]({})", text, href));
                    } else {
                        parts.push(text);
                    }
                } else if child.name == "code".to_string() {
                    parts.push(format!("`{}`", child.get_text()));
                } else if child.name == "br".to_string() {
                    parts.push("\n".to_string());
                } else {
                    parts.push(child.get_text());
                }
            }
        }
        parts.join(&"".to_string())
    }
    pub fn _table_to_markdown(&self, table: Tag) -> String {
        let mut rows = vec![];
        for tr in table.find_all("tr".to_string()).iter() {
            let mut cells = vec![];
            for td in tr.find_all(vec!["th".to_string(), "td".to_string()]).iter() {
                let mut text = td.get_text(/* strip= */ true).replace(&*"|".to_string(), &*"\\|".to_string());
                let mut text = regex::Regex::new(&"\\s+".to_string()).unwrap().replace_all(&" ".to_string(), text).to_string();
                cells.push(text);
            }
            if cells {
                rows.push(cells);
            }
        }
        if !rows {
            "".to_string()
        }
        _rows_to_markdown_table(rows)
    }
    pub fn _list_to_markdown(&mut self, element: Tag, parts: Vec<serde_json::Value>, ordered: bool, indent: i64) -> () {
        let mut prefix_space = ("  ".to_string() * indent);
        let mut counter = 1;
        for li in element.find_all("li".to_string(), /* recursive= */ false).iter() {
            let mut nested = li.find(&*vec!["ul".to_string(), "ol".to_string()]).map(|i| i as i64).unwrap_or(-1);
            let mut text = "".to_string();
            for child in li.children.iter() {
                if (/* /* isinstance(child, Tag) */ */ true && ("ul".to_string(), "ol".to_string()).contains(&child.name)) {
                    continue;
                } else if /* /* isinstance(child, Tag) */ */ true {
                    text += child.get_text(/* strip= */ true);
                } else if /* /* isinstance(child, str) */ */ true {
                    text += child.trim().to_string();
                }
            }
            if text {
                let mut marker = if ordered { format!("{}.", counter) } else { "-".to_string() };
                parts.push(format!("{}{} {}", prefix_space, marker, text));
                counter += 1;
            }
            if nested {
                self._list_to_markdown(nested, parts, /* ordered= */ nested.name == "ol".to_string(), /* indent= */ (indent + 1));
            }
        }
    }
}

/// Convert a list of row-lists into a Markdown table string.
pub fn _rows_to_markdown_table(rows: Vec<serde_json::Value>, max_body_rows: i64) -> String {
    // Convert a list of row-lists into a Markdown table string.
    if !rows {
        "".to_string()
    }
    let mut max_cols = rows.iter().map(|r| r.len()).collect::<Vec<_>>().iter().max().unwrap();
    for r in rows.iter() {
        while r.len() < max_cols {
            r.push("".to_string());
        }
    }
    let mut lines = vec![(("| ".to_string() + rows[0].join(&" | ".to_string())) + " |".to_string()), (("| ".to_string() + (vec!["---".to_string()] * max_cols).join(&" | ".to_string())) + " |".to_string())];
    let mut body = rows[1..];
    if (max_body_rows && body.len() > max_body_rows) {
        let mut body = body[..max_body_rows];
        for row in body.iter() {
            lines.push((("| ".to_string() + row.join(&" | ".to_string())) + " |".to_string()));
        }
        lines.push(format!("*... {} more rows ...*", ((rows.len() - 1) - max_body_rows)));
    } else {
        for row in body.iter() {
            lines.push((("| ".to_string() + row.join(&" | ".to_string())) + " |".to_string()));
        }
    }
    lines.join(&"\n".to_string())
}

/// Remove surrogate chars, WP shortcodes, and widget artifacts.
pub fn _sanitize_text(text: String) -> String {
    // Remove surrogate chars, WP shortcodes, and widget artifacts.
    if !text {
        "".to_string()
    }
    let mut text = text.encode("utf-8".to_string(), /* errors= */ "surrogateescape".to_string()).decode("utf-8".to_string(), /* errors= */ "replace".to_string());
    let mut text = regex::Regex::new(&"\\[/?[a-zA-Z_][a-zA-Z0-9_]*(?:\\s[^\\]]*)?]".to_string()).unwrap().replace_all(&"".to_string(), text).to_string();
    let mut text = regex::Regex::new(&"(?i)^ZenAIos Widget.*$".to_string()).unwrap().replace_all(&"".to_string(), text).to_string();
    let mut text = regex::Regex::new(&"\\n{3,}".to_string()).unwrap().replace_all(&"\n\n".to_string(), text).to_string();
    text
}
