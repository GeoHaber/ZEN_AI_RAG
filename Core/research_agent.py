"""
Research Agent — Autonomous Web Research with ReACT Loop
=========================================================
3-phase pipeline: Search → Browse → Synthesize (LLM-powered).
Supports ReACT-style iterative reasoning when llm_fn is provided.

Usage:
    from Core.research_agent import ResearchAgent, quick_research

    agent = ResearchAgent()
    result = agent.research("What is FLARE retrieval?", llm_fn=my_llm)
    print(result["answer"])
    print(result["sources"])
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Import our tools
from Core.tools.web_search import search_with_fallback  # noqa: E402

# Import content extractor for reading web pages
try:
    from content_extractor import scan_web

    _EXTRACTOR_AVAILABLE = True
except ImportError:
    _EXTRACTOR_AVAILABLE = False
    logger.warning("content_extractor not available — web browsing disabled")


# =============================================================================
# CONTENT EXTRACTOR HELPER
# =============================================================================


def extract_web_content(url: str, max_chars: int = 5000) -> Dict:
    """
    Extract content from a URL using content_extractor.

    Returns:
        Dict with keys: text, title, url
    """
    if not _EXTRACTOR_AVAILABLE:
        return {"text": "", "title": "", "url": url}

    try:
        result = scan_web(url)
        text = result.get("content", "")
        if len(text) > max_chars:
            text = text[:max_chars] + "…"
        return {
            "text": text,
            "title": result.get("title", url),
            "url": url,
        }
    except Exception as e:
        logger.error(f"Failed to extract content from {url}: {e}")
        return {"text": "", "title": "", "url": url}


# =============================================================================
# RESEARCH AGENT
# =============================================================================


class ResearchAgent:
    """
    Autonomous research agent with optional LLM synthesis.

    Workflow:
        1. Search Phase   — Find relevant URLs via search_with_fallback()
        2. Browse Phase   — Extract content from top URLs
        3. Synthesize     — LLM-powered answer (or snippet fallback)

    ReACT variant (research_react):
        Adds a Thought→Action→Observation loop for deeper research.
    """

    def __init__(
        self,
        llm_fn: Optional[Callable[[str], str]] = None,
        max_sources: int = 3,
        max_chars_per_source: int = 4000,
        search_provider: str = "duckduckgo",
    ):
        """
        Args:
            llm_fn:              Callable(prompt) -> str  (None = snippet fallback)
            max_sources:         How many URLs to browse
            max_chars_per_source: Max characters to keep per source
            search_provider:     Default provider for search_web()
        """
        self.llm_fn = llm_fn
        self.max_sources = max_sources
        self.max_chars_per_source = max_chars_per_source
        self.search_provider = search_provider

    # ── Phase 1: Search ───────────────────────────────────────────────────

    def _search_phase(self, query: str, max_results: int = 6) -> List[Dict]:
        """Find relevant URLs using fallback search."""
        logger.info(f"[Research] Searching: {query!r}")
        results = search_with_fallback(query, max_results=max_results)
        logger.info(f"[Research] Found {len(results)} results")
        return results

    # ── Phase 2: Browse ───────────────────────────────────────────────────

    def _browse_url(self, url: str) -> Dict:
        """Extract content from a single URL."""
        logger.info(f"[Research] Browsing: {url}")
        content = extract_web_content(url, max_chars=self.max_chars_per_source)
        return content

    def _browse_phase(self, search_results: List[Dict]) -> List[Dict]:
        """Browse top search results and return sources with content."""
        sources = []
        for result in search_results[: self.max_sources]:
            content = self._browse_url(result["url"])
            if content.get("text"):
                sources.append(
                    {
                        "url": result["url"],
                        "title": content.get("title") or result.get("title", result["url"]),
                        "text": content["text"],
                        "snippet": result.get("snippet", ""),
                    }
                )
        return sources

    # ── Phase 3: Synthesize ───────────────────────────────────────────────

    def _build_context(self, sources: List[Dict], max_total_chars: int = 8000) -> str:
        """Build a compact context string from sources."""
        parts = []
        chars_used = 0
        for i, src in enumerate(sources, 1):
            chunk = f"[Source {i}: {src['title']}]\n{src['text']}\n"
            if chars_used + len(chunk) > max_total_chars:
                # Truncate this source
                remaining = max_total_chars - chars_used
                if remaining > 200:
                    chunk = f"[Source {i}: {src['title']}]\n{src['text'][: remaining - 50]}…\n"
                    parts.append(chunk)
                break
            parts.append(chunk)
            chars_used += len(chunk)
        return "\n\n".join(parts)

    def _synthesize(
        self,
        query: str,
        sources: List[Dict],
        llm_fn: Optional[Callable[[str], str]] = None,
    ) -> str:
        """
        Generate an answer from collected sources.

        Uses LLM if available, otherwise returns structured snippet fallback.
        """
        if not sources:
            return "I couldn't find relevant information to answer your question."

        effective_llm = llm_fn or self.llm_fn

        # ── LLM synthesis ──
        if effective_llm:
            context = self._build_context(sources)
            prompt = (
                f"You are a research assistant. Answer the question using ONLY the sources below.\n\n"
                f"Question: {query}\n\n"
                f"Sources:\n{context}\n\n"
                f"Instructions:\n"
                f"- Answer directly and concisely (3-5 sentences)\n"
                f"- Cite sources as [Source 1], [Source 2], etc.\n"
                f"- If sources don't answer the question, say so\n"
                f"- Answer in the same language as the question\n\n"
                f"Answer:"
            )
            try:
                answer = effective_llm(prompt)
                if answer and len(answer.strip()) > 20:
                    return answer.strip()
            except Exception as e:
                logger.error(f"LLM synthesis failed: {e}")

        # ── Snippet fallback ──
        lines = [f"Based on {len(sources)} sources:\n"]
        for i, src in enumerate(sources, 1):
            snippet = src.get("snippet") or src["text"][:300]
            lines.append(f"**[{i}] {src['title']}**")
            lines.append(snippet.strip())
            lines.append(f"🔗 {src['url']}\n")
        return "\n".join(lines)

    # ── Full Research Pipeline ─────────────────────────────────────────────

    def research(
        self,
        query: str,
        max_sources: Optional[int] = None,
        llm_fn: Optional[Callable[[str], str]] = None,
    ) -> Dict:
        """
        Perform complete research cycle (synchronous).

        Args:
            query:       The research question
            max_sources: Override default max_sources
            llm_fn:      Override instance llm_fn

        Returns:
            Dict with:
                answer:      Synthesized answer string
                sources:     List of {url, title}
                raw_content: Full extracted content list
        """
        n = max_sources or self.max_sources

        # Phase 1: Search
        search_results = self._search_phase(query, max_results=n * 2)
        if not search_results:
            return {
                "answer": "I couldn't find any relevant information online.",
                "sources": [],
                "raw_content": [],
            }

        # Phase 2: Browse
        sources = self._browse_phase(search_results)

        # Phase 3: Synthesize
        answer = self._synthesize(query, sources, llm_fn=llm_fn)

        return {
            "answer": answer,
            "sources": [{"url": s["url"], "title": s["title"]} for s in sources],
            "raw_content": sources,
        }

    # ── ReACT Loop ────────────────────────────────────────────────────────

    def research_react(
        self,
        query: str,
        llm_fn: Optional[Callable[[str], str]] = None,
        max_iterations: int = 3,
    ) -> Dict:
        """
        ReACT-style research loop: Thought → Action → Observation × N → Answer.

        Each iteration refines the search query based on what was found.
        Requires an LLM; falls back to plain research() if none available.
        """
        effective_llm = llm_fn or self.llm_fn
        if not effective_llm:
            logger.info("ReACT: no LLM available, falling back to plain research")
            return self.research(query, llm_fn=llm_fn)

        all_sources: List[Dict] = []
        current_query = query
        observations: List[str] = []

        for iteration in range(1, max_iterations + 1):
            logger.info(f"[ReACT] Iteration {iteration}/{max_iterations}: {current_query!r}")

            # ── Thought: what should we search? ──
            if iteration > 1 and observations:
                thought_prompt = (
                    f"Original question: {query}\n\n"
                    f"Previous searches and findings:\n"
                    + "\n".join(f"- {obs}" for obs in observations)
                    + "\n\nWhat should I search next to better answer the original question?\n"
                    "Write ONLY the new search query (1 line, no explanation):"
                )
                try:
                    new_query = effective_llm(thought_prompt).strip()
                    new_query = re.sub(r'^["\']|["\']$', "", new_query)  # strip quotes
                    if new_query and len(new_query) > 5:
                        current_query = new_query
                        logger.info(f"[ReACT] Refined query: {current_query!r}")
                except Exception as e:
                    logger.error(f"[ReACT] Thought phase failed: {e}")

            # ── Action: search + browse ──
            search_results = self._search_phase(current_query, max_results=4)
            new_sources = self._browse_phase(search_results)

            # Deduplicate by URL
            known_urls = {s["url"] for s in all_sources}
            for src in new_sources:
                if src["url"] not in known_urls:
                    all_sources.append(src)
                    known_urls.add(src["url"])

            # ── Observation: summarize what was found ──
            obs = f"Searched '{current_query}': found {len(new_sources)} sources" + (
                f" — {', '.join(s['title'][:40] for s in new_sources[:2])}" if new_sources else ""
            )
            observations.append(obs)

            # Stop if we have enough information
            if len(all_sources) >= self.max_sources * 2:
                logger.info("[ReACT] Enough sources collected — stopping early")
                break

        # ── Final Answer ──
        answer = self._synthesize(query, all_sources[: self.max_sources * 2], llm_fn=effective_llm)

        return {
            "answer": answer,
            "sources": [{"url": s["url"], "title": s["title"]} for s in all_sources],
            "raw_content": all_sources,
            "react_trace": observations,
            "iterations_used": len(observations),
        }

    # ── Async Wrapper ─────────────────────────────────────────────────────

    async def research_async(
        self,
        query: str,
        max_sources: Optional[int] = None,
        llm_fn: Optional[Callable[[str], str]] = None,
        use_react: bool = False,
    ) -> Dict:
        """Async wrapper for Streamlit compatibility."""
        loop = asyncio.get_event_loop()
        if use_react:
            fn = lambda: self.research_react(query, llm_fn=llm_fn)  # noqa: E731
        else:
            fn = lambda: self.research(query, max_sources=max_sources, llm_fn=llm_fn)  # noqa: E731
        return await loop.run_in_executor(None, fn)


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================


def quick_research(
    query: str,
    max_sources: int = 3,
    llm_fn: Optional[Callable[[str], str]] = None,
    use_react: bool = False,
) -> str:
    """
    Quick research — returns just the answer string.

    Example:
        >>> answer = quick_research("What is FLARE retrieval?")
    """
    agent = ResearchAgent(llm_fn=llm_fn, max_sources=max_sources)
    if use_react and llm_fn:
        result = agent.research_react(query, llm_fn=llm_fn)
    else:
        result = agent.research(query, llm_fn=llm_fn)
    return result["answer"]
