"""
Core/knowledge_graph.py — SQLite-backed Knowledge Graph for RAG.

Features:
  - Entity extraction (LLM → regex fallback)
  - Relationship triple storage (subject, predicate, object)
  - Multi-hop graph traversal for complex queries
  - Source attribution (each triple linked to source chunk)

Ported from ZEN_RAG.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """SQLite-backed knowledge graph for entity/relationship storage.

    Thread-safe via per-thread connections.

    Usage:
        kg = KnowledgeGraph()
        kg.add_triples(triples, source_url="doc.pdf")
        entities = kg.query_entity("Albert Einstein")
        paths = kg.multi_hop("Einstein", "Nobel Prize", max_hops=3)
    """

    def __init__(self, db_path: str = "data/knowledge_graph.db"):
        self._db_path = db_path
        self._local = threading.local()
        self._init_lock = threading.Lock()
        self._ensure_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a thread-local SQLite connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            os.makedirs(os.path.dirname(self._db_path) or ".", exist_ok=True)
            self._local.conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _ensure_db(self):
        """Create tables if not present."""
        with self._init_lock:
            conn = self._get_conn()
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    entity_type TEXT DEFAULT 'unknown',
                    mention_count INTEGER DEFAULT 1,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS triples (
                    id TEXT PRIMARY KEY,
                    subject_id TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object_id TEXT NOT NULL,
                    source_url TEXT,
                    confidence REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (subject_id) REFERENCES entities(id),
                    FOREIGN KEY (object_id) REFERENCES entities(id)
                );

                CREATE INDEX IF NOT EXISTS idx_triples_subject ON triples(subject_id);
                CREATE INDEX IF NOT EXISTS idx_triples_object ON triples(object_id);
                CREATE INDEX IF NOT EXISTS idx_triples_predicate ON triples(predicate);
                CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
            """)
            conn.commit()

    @staticmethod
    def _entity_id(name: str) -> str:
        """Generate a stable entity ID from normalized name."""
        norm = name.strip().lower()
        return hashlib.md5(norm.encode()).hexdigest()[:12]

    # ─── Entity Management ─────────────────────────────────────────────────

    def add_entity(self, name: str, entity_type: str = "unknown") -> str:
        """Add or update an entity."""
        eid = self._entity_id(name)
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO entities (id, name, entity_type, mention_count)
               VALUES (?, ?, ?, 1)
               ON CONFLICT(id) DO UPDATE SET
                   mention_count = mention_count + 1,
                   entity_type = CASE
                       WHEN excluded.entity_type != 'unknown' THEN excluded.entity_type
                       ELSE entities.entity_type
                   END""",
            (eid, name.strip(), entity_type),
        )
        conn.commit()
        return eid

    def query_entity(self, name: str) -> List[Dict[str, Any]]:
        """Find all triples involving an entity (as subject or object)."""
        eid = self._entity_id(name)
        conn = self._get_conn()

        rows = conn.execute(
            """SELECT t.predicate, e2.name as object_name, t.source_url, t.confidence
               FROM triples t
               JOIN entities e2 ON t.object_id = e2.id
               WHERE t.subject_id = ?
               UNION ALL
               SELECT t.predicate, e1.name as subject_name, t.source_url, t.confidence
               FROM triples t
               JOIN entities e1 ON t.subject_id = e1.id
               WHERE t.object_id = ?""",
            (eid, eid),
        ).fetchall()

        return [dict(r) for r in rows]

    # ─── Triple Management ─────────────────────────────────────────────────

    def add_triples(
        self,
        triples: List[Tuple[str, str, str]],
        source_url: Optional[str] = None,
        confidence: float = 1.0,
    ):
        """Add relationship triples: [(subject, predicate, object), ...]"""
        conn = self._get_conn()
        for subj, pred, obj in triples:
            subj_id = self.add_entity(subj)
            obj_id = self.add_entity(obj)

            triple_key = f"{subj_id}:{pred.lower().strip()}:{obj_id}"
            tid = hashlib.md5(triple_key.encode()).hexdigest()[:12]

            conn.execute(
                """INSERT INTO triples (id, subject_id, predicate, object_id, source_url, confidence)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                       confidence = MAX(triples.confidence, excluded.confidence)""",
                (tid, subj_id, pred.strip(), obj_id, source_url, confidence),
            )
        conn.commit()

    # ─── Multi-Hop Traversal ───────────────────────────────────────────────

    def multi_hop(
        self,
        start_entity: str,
        end_entity: str,
        max_hops: int = 3,
    ) -> List[List[Dict]]:
        """Find paths between two entities via BFS."""
        start_id = self._entity_id(start_entity)
        end_id = self._entity_id(end_entity)
        conn = self._get_conn()

        # BFS
        queue: List[List[str]] = [[start_id]]
        visited: Set[str] = {start_id}
        paths: List[List[Dict]] = []

        while queue:
            path = queue.pop(0)
            current = path[-1]

            if len(path) - 1 > max_hops:
                continue

            if current == end_id and len(path) > 1:
                # Resolve path to readable format
                resolved = self._resolve_path(path)
                if resolved:
                    paths.append(resolved)
                continue

            # Expand neighbors
            rows = conn.execute(
                """SELECT t.object_id as neighbor, t.predicate, e.name
                   FROM triples t
                   JOIN entities e ON t.object_id = e.id
                   WHERE t.subject_id = ?
                   UNION
                   SELECT t.subject_id as neighbor, t.predicate, e.name
                   FROM triples t
                   JOIN entities e ON t.subject_id = e.id
                   WHERE t.object_id = ?""",
                (current, current),
            ).fetchall()

            for row in rows:
                neighbor = row["neighbor"]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])

        return paths[:5]  # Return top 5 paths

    def _resolve_path(self, entity_ids: List[str]) -> List[Dict]:
        """Convert a list of entity IDs to human-readable path."""
        conn = self._get_conn()
        path = []
        for i, eid in enumerate(entity_ids):
            row = conn.execute(
                "SELECT name, entity_type FROM entities WHERE id = ?", (eid,)
            ).fetchone()
            if row:
                node = {"name": row["name"], "type": row["entity_type"]}
                if i < len(entity_ids) - 1:
                    # Get the connecting predicate
                    edge = conn.execute(
                        """SELECT predicate FROM triples
                           WHERE (subject_id = ? AND object_id = ?)
                              OR (subject_id = ? AND object_id = ?)
                           LIMIT 1""",
                        (eid, entity_ids[i + 1], entity_ids[i + 1], eid),
                    ).fetchone()
                    if edge:
                        node["relation"] = edge["predicate"]
                path.append(node)
        return path

    # ─── Entity Extraction ─────────────────────────────────────────────────

    def extract_entities_regex(self, text: str) -> List[Tuple[str, str, str]]:
        """Extract entity triples from text using regex patterns.

        Returns list of (subject, predicate, object) tuples.
        """
        triples = []

        # Pattern: "X is a/the Y"
        for m in re.finditer(r"([A-Z][\w\s]{1,40}?)\s+is\s+(?:a|an|the)\s+([A-Z][\w\s]{1,40})", text):
            triples.append((m.group(1).strip(), "is_a", m.group(2).strip()))

        # Pattern: "X was founded by Y" / "X was created by Y"
        for m in re.finditer(r"([A-Z][\w\s]{1,40}?)\s+was\s+(?:founded|created|built|established)\s+by\s+([A-Z][\w\s]{1,40})", text):
            triples.append((m.group(1).strip(), "founded_by", m.group(2).strip()))

        # Pattern: "X is located in Y"
        for m in re.finditer(r"([A-Z][\w\s]{1,40}?)\s+is\s+(?:located|situated|based)\s+in\s+([A-Z][\w\s]{1,40})", text):
            triples.append((m.group(1).strip(), "located_in", m.group(2).strip()))

        # Pattern: "X works for/at Y"
        for m in re.finditer(r"([A-Z][\w\s]{1,40}?)\s+(?:works|worked)\s+(?:for|at)\s+([A-Z][\w\s]{1,40})", text):
            triples.append((m.group(1).strip(), "works_at", m.group(2).strip()))

        return triples

    # ─── Stats ─────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, int]:
        """Get graph statistics."""
        conn = self._get_conn()
        entities = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        triples = conn.execute("SELECT COUNT(*) FROM triples").fetchone()[0]
        return {"entities": entities, "triples": triples}

    def clear(self):
        """Clear entire knowledge graph."""
        conn = self._get_conn()
        conn.execute("DELETE FROM triples")
        conn.execute("DELETE FROM entities")
        conn.commit()
        logger.info("[KG] Knowledge graph cleared")
