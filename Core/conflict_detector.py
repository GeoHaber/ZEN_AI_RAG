"""
Conflict Detection Pipeline

Detects when sources provide contradictory information and
routes to human-in-the-loop resolver for user judgment.

Pipeline:
1. Retrieve multiple sources for query
2. Extract claims from each source
3. Compare claims for contradictions
4. If conflict detected → surface to human
5. Aggregate human judgments to resolve
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


@dataclass
class ExtractedFact:
    """A single factual claim from a source"""

    fact: str
    subject: str
    predicate: str
    value: str
    source_name: str
    source_type: str
    source_date: Optional[str]
    credibility: float
    relevance: float
    context_snippet: str  # Original sentence for reference


class ConflictDetector:
    """Detect contradictions in multi-source retrieval"""

    def __init__(self):
        self.fact_extraction_patterns = [
            # "X was born in Y"
            r"(\w+[\w\s]*\w+)\s+(?:was\s+)?born\s+(?:in|on)?\s+([^.,;]+)",
            # "X has Y members"
            r"(\w+[\w\s]*\w+)\s+has\s+(\d+[\w\s]*(?:members|employees|residents))",
            # "X is Y"
            r"(\w+[\w\s]*\w+)\s+is\s+([^.,;]+?)(?:\s+and|\s+but|[.,;])",
            # "X founded in Y"
            r"(\w+[\w\s]*\w+)\s+(?:was\s+)?founded\s+(?:in|on)?\s+([^.,;]+)",
            # "X has population of Y"
            r"(\w+[\w\s]*\w+)\s+(?:has\s+)?population\s+(?:of\s+)?(\d+[\w\s,]*)",
        ]

    def detect_conflicts_in_sources(
        self,
        query: str,
        sources: List[Dict[str, Any]],
        min_confidence: float = 0.7,
    ) -> List[Tuple[ExtractedFact, ExtractedFact, str]]:
        """
        Detect factual conflicts across sources.

        Returns:
            List of (fact1, fact2, conflict_summary)
        """
        # Extract facts from all sources
        all_facts = []
        for source in sources:
            facts = self._extract_facts_from_source(source)
            all_facts.extend(facts)

        if len(all_facts) < 2:
            return []

        # Find contradictions
        conflicts = []
        checked = set()

        for i, fact1 in enumerate(all_facts):
            for fact2 in all_facts[i + 1 :]:
                pair_key = (fact1.subject, fact2.subject)

                if pair_key in checked:
                    continue

                # Do they contradict?
                if self._are_contradictory(fact1, fact2):
                    checked.add(pair_key)
                    summary = self._summarize_conflict(fact1, fact2)
                    conflicts.append((fact1, fact2, summary))

        return conflicts

    def _extract_facts_from_source(
        self,
        source: Dict[str, Any],
    ) -> List[ExtractedFact]:
        """Extract factual claims from source text"""
        text = source.get("text", "")
        if not text:
            return []

        facts = []

        for pattern in self.fact_extraction_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    groups = match.groups()
                    if len(groups) >= 2:
                        subject = groups[0].strip()
                        value = groups[1].strip()

                        # Determine predicate from pattern
                        if "born" in pattern:
                            predicate = "born in"
                        elif "population" in pattern:
                            predicate = "has population"
                        elif "founded" in pattern:
                            predicate = "founded in"
                        elif "has" in pattern:
                            predicate = "has"
                        else:
                            predicate = "is"

                        fact = ExtractedFact(
                            fact=f"{subject} {predicate} {value}",
                            subject=subject,
                            predicate=predicate,
                            value=value,
                            source_name=source.get("name", "Unknown"),
                            source_type=source.get("type", "web"),
                            source_date=source.get("date"),
                            credibility=source.get("credibility", 0.5),
                            relevance=source.get("relevance", source.get("score", 0.5)),
                            context_snippet=text[max(0, match.start() - 50) : min(len(text), match.end() + 50)],
                        )

                        facts.append(fact)
                except (IndexError, AttributeError) as e:
                    logger.debug(f"Failed to extract fact from pattern: {e}")

        return facts

    def _are_contradictory(self, fact1: ExtractedFact, fact2: ExtractedFact) -> bool:
        """
        Check if two facts contradict each other.

        Criteria:
        - Same subject
        - Same predicate
        - Different values
        """
        # Must be about the same thing
        subj1 = fact1.subject.lower()
        subj2 = fact2.subject.lower()

        # Strict match OR partial match for longer subjects
        match = subj1 == subj2
        if not match and len(subj1) > 3 and len(subj2) > 3:
            match = (subj1 in subj2) or (subj2 in subj1)

        if not match:
            return False

        # Must be the same predicate
        if fact1.predicate.lower() != fact2.predicate.lower():
            return False

        # Values must be different (not just case/whitespace)
        if fact1.value.lower() == fact2.value.lower():
            return False

        # Check for negation (not true contradiction)
        if self._is_negated(fact1.value) or self._is_negated(fact2.value):
            return False

        return True

    def _is_negated(self, value: str) -> bool:
        """Check if value is negated"""
        negations = ["not", "never", "no ", "none", "isn't", "wasn't", "isn't"]
        return any(neg.lower() in value.lower() for neg in negations)

    def _summarize_conflict(self, fact1: ExtractedFact, fact2: ExtractedFact) -> str:
        """Generate human-readable summary of what conflicts"""
        return f"Sources disagree on '{fact1.predicate}' for '{fact1.subject}': '{fact1.value}' vs '{fact2.value}'"

    def find_supporting_evidence(
        self,
        query: str,
        sources: List[Dict[str, Any]],
        fact_value: str,
        max_results: int = 3,
    ) -> List[Dict[str, Any]]:
        """Find sources that support a particular claim"""
        supporting = []

        for source in sources:
            text = source.get("text", "").lower()
            if fact_value.lower() in text:
                supporting.append(source)
                if len(supporting) >= max_results:
                    break

        return supporting

    def reconcile_with_consensus(
        self,
        conflicts: List[Tuple[ExtractedFact, ExtractedFact, str]],
        all_sources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Try to reconcile conflicts using consensus.

        If N sources agree on a value and only M disagree,
        prefer the consensus but flag as uncertain.
        """
        reconciliation = {}

        for fact1, fact2, summary in conflicts:
            # Count how many sources support each value
            support_1 = self.find_supporting_evidence("", all_sources, fact1.value, max_results=len(all_sources))
            support_2 = self.find_supporting_evidence("", all_sources, fact2.value, max_results=len(all_sources))

            consensus_value = None
            consensus_confidence = 0.5

            if len(support_1) > len(support_2):
                consensus_value = fact1.value
                consensus_confidence = len(support_1) / max(len(support_1) + len(support_2), 1)
            elif len(support_2) > len(support_1):
                consensus_value = fact2.value
                consensus_confidence = len(support_2) / max(len(support_1) + len(support_2), 1)

            reconciliation[summary] = {
                "consensus_value": consensus_value,
                "consensus_confidence": consensus_confidence,
                "count_supporting_1": len(support_1),
                "count_supporting_2": len(support_2),
                "need_human_judgment": (consensus_confidence < 0.66),  # Uncertain if not 2/3 consensus
            }

        return reconciliation
