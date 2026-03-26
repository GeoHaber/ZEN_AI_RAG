"""
Core/query_processor.py - Intelligent query processing and expansion

Features:
- Query expansion (generate alternative phrasings)
- Query rewriting (clarify ambiguous queries)
- Multi-query generation (ask same thing different ways)
- Intent detection (factual vs. opinion vs. comparison)
"""

import logging
from typing import List, Dict, Optional
import re

logger = logging.getLogger(__name__)


class QueryProcessor:
    """Intelligent query processing for better retrieval"""

    def __init__(self, llm_config: Optional[Dict] = None):
        """
        Initialize query processor

        Args:
            llm_config: LLM configuration for query expansion
        """
        self.llm_config = llm_config
        self.expansion_enabled = True
        self.rewriting_enabled = True

    def process_query(self, query: str, expand: bool = True) -> Dict[str, any]:
        """
        Process query with expansion and rewriting

        Args:
            query: Original user query
            expand: Whether to generate alternative queries

        Returns:
            Dict with original query, expanded queries, and metadata
        """
        result = {
            "original": query,
            "processed": query,
            "alternatives": [],
            "intent": None,
        }

        # Clean and normalize query
        processed = self._normalize_query(query)
        result["processed"] = processed

        # Detect intent
        result["intent"] = self._detect_intent(processed)

        # Rewrite if needed (short or ambiguous queries)
        if self.rewriting_enabled and self._needs_rewriting(processed):
            rewritten = self._rewrite_query(processed)
            if rewritten:
                result["processed"] = rewritten
                logger.info(f"Rewrote query: '{query}' -> '{rewritten}'")

        # Expand query if enabled
        if expand and self.expansion_enabled:
            alternatives = self._expand_query(result["processed"])
            result["alternatives"] = alternatives
            logger.info(f"Expanded query into {len(alternatives)} alternatives")

        return result

    def _normalize_query(self, query: str) -> str:
        """Clean and normalize query text"""
        # Remove extra whitespace
        query = re.sub(r"\s+", " ", query.strip())

        # Ensure query ends with question mark if it's a question
        if self._is_question(query) and not query.endswith("?"):
            query += "?"

        return query

    def _is_question(self, query: str) -> bool:
        """Check if query is a question"""
        question_words = [
            "what",
            "when",
            "where",
            "who",
            "why",
            "how",
            "which",
            "can",
            "could",
            "would",
            "should",
            "is",
            "are",
            "does",
            "do",
        ]
        first_word = query.lower().split()[0] if query.split() else ""
        return first_word in question_words or query.endswith("?")

    def _needs_rewriting(self, query: str) -> bool:
        """Check if query needs rewriting"""
        # Short queries (< 3 words) often need expansion
        if len(query.split()) < 3:
            return True

        # Very long queries might need simplification
        if len(query.split()) > 50:
            return True

        return False

    def _rewrite_query(self, query: str) -> Optional[str]:
        """Rewrite query for clarity"""
        if not self.llm_config:
            return None

        try:
            # For short queries, expand them
            if len(query.split()) < 3:
                pass
            else:
                # For long queries, simplify them
                pass

            # Call LLM (simplified - actual implementation would use the LLM service)
            # For now, return None to avoid breaking without LLM
            return None

        except Exception as e:
            logger.error(f"Query rewriting failed: {e}")
            return None

    def _expand_query(self, query: str) -> List[str]:
        """Generate alternative phrasings of the query"""
        if not self.llm_config:
            # Fallback: simple synonym-based expansion
            return self._simple_expansion(query)

        try:
            # Use LLM to generate alternatives
            # For now, use simple expansion
            return self._simple_expansion(query)

        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return []

    def _simple_expansion(self, query: str) -> List[str]:
        """Simple rule-based query expansion"""
        alternatives = []

        # Synonym replacements
        synonyms = {
            "what is": ["define", "explain", "describe"],
            "how to": ["steps to", "way to", "method to"],
            "why": ["reason for", "cause of", "explanation for"],
            "when": ["time of", "date of", "period of"],
            "where": ["location of", "place of", "position of"],
        }

        query_lower = query.lower()
        for phrase, replacements in synonyms.items():
            if phrase in query_lower:
                for replacement in replacements:
                    alt = query_lower.replace(phrase, replacement)
                    alternatives.append(alt.capitalize())

        # Limit to 3 alternatives
        return alternatives[:3]

    def _detect_intent(self, query: str) -> str:
        """Detect query intent"""
        query_lower = query.lower()

        # Factual questions
        if any(word in query_lower for word in ["what", "when", "where", "who", "define", "explain"]):
            return "factual"

        # How-to questions
        if "how" in query_lower or "steps" in query_lower:
            return "how-to"

        # Comparison questions
        if any(word in query_lower for word in ["compare", "difference", "vs", "versus", "better"]):
            return "comparison"

        # Opinion questions
        if any(word in query_lower for word in ["should", "recommend", "best", "opinion"]):
            return "opinion"

        # Why questions (causal)
        if "why" in query_lower or "reason" in query_lower:
            return "causal"

        return "general"

    def generate_multi_queries(self, query: str, num_queries: int = 3) -> List[str]:
        """
        Generate multiple related queries for comprehensive retrieval

        Args:
            query: Original query
            num_queries: Number of queries to generate

        Returns:
            List of related queries
        """
        queries = [query]

        # Generate queries based on intent
        intent = self._detect_intent(query)

        if intent == "factual":
            # Add context and detail queries
            queries.append(f"What is the background of {query.replace('what is', '').strip()}?")
            queries.append(f"What are examples of {query.replace('what is', '').strip()}?")

        elif intent == "how-to":
            # Add prerequisite and detail queries
            queries.append(f"What do I need before {query.replace('how to', '').strip()}?")
            queries.append(f"What are common mistakes when {query.replace('how to', '').strip()}?")

        elif intent == "comparison":
            # Add individual queries for each item
            parts = re.split(r"\s+vs\s+|\s+versus\s+", query, flags=re.IGNORECASE)
            if len(parts) == 2:
                queries.append(f"What is {parts[0].strip()}?")
                queries.append(f"What is {parts[1].strip()}?")

        # Limit to requested number
        return queries[:num_queries]


# Singleton instance
_query_processor = None


def get_query_processor(llm_config: Optional[Dict] = None) -> QueryProcessor:
    """Get or create query processor instance"""
    global _query_processor
    if _query_processor is None:
        _query_processor = QueryProcessor(llm_config)
    return _query_processor
