"""
Core/conflict_detector.py — Cross-Source Fact Contradiction Detection.

Features:
  - Regex-based fact extraction (numbers, dates, names, claims)
  - Cross-source contradiction detection
  - Consensus reconciliation (majority-vote among sources)

Ported from ZEN_RAG.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ExtractedFact:
    """A single extracted fact from a source."""

    fact_type: str  # "number", "date", "claim", "name"
    value: str
    context: str  # Surrounding sentence
    source_url: str = ""
    source_title: str = ""
    chunk_index: int = 0


@dataclass
class Conflict:
    """A detected contradiction between sources."""

    topic: str
    fact_a: ExtractedFact
    fact_b: ExtractedFact
    conflict_type: str  # "numerical", "temporal", "factual"
    severity: str = "medium"  # "low", "medium", "high"


@dataclass
class ConflictReport:
    """Full conflict analysis of retrieved sources."""

    conflicts: List[Conflict] = field(default_factory=list)
    consensus_facts: List[Dict[str, Any]] = field(default_factory=list)
    total_facts_extracted: int = 0
    sources_analyzed: int = 0

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0


class ConflictDetector:
    """Cross-source contradiction detector for RAG chunks.

    Usage:
        detector = ConflictDetector()
        report = detector.detect(source_chunks)
        if report.has_conflicts:
            # Present conflicts to user
    """

    # Fact extraction patterns
    NUMBER_PATTERN = re.compile(
        r"(\b\d+\.?\d*\s*(?:%|percent|million|billion|thousand|kg|km|miles?|dollars?|euros?|USD|EUR|GBP)?)\b"
    )
    DATE_PATTERN = re.compile(
        r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}|"
        r"(?:january|february|march|april|may|june|july|august|september|"
        r"october|november|december)\s+\d{1,2},?\s+\d{4}|"
        r"\d{4})\b",
        re.IGNORECASE,
    )
    NAME_PATTERN = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b")

    def detect(self, source_chunks: List[Dict[str, Any]]) -> ConflictReport:
        """Detect contradictions across source chunks."""
        if not source_chunks:
            return ConflictReport()

        # Extract facts from each source
        all_facts: List[ExtractedFact] = []
        for i, chunk in enumerate(source_chunks):
            text = chunk.get("text", "")
            url = chunk.get("url", "")
            title = chunk.get("title", "")
            facts = self._extract_facts(text, url, title, i)
            all_facts.extend(facts)

        if not all_facts:
            return ConflictReport(sources_analyzed=len(source_chunks))

        # Detect conflicts
        conflicts = self._find_conflicts(all_facts)

        # Build consensus
        consensus = self._build_consensus(all_facts)

        return ConflictReport(
            conflicts=conflicts,
            consensus_facts=consensus,
            total_facts_extracted=len(all_facts),
            sources_analyzed=len(source_chunks),
        )

    def _extract_facts(
        self,
        text: str,
        source_url: str = "",
        source_title: str = "",
        chunk_index: int = 0,
    ) -> List[ExtractedFact]:
        """Extract verifiable facts from a text chunk."""
        facts = []
        sentences = re.split(r"(?<=[.!?])\s+", text)

        for sent in sentences:
            # Numbers
            for m in self.NUMBER_PATTERN.finditer(sent):
                facts.append(ExtractedFact(
                    fact_type="number",
                    value=m.group(1).strip(),
                    context=sent,
                    source_url=source_url,
                    source_title=source_title,
                    chunk_index=chunk_index,
                ))

            # Dates
            for m in self.DATE_PATTERN.finditer(sent):
                facts.append(ExtractedFact(
                    fact_type="date",
                    value=m.group(1).strip(),
                    context=sent,
                    source_url=source_url,
                    source_title=source_title,
                    chunk_index=chunk_index,
                ))

        return facts

    def _find_conflicts(self, facts: List[ExtractedFact]) -> List[Conflict]:
        """Find contradictions among extracted facts."""
        conflicts = []

        # Group facts by type
        by_type: Dict[str, List[ExtractedFact]] = {}
        for f in facts:
            by_type.setdefault(f.fact_type, []).append(f)

        # Check numerical conflicts
        for f_type, type_facts in by_type.items():
            if f_type == "number":
                conflicts.extend(self._check_numerical_conflicts(type_facts))
            elif f_type == "date":
                conflicts.extend(self._check_date_conflicts(type_facts))

        return conflicts

    def _check_numerical_conflicts(self, facts: List[ExtractedFact]) -> List[Conflict]:
        """Find conflicting numerical claims about the same topic."""
        conflicts = []

        for i, fa in enumerate(facts):
            for fb in facts[i + 1:]:
                # Same source → skip
                if fa.source_url and fa.source_url == fb.source_url:
                    continue

                # Check if they discuss the same topic (context overlap)
                if not self._same_topic(fa.context, fb.context):
                    continue

                # Check if values conflict
                try:
                    val_a = float(re.sub(r"[^\d.]", "", fa.value))
                    val_b = float(re.sub(r"[^\d.]", "", fb.value))
                    if val_a > 0 and val_b > 0:
                        ratio = max(val_a, val_b) / min(val_a, val_b)
                        if ratio > 1.5:  # >50% difference
                            severity = "high" if ratio > 3 else "medium"
                            conflicts.append(Conflict(
                                topic=self._extract_topic(fa.context, fb.context),
                                fact_a=fa,
                                fact_b=fb,
                                conflict_type="numerical",
                                severity=severity,
                            ))
                except (ValueError, ZeroDivisionError):
                    continue

        return conflicts

    def _check_date_conflicts(self, facts: List[ExtractedFact]) -> List[Conflict]:
        """Find conflicting date claims about the same topic."""
        conflicts = []

        for i, fa in enumerate(facts):
            for fb in facts[i + 1:]:
                if fa.source_url and fa.source_url == fb.source_url:
                    continue
                if not self._same_topic(fa.context, fb.context):
                    continue
                if fa.value != fb.value:
                    conflicts.append(Conflict(
                        topic=self._extract_topic(fa.context, fb.context),
                        fact_a=fa,
                        fact_b=fb,
                        conflict_type="temporal",
                        severity="medium",
                    ))

        return conflicts

    @staticmethod
    def _same_topic(context_a: str, context_b: str) -> bool:
        """Check if two contexts discuss the same topic (keyword overlap)."""
        from Core.constants import STOP_WORDS
        words_a = {w.lower() for w in re.findall(r"\w{4,}", context_a) if w.lower() not in STOP_WORDS}
        words_b = {w.lower() for w in re.findall(r"\w{4,}", context_b) if w.lower() not in STOP_WORDS}
        if not words_a or not words_b:
            return False
        overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
        return overlap > 0.3

    @staticmethod
    def _extract_topic(context_a: str, context_b: str) -> str:
        """Extract common topic from two contexts."""
        from Core.constants import STOP_WORDS
        words_a = {w.lower() for w in re.findall(r"\w{4,}", context_a) if w.lower() not in STOP_WORDS}
        words_b = {w.lower() for w in re.findall(r"\w{4,}", context_b) if w.lower() not in STOP_WORDS}
        common = words_a & words_b
        return " ".join(sorted(common)[:5]) if common else "unknown topic"

    @staticmethod
    def _build_consensus(facts: List[ExtractedFact]) -> List[Dict[str, Any]]:
        """Build majority-vote consensus from extracted facts."""
        # Group by (fact_type, approximate_topic)
        groups: Dict[str, List[ExtractedFact]] = {}
        for f in facts:
            key = f"{f.fact_type}:{f.value[:20]}"
            groups.setdefault(key, []).append(f)

        consensus = []
        for key, group in groups.items():
            if len(group) >= 2:
                consensus.append({
                    "fact_type": group[0].fact_type,
                    "value": group[0].value,
                    "support_count": len(group),
                    "sources": list({f.source_url for f in group if f.source_url}),
                })

        return sorted(consensus, key=lambda x: x["support_count"], reverse=True)
