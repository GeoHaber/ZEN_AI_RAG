import logging
import csv
import io
from pathlib import Path
from typing import List, Dict, Tuple

from .markdown_converter import _rows_to_markdown_table, _sanitize_text

logger = logging.getLogger(__name__)


# Optional heavy imports
def _try_import(name):
    try:
        return __import__(name)
    except ImportError:
        return None


_pdfplumber = _try_import("pdfplumber")
_PyPDF2 = _try_import("PyPDF2")
_docx = _try_import("docx")
_openpyxl = _try_import("openpyxl")
_pptx = _try_import("pptx")
_striprtf = _try_import("striprtf")
_chardet = _try_import("chardet")

try:
    from PIL import Image
    import pytesseract

    _HAS_OCR = True
except ImportError:
    _HAS_OCR = False


def _read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    enc = _chardet.detect(raw[:10000]).get("encoding") or "utf-8" if _chardet else "utf-8"
    return raw.decode(enc, errors="replace")


def _get_excel_rag_limits() -> Tuple[int, int]:
    try:
        from config_system import config

        max_rows = getattr(config.rag, "excel_max_rows_per_sheet", 500)
        return (int(max_rows) if max_rows else 500, 12000)
    except Exception:
        return (500, 12000)


def _extract_pdf(path: Path) -> Tuple[str, List[Dict]]:
    images = []
    if _pdfplumber:
        try:
            parts = []
            with _pdfplumber.open(str(path)) as pdf:
                for i, page in enumerate(pdf.pages):
                    parts.append(f"\n--- Page {i + 1} ---\n")
                    text = page.extract_text()
                    if (not text or len(text.strip()) < 10) and _HAS_OCR:
                        try:
                            ocr_text = pytesseract.image_to_string(page.to_image(resolution=300).original)
                            if ocr_text:
                                text = f"[OCR]\n{ocr_text}"
                        except Exception as exc:
                            logger.debug("%s", exc)
                    if text:
                        parts.append(text)
                    tables = page.extract_tables()
                    for table in tables:
                        rows = [[str(c or "").strip().replace("|", "\\|") for c in r] for r in table]
                        if rows:
                            parts.append(f"\n{_rows_to_markdown_table(rows)}")
            return _sanitize_text("\n".join(parts)), images
        except Exception as exc:
            logger.debug("%s", exc)
    if _PyPDF2:
        try:
            parts = []
            with open(path, "rb") as f:
                reader = _PyPDF2.PdfReader(f)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        parts.append(f"\n--- Page {i + 1} ---\n{text}")
            return _sanitize_text("\n".join(parts)), images
        except Exception as exc:
            logger.debug("%s", exc)
    return f"[PDF error: {path.name}]", images


def _extract_docx(path: Path) -> Tuple[str, List[Dict]]:
    if not _docx:
        return "[DOCX error]", []
    try:
        doc = _docx.Document(str(path))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            rows = [[c.text.strip().replace("|", "\\|") for c in r.cells] for r in table.rows]
            parts.append(_rows_to_markdown_table(rows))
        return _sanitize_text("\n\n".join(parts)), []
    except Exception:
        return "[Error reading DOCX]", []


def _extract_xlsx_sheets(path: Path):
    if not _openpyxl:
        return []
    try:
        wb = _openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        res = []
        for sn in wb.sheetnames:
            ws = wb[sn]
            rows = [
                [str(c if c is not None else "").strip().replace("|", "\\|") for c in r]
                for r in ws.iter_rows(values_only=True)
            ]
            if rows:
                res.append((sn, rows, rows[0]))
        wb.close()
        return res
    except Exception:
        return []


def _extract_xlsx(path: Path) -> str:
    sheets = _extract_xlsx_sheets(path)
    return _sanitize_text("\n".join([f"\n## Sheet: {n}\n" + _rows_to_markdown_table(r) for n, r, _ in sheets]))


def _extract_pptx(path: Path) -> Tuple[str, List[Dict]]:
    if not _pptx:
        return "[PPTX error]", []
    try:
        prs = _pptx.Presentation(str(path))
        parts = [s.notes_slide.notes_text_frame.text if s.has_notes_slide else "" for s in prs.slides]
        return _sanitize_text("\n".join(parts)), []
    except Exception:
        return "[Error reading PPTX]", []


def _extract_rtf(path: Path) -> str:
    if not _striprtf:
        return "[RTF error]"
    try:
        from striprtf.striprtf import rtf_to_text

        return _sanitize_text(rtf_to_text(path.read_text(errors="replace")))
    except Exception:
        return "[Error reading RTF]"


def _extract_csv(path: Path) -> str:
    try:
        raw = _read_text_file(path)
        dialect = csv.Sniffer().sniff(raw[:2000])
        reader = csv.reader(io.StringIO(raw), dialect)
        rows = [[c.strip().replace("|", "\\|") for c in r] for r in reader]
        return _sanitize_text(_rows_to_markdown_table(rows, 100))
    except Exception:
        return _read_text_file(path)


def _extract_html_file(path: Path) -> Tuple[str, List[Dict]]:
    from .web_extractor import _html_converter

    try:
        soup = BeautifulSoup(_read_text_file(path), "html.parser")
        return _sanitize_text(_html_converter.convert(soup)), []
    except Exception:
        return "[Error reading HTML]", []


def _get_file_extractor(suffix: str):
    suffix = suffix.lower()
    RICH = {
        ".pdf": _extract_pdf,
        ".docx": _extract_docx,
        ".pptx": _extract_pptx,
        ".html": _extract_html_file,
    }
    TEXT = {
        ".xlsx": _extract_xlsx,
        ".xls": _extract_xlsx,
        ".rtf": _extract_rtf,
        ".csv": _extract_csv,
    }
    if suffix in RICH:
        return ("rich", RICH[suffix])
    if suffix in TEXT:
        return ("text", TEXT[suffix])
    return ("code", suffix) if suffix in {".py", ".md", ".txt", ".json", ".yaml", ".sql"} else None


class FolderScanner:
    def __init__(
        self,
        max_depth=5,
        max_files=500,
        max_chars_total=500000,
        max_chars_per_file=30000,
    ):
        self.max_depth, self.max_files = max_depth, max_files
        self.max_chars_total, self.max_chars_per_file = (
            max_chars_total,
            max_chars_per_file,
        )
        self.unknown_extensions = {}

    def scan(self, folder, progress_callback=None, completed_items=None):
        root_path = Path(folder).resolve()
        files = self._collect_files(root_path, root_path, self.max_depth)[: self.max_files]
        all_text, all_sources = [], []
        total_chars = 0
        for i, fpath in enumerate(files):
            if total_chars >= self.max_chars_total:
                break
            if completed_items and str(fpath) in completed_items:
                continue
            if progress_callback:
                progress_callback(i + 1, len(files), f"{fpath.name}")
            text, images = self._extract_file(fpath)
            if not text:
                continue
            if len(text) > self.max_chars_per_file:
                text = text[: self.max_chars_per_file] + "..."
            all_text.append(f"=== FILE: {fpath.name} ===\n" + text)
            all_sources.append({"type": fpath.suffix, "path": str(fpath), "chars": len(text)})
            total_chars += len(text)
        return "\n\n".join(all_text), [], all_sources

    def _collect_files(self, root, folder, max_depth, depth=0):
        if depth >= max_depth:
            return []
        files = []
        try:
            for item in folder.iterdir():
                if item.name.startswith((".", "__")):
                    continue
                if item.is_file() and _get_file_extractor(item.suffix):
                    files.append(item)
                elif item.is_dir():
                    files.extend(self._collect_files(root, item, max_depth, depth + 1))
        except Exception as exc:
            logger.debug("%s", exc)
        return files

    def _extract_file(self, path: Path):
        ext = path.suffix.lower()
        extractor = _get_file_extractor(ext)
        if not extractor:
            return "", []
        kind, handler = extractor
        try:
            if kind == "rich":
                return handler(path)
            if kind == "text":
                return handler(path), []
            return _read_text_file(path), []
        except Exception:
            return "", []


def ingest_excel_file_to_row_sources(fpath, folder_path, max_data_rows=9999, file_size_kb=0.0):
    # Simplified version for now
    sheets = _extract_xlsx_sheets(fpath)
    res = []
    for sn, rows, _ in sheets:
        for i, r in enumerate(rows[:max_data_rows]):
            txt = f"Sheet: {sn} | Row {i} | " + " | ".join(r)
            res.append((txt, {"type": "xlsx", "path": str(fpath), "sheet": sn, "row": i}))
    return res
