"""
Human-in-the-Loop Conflict Resolution

Best practices from HITL research:
- Transparency: Show all claims, sources, credibility scores
- Agency: User decides what's true (expert judgment > algorithm)
- Feedback learning: System improves from user corrections
- Low friction: Simple voting interface for busy users

Based on patterns from:
- Crowdsourcing interfaces (Mechanical Turk, Amazon)
- Fact-checking platforms (Snopes, Full Fact)
- Active learning systems (human-in-loop ML)
- Trust frameworks (credibility assessment literature)
"""

import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class UserDecision(str, Enum):
    """User's judgment on conflicting claims"""

    CHOICE_1 = "claim_1"  # First version is correct
    CHOICE_2 = "claim_2"  # Second version is correct
    BOTH_VALID = "both"  # Both are valid in different contexts
    NEITHER = "neither"  # Both are wrong/incomplete
    UNCERTAIN = "uncertain"  # User doesn't know/can't decide


@dataclass
class ClaimVersion:
    """Single version of a claim from one source"""

    text: str
    source_name: str
    source_type: str  # "pdf", "web", "wiki", etc.
    source_date: Optional[str]
    credibility_score: float  # 0-1, higher = more credible
    relevance_score: float  # 0-1, how relevant to query


@dataclass
class ConflictToResolve:
    """A conflict presented to user for judgment"""

    conflict_id: str
    original_query: str
    subject: str  # What the claims are about
    predicate: str  # What attribute/property
    claim_1: ClaimVersion
    claim_2: ClaimVersion
    reasoning: str  # Why system thinks there's a conflict
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class UserJudgment:
    """User's decision on a conflict"""

    conflict_id: str
    decision: UserDecision
    confidence: float  # User's confidence in their decision (0-1)
    explanation: Optional[str] = None  # Why user chose this
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class JudgmentFeedback:
    """Feedback for ML system from user judgment"""

    conflict_id: str
    user_decision: UserDecision
    system_vote: Optional[str]  # Which claim system preferred
    system_confidence: float  # System's confidence
    user_confidence: float
    was_system_correct: bool
    source_1_credibility: float
    source_2_credibility: float
    timestamp: datetime = field(default_factory=datetime.now)

    def is_learning_opportunity(self) -> bool:
        """Did user disagree with system? Learn from this."""
        return not self.was_system_correct


class HumanLoopConflictResolver:
    """
    Presents conflicts to human for judgment.

    HITL Pattern: Algorithm finds multiple versions →
    Algorithm ranks by confidence → Human votes on best →
    System learns from feedback
    """

    def __init__(self, feedback_dir: Path = None):
        self.feedback_dir = feedback_dir or Path("data/conflict_feedback")
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        self.judgments: Dict[str, UserJudgment] = {}
        self._load_feedback_history()

    def detect_conflict_for_human(
        self,
        subject: str,
        predicate: str,
        value_1: str,
        source_1: Dict[str, Any],
        value_2: str,
        source_2: Dict[str, Any],
        query: str = "",
    ) -> ConflictToResolve:
        """
        Create conflict for human to judge.

        Args:
            subject: What we're talking about (e.g., "Albert Einstein")
            predicate: What attribute (e.g., "born in")
            value_1, value_2: Conflicting values
            source_1, source_2: Evidence for each
            query: Original user query

        Returns:
            ConflictToResolve object ready for UI display
        """
        import hashlib

        conflict_id = hashlib.md5(f"{subject}:{predicate}:{value_1}:{value_2}".encode()).hexdigest()[:12]

        claim_1 = ClaimVersion(
            text=f"{subject} {predicate} {value_1}",
            source_name=source_1.get("name", "Unknown"),
            source_type=source_1.get("type", "web"),
            source_date=source_1.get("date"),
            credibility_score=source_1.get("credibility", 0.5),
            relevance_score=source_1.get("relevance", source_1.get("score", 0.5)),
        )

        claim_2 = ClaimVersion(
            text=f"{subject} {predicate} {value_2}",
            source_name=source_2.get("name", "Unknown"),
            source_type=source_2.get("type", "web"),
            source_date=source_2.get("date"),
            credibility_score=source_2.get("credibility", 0.5),
            relevance_score=source_2.get("relevance", source_2.get("score", 0.5)),
        )

        reasoning = self._generate_conflict_reasoning(claim_1, claim_2)

        return ConflictToResolve(
            conflict_id=conflict_id,
            original_query=query,
            subject=subject,
            predicate=predicate,
            claim_1=claim_1,
            claim_2=claim_2,
            reasoning=reasoning,
        )

    def _generate_conflict_reasoning(self, claim_1: ClaimVersion, claim_2: ClaimVersion) -> str:
        """Generate human-friendly explanation of why this is a conflict"""
        source1_strong = claim_1.credibility_score > claim_2.credibility_score
        self._compare_dates(claim_1.source_date, claim_2.source_date)

        reasons = []

        # Why sources differ
        if claim_1.source_type != claim_2.source_type:
            reasons.append(f"Different source types: {claim_1.source_type.upper()} vs {claim_2.source_type.upper()}")

        if claim_1.source_date != claim_2.source_date:
            reasons.append(
                f"Different publication dates: {claim_1.source_date or 'unknown'} vs {claim_2.source_date or 'unknown'}"
            )

        if abs(claim_1.credibility_score - claim_2.credibility_score) > 0.2:
            more_credible = "first" if source1_strong else "second"
            reasons.append(f"{more_credible.capitalize()} source is more credible")

        reasoning = " | ".join(reasons) if reasons else "Sources contain conflicting information"
        return reasoning

    def format_conflict_for_ui(self, conflict: ConflictToResolve) -> Dict[str, Any]:
        """Format conflict for display in Streamlit UI"""
        return {
            "conflict_id": conflict.conflict_id,
            "subject": conflict.subject,
            "predicate": conflict.predicate,
            "query": conflict.original_query,
            "claim_1": {
                "text": conflict.claim_1.text,
                "source": conflict.claim_1.source_name,
                "type": conflict.claim_1.source_type,
                "date": conflict.claim_1.source_date,
                "credibility": conflict.claim_1.credibility_score,
                "relevance": conflict.claim_1.relevance_score,
            },
            "claim_2": {
                "text": conflict.claim_2.text,
                "source": conflict.claim_2.source_name,
                "type": conflict.claim_2.source_type,
                "date": conflict.claim_2.source_date,
                "credibility": conflict.claim_2.credibility_score,
                "relevance": conflict.claim_2.relevance_score,
            },
            "reasoning": conflict.reasoning,
            "timestamp": conflict.timestamp.isoformat(),
        }

    def record_user_judgment(
        self,
        conflict_id: str,
        decision: UserDecision,
        user_confidence: float = 0.7,
        explanation: str = None,
    ) -> UserJudgment:
        """
        Record user's vote on which claim is correct.

        This is the learning signal for improving future decisions.
        """
        judgment = UserJudgment(
            conflict_id=conflict_id,
            decision=decision,
            confidence=user_confidence,
            explanation=explanation,
        )

        self.judgments[conflict_id] = judgment
        self._save_judgment(judgment)

        return judgment

    def _save_judgment(self, judgment: UserJudgment) -> None:
        """Persist user judgment to disk"""
        file_path = self.feedback_dir / f"{judgment.conflict_id}.json"
        file_path.write_text(
            json.dumps(
                {
                    "conflict_id": judgment.conflict_id,
                    "decision": judgment.decision.value,
                    "confidence": judgment.confidence,
                    "explanation": judgment.explanation,
                    "timestamp": judgment.timestamp.isoformat(),
                },
                indent=2,
            )
        )

    def _load_feedback_history(self) -> None:
        """Load all past user judgments"""
        for file_path in self.feedback_dir.glob("*.json"):
            try:
                data = json.loads(file_path.read_text())
                judgment = UserJudgment(
                    conflict_id=data["conflict_id"],
                    decision=UserDecision(data["decision"]),
                    confidence=data["confidence"],
                    explanation=data.get("explanation"),
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                )
                self.judgments[judgment.conflict_id] = judgment
            except Exception as e:
                logger.warning(f"Failed to load judgment {file_path}: {e}")

    def get_feedback_statistics(self) -> Dict[str, Any]:
        """Analyze feedback patterns to improve system behavior"""
        if not self.judgments:
            return {"total_judgments": 0}

        decisions = [j.decision.value for j in self.judgments.values()]
        confidences = [j.confidence for j in self.judgments.values()]

        return {
            "total_judgments": len(self.judgments),
            "decision_distribution": {d.value: decisions.count(d.value) for d in UserDecision},
            "average_user_confidence": sum(confidences) / len(confidences),
            "high_confidence_judgments": sum(1 for c in confidences if c > 0.8),
            "uncertain_judgments": sum(1 for c in confidences if c < 0.5),
        }

    def _compare_dates(self, date1: Optional[str], date2: Optional[str]) -> bool:
        """Return True if date1 > date2 (more recent). Handle missing dates."""
        if not date1 or not date2:
            return False

        try:
            from datetime import datetime as dt

            d1 = dt.fromisoformat(date1)
            d2 = dt.fromisoformat(date2)
            return d1 > d2
        except (ValueError, AttributeError):
            return False

    def suggest_system_preference(self, conflict: ConflictToResolve) -> Tuple[int, float, str]:
        """
        What would the system vote? (for comparison)

        Returns:
            (claim_number: 1 or 2, confidence: 0-1, reasoning: str)
        """
        # Simple heuristic: credibility + recency + relevance
        score_1 = conflict.claim_1.credibility_score * 0.5 + conflict.claim_1.relevance_score * 0.3

        score_2 = conflict.claim_2.credibility_score * 0.5 + conflict.claim_2.relevance_score * 0.3

        # Adjust for date recency
        if self._compare_dates(conflict.claim_1.source_date, conflict.claim_2.source_date):
            score_1 += 0.2
        elif self._compare_dates(conflict.claim_2.source_date, conflict.claim_1.source_date):
            score_2 += 0.2

        choice = 1 if score_1 > score_2 else 2
        confidence = max(score_1, score_2)
        reasoning = f"Based on source credibility ({choice}.credibility={max(score_1, score_2):.2f})"

        return choice, confidence, reasoning
