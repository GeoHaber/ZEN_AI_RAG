import re
import logging
from typing import Dict, Any

logger = logging.getLogger("FastDispatcher")


class FastDispatcher:
    """
    optimize local small model dispatcher.
    Strategy:
    - Level 0: Zero-latency Regex (Greetings, simple queries)
    - Level 1: Intent Classification (needs RAG? needs Code?)
    - Level 2: Routing to appropriate handler
    """

    def __init__(self, backend, rag_system=None):
        self.backend = backend
        self.rag_system = rag_system
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile efficient regex patterns for Level 0."""
        self.fast_responses = {
            re.compile(
                r"^(hi|hello|hey|greetings)$", re.I
            ): "Hello! How can I help you today? \n\nI'm ready for coding, analysis, or just a chat.",
            re.compile(r"^(thanks|thank you|thx)$", re.I): "You're welcome! Let me know if you need anything else.",
            re.compile(r"^(who are you\??)$", re.I): "I am ZenAI, your local helpful assistant.",
            re.compile(r"^(date|time|what time is it\??)$", re.I): self._get_time_str,
        }

    def _get_time_str(self):
        from datetime import datetime

        return f"It is currently {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."

    async def dispatch(self, prompt: str, conversation_id: str = None) -> Dict[str, Any]:
        """
        Main entry point. Returns a dict explaining how to handle the prompt
        or providing a direct response.
        """
        # --- Level 0: Instant Check ---
        for pattern, response in self.fast_responses.items():
            if not pattern.search(prompt.strip()):
                continue
            if callable(response):
                return {"type": "direct", "content": response()}
            return {"type": "direct", "content": response}

        # --- Level 1: Intent Classification (Mock/Heuristic for now, can use small model later) ---
        # Heuristics for RAG: "who is", "what is", "search", "find", "?" (if it looks like a fact query)
        # Heuristics for Code: "code", "write function", "script", "python", "js"

        lower_p = prompt.lower()

        # 1. Code Detection
        if any(w in lower_p for w in ["code", "script", "function", "class", "def ", "import ", "python", "html"]):
            return {"type": "expert", "expert": "code", "prompt": prompt}

        # 2. RAG Detection (Simple Heuristic for speed)
        # In a real model-based classifier, we'd ask the 3B model.
        if self.rag_system and any(w in lower_p for w in ["search", "find", "read", "lookup", "who", "what"]):
            return {"type": "rag", "prompt": prompt}

        # Default: Standard Chat
        return {"type": "chat", "prompt": prompt}

    async def get_response_stream(self, prompt: str, ui_state=None):
        """
        Stream generator that internally routes based on dispatch logic.
        This replaces the direct backend call in the UI.
        """
        decision = await self.dispatch(prompt)
        logger.info(f"⚡ Dispatch Decision: {decision['type']}")

        if decision["type"] == "direct":
            # Simulate streaming for consistent UI effect
            yield decision["content"]
            return

        elif decision["type"] == "rag":
            # Pass through to external RAG handler (handled in UI logic currently)
            # OR we can inject a signal here.
            # For now, we return a special signal chunk or handled upstream.
            # To avoid refactoring the entire RAG logic in zena.py instantly,
            # we will assume the Caller handles 'rag' type logic if possible,
            # BUT since this must yield strings, we fall back to standard generation
            # if we can't easily hook RAG here without circular deps.
            # Ideally dispatcher returns the STRATEGY, and zena.py executes it.
            pass

        # Fallback to standard backend stream
        # (The actual RAG logic is currently embedded in zena.py's stream_response)
        # We will use this dispatcher primarily for Level 0 speedups
        # and future architecture.

        async for chunk in self.backend.send_message_async(decision["prompt"]):
            yield chunk
