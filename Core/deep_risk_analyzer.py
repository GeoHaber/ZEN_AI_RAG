import logging
from typing import List
import json

logger = logging.getLogger(__name__)


class DeepRiskAnalyzer:
    """
    LLM-based Risk Analyzer for RAG retrieval.
    inspects retrieved documents for semantic contradictions
    before generation.
    """

    def __init__(self, llm_service=None):
        """
        :param llm_service: Service to make LLM calls.
                            If None, attempts to get from global state or dependency injection.
        """
        self.llm_service = llm_service

    async def analyze_conflicts(
        self, query: str, retrieved_chunks: List[str], model: str = "gpt-3.5-turbo"
    ) -> List[str]:
        """
        Analyze chunks for contradictions regarding the query.
        Returns a list of warning strings.
        """
        if not retrieved_chunks or len(retrieved_chunks) < 2:
            return []

        # Construction of the analysis prompt
        context_text = ""
        for i, chunk in enumerate(retrieved_chunks):
            context_text += f"[Document {i + 1}]: {chunk}\n\n"

        system_prompt = (
            "You are an expert Fact-Checker. "
            "Your task is to identify if there are any FACTUAL CONTRADICTIONS between the provided documents "
            "regarding the user's query.\n"
            "If Document A says 'X is 5' and Document B says 'X is 10', that is a contradiction.\n"
            "If one document provides more detail than another, that is NOT a contradiction.\n"
            "Return the result as a JSON object with a key 'conflicts' which is a list of strings describing the contradictions.\n"
            "If no contradictions found, return {'conflicts': []}."
        )

        user_prompt = f"User Query: {query}\n\nRetrieved Documents:\n{context_text}"

        try:
            # We assume self.llm_service has a method similar to chat_completion or generate
            # adapting to the existing RAG pipeline's service structure
            if self.llm_service:
                response = await self.llm_service.chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    model=model,
                    temperature=0.0,
                    json_mode=True,
                )

                content = response.get("content", "{}")
                data = json.loads(content)
                return data.get("conflicts", [])
            else:
                logger.warning("DeepRiskAnalyzer: No LLM service provided, skipping analysis.")
                return []

        except Exception as e:
            logger.error(f"DeepRiskAnalyzer failed: {e}")
            return []
