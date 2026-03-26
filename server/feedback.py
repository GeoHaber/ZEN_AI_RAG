"""
FeedbackCollector — ring-buffer feedback store with per-model aggregation.

Extracted from api_server.py.
"""

import time
import uuid
from collections import deque
from typing import Any, Dict, List, Optional


class FeedbackCollector:
    """Ring-buffer feedback store with per-model aggregation."""

    VALID_TAGS = frozenset(
        [
            "accurate",
            "inaccurate",
            "fast",
            "slow",
            "creative",
            "verbose",
            "concise",
            "helpful",
            "unhelpful",
            "hallucination",
            "off_topic",
            "good_code",
            "bad_code",
            "well_formatted",
        ]
    )

    def __init__(self, max_events: int = 500):
        self._events: deque = deque(maxlen=max_events)
        self._total: int = 0
        self._model_stats: Dict[str, Dict[str, Any]] = {}

    def submit(
        self,
        model: str,
        thumbs: Optional[str] = None,
        rating: Optional[int] = None,
        tags: Optional[List[str]] = None,
        response_id: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record one piece of feedback. Returns the stored entry."""
        entry = {
            "feedback_id": uuid.uuid4().hex[:12],
            "response_id": response_id,
            "model": model,
            "thumbs": thumbs,
            "rating": rating,
            "tags": tags or [],
            "comment": comment,
            "timestamp": time.time(),
        }
        self._events.append(entry)
        self._total += 1
        self._update_model_stats(entry)
        return entry

    def _update_model_stats(self, entry: Dict[str, Any]) -> None:
        model = entry["model"]
        if model not in self._model_stats:
            self._model_stats[model] = {
                "total": 0,
                "thumbs_up": 0,
                "thumbs_down": 0,
                "rating_sum": 0.0,
                "rating_count": 0,
                "tag_counts": {},
            }
        s = self._model_stats[model]
        s["total"] += 1
        if entry["thumbs"] == "up":
            s["thumbs_up"] += 1
        elif entry["thumbs"] == "down":
            s["thumbs_down"] += 1
        if entry["rating"] is not None:
            s["rating_sum"] += entry["rating"]
            s["rating_count"] += 1
        for tag in entry.get("tags", []):
            s["tag_counts"][tag] = s["tag_counts"].get(tag, 0) + 1

    def history(self, last_n: int = 20, model: Optional[str] = None) -> List[Dict]:
        """Return newest-first feedback entries."""
        events = list(self._events)
        events.reverse()
        if model:
            events = [e for e in events if e["model"] == model]
        return events[:last_n]

    def model_summary(self, model: str) -> Optional[Dict[str, Any]]:
        """Per-model aggregate stats."""
        s = self._model_stats.get(model)
        if not s:
            return None
        avg_rating = round(s["rating_sum"] / s["rating_count"], 2) if s["rating_count"] > 0 else None
        approval = round(s["thumbs_up"] / max(s["thumbs_up"] + s["thumbs_down"], 1), 4)
        return {
            "model": model,
            "total_feedback": s["total"],
            "thumbs_up": s["thumbs_up"],
            "thumbs_down": s["thumbs_down"],
            "approval_rate": approval,
            "avg_rating": avg_rating,
            "top_tags": sorted(s["tag_counts"].items(), key=lambda x: x[1], reverse=True)[:10],
        }

    def all_summaries(self) -> Dict[str, Any]:
        """Summaries for every model that has feedback."""
        return {model: self.model_summary(model) for model in self._model_stats}

    def routing_adjustments(self) -> Dict[str, float]:
        """Per-model score adjustments derived from feedback.

        Positive = boost, negative = penalise. Scale: -10 to +10 points.
        """
        adjustments: Dict[str, float] = {}
        for model in self._model_stats:
            summary = self.model_summary(model)
            if not summary or summary["total_feedback"] < 3:
                continue
            adj = 0.0
            adj += (summary["approval_rate"] - 0.5) * 10.0
            if summary["avg_rating"] is not None:
                adj += (summary["avg_rating"] - 3.0) * 2.5
            adjustments[model] = round(adj, 2)
        return adjustments

    def stats(self) -> Dict[str, Any]:
        """Global feedback stats."""
        return {
            "total_feedback": self._total,
            "models_with_feedback": len(self._model_stats),
            "buffer_size": len(self._events),
            "buffer_capacity": self._events.maxlen,
        }

    def clear(self, model: Optional[str] = None) -> int:
        """Clear feedback. Returns count of cleared entries."""
        if model:
            before = len(self._events)
            self._events = type(self._events)(
                (e for e in self._events if e["model"] != model),
                maxlen=self._events.maxlen,
            )
            cleared = before - len(self._events)
            if model in self._model_stats:
                del self._model_stats[model]
            return cleared
        else:
            cleared = len(self._events)
            self._events.clear()
            self._model_stats.clear()
            self._total = 0
            return cleared
