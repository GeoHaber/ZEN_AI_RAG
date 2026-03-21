"""
Core/rag_models.py — Pydantic validation models for RAG data pipeline.

Provides validated dataclasses for:
  - ChunkPayload: what gets stored in Qdrant per chunk
  - RAGSearchResult: what hybrid_search() returns per result
  - QueryRewriteResult: multi-query expansion output
  - EvalSample: evaluation harness sample

Ported from ZEN_RAG.
"""

from __future__ import annotations
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChunkPayload(BaseModel):
    """Validated payload stored in Qdrant for each chunk."""

    model_config = ConfigDict(extra="allow")

    text: str = Field(..., min_length=1, description="Chunk text content")
    url: Optional[str] = Field(None, description="Source URL or file path")
    title: Optional[str] = Field(None, description="Document title")
    scan_root: Optional[str] = Field(None, description="Root path scanned")
    chunk_index: int = Field(0, ge=0, description="Position of this chunk in the document")
    is_table: bool = Field(False, description="True if chunk represents tabular data")
    sheet_name: Optional[str] = Field(None, description="Excel sheet name (tables only)")
    parent_id: Optional[str] = Field(None, description="Parent chunk hash (hierarchical chunking)")
    doc_type: Optional[str] = Field(None, description="Document type: pdf, docx, web, excel, ...")

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Chunk text must not be blank")
        return v.strip()


class RAGSearchResult(BaseModel):
    """Validated search result returned by hybrid_search / search."""

    model_config = ConfigDict(extra="allow")

    text: str = Field(..., min_length=1, description="Retrieved chunk text")
    url: Optional[str] = Field(None, description="Source URL or file path")
    title: Optional[str] = Field(None, description="Document title")
    score: float = Field(0.0, description="Retrieval score (Qdrant cosine or fusion)")
    rerank_score: Optional[float] = Field(None, description="Post-reranking score")
    fusion_score: Optional[float] = Field(None, description="RRF fusion score")
    is_cached: bool = Field(False, description="True if result came from cache")
    parent_text: Optional[str] = Field(None, description="Parent chunk text for context window")
    is_table: bool = Field(False, description="True if chunk is tabular data")

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("SearchResult text must not be blank")
        return v.strip()

    @field_validator("score", "rerank_score", "fusion_score", mode="before")
    @classmethod
    def coerce_float(cls, v: Any) -> Optional[float]:
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0


class QueryRewriteResult(BaseModel):
    """Output of multi-query expansion."""

    original: str = Field(..., description="Original user query")
    rewrites: List[str] = Field(default_factory=list, description="LLM-generated query variations")
    strategy: str = Field("passthrough", description="Strategy used: llm, template, passthrough")

    @property
    def all_queries(self) -> List[str]:
        """Original + all rewrites (deduplicated)."""
        seen = {self.original.lower()}
        result = [self.original]
        for q in self.rewrites:
            if q.lower() not in seen:
                seen.add(q.lower())
                result.append(q)
        return result


class EvalSample(BaseModel):
    """A single evaluation sample with ground truth."""

    query: str
    expected_answer: str
    retrieved_texts: List[str] = Field(default_factory=list)
    generated_answer: Optional[str] = None
    relevance_scores: List[float] = Field(default_factory=list)
    ndcg: Optional[float] = None
    mrr: Optional[float] = None
