"""
Core/follow_up_generator.py — Follow-Up Question Generator.

Generates contextual follow-up questions based on the current
answer and source chunks, using LLM or template fallback.

Ported from ZEN_RAG.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class FollowUpGenerator:
    """Generate follow-up questions from RAG answers.

    Usage:
        gen = FollowUpGenerator(llm_fn=my_generate)
        questions = gen.generate(answer, query, source_chunks)
    """

    # Template-based follow-up patterns
    TEMPLATES = {
        "definition": [
            "What are the main characteristics of {topic}?",
            "How does {topic} compare to similar concepts?",
            "What are real-world examples of {topic}?",
        ],
        "process": [
            "What are the prerequisites for {topic}?",
            "What are common problems when {topic}?",
            "Are there alternative approaches to {topic}?",
        ],
        "comparison": [
            "What are the advantages of each option?",
            "In what situations is one better than the other?",
            "What do experts recommend?",
        ],
        "general": [
            "Can you provide more details about {topic}?",
            "What are the implications of {topic}?",
            "How has {topic} evolved over time?",
        ],
    }

    def __init__(
        self,
        llm_fn: Optional[Callable] = None,
        max_questions: int = 3,
    ):
        self.llm_fn = llm_fn
        self.max_questions = max_questions

    def generate(
        self,
        answer: str,
        query: str,
        source_chunks: Optional[List[Dict]] = None,
    ) -> List[str]:
        """Generate follow-up questions."""
        if not answer or not query:
            return []

        # Try LLM generation first
        if self.llm_fn:
            try:
                questions = self._llm_generate(answer, query, source_chunks)
                if questions:
                    return questions[:self.max_questions]
            except Exception as e:
                logger.warning(f"[FollowUp] LLM generation failed: {e}")

        # Fallback to templates
        return self._template_generate(answer, query)[:self.max_questions]

    def _llm_generate(
        self,
        answer: str,
        query: str,
        source_chunks: Optional[List[Dict]] = None,
    ) -> List[str]:
        """Use LLM to generate follow-up questions."""
        context_hint = ""
        if source_chunks:
            topics = set()
            for c in source_chunks[:3]:
                for w in re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", c.get("text", "")):
                    topics.add(w)
            if topics:
                context_hint = f"\nKey topics in sources: {', '.join(list(topics)[:10])}"

        prompt = (
            f"Based on this Q&A, suggest {self.max_questions} natural follow-up questions "
            f"that a user might ask next.\n\n"
            f"Question: {query}\n"
            f"Answer: {answer[:500]}\n"
            f"{context_hint}\n\n"
            f"Follow-up questions (one per line, no numbering):"
        )

        response = self.llm_fn(prompt)
        if not response:
            return []

        lines = [l.strip().lstrip("0123456789.-) ") for l in response.strip().split("\n")]
        return [l for l in lines if l and len(l) > 10 and l.endswith("?")]

    def _template_generate(self, answer: str, query: str) -> List[str]:
        """Generate follow-up questions from templates."""
        topic = self._extract_topic(query)
        query_type = self._classify_query(query)

        templates = self.TEMPLATES.get(query_type, self.TEMPLATES["general"])
        questions = []
        for tpl in templates:
            try:
                q = tpl.format(topic=topic)
                questions.append(q)
            except (KeyError, IndexError):
                continue

        return questions

    @staticmethod
    def _extract_topic(query: str) -> str:
        """Extract main topic from query."""
        # Remove question words
        topic = re.sub(
            r"^(what|how|why|when|where|who|which|can|does|is|are)\s+(is|are|does|do|was|were|the|a|an)?\s*",
            "",
            query.lower(),
            flags=re.IGNORECASE,
        ).strip().rstrip("?.")
        return topic or query[:50]

    @staticmethod
    def _classify_query(query: str) -> str:
        """Classify query type for template selection."""
        q = query.lower()
        if re.search(r"\b(what\s+is|define|meaning)\b", q):
            return "definition"
        if re.search(r"\b(how\s+to|steps|process|method)\b", q):
            return "process"
        if re.search(r"\b(compare|vs|versus|difference|better)\b", q):
            return "comparison"
        return "general"
