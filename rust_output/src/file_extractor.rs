use anyhow::{Result, Context};
use crate::markdown_converter::{_rows_to_markdown_table, _sanitize_text};
use std::collections::HashMap;
use std::collections::HashSet;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static _PDFPLUMBER: std::sync::LazyLock<_try_import> = std::sync::LazyLock::new(|| Default::default());

pub static _PYPDF2: std::sync::LazyLock<_try_import> = std::sync::LazyLock::new(|| Default::default());

pub static _DOCX: std::sync::LazyLock<_try_import> = std::sync::LazyLock::new(|| Default::default());

pub static _OPENPYXL: std::sync::LazyLock<_try_import> = std::sync::LazyLock::new(|| Default::default());

pub static _PPTX: std::sync::LazyLock<_try_import> = std::sync::LazyLock::new(|| Default::default());

pub static _STRIPRTF: std::sync::LazyLock<_try_import> = std::sync::LazyLock::new(|| Default::default());

pub static _CHARDET: std::sync::LazyLock<_try_import> = std::sync::LazyLock::new(|| Default::default());

#[derive(Debug, Clone)]
pub struct FolderScanner {
    pub unknown_extensions: HashMap<String, serde_json::Value>,
}

impl FolderScanner {
    pub fn new(max_depth: String, max_files: String, max_chars_total: String, max_chars_per_file: String) -> Self {
        Self {
            unknown_extensions: HashMap::new(),
        }
    }
    pub fn scan(&mut self, folder: String, progress_callback: String, completed_items: String) -> () {
        let mut root_path = PathBuf::from(folder).canonicalize().unwrap_or_default();
        let mut files = self._collect_files(root_path, root_path, self.max_depth)[..self.max_files];
        let (mut all_text, mut all_sources) = (vec![], vec![]);
        let mut total_chars = 0;
        for (i, fpath) in files.iter().enumerate().iter() {
            if total_chars >= self.max_chars_total {
                break;
            }
            if (completed_items && completed_items.contains(&fpath.to_string())) {
                continue;
            }
            if progress_callback {
                progress_callback((i + 1), files.len(), format!("{}", fpath.file_name().unwrap_or_default().to_str().unwrap_or("")));
            }
            let (mut text, mut images) = self._extract_file(fpath);
            if !text {
                continue;
            }
            if text.len() > self.max_chars_per_file {
                let mut text = (text[..self.max_chars_per_file] + "...".to_string());
            }
            all_text.push((format!("=== FILE: {} ===\n", fpath.file_name().unwrap_or_default().to_str().unwrap_or("")) + text));
            all_sources.push(HashMap::from([("type".to_string(), fpath.extension().unwrap_or_default().to_str().unwrap_or("")), ("path".to_string(), fpath.to_string()), ("chars".to_string(), text.len())]));
            total_chars += text.len();
        }
        (all_text.join(&"\n\n".to_string()), vec![], all_sources)
    }
    pub fn _collect_files(&mut self, root: String, folder: String, max_depth: String, depth: String) -> Result<()> {
        if depth >= max_depth {
            vec![]
        }
        let mut files = vec![];
        // try:
        {
            for item in folder.iterdir().iter() {
                if item.name.starts_with(&*(".".to_string(), "__".to_string())) {
                    continue;
                }
                if (item.is_file() && _get_file_extractor(item.extension().unwrap_or_default().to_str().unwrap_or(""))) {
                    files.push(item);
                } else if item.is_dir() {
                    files.extend(self._collect_files(root, item, max_depth, (depth + 1)));
                }
            }
        }
        // except Exception as exc:
        Ok(files)
    }
    pub fn _extract_file(&self, path: PathBuf) -> Result<()> {
        let mut ext = path.extension().unwrap_or_default().to_str().unwrap_or("").to_lowercase();
        let mut extractor = _get_file_extractor(ext);
        if !extractor {
            ("".to_string(), vec![])
        }
        let (mut kind, mut handler) = extractor;
        // try:
        {
            if kind == "rich".to_string() {
                handler(path)
            }
            if kind == "text".to_string() {
                (handler(path), vec![])
            }
            (_read_text_file(path), vec![])
        }
        // except Exception as _e:
    }
}

pub fn _try_import(name: String) -> Result<()> {
    // try:
    {
        __import__(name)
    }
    // except ImportError as _e:
}

pub fn _read_text_file(path: PathBuf) -> String {
    let mut raw = path.read_bytes();
    let mut enc = if _chardet { (_chardet.detect(raw[..10000]).get(&"encoding".to_string()).cloned() || "utf-8".to_string()) } else { "utf-8".to_string() };
    raw.decode(enc, /* errors= */ "replace".to_string())
}

pub fn _get_excel_rag_limits() -> Result<(i64, i64)> {
    // try:
    {
        // TODO: from config_system import config
        let mut max_rows = /* getattr */ 500;
        (if max_rows { max_rows.to_string().parse::<i64>().unwrap_or(0) } else { 500 }, 12000)
    }
    // except Exception as _e:
}

pub fn _extract_pdf(path: PathBuf) -> Result<(String, Vec<HashMap>)> {
    let mut images = vec![];
    if _pdfplumber {
        // try:
        {
            let mut parts = vec![];
            let mut pdf = _pdfplumber.open(path.to_string());
            {
                for (i, page) in pdf.pages.iter().enumerate().iter() {
                    parts.push(format!("\n--- Page {} ---\n", (i + 1)));
                    let mut text = page.extract_text();
                    if ((!text || text.trim().to_string().len() < 10) && _HAS_OCR) {
                        // try:
                        {
                            let mut ocr_text = pytesseract.image_to_string(page.to_image(/* resolution= */ 300).original);
                            if ocr_text {
                                let mut text = format!("[OCR]\n{}", ocr_text);
                            }
                        }
                        // except Exception as exc:
                    }
                    if text {
                        parts.push(text);
                    }
                    let mut tables = page.extract_tables();
                    for table in tables.iter() {
                        let mut rows = table.iter().map(|r| r.iter().map(|c| (c || "".to_string()).to_string().trim().to_string().replace(&*"|".to_string(), &*"\\|".to_string())).collect::<Vec<_>>()).collect::<Vec<_>>();
                        if rows {
                            parts.push(format!("\n{}", _rows_to_markdown_table(rows)));
                        }
                    }
                }
            }
            (_sanitize_text(parts.join(&"\n".to_string())), images)
        }
        // except Exception as exc:
    }
    if _PyPDF2 {
        // try:
        {
            let mut parts = vec![];
            let mut f = File::open(path)?;
            {
                let mut reader = _PyPDF2.PdfReader(f);
                for (i, page) in reader.pages.iter().enumerate().iter() {
                    let mut text = page.extract_text();
                    if text {
                        parts.push(format!("\n--- Page {} ---\n{}", (i + 1), text));
                    }
                }
            }
            (_sanitize_text(parts.join(&"\n".to_string())), images)
        }
        // except Exception as exc:
    }
    Ok((format!("[PDF error: {}]", path.file_name().unwrap_or_default().to_str().unwrap_or("")), images))
}

pub fn _extract_docx(path: PathBuf) -> Result<(String, Vec<HashMap>)> {
    if !_docx {
        ("[DOCX error]".to_string(), vec![])
    }
    // try:
    {
        let mut doc = _docx.Document(path.to_string());
        let mut parts = doc.paragraphs.iter().filter(|p| p.text.trim().to_string()).map(|p| p.text).collect::<Vec<_>>();
        for table in doc.tables.iter() {
            let mut rows = table.rows.iter().map(|r| r.cells.iter().map(|c| c.text.trim().to_string().replace(&*"|".to_string(), &*"\\|".to_string())).collect::<Vec<_>>()).collect::<Vec<_>>();
            parts.push(_rows_to_markdown_table(rows));
        }
        (_sanitize_text(parts.join(&"\n\n".to_string())), vec![])
    }
    // except Exception as _e:
}

pub fn _extract_xlsx_sheets(path: PathBuf) -> Result<()> {
    if !_openpyxl {
        vec![]
    }
    // try:
    {
        let mut wb = _openpyxl.load_workbook(path.to_string(), /* read_only= */ true, /* data_only= */ true);
        let mut res = vec![];
        for sn in wb.sheetnames.iter() {
            let mut ws = wb[&sn];
            let mut rows = ws.iter_rows(/* values_only= */ true).iter().map(|r| r.iter().map(|c| if c.is_some() { c } else { "".to_string() }.to_string().trim().to_string().replace(&*"|".to_string(), &*"\\|".to_string())).collect::<Vec<_>>()).collect::<Vec<_>>();
            if rows {
                res.push((sn, rows, rows[0]));
            }
        }
        wb.close();
        res
    }
    // except Exception as _e:
}

pub fn _extract_xlsx(path: PathBuf) -> String {
    let mut sheets = _extract_xlsx_sheets(path);
    _sanitize_text(sheets.iter().map(|(n, r, _)| (format!("\n## Sheet: {}\n", n) + _rows_to_markdown_table(r))).collect::<Vec<_>>().join(&"\n".to_string()))
}

pub fn _extract_pptx(path: PathBuf) -> Result<(String, Vec<HashMap>)> {
    if !_pptx {
        ("[PPTX error]".to_string(), vec![])
    }
    // try:
    {
        let mut prs = _pptx.Presentation(path.to_string());
        let mut parts = prs.slides.iter().map(|s| if s.has_notes_slide { s.notes_slide.notes_text_frame.text } else { "".to_string() }).collect::<Vec<_>>();
        (_sanitize_text(parts.join(&"\n".to_string())), vec![])
    }
    // except Exception as _e:
}

pub fn _extract_rtf(path: PathBuf) -> Result<String> {
    if !_striprtf {
        "[RTF error]".to_string()
    }
    // try:
    {
        // TODO: from striprtf.striprtf import rtf_to_text
        _sanitize_text(rtf_to_text(path.read_to_string())))
    }
    // except Exception as _e:
}

pub fn _extract_csv(path: PathBuf) -> Result<String> {
    // try:
    {
        let mut raw = _read_text_file(path);
        let mut dialect = csv::Sniffer().sniff(raw[..2000]);
        let mut reader = csv::reader(io.StringIO(raw), dialect);
        let mut rows = reader.iter().map(|r| r.iter().map(|c| c.trim().to_string().replace(&*"|".to_string(), &*"\\|".to_string())).collect::<Vec<_>>()).collect::<Vec<_>>();
        _sanitize_text(_rows_to_markdown_table(rows, 100))
    }
    // except Exception as _e:
}

pub fn _extract_html_file(path: PathBuf) -> Result<(String, Vec<HashMap>)> {
    // TODO: from .web_extractor import _html_converter
    // try:
    {
        let mut soup = BeautifulSoup(_read_text_file(path), "html.parser".to_string());
        (_sanitize_text(_html_converter.convert(soup)), vec![])
    }
    // except Exception as _e:
}

pub fn _get_file_extractor(suffix: String) -> () {
    let mut suffix = suffix.to_lowercase();
    let mut RICH = HashMap::from([(".pdf".to_string(), _extract_pdf), (".docx".to_string(), _extract_docx), (".pptx".to_string(), _extract_pptx), (".html".to_string(), _extract_html_file)]);
    let mut TEXT = HashMap::from([(".xlsx".to_string(), _extract_xlsx), (".xls".to_string(), _extract_xlsx), (".rtf".to_string(), _extract_rtf), (".csv".to_string(), _extract_csv)]);
    if RICH.contains(&suffix) {
        ("rich".to_string(), RICH[&suffix])
    }
    if TEXT.contains(&suffix) {
        ("text".to_string(), TEXT[&suffix])
    }
    if HashSet::from([".py".to_string(), ".md".to_string(), ".txt".to_string(), ".json".to_string(), ".yaml".to_string(), ".sql".to_string()]).contains(&suffix) { ("code".to_string(), suffix) } else { None }
}

pub fn ingest_excel_file_to_row_sources(fpath: String, folder_path: String, max_data_rows: String, file_size_kb: String) -> () {
    let mut sheets = _extract_xlsx_sheets(fpath);
    let mut res = vec![];
    for (sn, rows, _) in sheets.iter() {
        for (i, r) in rows[..max_data_rows].iter().enumerate().iter() {
            let mut txt = (format!("Sheet: {} | Row {} | ", sn, i) + r.join(&" | ".to_string()));
            res.push((txt, HashMap::from([("type".to_string(), "xlsx".to_string()), ("path".to_string(), fpath.to_string()), ("sheet".to_string(), sn), ("row".to_string(), i)])));
        }
    }
    res
}
