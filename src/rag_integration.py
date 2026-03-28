"""
RAG Integration – Thin adapter around zena_mode.rag_pipeline.LocalRAG

Responsibilities:
  • Initialise LocalRAG (Qdrant + embeddings + hybrid search)
  • Provide upload_document / search_context / index_content
  • Fall back to a minimal in-memory store when LocalRAG is absent

All LLM-generation logic lives in Core/services/rag_service.py.
"""

import asyncio
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Cache TTL for suggested questions and data summary (seconds)
_SUGGESTED_CACHE_TTL = 300

# Synonyms for semantic search (terms from indexed data; used for query expansion).
_SINONIME_RO_CAUTARE = {
    "paturi": [
        "pat",
        "locuri",
        "capacitate",
        "paturi structură",
        "paturi reale",
        "paturi libere",
    ],
    "pat": ["paturi", "locuri"],
    "secți": ["sectie", "sectii", "departament", "secție"],
    "secții": ["sectie", "sectii", "departament", "secție"],
    "sectie": ["secți", "secții", "departament"],
    "ati": ["terapie intensivă", "intensiv", "ATI"],
    "pacienți": ["bolnavi", "internați", "pacient"],
    "bolnavi": ["pacienți", "internați"],
    "internați": ["pacienți", "bolnavi", "internări"],
    "ocupare": ["grad ocupare", "ocupare spital", "grad"],
    "medicină": ["medicina", "internă", "secție medicală"],
    "chirurgie": ["chirurgic", "operat"],
    "internări": ["internați", "externări", "miscări"],
    "externări": ["externări", "internări"],
    "statistici": ["sumar", "total", "număr", "date"],
    "spital": ["spitalul", "unitate", "spital clinic"],
}

# Complex query expansion (defaults; overridden by config when available)
COMPLEX_QUERY_WORD_THRESHOLD = 6
MAX_SYNONYMS_SIMPLE = 2
MAX_SYNONYMS_COMPLEX = 5
MAX_EXPANDED_QUERY_CHARS = 300

# Romanian stopwords (short list for key-term extraction)
_RO_STOPWORDS = frozenset(
    {
        "și",
        "sau",
        "dar",
        "pentru",
        "din",
        "cu",
        "la",
        "de",
        "în",
        "pe",
        "ce",
        "care",
        "cel",
        "cea",
        "cele",
        "un",
        "o",
        "unei",
        "unui",
        "este",
        "sunt",
        "au",
        "are",
        "fi",
        "fost",
        "este",
        "că",
        "cum",
        "când",
        "unde",
        "care",
        "ceea",
        "acest",
        "această",
        "aceste",
        "acel",
        "aceea",
        "acele",
        "cel",
        "cea",
        "acestea",
    }
)


def _get_complex_query_config() -> Tuple[int, bool]:
    """Return (word_threshold, multi_query_enabled). Uses config if available."""
    try:
        from config_enhanced import Config

        thresh = int(getattr(Config, "RAG_COMPLEX_QUERY_WORD_THRESHOLD", COMPLEX_QUERY_WORD_THRESHOLD))
        enabled = bool(getattr(Config, "RAG_MULTI_QUERY_ENABLED", True))
        return (thresh, enabled)
    except Exception:
        return (COMPLEX_QUERY_WORD_THRESHOLD, True)


def _key_terms_query(query: str, max_terms: int = 12) -> str:
    """Extract a short string of important terms for retrieval (domain terms + synonym dict keys/values)."""
    if not query or not query.strip():
        return query
    q = query.strip().lower()
    words = re.findall(r"[a-zăâîșț]+", q)
    seen: set = set()
    terms: List[str] = []
    # All terms that appear in synonym dict (keys or in values)
    dict_terms = set(_SINONIME_RO_CAUTARE.keys())
    for vals in _SINONIME_RO_CAUTARE.values():
        dict_terms.update(v for v in vals if isinstance(v, str) and len(v) > 1)
    for w in words:
        if w in _RO_STOPWORDS or len(w) < 2:
            continue
        if w.lower() in seen:
            continue
        # Keep: in dict, or length > 3 (likely domain term)
        if w in dict_terms or len(w) > 3:
            seen.add(w.lower())
            terms.append(w)
            if len(terms) >= max_terms:
                break
    if not terms:
        # Fallback: non-stopwords length > 2
        for w in words:
            if w not in _RO_STOPWORDS and len(w) > 2 and w.lower() not in seen:
                seen.add(w.lower())
                terms.append(w)
                if len(terms) >= max_terms:
                    break
    return " ".join(terms) if terms else q[:200].strip()


def _extract_terms_from_indexed_text(text: str, max_terms: int = 8) -> List[str]:
    """Extract only terms/labels that actually appear in the indexed text. No global content."""
    if not text or not text.strip():
        return []

    # Exclude pure numbers and percentages — keep only labels with letters
    def is_label(s: str) -> bool:
        if not s or len(s) < 2 or len(s) > 60:
            return False
        s_clean = s.strip()
        if re.match(r"^[\d\s.,%]+$", s_clean):
            return False
        return bool(re.search(r"[a-zA-Zăâîșț]", s_clean))

    seen_lower: set = set()
    terms: List[str] = []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines:
        if len(line) > 80:
            continue
        if "|" in line:
            parts = [p.strip() for p in line.split("|") if p.strip() and p.strip() != "---"]
            for p in parts:
                if is_label(p) and p.lower() not in seen_lower:
                    seen_lower.add(p.lower())
                    terms.append(p)
                    if len(terms) >= max_terms:
                        return terms
            continue
        if is_label(line) and line.lower() not in seen_lower:
            seen_lower.add(line.lower())
            terms.append(line)
            if len(terms) >= max_terms:
                return terms
    return terms[:max_terms]


def _parse_markdown_tables(text: str) -> List[List[Dict[str, str]]]:
    """Extract markdown tables from text (| A | B |). Returns list of tables; each table = list of dicts (keys = header)."""
    if not text or "|" not in text:
        return []

    def row_cells(line: str) -> List[str]:
        parts = line.split("|")
        if len(parts) < 2:
            return []
        out = [p.strip() for p in parts[1:-1]]
        return out if out else [p.strip() for p in parts if p.strip()]

    tables: List[List[Dict[str, str]]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if "|" not in line:
            i += 1
            continue
        cells = row_cells(line)
        if not cells:
            i += 1
            continue
        if re.match(r"^[\s\-:]+$", "".join(cells)):
            i += 1
            continue
        headers = cells
        i += 1
        if i < len(lines) and "|" in lines[i]:
            sep = row_cells(lines[i])
            if sep and re.match(r"^[\-\s:]+$", " ".join(sep)):
                i += 1
        rows: List[Dict[str, str]] = []
        while i < len(lines):
            row_line = lines[i]
            if "|" not in row_line:
                break
            row_cells_list = row_cells(row_line)
            if len(row_cells_list) != len(headers):
                break
            rows.append(dict(zip(headers, row_cells_list)))
            i += 1
        if rows:
            tables.append(rows)
    return tables


def _enrich_results_with_tables(results: List[dict]) -> List[dict]:
    """Add 'tables' and 'has_table' fields to each result that contains markdown tables."""
    for r in results:
        text = r.get("text") or ""
        tables = _parse_markdown_tables(text)
        r["has_table"] = len(tables) > 0
        r["tables"] = tables
    return results


def _expand_romanian_query(query: str) -> str:
    """Expand query with synonyms for better semantic search.
    For long queries (word count > threshold), allows more synonyms and caps total length.
    """
    if not query or not query.strip():
        return query
    q = query.strip().lower()
    words = re.findall(r"[a-zăâîșț]+", q)
    word_count = len(words)
    max_syn = MAX_SYNONYMS_COMPLEX if word_count > COMPLEX_QUERY_WORD_THRESHOLD else MAX_SYNONYMS_SIMPLE
    extra = []
    for w in words:
        if w in _SINONIME_RO_CAUTARE:
            for syn in _SINONIME_RO_CAUTARE[w]:
                if syn not in q and syn not in extra:
                    extra.append(syn)
    if not extra:
        return query
    expanded = query + " " + " ".join(extra[:max_syn])
    if MAX_EXPANDED_QUERY_CHARS and len(expanded) > MAX_EXPANDED_QUERY_CHARS:
        truncated = expanded[:MAX_EXPANDED_QUERY_CHARS]
        expanded = truncated.rsplit(maxsplit=1)[0] if " " in truncated else truncated
    return expanded


def _merge_results_rrf(result_lists: List[List[dict]], top_k: int = 5, k_rrf: int = 60) -> List[dict]:
    """Merge multiple search result lists with Reciprocal Rank Fusion. Keeps best of original + expanded query."""
    if not result_lists:
        return []
    key_to_item: Dict[Tuple[str, str], dict] = {}
    key_to_rrf: Dict[Tuple[str, str], float] = {}
    for rank_list in result_lists:
        for rank, r in enumerate(rank_list, 1):
            url = r.get("url") or r.get("title") or ""
            text = (r.get("text") or "")[:300]
            key = (url, text)
            if key not in key_to_item:
                key_to_item[key] = r
                key_to_rrf[key] = 0.0
            key_to_rrf[key] += 1.0 / (k_rrf + rank)
    sorted_keys = sorted(key_to_rrf.keys(), key=lambda x: -key_to_rrf[x])[:top_k]
    out = []
    for key in sorted_keys:
        item = key_to_item[key].copy()
        item["score"] = key_to_rrf[key] / len(result_lists)  # normalize for display
        out.append(item)
    return out


# Ensure project root is importable
sys.path.append(str(Path(__file__).parent))

logger = logging.getLogger(__name__)


# ─── helper ──────────────────────────────────────────────────────────

# High context limit so we include all retrieved results for accurate counts (no truncation)
DEFAULT_CONTEXT_MAX_CHARS = 80_000


def format_context(results: List[dict], max_chars: int = None) -> str:
    """Format retrieved chunks for LLM context. Excel row results get a clear Row/Sheet/Date prefix.
    Uses a high default max_chars so all results are included for accurate numbers; no truncation."""
    if max_chars is None:
        max_chars = DEFAULT_CONTEXT_MAX_CHARS
    if not results:
        return ""
    parts = []
    for r in results:
        text = r.get("text", "") or ""
        source = r.get("source") or r.get("title") or r.get("url") or r.get("source_file") or "?"
        score = r.get("score", 0)
        if r.get("sheet_name") is not None or r.get("date") is not None or r.get("row_index") is not None:
            prefix_parts = []
            if r.get("sheet_name") is not None:
                prefix_parts.append(f"Sheet: {r.get('sheet_name')}")
            if r.get("date") is not None:
                prefix_parts.append(f"Date: {r.get('date')}")
            if r.get("row_index") is not None:
                prefix_parts.append(f"Row: {r.get('row_index')}")
            prefix = " | ".join(prefix_parts)
            fmt = f"[{prefix}] {text} (Source: {source})"
        else:
            fmt = f"[Score: {score:.2f}] {text} (Source: {source})"
        parts.append(fmt)
    out = "\n\n".join(parts)
    return out[:max_chars] if len(out) > max_chars else out


class _MockRAG:
    """Minimal in-memory RAG for tests. Shares ``format_context`` with main class."""

    def __init__(self) -> None:
        self.docs: List[dict] = []

    async def upload_document(self, path: str, collection: str = "default"):
        try:
            text = Path(path).read_text(encoding="utf-8") if Path(path).exists() else str(path)
        except Exception:
            text = str(path)
        self.docs.append({"text": text, "source": str(path), "collection": collection})
        return True, f"Indexed: {path}"

    async def search_context(self, query: str, collection: str = "default", top_k: int = 3, **kw):
        q = query.lower()
        scored = []
        for d in self.docs:
            if collection and d.get("collection") != collection:
                continue
            txt = d.get("text", "").lower()
            if q in txt:
                score = 0.9
            else:
                hits = sum(1 for w in q.split() if w in txt)
                score = min(0.5 + 0.1 * hits, 0.8) if hits else 0.0
            if score > 0:
                scored.append(
                    {
                        "text": d.get("text", ""),
                        "score": score,
                        "source": d.get("source"),
                        "collection": d.get("collection"),
                    }
                )
        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:top_k]

    def format_context_for_llm(self, results, max_tokens=2000):
        return format_context(results, max_chars=max_tokens)

    def get_stats(self):
        return {
            "documents_uploaded": len(self.docs),
            "collections": {},
            "total_collection_size": sum(len(d.get("text", "")) for d in self.docs),
        }


def _path_under_root(file_path: str, root_path: str) -> bool:
    """True if file_path is the same as root_path or under it (for filesystem paths only)."""
    if not file_path or not root_path or file_path.startswith("http") or root_path.startswith("http"):
        return True  # no filter for URLs
    try:
        fp = Path(file_path).resolve()
        root = Path(root_path).resolve()
        return fp == root or root in fp.parents
    except (OSError, ValueError):
        return False


def _split_aggregated_text(content: str, sources: List[dict]) -> List[str]:
    """Split aggregated extraction output back into per-source blocks.

    content_extractor emits blocks separated by ``=== PAGE/FILE: … ===``
    headers.  If parsing fails we distribute proportionally by char count.
    """
    header_re = re.compile(r"^=== (?:PAGE|FILE): .+? ===$", re.MULTILINE)
    splits = header_re.split(content)
    if splits and not splits[0].strip():
        splits = splits[1:]

    if len(splits) >= len(sources):
        return [s.strip() for s in splits[: len(sources)]]

    # Proportional fallback
    total = max(sum(s.get("chars", 1) for s in sources), 1)
    blocks, pos = [], 0
    for src in sources:
        length = max(100, int(len(content) * src.get("chars", 1) / total))
        blocks.append(content[pos : pos + length].strip())
        pos += length
    return blocks


# ─── RAGIntegration ──────────────────────────────────────────────────


class RAGIntegration:
    """Thin wrapper around LocalRAG (Qdrant) with in-memory fallback."""

    def __init__(self) -> None:
        self.rag_manager = None  # LocalRAG instance or None
        self.documents: List[dict] = []
        self.collections: Dict[str, List[dict]] = {}
        self.initialized = False
        self._mem_docs: List[dict] = []  # in-memory fallback store
        self._suggested_cache: Optional[Tuple[float, int, List[str]]] = None  # (ts, chunk_count, questions)
        self._summary_cache: Optional[Tuple[float, int, dict]] = None  # (ts, chunk_count, summary)
        self._stats_cache: Optional[Tuple[float, dict]] = None  # (ts, stats) – cache scurt pentru viteză

    @property
    def _is_pro(self) -> bool:
        """True when backed by LocalRAG (not in-memory fallback)."""
        return self.rag_manager is not None and hasattr(self.rag_manager, "build_index")

    @property
    def _has_mock(self) -> bool:
        """True when backed by a _MockRAG (or any non-pro manager)."""
        return self.rag_manager is not None and not self._is_pro

    # ── lifecycle ────────────────────────────────────────

    async def initialize(self) -> bool:
        """Try LocalRAG; fall back to in-memory store."""
        try:
            logger.info("Initializing RAG engine (Qdrant)…")
            from zena_mode.rag_pipeline import LocalRAG

            storage = Path(os.getcwd()) / "rag_storage"
            self.rag_manager = LocalRAG(cache_dir=storage)
            self.rag_manager.warmup()
            self.initialized = True
            logger.info("RAG engine initialised at %s", storage)
            return True
        except ImportError as exc:
            logger.warning("LocalRAG unavailable (%s) – using in-memory fallback", exc)
            self.rag_manager = _MockRAG()
            self.initialized = True
            return True
        except Exception as exc:
            logger.error("RAG init failed: %s", exc)
            self.initialized = False
            return False

    # ── upload / index ───────────────────────────────────

    async def upload_document(
        self,
        file_path: str,
        collection_name: str = "default",
        metadata: Optional[dict] = None,
    ) -> Tuple[bool, str]:
        if not self.initialized:
            return False, "RAG not initialised"

        fp = Path(file_path)
        if not fp.exists():
            return False, f"File not found: {fp}"

        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            text = str(fp)

        if self._is_pro:
            import streamlit as st

            threshold = st.session_state.get("setting_dedup_sensitivity", 0.9)
            filter_junk = st.session_state.get("setting_enable_boilerplate_removal", True)

            doc = {
                "content": text,
                "url": str(fp),
                "title": fp.name,
                "metadata": metadata or {},
            }
            await asyncio.to_thread(
                self.rag_manager.build_index,
                [doc],
                dedup_threshold=threshold,
                filter_junk=filter_junk,
            )
        elif self._has_mock:
            return await self.rag_manager.upload_document(str(fp), collection=collection_name)
        else:
            self._mem_docs.append({"text": text, "source": str(fp), "collection": collection_name})

        info = {
            "name": fp.name,
            "path": str(fp),
            "collection": collection_name,
            "size": fp.stat().st_size,
            "uploaded_at": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self.documents.append(info)
        self.collections.setdefault(collection_name, []).append(info)
        return True, f"Indexed: {fp.name}"

    async def index_content(
        self,
        content: str,
        sources: List[dict],
        source_name: str = "scan",
    ) -> Tuple[bool, str]:
        """Index raw extracted text (from content_extractor).

        source_name is the dataset/folder path from the UI (resolved). It is used as
        fallback for doc url/title when a source has no "path". The vector index does
        NOT store source_name; only per-document "url" (file path) and "title" are in
        the payload. Search and list_indexed_sources do not filter by dataset path.
        See docs/VECTOR_INDEX_AND_DATASET_PATH.md.
        """
        if not self.initialized and not await self.initialize():
            return False, "RAG engine not available"

        documents = []
        if sources:
            blocks = _split_aggregated_text(content, sources)
            # Only index sources whose path is under source_name (enforce UI path)
            for src, block in zip(sources, blocks):
                src_path = src.get("path", source_name)
                if not _path_under_root(src_path, source_name):
                    logger.warning(
                        "Skipping source outside scan root: %s (root: %s)",
                        src_path,
                        source_name,
                    )
                    continue
                doc = {
                    "content": block,
                    "url": src_path,
                    "title": src.get("title", source_name),
                    "scan_root": source_name,
                }
                if src.get("is_table"):
                    doc["is_table"] = True
                    if src.get("sheet_name") is not None:
                        doc["sheet_name"] = src["sheet_name"]
                    if src.get("columns") is not None:
                        doc["columns"] = src["columns"]
                if src.get("excel_row"):
                    doc["excel_row"] = True
                    for key in (
                        "file_id",
                        "dataset",
                        "sheet",
                        "sheet_name",
                        "date",
                        "entity",
                        "category",
                        "dept_name",
                        "dept_id",
                        "beds_real",
                        "beds_struct",
                        "patients_present",
                        "free_beds",
                        "source_file",
                        "source_sheet",
                        "row_index",
                        "unit",
                    ):
                        if key in src:
                            doc[key] = src[key]
                documents.append(doc)
        else:
            documents.append(
                {
                    "content": content,
                    "url": source_name,
                    "title": source_name,
                    "scan_root": source_name,
                }
            )

        if not documents:
            return False, "No content to index"

        if self._is_pro:
            import streamlit as st

            threshold = st.session_state.get("setting_dedup_sensitivity", 0.9)
            filter_junk = st.session_state.get("setting_enable_boilerplate_removal", True)

            await asyncio.to_thread(
                self.rag_manager.build_index,
                documents,
                dedup_threshold=threshold,
                filter_junk=filter_junk,
            )
        elif self._has_mock:
            for doc in documents:
                self.rag_manager.docs.append(
                    {
                        "text": doc["content"],
                        "source": doc["url"],
                        "collection": "default",
                    }
                )
        else:
            for doc in documents:
                self._mem_docs.append(
                    {
                        "text": doc["content"],
                        "source": doc["url"],
                        "collection": "default",
                    }
                )

        # Track indexed documents in metadata
        for doc in documents:
            self.documents.append(
                {
                    "path": doc["url"],
                    "title": doc["title"],
                    "size": len(doc["content"]),
                }
            )

        total = sum(len(d["content"]) for d in documents)
        return True, f"Indexed {len(documents)} sources ({total:,} chars)"

    async def delete_document(self, path: str) -> bool:
        """Delete a document by its source path/URL."""
        if not self.initialized:
            return False

        # 1. Remove from backend
        if self._is_pro:
            # Helper to run sync method in thread
            await asyncio.to_thread(self.rag_manager.delete_document_by_url, path)
        elif self._has_mock:
            # MockRAG doesn't strictly support delete in this simple version,
            # but we can filter its docs list if we wanted to be thorough.
            # self.rag_manager.docs = [d for d in self.rag_manager.docs if d.get('source') != path]
            pass
        else:
            # In-memory fallback
            self._mem_docs = [d for d in self._mem_docs if d.get("source") != path]

        # 2. Remove from session metadata lists
        self.documents = [d for d in self.documents if d.get("path") != path]

        # Cleanup collections
        for name, docs in self.collections.items():
            self.collections[name] = [d for d in docs if d.get("path") != path]

        logger.info(f"Deleted document: {path}")
        return True

    # ── search ───────────────────────────────────────────

    async def search_context(
        self,
        query: str,
        collection_name: str = "default",
        top_k: int = 3,
        score_threshold: float = 0.5,
        use_hybrid: bool = True,
        alpha: float = 0.5,
    ) -> List[dict]:
        if not self.initialized or (self.rag_manager is None and not self._mem_docs):
            return []

        if self._is_pro:
            # Dispatch to appropriate backend method
            if use_hybrid:
                # Ensure backend has hybrid_search
                if hasattr(self.rag_manager, "hybrid_search"):
                    raw = await asyncio.to_thread(
                        self.rag_manager.hybrid_search,
                        query,
                        k=top_k,
                        alpha=alpha,
                        rerank=True,
                    )
                else:
                    # Fallback if method missing (unlikely)
                    raw = await asyncio.to_thread(
                        self.rag_manager.search,
                        query,
                        k=top_k,
                        rerank=True,
                    )
            else:
                raw = await asyncio.to_thread(
                    self.rag_manager.search,
                    query,
                    k=top_k,
                    rerank=True,
                )

            # Normalise score key: hybrid_search uses rerank_score/fusion_score
            import math

            def _normalise_score(r: dict) -> float:
                if "rerank_score" in r:
                    # Sigmoid normalises cross-encoder logits to 0-1
                    return 1.0 / (1.0 + math.exp(-r["rerank_score"]))
                if "score" in r:
                    return r["score"]  # Already 0-1 (cosine similarity)
                if "fusion_score" in r:
                    # RRF scores are small; scale for comparison
                    return min(r["fusion_score"] * 60, 1.0)
                return 0.0

            results = []
            for r in raw:
                if _normalise_score(r) < score_threshold:
                    continue
                item = {
                    "text": r.get("text", ""),
                    "score": _normalise_score(r),
                    "source": r.get("url") or r.get("title", "unknown"),
                    "collection": collection_name,
                }
                for key in (
                    "sheet_name",
                    "date",
                    "row_index",
                    "source_file",
                    "dataset",
                    "sheet",
                    "dept_name",
                ):
                    if r.get(key) is not None:
                        item[key] = r[key]
                results.append(item)
            return _enrich_results_with_tables(results)

        if self._has_mock:
            results = await self.rag_manager.search_context(
                query,
                collection=collection_name,
                top_k=top_k,
            )
            filtered = [r for r in results if r.get("score", 0) >= score_threshold]
            return _enrich_results_with_tables(filtered)

        # Bare in-memory substring fallback (rag_manager is None)
        q = query.lower()
        scored = []
        for d in self._mem_docs:
            if collection_name and d.get("collection") != collection_name:
                continue
            txt = d.get("text", "").lower()
            if q in txt:
                score = 0.9
            else:
                hits = sum(1 for w in q.split() if w in txt)
                score = min(0.5 + 0.1 * hits, 0.8) if hits else 0.0
            if score >= score_threshold:
                scored.append(
                    {
                        "text": d.get("text", ""),
                        "score": score,
                        "source": d.get("source"),
                        "collection": d.get("collection"),
                    }
                )
        scored.sort(key=lambda r: r["score"], reverse=True)
        return _enrich_results_with_tables(scored[:top_k])

    async def query_context(
        self,
        query: str,
        top_k: int = 5,
        max_context_chars: int = None,
        score_threshold: float = 0.3,
        use_hybrid: bool = True,
        alpha: float = 0.5,
    ) -> Tuple[str, List[dict]]:
        """Retrieve + format context for an LLM prompt. Uses high default max_context_chars so all results are included for accurate numbers."""
        if max_context_chars is None:
            max_context_chars = DEFAULT_CONTEXT_MAX_CHARS
        results = await self.search_context(
            query,
            top_k=top_k,
            score_threshold=score_threshold,
            use_hybrid=use_hybrid,
            alpha=alpha,
        )
        if not results:
            return "", []

        parts = []
        total = 0
        for i, r in enumerate(results):
            block = f"[Source {i + 1}: {r.get('source', '?')} | Score: {r.get('score', 0):.2f}]\n{r.get('text', '')}"
            if total + len(block) > max_context_chars and total > 0:
                break
            parts.append(block)
            total += len(block)
        return "\n\n".join(parts), results

    def format_context_for_llm(self, results: List[dict], max_tokens: int = None) -> str:
        """Format search results for LLM context injection. Uses high default so all results are included for accurate numbers."""
        return format_context(results, max_chars=max_tokens or DEFAULT_CONTEXT_MAX_CHARS)

    def search(self, query: str, k: int = 5, rerank: bool = False) -> List[dict]:
        """Hybrid (semantic + lexical) search over all documents; results are enriched with tables.
        Uses hybrid (semantic + BM25) when available. For complex (long) queries, runs multi-query + RRF.
        """
        import math

        def _norm_score(r: dict) -> float:
            if r.get("rerank_score") is not None:
                return 1.0 / (1.0 + math.exp(-r["rerank_score"]))
            if r.get("score") is not None:
                return r["score"]
            return min((r.get("fusion_score") or 0) * 60, 1.0)

        def _raw_to_result(r: dict) -> dict:
            res = {
                "text": r.get("text", ""),
                "url": r.get("url"),
                "title": r.get("title"),
                "score": _norm_score(r),
                "source": r.get("url") or r.get("title") or r.get("source_file") or "unknown",
            }
            if r.get("is_table"):
                res["is_table"] = True
                if r.get("sheet_name") is not None:
                    res["sheet_name"] = r["sheet_name"]
                if r.get("columns") is not None:
                    res["columns"] = r["columns"]
            for key in (
                "date",
                "row_index",
                "source_file",
                "dataset",
                "sheet",
                "dept_name",
                "entity",
                "category",
            ):
                if r.get(key) is not None:
                    res[key] = r[key]
            return res

        if self._is_pro and self.rag_manager:
            expanded = _expand_romanian_query(query)
            words = re.findall(r"[a-zăâîșț]+", (query or "").strip().lower())
            word_count = len(words)
            complex_threshold, multi_query_enabled = _get_complex_query_config()
            is_complex = word_count > complex_threshold or len((query or "").strip()) > 80

            use_hybrid = (
                hasattr(self.rag_manager, "hybrid_search")
                and getattr(self.rag_manager, "chunks", None)
                and len(self.rag_manager.chunks) > 0
            )
            alpha = 0.5
            try:
                from ui.state import get_settings

                s = get_settings()
                alpha = float(s.get("setting_hybrid_alpha", 0.5) or 0.5)
            except Exception as exc:
                logger.debug("%s", exc)

            # Multi-query path: complex question → search expanded + key-term query, merge with RRF, then rerank once with original query
            if is_complex and multi_query_enabled:
                key_terms_str = _key_terms_query(query)
                if not key_terms_str or key_terms_str.strip() == expanded.strip():
                    key_terms_str = None
                if key_terms_str and len(key_terms_str.split()) >= 2:
                    k_fetch = max(k * 2, 10)
                    if use_hybrid:
                        r1 = self.rag_manager.hybrid_search(expanded, k=k_fetch, alpha=alpha, rerank=False)
                        r2 = self.rag_manager.hybrid_search(key_terms_str, k=k_fetch, alpha=alpha, rerank=False)
                    else:
                        r1 = self.rag_manager.search(expanded, k=k_fetch, rerank=False, scan_root=None)
                        r2 = self.rag_manager.search(key_terms_str, k=k_fetch, rerank=False, scan_root=None)
                    merged = _merge_results_rrf([r1, r2], top_k=k * 3 if rerank else k, k_rrf=60)
                    if rerank and merged and hasattr(self.rag_manager, "rerank"):
                        merged = self.rag_manager.rerank(query, merged, top_k=k)
                    else:
                        merged = merged[:k]
                    results = [_raw_to_result(r) for r in merged]
                    return _enrich_results_with_tables(results)

            # Single-query path
            if use_hybrid:
                raw = self.rag_manager.hybrid_search(expanded, k=k, alpha=alpha, rerank=rerank)
                results = [_raw_to_result(r) for r in raw]
            else:
                q_orig = query.strip()
                if q_orig and expanded.strip() != q_orig:
                    r1 = self.rag_manager.search(q_orig, k=k * 2, rerank=rerank, scan_root=None)
                    r2 = self.rag_manager.search(expanded, k=k * 2, rerank=rerank, scan_root=None)
                    results = _merge_results_rrf([r1, r2], top_k=k)
                else:
                    results = self.rag_manager.search(expanded, k=k, rerank=rerank, scan_root=None)
                for r in results:
                    if "source" not in r:
                        r["source"] = r.get("url") or r.get("title") or "unknown"
        else:
            q = query.lower()
            scored = []
            for d in self._mem_docs:
                txt = d.get("text", "").lower()
                if q in txt:
                    score = 0.9
                else:
                    hits = sum(1 for w in q.split() if w in txt)
                    score = min(0.5 + 0.1 * hits, 0.8) if hits else 0.0
                if score >= 0.3:
                    scored.append(
                        {
                            "text": d.get("text", "")[:1000],
                            "score": score,
                            "source": d.get("source"),
                            "collection": d.get("collection"),
                        }
                    )
            scored.sort(key=lambda r: r["score"], reverse=True)
            results = scored[:k]
        return _enrich_results_with_tables(results)

    def search_with_fallback(self, query: str, k: int = 5, min_score: float = 0.35, rerank: bool = False) -> dict:
        """Semantic search (with synonym expansion); on no results: message + suggested questions from indexed data only.
        Responses contain only content from the vector DB, no generic text.
        """
        results = self.search(query, k=k, rerank=rerank)
        stats = self.get_stats()
        total_chunks = stats.get("chunks", 0)

        # Filter results by minimum score threshold
        relevant_results = [r for r in results if r.get("score", 0) >= min_score]

        if relevant_results:
            return {
                "success": True,
                "results": relevant_results,
                "message": None,
                "suggested_questions": None,
            }

        if total_chunks == 0:
            return {
                "success": False,
                "results": [],
                "message": "No indexed data. Load documents to search.",
                "suggested_questions": None,
            }

        # Clear message and terms extracted from indexed data only
        suggested = self.get_suggested_questions()
        if suggested:
            msg = "No results found. You can search by one of the terms from the indexed data:"
        else:
            msg = "No results found. Could not extract suggestions from indexed data."
        return {
            "success": False,
            "results": [],
            "message": msg,
            "suggested_questions": suggested if suggested else None,
        }

    def get_suggested_questions(self) -> List[str]:
        """Search terms extracted only from indexed content. No global phrasing."""
        if not self._is_pro or not self.rag_manager:
            return []

        stats = self.get_stats()
        chunk_count = stats.get("chunks", 0)
        now = time.time()
        if self._suggested_cache is not None:
            ts, cached_count, questions = self._suggested_cache
            if now - ts <= _SUGGESTED_CACHE_TTL and cached_count == chunk_count:
                return questions
            self._suggested_cache = None

        try:
            if not self.rag_manager.qdrant:
                return []
            points, _ = self.rag_manager.qdrant.scroll(self.rag_manager.collection_name, limit=30, with_payload=True)
            all_text = "\n".join((p.payload or {}).get("text", "") for p in points)
            terms = _extract_terms_from_indexed_text(all_text, max_terms=6)
            result = terms
            self._suggested_cache = (now, chunk_count, result)
            return result
        except Exception as e:
            logger.warning(f"Error extracting suggested terms: {e}")
            return []

    def get_data_summary(self) -> dict:
        """Summary of indexed data for the user. From index only. Cache 5 min."""
        stats = self.get_stats()
        total_chunks = stats.get("chunks", 0)
        now = time.time()

        if total_chunks == 0:
            return {
                "has_data": False,
                "message": "No indexed data.",
                "topics": [],
                "suggested_questions": [],
            }

        if self._summary_cache is not None:
            ts, cached_count, summary = self._summary_cache
            if now - ts <= _SUGGESTED_CACHE_TTL and cached_count == total_chunks:
                return summary
            self._summary_cache = None

        suggested = self.get_suggested_questions()
        # Topics from terms extracted from index only
        summary = {
            "has_data": True,
            "message": f"{total_chunks} indexed chunks.",
            "topics": suggested[:5],
            "suggested_questions": suggested,
        }
        self._summary_cache = (now, total_chunks, summary)
        return summary

    # ── bookkeeping ──────────────────────────────────────

    def get_stats(self) -> dict:
        """Get RAG statistics. Cache 1s to avoid repeated Qdrant calls in same request."""
        now = time.time()
        if self._stats_cache is not None:
            ts, cached = self._stats_cache
            if now - ts < 1.0:
                return cached
            self._stats_cache = None

        stats = {
            "documents_uploaded": len(self.documents),
            "collections": {n: len(d) for n, d in self.collections.items()},
            "total_collection_size": sum(d.get("size", 0) for d in self.documents),
            "initialized": self.initialized,
            "backend": "LocalRAG" if self._is_pro else "in-memory",
        }
        if self._is_pro and self.rag_manager:
            try:
                rag_stats = self.rag_manager.get_stats()
                stats["chunks"] = rag_stats.get("total_chunks", 0)
                stats["collection"] = rag_stats.get("collection", "")
                stats["documents"] = stats["chunks"]
            except Exception as exc:
                logger.debug("%s", exc)
        self._stats_cache = (now, stats)
        return stats

    def clear_collection(self, collection_name: str) -> bool:
        self.collections[collection_name] = []
        self._mem_docs = [d for d in self._mem_docs if d.get("collection") != collection_name]
        return True

    def clear_vector_index(self) -> bool:
        """Clear the entire Qdrant vector index. Use to remove wrongly indexed data, then re-scan only the desired path."""
        if not self._is_pro or not self.rag_manager:
            return False
        if not hasattr(self.rag_manager, "clear_vector_index"):
            return False
        ok = self.rag_manager.clear_vector_index()
        if ok:
            self._stats_cache = None
            self._suggested_cache = None
            self._summary_cache = None
        return ok

    def list_documents(self, collection_name: Optional[str] = None) -> List[dict]:
        if collection_name:
            return self.collections.get(collection_name, [])
        return self.documents

    def list_indexed_sources(self) -> List[dict]:
        """List real sources from the vector DB (Qdrant). For UI display.
        Returns ALL sources in the collection; no filter by current dataset path.
        """
        if not self._is_pro or not self.rag_manager or not getattr(self.rag_manager, "qdrant", None):
            return []
        try:
            client = self.rag_manager.qdrant
            col = self.rag_manager.collection_name
            # Aggregate unique sources from payloads
            seen: set = set()
            out: List[dict] = []
            offset = None
            while True:
                points, offset = client.scroll(
                    collection_name=col,
                    limit=200,
                    offset=offset,
                    with_payload=True,
                )
                if not points:
                    break
                for p in points:
                    payload = p.payload or {}
                    url = payload.get("url") or payload.get("source") or ""
                    title = payload.get("title") or ""
                    key = (url, title)
                    if key in seen or not (url or title):
                        continue
                    seen.add(key)
                    out.append(
                        {
                            "name": title or url.split("/")[-1] if url else "?",
                            "path": url,
                            "title": title,
                            "source": url,
                        }
                    )
                if offset is None:
                    break
            return out
        except Exception as e:
            logger.warning("list_indexed_sources failed: %s", e)
            return []

    def get_vector_load_report(self) -> Optional[Dict[str, Any]]:
        """Get full load report from the vector DB: all chunks, chars, breakdown by source and scan_root.
        Returns None if not using Qdrant; otherwise a dict with total_chunks, total_characters,
        unique_sources, by_source (list of {url, title, chunks, characters}), by_scan_root (if present),
        and collection_name. Use for clear reports on existing load.
        """
        if not self._is_pro or not self.rag_manager or not getattr(self.rag_manager, "qdrant", None):
            return None
        try:
            client = self.rag_manager.qdrant
            col = self.rag_manager.collection_name
            # Aggregate over all points
            total_chunks = 0
            total_characters = 0
            by_url: Dict[tuple, Dict[str, Any]] = {}  # (url, title) -> {chunks, characters}
            by_scan_root: Dict[str, Dict[str, Any]] = {}  # scan_root -> {chunks, urls set}
            offset = None
            while True:
                points, offset = client.scroll(
                    collection_name=col,
                    limit=500,
                    offset=offset,
                    with_payload=True,
                )
                if not points:
                    break
                for p in points:
                    payload = p.payload or {}
                    text = (payload.get("text") or "").strip()
                    url = payload.get("url") or payload.get("source") or ""
                    title = (payload.get("title") or "").strip() or (url.split("/")[-1] if url else "?")
                    scan_root = (payload.get("scan_root") or "").strip() or None
                    total_chunks += 1
                    total_characters += len(text)
                    key = (url, title)
                    if key not in by_url:
                        by_url[key] = {
                            "url": url,
                            "title": title,
                            "chunks": 0,
                            "characters": 0,
                        }
                    by_url[key]["chunks"] += 1
                    by_url[key]["characters"] += len(text)
                    if scan_root:
                        if scan_root not in by_scan_root:
                            by_scan_root[scan_root] = {"chunks": 0, "urls": set()}
                        by_scan_root[scan_root]["chunks"] += 1
                        by_scan_root[scan_root]["urls"].add(url or title)
                if offset is None:
                    break
            by_source = sorted(by_url.values(), key=lambda x: x["chunks"], reverse=True)
            for s in by_source:
                s["characters"] = int(s["characters"])
            report_by_scan_root = [
                {
                    "scan_root": root,
                    "chunks": data["chunks"],
                    "sources_count": len(data["urls"]),
                }
                for root, data in sorted(by_scan_root.items(), key=lambda x: -x[1]["chunks"])
            ]
            return {
                "collection_name": col,
                "total_chunks": total_chunks,
                "total_characters": total_characters,
                "unique_sources": len(by_url),
                "by_source": by_source,
                "by_scan_root": report_by_scan_root,
            }
        except Exception as e:
            logger.warning("get_vector_load_report failed: %s", e)
            return None


# ─── singleton ───────────────────────────────────────────────────────

_rag_integration: Optional[RAGIntegration] = None


async def get_rag() -> RAGIntegration:
    """Get or create the global RAG integration singleton."""
    global _rag_integration
    if _rag_integration is None:
        _rag_integration = RAGIntegration()
        await _rag_integration.initialize()
    return _rag_integration
