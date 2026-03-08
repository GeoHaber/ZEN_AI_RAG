"""
RAG Integration — Document upload and context retrieval wrapper.

Wraps zena_mode.rag_manager / rag_core_bridge to provide a clean
interface for the application to use RAG functionality.

Includes:
  - MockRAG fallback for testing without a vector store
  - Hybrid search (vector + BM25 + reranking) via LocalRAGv2
  - Content splitting for multi-source indexing
  - Context formatting for LLM consumption

Adapted from RAG_RAT/rag_integration.py.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Ensure project root is on sys.path so config_system resolves
sys.path.append(str(Path(__file__).parent))


# ─── Helper: split aggregated text back into per-source blocks ──


def _split_aggregated_text(content: str, sources: List[dict]) -> List[str]:
    """Split content_extractor output into per-source text blocks."""
    header_pattern = re.compile(r"^=== (?:PAGE|FILE): .+? ===$", re.MULTILINE)
    splits = header_pattern.split(content)
    if splits and not splits[0].strip():
        splits = splits[1:]
    if len(splits) >= len(sources):
        return [s.strip() for s in splits[: len(sources)]]
    # Proportional fallback
    total = sum(s.get("chars", 1) for s in sources)
    blocks, pos = [], 0
    for src in sources:
        frac = src.get("chars", 1) / max(total, 1)
        length = max(100, int(len(content) * frac))
        blocks.append(content[pos : pos + length].strip())
        pos += length
    return blocks


# ─── MockRAG ─────────────────────────────────────────────


class _MockRAG:
    """Lightweight in-memory RAG for local testing."""

    def __init__(self):
        self.docs: List[Dict[str, Any]] = []

    async def upload_document(self, path: str, collection: str = "default"):
        try:
            p = Path(path)
            text = p.read_text(encoding="utf-8") if p.exists() else str(path)
        except Exception:
            text = str(path)
        self.docs.append({"text": text, "source": str(path), "collection": collection})
        return True, f"Mock indexed: {path}"

    async def search_context(self, query: str, collection: str = "default", top_k: int = 3, **kwargs):
        q = query.lower()
        results = []
        for d in self.docs:
            if collection and d.get("collection") != collection:
                continue
            txt = d.get("text", "").lower()
            score = 0.0
            if q in txt:
                score = 0.9
            else:
                match_count = sum(1 for w in q.split() if w in txt)
                if match_count:
                    score = min(0.5 + 0.1 * match_count, 0.8)
            if score > 0:
                results.append(
                    {
                        "text": d.get("text", "")[:1000],
                        "score": score,
                        "source": d.get("source"),
                        "collection": d.get("collection"),
                    }
                )
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]

    def format_context_for_llm(self, results, max_tokens=2000):
        if not results:
            return ""
        parts, total = [], 0
        for r in results:
            fmt = f"[Score:{r['score']:.2f}] {r['text'][:400]} (Source:{r.get('source')})"
            if total + len(fmt) + 2 > max_tokens:
                break
            parts.append(fmt)
            total += len(fmt) + 2
        return "\n\n".join(parts)[:max_tokens]

    def get_stats(self):
        return {
            "documents_uploaded": len(self.docs),
            "collections": {},
            "total_collection_size": sum(len(d.get("text", "")) for d in self.docs),
        }


# ─── RAGIntegration ─────────────────────────────────────


class RAGIntegration:
    """Wrapper around RAG manager for document handling and retrieval."""

    def __init__(self):
        self.rag_manager: Any = None
        self.documents: List[Dict[str, Any]] = []
        self.collections: Dict[str, List[Dict[str, Any]]] = {}
        self.initialized = False

    async def initialize(self) -> bool:
        """Initialize the RAG manager."""
        try:
            storage_path = Path(os.getcwd()) / "rag_storage"
            from zena_mode.rag_core_bridge import LocalRAGv2 as LocalRAG

            logger.info("Initializing RAG Engine (rag_core + Qdrant)…")
            self.rag_manager = LocalRAG(cache_dir=storage_path)
            self.rag_manager.warmup()
            self.initialized = True
            logger.info(f"✅ RAG Engine initialized at {storage_path}")
            return True
        except ImportError as exc:
            logger.warning(f"RAG manager not available: {exc}")
            logger.info("Falling back to in-process MockRAG")
            self.rag_manager = _MockRAG()
            self.initialized = True
            return True
        except Exception as exc:
            logger.error(f"Failed to initialize RAG: {exc}")
            self.initialized = False
            return False

    # ─── Upload ──────────────────────────────────────────

    async def upload_document(
        self,
        file_path: str,
        collection_name: str = "default",
        metadata: Optional[dict] = None,
    ) -> Tuple[bool, str]:
        if not self.initialized:
            return False, "RAG manager not initialized"
        try:
            fp = Path(file_path)
            if not fp.exists():
                return False, f"File not found: {fp}"
            logger.info(f"Indexing document: {fp.name}")
            if hasattr(self.rag_manager, "build_index"):
                text = fp.read_text(encoding="utf-8", errors="ignore")
                doc = {
                    "content": text,
                    "url": str(fp),
                    "title": fp.name,
                    "metadata": metadata or {},
                }
                await asyncio.to_thread(self.rag_manager.build_index, [doc])
                self._track(fp, collection_name, metadata)
                return True, f"✅ Indexed (Persistent): {fp.name}"
            return await self.rag_manager.upload_document(str(fp), collection=collection_name)
        except Exception as exc:
            return False, f"Failed to index document: {exc}"

    # ─── Search ──────────────────────────────────────────

    async def search_context(
        self,
        query: str,
        collection_name: str = "default",
        top_k: int = 3,
        score_threshold: float = 0.5,
    ) -> List[dict]:
        if not self.initialized or not self.rag_manager:
            return []
        try:
            if hasattr(self.rag_manager, "hybrid_search"):
                results = await asyncio.to_thread(self.rag_manager.hybrid_search, query, k=top_k, rerank=True)
                return [
                    {
                        "text": r.get("text", ""),
                        "score": r.get("score", 0),
                        "source": r.get("url") or r.get("title") or "unknown",
                        "collection": collection_name,
                    }
                    for r in results
                    if r.get("score", 0) >= score_threshold
                ]
            results = await self.rag_manager.search_context(query, collection=collection_name, top_k=top_k)
            return [r for r in results if r.get("score", 0) >= score_threshold]
        except Exception as exc:
            logger.error(f"Search failed: {exc}")
            return []

    # ─── Bulk index ──────────────────────────────────────

    async def index_content(
        self,
        content: str,
        sources: List[dict],
        source_name: str = "scan",
    ) -> Tuple[bool, str]:
        """Index raw extracted content into the vector database."""
        if not self.initialized:
            ok = await self.initialize()
            if not ok:
                return False, "RAG engine not available"
        try:
            documents = []
            if sources:
                blocks = _split_aggregated_text(content, sources)
                for src, block_text in zip(sources, blocks):
                    documents.append(
                        {
                            "content": block_text,
                            "url": src.get("path", source_name),
                            "title": src.get("title", source_name),
                        }
                    )
            else:
                documents.append({"content": content, "url": source_name, "title": source_name})
            if not documents:
                return False, "No content to index"
            if hasattr(self.rag_manager, "build_index"):
                await asyncio.to_thread(self.rag_manager.build_index, documents)
                total = sum(len(d["content"]) for d in documents)
                return True, f"✅ Indexed {len(documents)} sources ({total:,} chars)"
            for doc in documents:
                self.rag_manager.docs.append(
                    {
                        "text": doc.get("content", ""),
                        "source": doc.get("url", "unknown"),
                        "collection": "default",
                    }
                )
            return True, f"Indexed {len(documents)} sources (in-memory)"
        except Exception as exc:
            return False, f"Indexing failed: {exc}"

    # ─── Context formatting ──────────────────────────────

    async def query_context(
        self,
        query: str,
        top_k: int = 5,
        max_context_chars: int = 12000,
        score_threshold: float = 0.3,
    ) -> Tuple[str, List[dict]]:
        """Retrieve and format relevant context for a user query."""
        results = await self.search_context(query, top_k=top_k, score_threshold=score_threshold)
        if not results:
            return "", []
        parts, total = [], 0
        for i, r in enumerate(results):
            block = f"[Source {i + 1}: {r.get('source', '?')} | Score: {r.get('score', 0):.2f}]\n{r.get('text', '')}"
            if total + len(block) > max_context_chars:
                break
            parts.append(block)
            total += len(block)
        return "\n\n".join(parts), results

    def format_context_for_llm(self, results: List[dict], max_tokens: int = 12000) -> str:
        if not results:
            return ""
        parts, total = [], 0
        for r in results:
            fmt = f"[Score: {r.get('score', 0):.2f}] {r.get('text', '')} (Source: {r.get('source', '?')})"
            if total + len(fmt) + 2 > max_tokens:
                break
            parts.append(fmt)
            total += len(fmt) + 2
        out = f"Context:\n" + "\n\n".join(parts) + "\n"
        return out[:max_tokens]

    # ─── Stats / management ──────────────────────────────

    def get_stats(self) -> dict:
        return {
            "documents_uploaded": len(self.documents),
            "collections": {n: len(d) for n, d in self.collections.items()},
            "total_collection_size": sum(d.get("size", 0) for d in self.documents),
            "initialized": self.initialized,
        }

    def list_documents(self, collection_name: Optional[str] = None) -> List[dict]:
        if collection_name:
            return self.collections.get(collection_name, [])
        return self.documents

    def clear_collection(self, collection_name: str) -> bool:
        self.collections[collection_name] = []
        return True

    # ─── Private helpers ─────────────────────────────────

    def _track(self, fp: Path, collection_name: str, metadata: Optional[dict]) -> None:
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


# ─── Global singleton ───────────────────────────────────

_rag_integration: Optional[RAGIntegration] = None


async def get_rag() -> RAGIntegration:
    """Get or create the global RAG integration."""
    global _rag_integration
    if _rag_integration is None:
        _rag_integration = RAGIntegration()
        await _rag_integration.initialize()
    return _rag_integration


if __name__ == "__main__":

    async def _test():
        rag = await get_rag()
        # [X-Ray auto-fix] print(f"RAG Stats: {rag.get_stats()}")

    asyncio.run(_test())
