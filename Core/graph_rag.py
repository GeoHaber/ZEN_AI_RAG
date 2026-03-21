"""
Core/graph_rag.py — Graph RAG with Community Detection & Summarization.

Industry best practice: Beyond basic entity-triple storage, Graph RAG
builds community-level summaries enabling answers to global/thematic
queries that no single chunk can address.

Pipeline:
  1. Extract entities and relationships from chunks
  2. Build graph communities (connected components / Leiden)
  3. Generate summaries per community
  4. At query time: match communities → use summaries as context
  5. For local queries: traditional entity lookup + multi-hop

This is inspired by Microsoft's "GraphRAG" (2024) paper which showed
that community summaries dramatically improve answers to global
sensemaking questions ("What are the main themes in this dataset?").

References:
  - Edge et al. "From Local to Global: A Graph RAG Approach" (Microsoft, 2024)
  - Community detection via connected components (lightweight alternative to Leiden)
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Community:
    """A community of related entities from the knowledge graph."""

    community_id: str
    entities: List[str] = field(default_factory=list)
    relationships: List[Tuple[str, str, str]] = field(default_factory=list)
    summary: str = ""
    keywords: List[str] = field(default_factory=list)
    size: int = 0
    level: int = 0  # Hierarchy level (0 = leaf, higher = more abstract)


@dataclass
class GraphRAGResult:
    """Result from Graph RAG query."""

    answer: str = ""
    matched_communities: List[Community] = field(default_factory=list)
    entity_context: List[Dict[str, Any]] = field(default_factory=list)
    strategy: str = "local"  # "local" or "global"
    community_summaries_used: int = 0


class GraphRAG:
    """Graph-based RAG with community detection and hierarchical summarization.

    Extends the basic KnowledgeGraph with:
    - Automatic community detection (connected components)
    - LLM-generated community summaries
    - Global query answering via community map-reduce
    - Local query answering via entity + multi-hop traversal

    Usage:
        graph_rag = GraphRAG(knowledge_graph=kg, llm_fn=my_generate)
        graph_rag.build_communities()  # After indexing documents

        # Global query (themes, overview)
        result = graph_rag.query("What are the main themes?", strategy="global")

        # Local query (specific entity)
        result = graph_rag.query("How does X relate to Y?", strategy="local")
    """

    def __init__(
        self,
        knowledge_graph: Any = None,
        llm_fn: Optional[Callable] = None,
        min_community_size: int = 3,
        max_community_summary_len: int = 500,
    ):
        """
        Args:
            knowledge_graph: KnowledgeGraph instance for entity/triple data
            llm_fn: function(prompt) -> str for summarization
            min_community_size: minimum entities to form a community
            max_community_summary_len: max chars per community summary
        """
        self.kg = knowledge_graph
        self.llm_fn = llm_fn
        self.min_community_size = min_community_size
        self.max_summary_len = max_community_summary_len
        self.communities: List[Community] = []
        self._entity_to_community: Dict[str, str] = {}

    def build_communities(self) -> List[Community]:
        """Detect communities via connected components and generate summaries.

        Steps:
          1. Extract adjacency from knowledge graph
          2. Find connected components (lightweight community detection)
          3. Filter by min size
          4. Generate summaries per community
        """
        if not self.kg:
            logger.warning("[GraphRAG] No knowledge graph provided")
            return []

        # Step 1: Build adjacency list from KG
        adjacency, entity_names = self._build_adjacency()
        if not adjacency:
            logger.info("[GraphRAG] Empty graph, no communities to build")
            return []

        # Step 2: Find connected components
        components = self._connected_components(adjacency, entity_names)

        # Step 3: Filter and build Community objects
        self.communities = []
        self._entity_to_community = {}

        for i, (entities, relationships) in enumerate(components):
            if len(entities) < self.min_community_size:
                continue

            cid = hashlib.sha256(
                "|".join(sorted(entities)).encode()
            ).hexdigest()[:12]

            community = Community(
                community_id=cid,
                entities=sorted(entities),
                relationships=relationships,
                size=len(entities),
                keywords=self._extract_keywords(entities, relationships),
            )

            # Generate summary
            if self.llm_fn:
                community.summary = self._generate_community_summary(community)
            else:
                community.summary = self._heuristic_summary(community)

            self.communities.append(community)
            for entity in entities:
                self._entity_to_community[entity.lower()] = cid

        logger.info(
            f"[GraphRAG] Built {len(self.communities)} communities "
            f"from {sum(c.size for c in self.communities)} entities"
        )
        return self.communities

    def query(
        self,
        query: str,
        strategy: str = "auto",
        top_k_communities: int = 3,
    ) -> GraphRAGResult:
        """Answer a query using the knowledge graph and community summaries.

        Args:
            query: User query
            strategy: "local" (entity lookup), "global" (community summaries),
                      or "auto" (detect best strategy)
            top_k_communities: max communities for global queries
        """
        if strategy == "auto":
            strategy = self._detect_strategy(query)

        if strategy == "global":
            return self._global_query(query, top_k_communities)
        else:
            return self._local_query(query)

    def _global_query(self, query: str, top_k: int) -> GraphRAGResult:
        """Answer using community summaries (map-reduce pattern).

        1. Match query to relevant communities
        2. Collect community summaries
        3. Use summaries as context for generation
        """
        matched = self._match_communities(query, top_k)

        if not matched:
            return GraphRAGResult(strategy="global")

        # Build context from community summaries
        summaries = []
        for community in matched:
            if community.summary:
                summaries.append(
                    f"[Community: {', '.join(community.entities[:5])}]\n"
                    f"{community.summary}"
                )

        context = "\n\n".join(summaries)
        answer = ""

        if self.llm_fn and context:
            try:
                prompt = (
                    f"Using the following knowledge graph community summaries, "
                    f"answer the question comprehensively.\n\n"
                    f"Community Summaries:\n{context}\n\n"
                    f"Question: {query}\n\nAnswer:"
                )
                answer = self.llm_fn(prompt)
            except Exception as e:
                logger.warning(f"[GraphRAG] Global generation failed: {e}")

        return GraphRAGResult(
            answer=answer or "",
            matched_communities=matched,
            strategy="global",
            community_summaries_used=len(matched),
        )

    def _local_query(self, query: str) -> GraphRAGResult:
        """Answer using entity lookup and multi-hop traversal."""
        if not self.kg:
            return GraphRAGResult(strategy="local")

        # Extract entities from query
        entities = self._extract_query_entities(query)
        entity_context = []

        for entity in entities[:5]:
            try:
                triples = self.kg.query_entity(entity)
                if triples:
                    entity_context.append({
                        "entity": entity,
                        "facts": triples[:10],
                    })
            except Exception:
                continue

        # Try multi-hop between entity pairs
        if len(entities) >= 2:
            try:
                paths = self.kg.multi_hop(entities[0], entities[1], max_hops=3)
                if paths:
                    entity_context.append({
                        "entity": f"{entities[0]} → {entities[1]}",
                        "paths": paths[:3],
                    })
            except Exception:
                pass

        # Find matching communities for extra context
        matched_communities = []
        for entity in entities:
            cid = self._entity_to_community.get(entity.lower())
            if cid:
                community = next(
                    (c for c in self.communities if c.community_id == cid), None
                )
                if community and community not in matched_communities:
                    matched_communities.append(community)

        return GraphRAGResult(
            entity_context=entity_context,
            matched_communities=matched_communities[:3],
            strategy="local",
        )

    def _build_adjacency(self) -> Tuple[Dict[str, Set[str]], Dict[str, str]]:
        """Extract adjacency list from knowledge graph."""
        adjacency: Dict[str, Set[str]] = defaultdict(set)
        entity_names: Dict[str, str] = {}

        try:
            conn = self.kg._get_conn()

            # Get all entities
            rows = conn.execute("SELECT id, name FROM entities").fetchall()
            for r in rows:
                entity_names[r["id"]] = r["name"]

            # Get all triples
            rows = conn.execute(
                "SELECT subject_id, predicate, object_id FROM triples"
            ).fetchall()
            for r in rows:
                sid, oid = r["subject_id"], r["object_id"]
                adjacency[sid].add(oid)
                adjacency[oid].add(sid)

        except Exception as e:
            logger.warning(f"[GraphRAG] Failed to build adjacency: {e}")

        return adjacency, entity_names

    @staticmethod
    def _connected_components(
        adjacency: Dict[str, Set[str]],
        entity_names: Dict[str, str],
    ) -> List[Tuple[List[str], List[Tuple[str, str, str]]]]:
        """Find connected components in the graph."""
        visited: Set[str] = set()
        components = []

        for node in adjacency:
            if node in visited:
                continue

            # BFS for this component
            component_nodes: Set[str] = set()
            queue = [node]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                component_nodes.add(current)
                for neighbor in adjacency.get(current, set()):
                    if neighbor not in visited:
                        queue.append(neighbor)

            # Resolve to names
            names = [
                entity_names.get(n, n) for n in component_nodes
            ]

            # Collect relationships within this component
            relationships = []
            for n in component_nodes:
                for neighbor in adjacency.get(n, set()):
                    if neighbor in component_nodes:
                        subj = entity_names.get(n, n)
                        obj = entity_names.get(neighbor, neighbor)
                        relationships.append((subj, "related_to", obj))

            components.append((names, relationships))

        return components

    def _match_communities(self, query: str, top_k: int) -> List[Community]:
        """Match query to relevant communities via keyword overlap."""
        query_words = set(
            w.lower() for w in re.findall(r"\b\w{3,}\b", query)
        )

        scored = []
        for community in self.communities:
            community_words = set(
                w.lower() for w in community.keywords
            )
            # Also include entity names as words
            for entity in community.entities:
                community_words.update(
                    w.lower() for w in re.findall(r"\b\w{3,}\b", entity)
                )

            overlap = len(query_words & community_words)
            if overlap > 0:
                score = overlap / max(len(query_words), 1)
                scored.append((community, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [c for c, _ in scored[:top_k]]

    def _generate_community_summary(self, community: Community) -> str:
        """Use LLM to generate a community summary."""
        try:
            entities_str = ", ".join(community.entities[:15])
            rels_str = "\n".join(
                f"  - {s} → {p} → {o}"
                for s, p, o in community.relationships[:20]
            )
            prompt = (
                f"The following entities and relationships form a thematic community "
                f"in a knowledge graph. Write a concise summary (2-4 sentences) "
                f"describing the main theme and key facts.\n\n"
                f"Entities: {entities_str}\n"
                f"Relationships:\n{rels_str}\n\n"
                f"Summary:"
            )
            response = self.llm_fn(prompt)
            if response and len(response.strip()) > 20:
                return response.strip()[:self.max_summary_len]
        except Exception as e:
            logger.debug(f"[GraphRAG] Summary generation failed: {e}")

        return self._heuristic_summary(community)

    @staticmethod
    def _heuristic_summary(community: Community) -> str:
        """Generate a simple summary without LLM."""
        entities = ", ".join(community.entities[:8])
        n_rels = len(community.relationships)
        return (
            f"This community contains {community.size} entities including "
            f"{entities}. There are {n_rels} known relationships among them."
        )

    @staticmethod
    def _extract_keywords(
        entities: List[str],
        relationships: List[Tuple[str, str, str]],
    ) -> List[str]:
        """Extract keywords from community entities and relationships."""
        words = set()
        for entity in entities:
            words.update(
                w.lower() for w in re.findall(r"\b\w{3,}\b", entity)
            )
        for s, p, o in relationships:
            words.update(
                w.lower() for w in re.findall(r"\b\w{3,}\b", f"{s} {p} {o}")
            )
        return sorted(words)

    @staticmethod
    def _extract_query_entities(query: str) -> List[str]:
        """Extract potential entity names from query."""
        # Capitalized multi-word phrases
        entities = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", query)
        # Quoted strings
        entities += re.findall(r'"([^"]+)"', query)
        entities += re.findall(r"'([^']+)'", query)

        if not entities:
            # Fall back to significant words
            entities = [
                w for w in re.findall(r"\b\w{4,}\b", query)
                if w.lower() not in {
                    "what", "where", "when", "which", "about",
                    "does", "have", "that", "this", "with",
                    "from", "they", "been", "were", "their",
                    "between", "relationship", "connection",
                }
            ]

        return entities[:5]

    @staticmethod
    def _detect_strategy(query: str) -> str:
        """Detect whether a query is global or local."""
        global_markers = [
            "main themes", "overview", "summarize", "key topics",
            "what are the", "list all", "major findings",
            "general", "overall", "themes", "categories",
        ]
        q_lower = query.lower()
        for marker in global_markers:
            if marker in q_lower:
                return "global"
        return "local"
