"""
Core/sql_router.py — Statistical/Analytical Query Router for ZEN_RAG.

Phase 2.2: Detects queries that require data aggregation (count, sum, average, max/min)
and routes them through an LLM-powered SQL generation path rather than pure semantic search.

Architecture:
  1. SQLRouter.classify(query) → "sql" | "rag" | "hybrid"
  2. SQLRouter.generate_sql(query, schema) → SQL string
  3. SQLRouter.execute(sql, db_path) → results dict
  4. SQLRouter.format_answer(query, results) → natural language answer

The STAT path is especially valuable for:
  - Hospital/medical operational data (beds, patients, occupancy rates)
  - Financial data (totals, averages, trends by date/category)
  - Any Excel-imported tabular datasets

Usage:
    router = SQLRouter(llm=my_llm)
    kind = router.classify("How many free beds are in Pediatrics today?")
    if kind == "sql":
        sql = router.generate_sql(query, schema=router.get_schema(db_path))
        results = router.execute(sql, db_path)
        answer = router.format_answer(query, results)
    else:
        results = rag.hybrid_search(query, k=5)
"""

import logging
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Statistical query detection
# =============================================================================

_STAT_PATTERNS = [
    # Count / How many
    re.compile(r"\b(how\s+many|count|total\s+number|number\s+of)\b", re.I),
    # Aggregates
    re.compile(r"\b(sum|average|avg|mean|median|maximum|minimum|max|min)\b", re.I),
    # Percentage / ratio
    re.compile(r"\b(percent|percentage|ratio|rate|proportion)\b", re.I),
    # Time-series
    re.compile(
        r"\b(trend|over\s+time|by\s+month|by\s+year|by\s+day|daily|monthly|yearly)\b",
        re.I,
    ),
    # Comparison aggregates
    re.compile(r"\b(highest|lowest|most|least|top\s+\d|bottom\s+\d|rank)\b", re.I),
    # Group by
    re.compile(r"\b(by\s+(department|category|date|sheet|unit|ward|hospital))\b", re.I),
]

_RAG_PATTERNS = [
    # Qualitative questions → RAG
    re.compile(
        r"\b(what\s+is|explain|describe|why|how\s+does|definition|meaning|tell\s+me\s+about)\b",
        re.I,
    ),
    # Procedural
    re.compile(r"\b(how\s+to|steps?|process|guide|tutorial)\b", re.I),
]


def classify_query(query: str) -> str:
    """
    Classify query as 'sql', 'rag', or 'hybrid'.

    Returns:
        'sql'    — statistical/aggregation query → use SQL path
        'rag'    — qualitative/semantic query → use vector search
        'hybrid' — could benefit from both
    """
    stat_hits = sum(1 for p in _STAT_PATTERNS if p.search(query))
    rag_hits = sum(1 for p in _RAG_PATTERNS if p.search(query))

    if stat_hits >= 2:
        return "sql"
    if stat_hits == 1 and rag_hits == 0:
        return "sql"
    if stat_hits >= 1 and rag_hits >= 1:
        return "hybrid"
    return "rag"


# =============================================================================
# Schema introspection
# =============================================================================


def get_sqlite_schema(db_path: str) -> str:
    """Return CREATE TABLE statements from a SQLite database as a string."""
    try:
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL").fetchall()
            return "\n\n".join(f"-- Table: {name}\n{sql}" for name, sql in rows)
    except Exception as e:
        logger.warning(f"[SQLRouter] Schema introspection failed: {e}")
        return ""


# =============================================================================
# SQL Router
# =============================================================================

_SQL_GEN_PROMPT = """You are a SQL expert. Given the database schema and user question, write a valid SQLite SQL query.

Rules:
- Use ONLY tables and columns that exist in the schema
- Keep the query simple and readable
- For date comparisons, use SQLite date functions
- Return ONLY the SQL query, no explanation
- Do not use markdown code blocks

Schema:
{schema}

User question: "{question}"

SQL query:"""

_ANSWER_FORMAT_PROMPT = """Convert this SQL result to a clear, concise natural language answer.

Question: "{question}"
SQL result (as text): {result}

Answer in 1-3 sentences:"""


class SQLRouter:
    """
    Routes statistical queries through SQL generation and execution.

    For ZEN_RAG, the primary SQL target is the knowledge_graph.db SQLite database
    and any Excel data that has been imported into SQLite via the content_extractor.
    """

    def __init__(
        self,
        llm: Any = None,
        default_db_path: Optional[str] = None,
    ):
        """
        Args:
            llm: LLM adapter for SQL generation and answer formatting.
            default_db_path: Default SQLite database path.
        """
        self.llm = llm
        self.default_db_path = default_db_path

    def classify(self, query: str) -> str:
        """Classify query as 'sql', 'rag', or 'hybrid'."""
        return classify_query(query)

    def get_schema(self, db_path: str = None) -> str:
        """Get schema from the target SQLite database."""
        path = db_path or self.default_db_path
        if not path:
            return ""
        return get_sqlite_schema(str(path))

    def generate_sql(self, query: str, schema: str, db_path: str = None) -> Optional[str]:
        """
        Generate SQL for the given query using the LLM.

        Args:
            query: User natural language query.
            schema: Database schema (from get_schema()).
            db_path: Optional override for database path.

        Returns:
            SQL string or None if generation failed.
        """
        if not schema:
            logger.warning("[SQLRouter] No schema available for SQL generation.")
            return None

        if self.llm is None:
            logger.warning("[SQLRouter] No LLM configured. Cannot generate SQL.")
            return None

        prompt = _SQL_GEN_PROMPT.format(schema=schema, question=query)
        try:
            if hasattr(self.llm, "query_sync"):
                sql = self.llm.query_sync(prompt, max_tokens=300, temperature=0.0)
            elif hasattr(self.llm, "generate"):
                sql = self.llm.generate(prompt)
            else:
                return None

            # Clean up response
            sql = sql.strip()
            # Remove markdown code blocks if present
            sql = re.sub(r"```(?:sql)?\s*", "", sql)
            sql = re.sub(r"```\s*$", "", sql).strip()

            # Basic safety check: reject dangerous statements
            danger = re.compile(r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE)\b", re.I)
            if danger.search(sql):
                logger.warning(f"[SQLRouter] Generated SQL contains dangerous statement, rejecting: {sql[:100]}")
                return None

            logger.debug(f"[SQLRouter] Generated SQL: {sql[:200]}")
            return sql

        except Exception as e:
            logger.error(f"[SQLRouter] SQL generation failed: {e}")
            return None

    def execute(
        self,
        sql: str,
        db_path: str = None,
        max_rows: int = 100,
    ) -> Dict:
        """
        Execute SQL against the target SQLite database.

        Args:
            sql: SQL query to execute.
            db_path: Database path (uses default_db_path if None).
            max_rows: Maximum rows to return.

        Returns:
            Dict with 'columns', 'rows', 'row_count', 'error' keys.
        """
        path = db_path or self.default_db_path
        if not path:
            return {"error": "No database path configured.", "rows": [], "columns": []}

        if not Path(path).exists():
            return {"error": f"Database not found: {path}", "rows": [], "columns": []}

        try:
            with sqlite3.connect(path, timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(sql)
                columns = [d[0] for d in cursor.description] if cursor.description else []
                all_rows = cursor.fetchmany(max_rows)
                rows = [dict(row) for row in all_rows]
                return {
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "error": None,
                }
        except sqlite3.Error as e:
            logger.error(f"[SQLRouter] SQL execution error: {e} | SQL: {sql[:200]}")
            return {"error": str(e), "rows": [], "columns": []}

    def format_answer(self, query: str, sql_result: Dict) -> str:
        """
        Format SQL result as a natural language answer using the LLM.

        Falls back to a structured text representation if LLM is unavailable.
        """
        if sql_result.get("error"):
            return f"I couldn't retrieve the data: {sql_result['error']}"

        rows = sql_result.get("rows", [])
        columns = sql_result.get("columns", [])
        row_count = sql_result.get("row_count", 0)

        if not rows:
            return "The query returned no results."

        # Build result text for LLM
        result_text = f"{row_count} row(s) found.\n"
        result_text += " | ".join(columns) + "\n"
        result_text += "\n".join(" | ".join(str(row.get(c, "")) for c in columns) for row in rows[:10])
        if row_count > 10:
            result_text += f"\n... and {row_count - 10} more rows."

        if self.llm is not None:
            try:
                prompt = _ANSWER_FORMAT_PROMPT.format(
                    question=query,
                    result=result_text[:2000],
                )
                if hasattr(self.llm, "query_sync"):
                    return self.llm.query_sync(prompt, max_tokens=200, temperature=0.1).strip()
                elif hasattr(self.llm, "generate"):
                    return self.llm.generate(prompt).strip()
            except Exception as e:
                logger.warning(f"[SQLRouter] Answer formatting failed: {e}")

        # Fallback: return raw table
        return f"Found {row_count} result(s):\n\n" + result_text

    def route_and_answer(
        self,
        query: str,
        rag: Any = None,
        db_path: str = None,
        schema: str = None,
        k: int = 5,
    ) -> Dict:
        """
        Complete routing pipeline: classify → generate SQL or RAG → return answer.

        Args:
            query: User query.
            rag: LocalRAG instance for semantic search fallback.
            db_path: SQLite database path.
            schema: Pre-computed schema string (optional, avoids repeated introspection).
            k: Number of RAG results for hybrid/rag path.

        Returns:
            Dict with keys: 'answer', 'path' ('sql'|'rag'|'hybrid'), 'sql', 'results', 'chunks'
        """
        route = self.classify(query)
        logger.info(f"[SQLRouter] Query classified as: {route} | '{query[:60]}'")

        output = {
            "path": route,
            "answer": "",
            "sql": None,
            "sql_results": None,
            "chunks": [],
        }

        # SQL path
        if route in ("sql", "hybrid"):
            _schema = schema or self.get_schema(db_path)
            sql = self.generate_sql(query, _schema, db_path)
            if sql:
                output["sql"] = sql
                sql_results = self.execute(sql, db_path)
                output["sql_results"] = sql_results
                if not sql_results.get("error") and sql_results.get("rows"):
                    output["answer"] = self.format_answer(query, sql_results)
                    if route == "sql":
                        return output  # SQL path sufficient
                else:
                    logger.info("[SQLRouter] SQL path returned no results, falling back to RAG.")

        # RAG path (for 'rag', 'hybrid', or SQL fallback)
        if rag is not None:
            try:
                chunks = rag.hybrid_search(query, k=k)
                output["chunks"] = chunks
                if not output["answer"]:
                    output["answer"] = ""  # RAG caller will handle LLM generation
            except Exception as e:
                logger.error(f"[SQLRouter] RAG search failed: {e}")

        return output
