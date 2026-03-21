"""
Core/query_router.py — Adaptive Query Router & Intent Classifier.

Industry best practice: Not all queries need the same retrieval strategy.
Route queries to the optimal pipeline based on intent classification:

  - SIMPLE: Direct lookup (single-hop, keyword-heavy)
  - ANALYTICAL: Multi-hop reasoning (comparison, why, impact analysis)
  - MULTI_HOP: Knowledge graph traversal (entity relationships)
  - TEMPORAL: Time-sensitive queries (recent events, dates)
  - AGGREGATE: Summary/overview queries across many documents

This prevents over-engineering simple lookups while ensuring complex
queries get the full pipeline (HyDE, FLARE, CRAG, reranking).

References:
  - LlamaIndex "RouterQueryEngine" pattern
  - Adaptive RAG (Jeong et al. 2024)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """Classified query intent for routing."""
    SIMPLE = "simple"
    ANALYTICAL = "analytical"
    MULTI_HOP = "multi_hop"
    TEMPORAL = "temporal"
    AGGREGATE = "aggregate"
    CONVERSATIONAL = "conversational"


@dataclass
class RoutingDecision:
    """Decision output from the query router."""

    intent: QueryIntent
    confidence: float
    recommended_pipeline: List[str] = field(default_factory=list)
    use_hyde: bool = False
    use_flare: bool = False
    use_crag: bool = False
    use_reranker: bool = True
    use_knowledge_graph: bool = False
    use_contextual_compression: bool = True
    top_k: int = 10
    temperature: float = 0.7
    reasoning: str = ""


# Patterns for intent classification
_SIMPLE_PATTERNS = [
    re.compile(r"^what\s+is\s+", re.I),
    re.compile(r"^define\s+", re.I),
    re.compile(r"^who\s+is\s+", re.I),
    re.compile(r"^when\s+(?:was|did|is)\s+", re.I),
    re.compile(r"^where\s+is\s+", re.I),
]

_ANALYTICAL_PATTERNS = [
    re.compile(r"\bwhy\s+(?:does|do|did|is|are|was|were)\b", re.I),
    re.compile(r"\bcompare\b", re.I),
    re.compile(r"\bdifference\s+between\b", re.I),
    re.compile(r"\bpros?\s+and\s+cons?\b", re.I),
    re.compile(r"\badvantage|disadvantage|tradeoff|trade-off\b", re.I),
    re.compile(r"\bimpact|effect|consequence|implication\b", re.I),
    re.compile(r"\banalyze|evaluate|assess|critique\b", re.I),
]

_MULTI_HOP_PATTERNS = [
    re.compile(r"\brelationship\s+between\b", re.I),
    re.compile(r"\brelationship\b.*\band\b", re.I),
    re.compile(r"\bhow\s+does\s+.+\s+(?:affect|influence|relate|connect)\b", re.I),
    re.compile(r"\bwhat\s+(?:led|leads)\s+to\b", re.I),
    re.compile(r"\bchain\s+of\b", re.I),
    re.compile(r"\bcause.+effect\b", re.I),
    re.compile(r"\b(?:connection|link)\s+between\b", re.I),
    re.compile(r"\bbetween\b.+\band\b", re.I),
]

_TEMPORAL_PATTERNS = [
    re.compile(r"\b(?:recent|latest|current|new|updated|today|yesterday|this\s+(?:week|month|year))\b", re.I),
    re.compile(r"\b\d{4}\b"),  # Year reference
    re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d", re.I),
    re.compile(r"\btimeline|chronolog|history\s+of\b", re.I),
    re.compile(r"\bbefore|after|since|until\b", re.I),
]

_AGGREGATE_PATTERNS = [
    re.compile(r"\bsummar(?:y|ize)\b", re.I),
    re.compile(r"\boverview\b", re.I),
    re.compile(r"\blist\s+(?:all|the|every)\b", re.I),
    re.compile(r"\bhow\s+many\b", re.I),
    re.compile(r"\ball\s+(?:the|of)\b", re.I),
    re.compile(r"\bmain\s+(?:points|ideas|topics|themes)\b", re.I),
    re.compile(r"\bkey\s+(?:takeaways|findings|points)\b", re.I),
]

_CONVERSATIONAL_PATTERNS = [
    re.compile(r"^(?:hi|hello|hey|thanks|thank|ok|okay|sure|yes|no)\b", re.I),
    re.compile(r"^(?:can you|could you|please)\b", re.I),
    re.compile(r"\bthat|this|it|those|these\b.*\b(?:you|mentioned|said|earlier)\b", re.I),
]


# Pipeline configurations per intent
_PIPELINE_CONFIG: Dict[QueryIntent, Dict[str, Any]] = {
    QueryIntent.SIMPLE: {
        "pipeline": ["retrieve", "rerank", "generate"],
        "use_hyde": False,
        "use_flare": False,
        "use_crag": False,
        "use_knowledge_graph": False,
        "top_k": 5,
        "temperature": 0.3,
    },
    QueryIntent.ANALYTICAL: {
        "pipeline": ["hyde", "retrieve", "rerank", "compress", "crag", "generate"],
        "use_hyde": True,
        "use_flare": True,
        "use_crag": True,
        "use_knowledge_graph": False,
        "top_k": 15,
        "temperature": 0.5,
    },
    QueryIntent.MULTI_HOP: {
        "pipeline": ["kg_lookup", "retrieve", "rerank", "flare", "generate"],
        "use_hyde": False,
        "use_flare": True,
        "use_crag": True,
        "use_knowledge_graph": True,
        "top_k": 15,
        "temperature": 0.5,
    },
    QueryIntent.TEMPORAL: {
        "pipeline": ["retrieve", "rerank", "filter_temporal", "generate"],
        "use_hyde": False,
        "use_flare": False,
        "use_crag": False,
        "use_knowledge_graph": False,
        "top_k": 10,
        "temperature": 0.3,
    },
    QueryIntent.AGGREGATE: {
        "pipeline": ["hyde", "retrieve", "rerank", "compress", "generate"],
        "use_hyde": True,
        "use_flare": False,
        "use_crag": True,
        "use_knowledge_graph": False,
        "top_k": 20,
        "temperature": 0.5,
    },
    QueryIntent.CONVERSATIONAL: {
        "pipeline": ["generate"],
        "use_hyde": False,
        "use_flare": False,
        "use_crag": False,
        "use_knowledge_graph": False,
        "top_k": 3,
        "temperature": 0.7,
    },
}


class QueryRouter:
    """Adaptive query router that classifies intent and recommends pipeline.

    Combines heuristic pattern matching with optional LLM-based
    classification for robust query routing.

    Usage:
        router = QueryRouter()
        decision = router.route("Compare Python and JavaScript for ML")
        # decision.intent == QueryIntent.ANALYTICAL
        # decision.use_hyde == True, decision.use_flare == True
    """

    def __init__(self, llm_fn: Optional[Callable] = None):
        """
        Args:
            llm_fn: Optional LLM function for enhanced classification
        """
        self.llm_fn = llm_fn

    def route(self, query: str, context: Optional[Dict[str, Any]] = None) -> RoutingDecision:
        """Classify query intent and return routing decision.

        Args:
            query: User query
            context: Optional context (e.g. conversation history)

        Returns:
            RoutingDecision with recommended pipeline configuration
        """
        if not query or not query.strip():
            return RoutingDecision(
                intent=QueryIntent.CONVERSATIONAL,
                confidence=1.0,
                reasoning="Empty query",
            )

        # Score each intent
        intent_scores = self._score_intents(query)

        # Optional LLM boost
        if self.llm_fn:
            llm_intent = self._llm_classify(query)
            if llm_intent:
                intent_scores[llm_intent] = intent_scores.get(llm_intent, 0) + 0.5

        # Handle conversation context (references to previous messages)
        if context and context.get("has_history"):
            intent_scores[QueryIntent.CONVERSATIONAL] += 0.2

        # Pick highest-scoring intent
        best_intent = max(intent_scores, key=intent_scores.get)
        best_score = intent_scores[best_intent]

        # Normalize confidence
        total = sum(intent_scores.values())
        confidence = best_score / total if total > 0 else 0.0

        # Build routing decision from pipeline config
        config = _PIPELINE_CONFIG.get(best_intent, _PIPELINE_CONFIG[QueryIntent.SIMPLE])

        return RoutingDecision(
            intent=best_intent,
            confidence=confidence,
            recommended_pipeline=config["pipeline"],
            use_hyde=config["use_hyde"],
            use_flare=config["use_flare"],
            use_crag=config["use_crag"],
            use_reranker=True,
            use_knowledge_graph=config["use_knowledge_graph"],
            use_contextual_compression=best_intent in (
                QueryIntent.ANALYTICAL, QueryIntent.AGGREGATE,
            ),
            top_k=config["top_k"],
            temperature=config["temperature"],
            reasoning=f"Matched intent '{best_intent.value}' with confidence {confidence:.2f}",
        )

    def _score_intents(self, query: str) -> Dict[QueryIntent, float]:
        """Score query against all intent patterns."""
        scores: Dict[QueryIntent, float] = {intent: 0.0 for intent in QueryIntent}

        pattern_map = {
            QueryIntent.SIMPLE: _SIMPLE_PATTERNS,
            QueryIntent.ANALYTICAL: _ANALYTICAL_PATTERNS,
            QueryIntent.MULTI_HOP: _MULTI_HOP_PATTERNS,
            QueryIntent.TEMPORAL: _TEMPORAL_PATTERNS,
            QueryIntent.AGGREGATE: _AGGREGATE_PATTERNS,
            QueryIntent.CONVERSATIONAL: _CONVERSATIONAL_PATTERNS,
        }

        for intent, patterns in pattern_map.items():
            for pattern in patterns:
                if pattern.search(query):
                    scores[intent] += 1.0

        # Complexity bonus: longer queries tend toward analytical/multi-hop
        word_count = len(query.split())
        if word_count > 15:
            scores[QueryIntent.ANALYTICAL] += 0.5
            scores[QueryIntent.MULTI_HOP] += 0.3
        elif word_count < 5:
            scores[QueryIntent.SIMPLE] += 0.5

        # Question mark bonus
        if "?" in query:
            scores[QueryIntent.SIMPLE] += 0.1

        # Baseline: every query has some SIMPLE score
        scores[QueryIntent.SIMPLE] = max(scores[QueryIntent.SIMPLE], 0.3)

        return scores

    def _llm_classify(self, query: str) -> Optional[QueryIntent]:
        """Use LLM for intent classification."""
        try:
            prompt = (
                "Classify this query into exactly one category:\n"
                "- simple: factual lookup, definition, who/what/where\n"
                "- analytical: comparison, why, impact analysis, evaluation\n"
                "- multi_hop: relationship chains, cause-effect, entity connections\n"
                "- temporal: time-sensitive, recent events, historical timeline\n"
                "- aggregate: summary, list all, overview, key points\n"
                "- conversational: greetings, follow-ups, acknowledgments\n\n"
                f"Query: {query}\n\n"
                "Category (one word only):"
            )
            response = self.llm_fn(prompt).strip().lower()

            intent_map = {
                "simple": QueryIntent.SIMPLE,
                "analytical": QueryIntent.ANALYTICAL,
                "multi_hop": QueryIntent.MULTI_HOP,
                "temporal": QueryIntent.TEMPORAL,
                "aggregate": QueryIntent.AGGREGATE,
                "conversational": QueryIntent.CONVERSATIONAL,
            }
            return intent_map.get(response)
        except Exception:
            return None

    @staticmethod
    def get_pipeline_for_intent(intent: QueryIntent) -> Dict[str, Any]:
        """Get the full pipeline configuration for a given intent."""
        return dict(_PIPELINE_CONFIG.get(intent, _PIPELINE_CONFIG[QueryIntent.SIMPLE]))
