"""
Core/parent_document_retrieval.py — Hierarchical Parent Document Retrieval.

Industry best practice: Index smaller child chunks for precise matching
but return their larger parent chunks to give the LLM more context.
This solves the chunk-size tradeoff: small chunks for retrieval precision,
large chunks for generation context.

Pipeline:
  1. Split documents into large "parent" chunks (e.g., 2000 chars)
  2. Split parents into smaller "child" chunks (e.g., 500 chars)
  3. Index child chunks with parent_id reference
  4. On retrieval: match child chunks, then return parent chunks
  5. Deduplicate parents to avoid redundant context

References:
  - LangChain ParentDocumentRetriever
  - "Small-to-Big" retrieval pattern (LlamaIndex)
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ParentChunk:
    """A parent chunk containing child chunks."""

    text: str
    chunk_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    children: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not self.chunk_id:
            self.chunk_id = hashlib.sha256(
                self.text[:200].encode()
            ).hexdigest()[:16]


@dataclass
class ParentRetrievalResult:
    """Result of parent document retrieval."""

    parent_chunks: List[ParentChunk] = field(default_factory=list)
    matched_children: List[Dict[str, Any]] = field(default_factory=list)
    child_to_parent_map: Dict[str, str] = field(default_factory=dict)
    total_parent_chars: int = 0


class ParentDocumentRetriever:
    """Hierarchical retrieval: match children, return parents.

    Indexes small chunks for precision but expands to full parent
    context for generation, giving the LLM the surrounding context
    it needs to produce coherent answers.

    Usage:
        pdr = ParentDocumentRetriever(parent_size=2000, child_size=500)
        parents, children = pdr.create_hierarchy(document_text, metadata)
        # Index children in vector store with parent_id

        # At retrieval time:
        results = pdr.expand_to_parents(matched_children, parent_store)
    """

    def __init__(
        self,
        parent_size: int = 2000,
        child_size: int = 500,
        child_overlap: int = 50,
        max_parents_returned: int = 5,
    ):
        """
        Args:
            parent_size: char size for parent chunks
            child_size: char size for child chunks
            child_overlap: overlap between child chunks
            max_parents_returned: max parent chunks in output
        """
        self.parent_size = parent_size
        self.child_size = child_size
        self.child_overlap = child_overlap
        self.max_parents_returned = max_parents_returned
        self._parent_store: Dict[str, ParentChunk] = {}

    def create_hierarchy(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[ParentChunk], List[Dict[str, Any]]]:
        """Split a document into parent and child chunks.

        Returns:
            (parent_chunks, child_chunks) where each child has 'parent_id'
        """
        metadata = metadata or {}
        parents = self._split_text(text, self.parent_size, overlap=0)
        all_children = []

        parent_chunks = []
        for i, parent_text in enumerate(parents):
            parent = ParentChunk(
                text=parent_text,
                metadata={**metadata, "parent_index": i},
            )

            # Split parent into children
            child_texts = self._split_text(
                parent_text, self.child_size, self.child_overlap
            )
            for j, child_text in enumerate(child_texts):
                child = {
                    "text": child_text,
                    "parent_id": parent.chunk_id,
                    "chunk_index": len(all_children),
                    "child_index": j,
                    "parent_index": i,
                    **metadata,
                }
                parent.children.append(child)
                all_children.append(child)

            parent_chunks.append(parent)
            self._parent_store[parent.chunk_id] = parent

        logger.info(
            f"[ParentDoc] Created {len(parent_chunks)} parents, "
            f"{len(all_children)} children"
        )
        return parent_chunks, all_children

    def expand_to_parents(
        self,
        matched_children: List[Dict[str, Any]],
        parent_store: Optional[Dict[str, ParentChunk]] = None,
    ) -> ParentRetrievalResult:
        """Given matched child chunks, expand to their parent chunks.

        Deduplicates parents and orders by number of matched children
        (more child matches = more relevant parent).
        """
        store = parent_store or self._parent_store
        result = ParentRetrievalResult(matched_children=matched_children)

        # Group children by parent_id
        parent_hits: Dict[str, int] = {}
        child_map: Dict[str, str] = {}

        for child in matched_children:
            pid = child.get("parent_id")
            if pid:
                parent_hits[pid] = parent_hits.get(pid, 0) + 1
                child_key = child.get("text", "")[:50]
                child_map[child_key] = pid

        result.child_to_parent_map = child_map

        # Sort parents by hit count (most relevant first)
        ranked_parents = sorted(
            parent_hits.items(), key=lambda x: x[1], reverse=True
        )

        for pid, hit_count in ranked_parents[:self.max_parents_returned]:
            parent = store.get(pid)
            if parent:
                result.parent_chunks.append(parent)
                result.total_parent_chars += len(parent.text)

        logger.info(
            f"[ParentDoc] Expanded {len(matched_children)} children → "
            f"{len(result.parent_chunks)} parents "
            f"({result.total_parent_chars} chars)"
        )
        return result

    def get_parent_context(
        self,
        search_results: List[Dict[str, Any]],
        parent_store: Optional[Dict[str, ParentChunk]] = None,
    ) -> List[Dict[str, Any]]:
        """Replace child search results with their parent chunks.

        Maintains result ordering while expanding context.
        Returns results suitable for the standard RAG pipeline.
        """
        store = parent_store or self._parent_store
        seen_parents = set()
        expanded = []

        for result in search_results:
            pid = result.get("parent_id")
            if pid and pid not in seen_parents:
                parent = store.get(pid)
                if parent:
                    seen_parents.add(pid)
                    expanded.append({
                        **result,
                        "text": parent.text,
                        "parent_text": parent.text,
                        "_expanded_from_child": True,
                        "_child_score": result.get("score", 0),
                    })
                    continue

            # If no parent, keep the original chunk
            if not pid or pid in seen_parents:
                if result.get("text", "")[:50] not in {
                    e.get("text", "")[:50] for e in expanded
                }:
                    expanded.append(result)

        return expanded[:self.max_parents_returned * 2]

    def register_parents(self, parents: List[ParentChunk]):
        """Register parent chunks for later retrieval expansion."""
        for parent in parents:
            self._parent_store[parent.chunk_id] = parent

    def clear(self):
        """Clear the parent store."""
        self._parent_store.clear()

    @staticmethod
    def _split_text(text: str, chunk_size: int, overlap: int = 0) -> List[str]:
        """Simple character-level text splitter with overlap."""
        if not text or chunk_size <= 0:
            return []

        # Clamp overlap to less than chunk_size to guarantee forward progress
        overlap = min(overlap, chunk_size - 1)

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size

            # Try to break at a sentence or paragraph boundary
            if end < len(text):
                # Look for nearest paragraph break
                para_break = text.rfind("\n\n", start, end)
                if para_break > start + chunk_size // 2:
                    end = para_break + 2
                else:
                    # Look for nearest sentence break
                    sent_break = max(
                        text.rfind(". ", start, end),
                        text.rfind("! ", start, end),
                        text.rfind("? ", start, end),
                    )
                    if sent_break > start + chunk_size // 2:
                        end = sent_break + 2

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            new_start = end - overlap if overlap > 0 else end
            # Guarantee forward progress: at least 1 char advance
            start = max(new_start, start + 1)

        return chunks
