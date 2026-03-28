"""
Core/follow_up_generator.py — AI-powered follow-up question generator.

After every RAG answer, generates 3 contextual follow-up questions that
the user might naturally want to ask next. Makes the conversation feel
alive and guides users to explore the indexed data deeper.

Usage:
    gen = FollowUpGenerator(llm=my_llm)
    questions = gen.generate("How many beds are free?", answer_text, sources)
    # Returns: ["Which ward has most free beds?", "Trend vs yesterday?", ...]
"""

import logging
import re
from typing import Any, List

logger = logging.getLogger(__name__)

_PROMPT = """You are a helpful assistant. The user just asked a question and received an answer.
Generate exactly 3 short follow-up questions the user might want to ask next.

Rules:
- Each question must be directly related to the answer content
- Keep each question under 60 characters
- Make them diverse (don't repeat the same angle)
- Be specific to facts mentioned in the answer
- Output ONLY the 3 questions, one per line, no numbering or bullets

Original question: "{query}"

Answer summary: "{answer_snippet}"

3 follow-up questions:"""

# Template fallbacks when LLM is unavailable
_GENERIC_FOLLOW_UPS = [
    "Can you give more details?",
    "How does this compare to last week?",
    "What are the main factors affecting this?",
]


class FollowUpGenerator:
    """Generates contextual follow-up questions using LLM or templates."""

    def __init__(self, llm: Any = None, timeout: float = 10.0):
        self.llm = llm
        self.timeout = timeout

    def generate(
        self,
        query: str,
        answer: str,
        sources: List[dict] = None,
        n: int = 3,
    ) -> List[str]:
        """
        Generate follow-up questions based on query + answer.

        Args:
            query: The original user question.
            answer: The assistant's answer (HTML will be stripped).
            sources: Retrieved source chunks (for domain context).
            n: Number of follow-up questions to generate (default 3).

        Returns:
            List of follow-up question strings (may be fewer than n if generation fails).
        """
        clean_answer = _strip_html(answer)[:600]

        if self.llm is not None:
            try:
                return self._llm_generate(query, clean_answer, n)
            except Exception as e:
                logger.debug(f"[FollowUp] LLM generation failed: {e}, using templates.")

        return self._template_generate(query, sources or [], n)

    def _llm_generate(self, query: str, answer_snippet: str, n: int) -> List[str]:
        prompt = _PROMPT.format(query=query[:200], answer_snippet=answer_snippet[:400])

        if hasattr(self.llm, "query_sync"):
            resp = self.llm.query_sync(prompt, max_tokens=150, temperature=0.7)
        elif hasattr(self.llm, "generate"):
            resp = self.llm.generate(prompt)
        else:
            return _GENERIC_FOLLOW_UPS[:n]

        if not resp or not resp.strip():
            return _GENERIC_FOLLOW_UPS[:n]

        lines = [_clean_question(line) for line in resp.strip().split("\n") if line.strip() and len(line.strip()) > 5]
        # Filter out anything that looks like a header or meta-commentary
        filtered = [q for q in lines if q and not q.lower().startswith(("here", "follow", "question", "sure"))]
        return filtered[:n] if filtered else _GENERIC_FOLLOW_UPS[:n]

    def _template_generate(self, query: str, sources: List[dict], n: int) -> List[str]:
        """Fast template-based follow-ups extracted from source content."""
        follow_ups = []
        q_lower = query.lower()

        if any(w in q_lower for w in ("how many", "count", "total", "beds", "patients")):
            follow_ups += [
                "How does this compare to yesterday?",
                "Which department has the most capacity?",
                "Show me the weekly trend.",
            ]
        elif any(w in q_lower for w in ("what is", "explain", "describe", "define")):
            follow_ups += [
                "Can you give an example?",
                "What are the key benefits?",
                "How does this work in practice?",
            ]
        elif any(w in q_lower for w in ("how to", "steps", "process", "guide")):
            follow_ups += [
                "What are the requirements?",
                "How long does this take?",
                "What could go wrong?",
            ]
        elif any(w in q_lower for w in ("contact", "phone", "email", "address")):
            follow_ups += [
                "What are the opening hours?",
                "Is there an online alternative?",
                "Who is the contact person?",
            ]
        else:
            follow_ups = list(_GENERIC_FOLLOW_UPS)

        return follow_ups[:n]


# ── Helpers ──────────────────────────────────────────────────────────────────


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", " ", text).strip()


def _clean_question(line: str) -> str:
    """Strip numbering, bullets, quotes from a line."""
    line = line.strip()
    line = re.sub(r"^[\d]+[\.\)]\s*", "", line)
    line = re.sub(r"^[-*•]\s*", "", line)
    line = line.strip("\"'")
    # Ensure ends with ?
    if line and not line.endswith("?"):
        line += "?"
    return line.strip()
