"""
Conflict Resolver - Detect & reconcile conflicting information across documents

When RAG retrieves multiple sources mentioning the same entity (person, org, place),
this module detects contradictions and helps choose the most reliable information.

Strategies:
1. Source Credibility - Some sources are more authoritative
2. Recency - Prefer newer information
3. Consensus - If multiple sources agree, higher confidence
4. Explicitness - Direct statements > inferences
5. Context Matching - Information in same context is more reliable
"""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Assertion:
    """Single factual claim extracted from a source"""

    entity: str  # "Barack Obama", "Apple Inc.", "Berlin"
    predicate: str  # "birth_year", "founded", "population"
    value: str  # "1961", "1976", "3.6M"
    source_name: str
    source_type: str  # "web", "pdf", "txt"
    source_date: Optional[datetime] = None
    context: str = ""  # surrounding text for disambiguation
    confidence: float = 1.0  # 0-1 based on source reliability


@dataclass
class Conflict:
    """Two+ assertions about same entity/predicate with different values"""

    entity: str
    predicate: str
    assertions: List[Assertion]
    resolution: Optional[str] = None  # Which value is correct
    reasoning: str = ""  # Why that value is correct


class SourceCredibilityMap:
    """Define source reliability: some sources are inherently more trustworthy"""

    # Source type credibility (0-1)
    TYPE_SCORES = {
        "official_site": 0.95,  # Official government/company website
        "academic": 0.90,  # Academic papers, journals
        "news": 0.75,  # News articles (varies by outlet)
        "wiki": 0.65,  # Wikipedia (collaborative but reviewed)
        "pdf": 0.60,  # PDFs (quality varies widely)
        "web": 0.50,  # General web pages
        "txt": 0.40,  # Plain text files
        "unknown": 0.50,
    }

    def __init__(self):
        # Custom overrides: {source_name: credibility_score}
        self.overrides: Dict[str, float] = {
            "wikipedia.org": 0.70,
            "britannica.com": 0.85,
            "bbc.com": 0.80,
            "reuters.com": 0.85,
            "apnews.com": 0.85,
        }

    def score(self, assertion: Assertion) -> float:
        """Get credibility score for a source (0-1)"""
        # Check for override first
        for override_name, score in self.overrides.items():
            if override_name in assertion.source_name.lower():
                return score

        # Fall back to type score
        return self.TYPE_SCORES.get(assertion.source_type, 0.5)


class ConflictResolver:
    """Detect and resolve conflicts in factual assertions"""

    def __init__(self):
        self.credibility = SourceCredibilityMap()

    def detect_conflicts(self, assertions: List[Assertion]) -> List[Conflict]:
        """Find all contradictions in a set of assertions"""
        if not assertions:
            return []

        # Group by (entity, predicate)
        grouped: Dict[Tuple[str, str], List[Assertion]] = {}
        for a in assertions:
            key = (a.entity.lower(), a.predicate.lower())
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(a)

        # Find conflicts (multiple different values for same entity/predicate)
        conflicts = []
        for (entity, predicate), group in grouped.items():
            unique_values = set(a.value.lower() for a in group)
            if len(unique_values) > 1:
                # Conflict: different values exist
                conflicts.append(
                    Conflict(
                        entity=entity,
                        predicate=predicate,
                        assertions=group,
                    )
                )

        return conflicts

    def resolve_conflict(self, conflict: Conflict) -> Conflict:
        """Suggest the most reliable value for a conflicted assertion"""

        # Strategy 1: Consensus - if majority agrees on one value
        value_counts = {}
        for a in conflict.assertions:
            val = a.value.lower()
            value_counts[val] = value_counts.get(val, 0) + 1

        max_count = max(value_counts.values())
        if max_count >= len(conflict.assertions) * 0.66:  # 66%+ consensus
            consensus_value = [v for v, c in value_counts.items() if c == max_count][0]
            conflict.resolution = consensus_value
            conflict.reasoning = (
                f"Consensus: {max_count}/{len(conflict.assertions)} sources agree on '{consensus_value}'"
            )
            return conflict

        # Strategy 2: Credibility + Recency
        scored = []
        for a in conflict.assertions:
            cred_score = self.credibility.score(a)
            recency_score = self._recency_score(a.source_date)
            combined = cred_score * 0.6 + recency_score * 0.4  # Credibility > Recency
            scored.append((a, combined))

        # Pick highest scoring assertion
        best_assertion, best_score = max(scored, key=lambda x: x[1])
        conflict.resolution = best_assertion.value
        conflict.reasoning = (
            f"Highest reliability: {best_assertion.source_name} "
            f"(credibility={self.credibility.score(best_assertion):.2f}, "
            f"recency={self._recency_score(best_assertion.source_date):.2f})"
        )

        return conflict

    def _recency_score(self, date: Optional[datetime]) -> float:
        """Score how recent a source is (0-1, higher is more recent)"""
        if date is None:
            return 0.5  # Unknown date = neutral

        age_days = (datetime.now() - date).days
        if age_days < 30:
            return 1.0
        elif age_days < 365:
            return 0.8
        elif age_days < 1825:  # 5 years
            return 0.5
        else:
            return 0.2  # Very old

    def build_assertion_summary(self, conflicts: List[Conflict]) -> str:
        """Generate human-readable conflict summary"""
        if not conflicts:
            return ""

        lines = ["⚠️ **Information Conflicts Detected:**\n"]
        for conflict in conflicts:
            lines.append(f"- **{conflict.entity}** ({conflict.predicate}):")
            for a in conflict.assertions:
                lines.append(f"  - `{a.value}` — from {a.source_name}")
            if conflict.resolution:
                lines.append(f"  **→ Recommended: `{conflict.resolution}`** ({conflict.reasoning})\n")
            else:
                lines.append("  **→ Unable to resolve. Check sources.**\n")

        return "\n".join(lines)


def extract_entities_and_claims(text: str, source_name: str) -> List[Assertion]:
    """
    Extract factual claims from a document.

    ⚠️ This is a SIMPLIFIED version. A production system would use:
    - Named Entity Recognition (NER) for entity detection
    - Open Information Extraction (OpenIE) for claim extraction
    - LLM-based extraction with structured output
    """
    # For now, just return empty list - real implementation would use NLP
    # This is a placeholder for where advanced NLP would go
    return []


# Example usage
if __name__ == "__main__":
    # Simulated assertions from different sources
    assertions = [
        Assertion(
            entity="Albert Einstein",
            predicate="birth_year",
            value="1879",
            source_name="britannica.com",
            source_type="academic",
            source_date=datetime(2020, 1, 1),
            confidence=0.95,
        ),
        Assertion(
            entity="Albert Einstein",
            predicate="birth_year",
            value="1878",  # Wrong!
            source_name="old_website.com",
            source_type="web",
            source_date=datetime(1999, 1, 1),
            confidence=0.4,
        ),
        Assertion(
            entity="Albert Einstein",
            predicate="birth_year",
            value="1879",
            source_name="wikipedia.org",
            source_type="wiki",
            source_date=datetime(2024, 1, 1),
            confidence=0.85,
        ),
    ]

    resolver = ConflictResolver()
    conflicts = resolver.detect_conflicts(assertions)
    # [X-Ray auto-fix] print(f"Found {len(conflicts)} conflicts:")
    for conflict in conflicts:
        resolved = resolver.resolve_conflict(conflict)
        print(resolver.build_assertion_summary([resolved]))
