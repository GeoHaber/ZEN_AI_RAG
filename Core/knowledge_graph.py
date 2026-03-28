"""
Core/knowledge_graph.py — LightRAG-style Knowledge Graph for ZEN_RAG.

Phase 3.1: Entity and relationship extraction + graph-based multi-hop retrieval.

Inspired by:
  - LightRAG (ICLR '25): dual-level retrieval — local (entity) + global (community)
  - HippoRAG: entity-centric KG with PPR traversal
  - EcphoryRAG: 94% token reduction via entity-centric indexing

Architecture:
  - Entity extraction via LLM (NER) or spaCy fallback
  - Relationship triples: (entity_a, relation, entity_b)
  - Storage: SQLite (zero-dependency, works offline)
  - Retrieval: entity match → related entity expansion → chunk recall

Usage:
    kg = KnowledgeGraph(db_path="rag_storage/knowledge_graph.db")
    kg.ingest_chunks(chunks, llm=my_llm)
    results = kg.query("What hospitals does Dr. Smith work at?")
"""

import hashlib
import json
import logging
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)

# =============================================================================
# Schema
# =============================================================================

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entities (
    id       TEXT PRIMARY KEY,
    name     TEXT NOT NULL,
    type     TEXT DEFAULT 'UNKNOWN',
    aliases  TEXT DEFAULT '[]',
    chunk_id TEXT
);

CREATE TABLE IF NOT EXISTS relations (
    id         TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    predicate  TEXT NOT NULL,
    object_id  TEXT NOT NULL,
    weight     REAL DEFAULT 1.0,
    chunk_id   TEXT,
    FOREIGN KEY(subject_id) REFERENCES entities(id),
    FOREIGN KEY(object_id)  REFERENCES entities(id)
);

CREATE TABLE IF NOT EXISTS chunk_entities (
    chunk_id  TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    PRIMARY KEY (chunk_id, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_entities_name   ON entities(name);
CREATE INDEX IF NOT EXISTS idx_relations_subj  ON relations(subject_id);
CREATE INDEX IF NOT EXISTS idx_relations_obj   ON relations(object_id);
CREATE INDEX IF NOT EXISTS idx_ce_chunk        ON chunk_entities(chunk_id);
CREATE INDEX IF NOT EXISTS idx_ce_entity       ON chunk_entities(entity_id);
"""

# =============================================================================
# Entity extraction helpers
# =============================================================================

_LLM_ENTITY_PROMPT = """Extract named entities and relationships from the text below.

Return ONLY a JSON object with this structure:
{{
  "entities": [
    {{"name": "EntityName", "type": "PERSON|ORG|PLACE|CONCEPT|PRODUCT|OTHER"}}
  ],
  "relations": [
    {{"subject": "EntityA", "predicate": "relation_verb", "object": "EntityB"}}
  ]
}}

Text:
{text}

JSON:"""


def _spacy_extract(text: str) -> Tuple[List[Dict], List[Dict]]:
    """Extract entities using spaCy (no LLM needed). Returns (entities, relations=[])."""
    try:
        import spacy

        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text[:5000])  # Limit to 5k chars for speed
        entities = [{"name": ent.text.strip(), "type": ent.label_} for ent in doc.ents if len(ent.text.strip()) > 1]
        return entities, []
    except Exception:
        return [], []


def _regex_extract(text: str) -> Tuple[List[Dict], List[Dict]]:
    """Minimal regex NER: capitalized noun phrases as UNKNOWN entities."""
    pattern = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b")
    entities = [{"name": m.group(1), "type": "UNKNOWN"} for m in pattern.finditer(text) if len(m.group(1)) > 2]
    # Deduplicate
    seen: Set[str] = set()
    unique = []
    for e in entities:
        if e["name"].lower() not in seen:
            seen.add(e["name"].lower())
            unique.append(e)
    return unique[:20], []  # Cap at 20 to avoid noise


def _entity_id(name: str) -> str:
    return hashlib.sha256(name.lower().strip().encode()).hexdigest()[:16]


# =============================================================================
# KnowledgeGraph
# =============================================================================


class KnowledgeGraph:
    """
    SQLite-backed knowledge graph with LLM/spaCy/regex entity extraction.

    The graph enables multi-hop retrieval:
      query → entity match → expand to related entities → recall chunks containing those entities
    """

    def __init__(self, db_path: str = "rag_storage/knowledge_graph.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(_SCHEMA_SQL)

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    # =========================================================================
    # Ingestion
    # =========================================================================

    def ingest_chunks(
        self,
        chunks: List[Dict],
        llm: Any = None,
        use_spacy: bool = True,
        batch_size: int = 20,
    ) -> Dict[str, int]:
        """
        Extract entities and relations from chunks and store in the graph.

        Args:
            chunks: List of chunk dicts with 'text' key.
            llm: Optional LLM adapter (for higher-quality extraction).
            use_spacy: Try spaCy before regex fallback.
            batch_size: Number of chunks to process per LLM call (batched for efficiency).

        Returns:
            Stats dict: {"entities_added": N, "relations_added": M, "chunks_processed": P}
        """
        stats = {"entities_added": 0, "relations_added": 0, "chunks_processed": 0}

        for chunk in chunks:
            text = chunk.get("text", "")
            chunk_id = hashlib.sha256(text.encode()).hexdigest()[:16]

            if not text.strip():
                continue

            # Extract
            entities, relations = self._extract(text, llm, use_spacy)
            if not entities:
                continue

            # Store
            with self._lock:
                with self._get_conn() as conn:
                    for ent in entities:
                        eid = _entity_id(ent["name"])
                        conn.execute(
                            "INSERT OR IGNORE INTO entities (id, name, type, chunk_id) VALUES (?,?,?,?)",
                            (eid, ent["name"], ent.get("type", "UNKNOWN"), chunk_id),
                        )
                        conn.execute(
                            "INSERT OR IGNORE INTO chunk_entities (chunk_id, entity_id) VALUES (?,?)",
                            (chunk_id, eid),
                        )
                        stats["entities_added"] += 1

                    for rel in relations:
                        sid = _entity_id(rel.get("subject", ""))
                        oid = _entity_id(rel.get("object", ""))
                        pred = rel.get("predicate", "related_to")
                        rid = hashlib.sha256(f"{sid}{pred}{oid}".encode()).hexdigest()[:16]
                        # Ensure entities exist
                        conn.execute(
                            "INSERT OR IGNORE INTO entities (id, name, type, chunk_id) VALUES (?,?,?,?)",
                            (sid, rel.get("subject", ""), "UNKNOWN", chunk_id),
                        )
                        conn.execute(
                            "INSERT OR IGNORE INTO entities (id, name, type, chunk_id) VALUES (?,?,?,?)",
                            (oid, rel.get("object", ""), "UNKNOWN", chunk_id),
                        )
                        conn.execute(
                            "INSERT OR IGNORE INTO relations (id, subject_id, predicate, object_id, chunk_id) VALUES (?,?,?,?,?)",
                            (rid, sid, pred, oid, chunk_id),
                        )
                        stats["relations_added"] += 1

            stats["chunks_processed"] += 1

        logger.info(
            f"[KG] Ingested {stats['chunks_processed']} chunks => "
            f"{stats['entities_added']} entities, {stats['relations_added']} relations"
        )
        return stats

    def _extract(self, text: str, llm: Any, use_spacy: bool) -> Tuple[List[Dict], List[Dict]]:
        """Extract entities and relations using best available method."""
        # 1. LLM (highest quality)
        if llm is not None:
            try:
                prompt = _LLM_ENTITY_PROMPT.format(text=text[:2000])
                if hasattr(llm, "query_sync"):
                    resp = llm.query_sync(prompt, max_tokens=400, temperature=0.1)
                elif hasattr(llm, "generate"):
                    resp = llm.generate(prompt)
                else:
                    resp = ""
                if resp:
                    # Extract JSON from response
                    match = re.search(r"\{.*\}", resp, re.DOTALL)
                    if match:
                        data = json.loads(match.group())
                        return data.get("entities", []), data.get("relations", [])
            except Exception as e:
                logger.debug(f"[KG] LLM extraction failed: {e}")

        # 2. spaCy
        if use_spacy:
            entities, relations = _spacy_extract(text)
            if entities:
                return entities, relations

        # 3. Regex fallback
        return _regex_extract(text)

    # =========================================================================
    # Query / Retrieval
    # =========================================================================

    def find_entities(self, query: str, top_n: int = 10) -> List[Dict]:
        """Find entities in the graph that match the query text."""
        tokens = [t.lower() for t in re.split(r"\W+", query) if len(t) > 2]
        if not tokens:
            return []

        with self._get_conn() as conn:
            results = []
            seen_ids: Set[str] = set()
            for token in tokens[:5]:  # Top-5 tokens
                rows = conn.execute(
                    "SELECT * FROM entities WHERE LOWER(name) LIKE ? LIMIT 20",
                    (f"%{token}%",),
                ).fetchall()
                for row in rows:
                    if row["id"] not in seen_ids:
                        seen_ids.add(row["id"])
                        results.append(dict(row))

        return results[:top_n]

    def expand_entities(self, entity_ids: List[str], hops: int = 2) -> Set[str]:
        """
        Graph traversal: expand entity set by following relations up to `hops` hops.
        Returns set of all entity IDs reachable within the hop limit.
        """
        if not entity_ids:
            return set()

        visited: Set[str] = set(entity_ids)
        frontier: Set[str] = set(entity_ids)

        with self._get_conn() as conn:
            for _ in range(hops):
                if not frontier:
                    break
                new_frontier: Set[str] = set()
                for eid in frontier:
                    rows = conn.execute(
                        "SELECT object_id FROM relations WHERE subject_id=? "
                        "UNION SELECT subject_id FROM relations WHERE object_id=?",
                        (eid, eid),
                    ).fetchall()
                    for row in rows:
                        nid = row[0]
                        if nid not in visited:
                            visited.add(nid)
                            new_frontier.add(nid)
                frontier = new_frontier

        return visited

    def get_chunk_ids_for_entities(self, entity_ids: Set[str]) -> List[str]:
        """Return chunk IDs that contain any of the given entities."""
        if not entity_ids:
            return []
        placeholders = ",".join("?" * len(entity_ids))
        with self._get_conn() as conn:
            rows = conn.execute(
                f"SELECT DISTINCT chunk_id FROM chunk_entities WHERE entity_id IN ({placeholders})",
                list(entity_ids),
            ).fetchall()
        return [row[0] for row in rows]

    def query(
        self,
        query_text: str,
        rag_chunks: List[Dict] = None,
        top_k: int = 5,
        hops: int = 2,
    ) -> List[Dict]:
        """
        Entity-aware retrieval:
          1. Find entities in query text
          2. Expand entity set via graph traversal (multi-hop)
          3. Recall chunks containing expanded entities
          4. Optionally merge with standard RAG chunks (passed via rag_chunks)

        Args:
            query_text: User query.
            rag_chunks: Standard RAG results (optional, for fusion).
            top_k: Number of results to return.
            hops: How many hops to traverse.

        Returns:
            List of chunk dicts with '_kg_score' key.
        """
        if not query_text.strip():
            return rag_chunks[:top_k] if rag_chunks else []

        # 1. Find seed entities
        matched_entities = self.find_entities(query_text, top_n=10)
        seed_ids = [e["id"] for e in matched_entities]

        if not seed_ids:
            logger.debug("[KG] No entities found for query, returning RAG results only.")
            return (rag_chunks or [])[:top_k]

        # 2. Expand via graph
        expanded_ids = self.expand_entities(seed_ids, hops=hops)

        # 3. Get chunk IDs
        kg_chunk_ids = set(self.get_chunk_ids_for_entities(expanded_ids))

        if not kg_chunk_ids:
            return (rag_chunks or [])[:top_k]

        # 4. Score RAG chunks by KG membership
        if rag_chunks:
            for chunk in rag_chunks:
                text = chunk.get("text", "")
                chunk_id = hashlib.sha256(text.encode()).hexdigest()[:16]
                chunk["_kg_score"] = 1.0 if chunk_id in kg_chunk_ids else 0.0

            # Re-rank: prefer chunks that appear in KG expansion
            rag_chunks.sort(
                key=lambda c: (
                    c.get("_kg_score", 0.0),
                    c.get("rerank_score", c.get("score", 0.0)),
                ),
                reverse=True,
            )
            return rag_chunks[:top_k]

        logger.debug(f"[KG] Found {len(kg_chunk_ids)} chunks via entity expansion.")
        return []

    def get_stats(self) -> Dict[str, int]:
        """Return entity/relation counts."""
        with self._get_conn() as conn:
            entities = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            relations = conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0]
            chunks = conn.execute("SELECT COUNT(DISTINCT chunk_id) FROM chunk_entities").fetchone()[0]
        return {"entities": entities, "relations": relations, "indexed_chunks": chunks}
