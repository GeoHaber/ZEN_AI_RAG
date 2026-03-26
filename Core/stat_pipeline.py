"""
STAT pipeline — schema + examples from Qdrant → constraints → SQL generation → optional execute.

For queries like "What was the bed occupancy rate per section on 10.02.2026?"
Retrieves schema-like context from RAG, builds constraints, asks LLM for SQL, optionally runs it.
See docs/GOLDEN_INTERACTION_FLOW.md.
"""

import logging
import os
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Optional: path to SQLite .db or directory with data for execution (env or config)
STAT_DATASOURCE_PATH = os.environ.get("STAT_DATASOURCE_PATH", "")


def _extract_constraints(query: str) -> Dict[str, Any]:
    """Extract date, metric, and group-by from the user query."""
    constraints = {"date": None, "metric": None, "group_by": None, "raw": query.strip()}
    q = query.strip().lower()
    # Date: "în data de 10.02.2026", "data de 10.02.2026", "10.02.2026", "2026-02-10"
    date_patterns = [
        r"(?:în\s+)?data\s+de\s+(\d{1,2}[./]\d{1,2}[./]\d{2,4})",
        r"(\d{1,2}[./]\d{1,2}[./]\d{2,4})",
        r"(\d{4}-\d{2}-\d{2})",
    ]
    for pat in date_patterns:
        m = re.search(pat, q, re.IGNORECASE)
        if m:
            constraints["date"] = m.group(1).replace(".", "-")
            break
    # Metric: occupancy rate, count, etc.
    if ("rata" in q and "ocupare" in q) or ("rate" in q and "occupancy" in q):
        constraints["metric"] = "bed occupancy rate"
    elif "ocupare" in q or "occupancy" in q:
        constraints["metric"] = "bed occupancy"
    elif "număr" in q or "numar" in q or "count" in q or "number" in q:
        constraints["metric"] = "count"
    # Group by: per section
    if "secție" in q or "sectie" in q or "secți" in q or "section" in q:
        constraints["group_by"] = "section"
    return constraints


# Max context chars for STAT so we don't truncate and miss the right table (align with rag_integration)
STAT_CONTEXT_MAX_CHARS = 80_000


def _build_schema_query(user_query: str) -> str:
    """Build a search query to retrieve the right table/sheet and schema from the knowledge base.
    User query is put first so semantic search returns chunks from the table that matches the question
    (e.g. occupancy by section, date); then schema/structure hints so table definitions are also considered."""
    q = (user_query or "").strip()
    if not q:
        return "schema table section beds occupancy"
    # User question first — drives retrieval to the right table/sheet
    out = q[:400]
    # Then schema/table hints so we also get structure if present
    hints = ["schema", "structure", "table", "section", "beds", "occupancy"]
    q_lower = q.lower()
    if "rate" in q_lower or "occupancy" in q_lower or "rata" in q_lower or "ocupare" in q_lower:
        hints.extend(["occupancy rate", "indicator"])
    if "section" in q_lower or "secție" in q_lower or "sectie" in q_lower:
        hints.append("section department")
    return out + " " + " ".join(hints)


async def run_stat_pipeline(
    query: str,
    get_rag_integration,
    llm_config: Dict[str, Any],
    get_llm_response,  # async (messages, provider, model, **kw) -> str
) -> Dict[str, Any]:
    """
    Run the STAT path: retrieve schema context → build constraints → generate SQL → optional execute.

    Returns:
        dict with: response (str), sources (list), applied_filters (dict), sql_generated (str or None),
        error (str or None), from_stat (True).
    """
    result = {
        "response": "",
        "sources": [],
        "applied_filters": {},
        "sql_generated": None,
        "error": None,
        "from_stat": True,
    }
    try:
        rag = get_rag_integration() if callable(get_rag_integration) else get_rag_integration
        if not rag or not getattr(rag, "search_context", None):
            result["error"] = "RAG not available for STAT path."
            result["response"] = _stat_fallback_message(None, None)
            return result

        # 1. Retrieve context from Qdrant (user query first so we get the right table/sheet)
        schema_query = _build_schema_query(query)
        try:
            top_k = 30
            try:
                from config_enhanced import Config

                top_k = getattr(Config, "TOP_K_RESULTS", 30)
            except Exception as exc:
                logger.debug("%s", exc)
            schema_results = await rag.search_context(schema_query, top_k=top_k)
        except Exception as e:
            logger.warning("STAT: search_context failed: %s", e)
            schema_results = []
        # No per-result or total truncation — include full context so the right table is present
        context_parts = []
        total_len = 0
        for r in schema_results:
            text = (r.get("text") or r.get("content") or "").strip()
            if not text:
                continue
            # Include sheet/row metadata so LLM can pick the right table
            prefix = ""
            if r.get("sheet_name") is not None:
                prefix = f"[Sheet: {r.get('sheet_name')}] "
            if r.get("date") is not None:
                prefix += f"[Date: {r.get('date')}] "
            if r.get("row_index") is not None:
                prefix += f"[Row: {r.get('row_index')}] "
            block = (prefix + text).strip()
            if total_len + len(block) + 2 > STAT_CONTEXT_MAX_CHARS and total_len > 0:
                break
            context_parts.append(block)
            total_len += len(block) + 2
        context_text = "\n\n".join(context_parts).strip()
        result["sources"] = [
            {
                "text": (r.get("text") or r.get("content") or "")[:2000],
                "source": r.get("source", "?"),
                "sheet_name": r.get("sheet_name"),
                "date": r.get("date"),
            }
            for r in schema_results
        ]

        # 2. Build constraints from user query
        constraints = _extract_constraints(query)
        result["applied_filters"] = {k: v for k, v in constraints.items() if v and k != "raw"}

        # 3. Prompt LLM for SQL or direct answer
        system = (
            "You are an assistant that generates SQL or answers from schema and examples. "
            "Context contains table/sheet rows; each block may have [Sheet: name] [Date: ...] [Row: ...]. "
            "Identify the correct table/sheet from context and use only tables/columns from that context. "
            "Reply concis. If there is not enough context, say what is missing."
        )
        user_block = f"Question: {query}\n\n"
        if context_text:
            user_block += f"Context (schema/examples — use only the relevant tables/sheets from this context):\n{context_text}\n\n"
        user_block += f"Extracted constraints: {constraints}\n\n"
        user_block += "Generate SQL (SELECT ...) to answer the question, or answer directly from context if sufficient."
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_block},
        ]
        try:
            sql_or_answer = await get_llm_response(
                messages,
                provider=llm_config.get("provider"),
                model=llm_config.get("model"),
                api_key=llm_config.get("api_key"),
                temperature=0.3,
                max_tokens=512,
            )
        except Exception as e:
            logger.warning("STAT: LLM call failed: %s", e)
            result["error"] = str(e)
            result["response"] = _stat_fallback_message(None, constraints)
            return result

        # 4. Detect if output looks like SQL
        sql_candidate = (sql_or_answer or "").strip()
        if re.search(r"\bSELECT\b", sql_candidate, re.IGNORECASE):
            result["sql_generated"] = sql_candidate
            # 5. Execute if data source configured
            if STAT_DATASOURCE_PATH and os.path.exists(STAT_DATASOURCE_PATH):
                exec_result = _execute_sql_if_sqlite(sql_candidate, STAT_DATASOURCE_PATH)
                if exec_result.get("error"):
                    result["response"] = (
                        f"SQL was generated but execution failed: {exec_result['error']}\n\n"
                        f"**SQL:**\n```sql\n{sql_candidate[:800]}\n```\n\n"
                        f"Applied filters: {result['applied_filters']}"
                    )
                else:
                    result["response"] = (
                        f"**Result:**\n{exec_result.get('summary', '')}\n\n"
                        f"**Applied filters:** {result['applied_filters']}\n\n"
                        f"*(Details from database)*"
                    )
            else:
                result["response"] = (
                    "**STAT path:** SQL was generated from the knowledge-base schema. "
                    "To execute and return numbers from the database, set the environment variable "
                    "`STAT_DATASOURCE_PATH` to a SQLite (.db) file or data directory.\n\n"
                    f"**Generated SQL:**\n```sql\n{sql_candidate[:1000]}\n```\n\n"
                    f"**Applied filters:** {result['applied_filters']}"
                )
        else:
            result["response"] = sql_or_answer or _stat_fallback_message(context_text, constraints)
    except Exception as e:
        logger.exception("STAT pipeline error: %s", e)
        result["error"] = str(e)
        result["response"] = _stat_fallback_message(None, None)
    return result


def _execute_sql_if_sqlite(sql: str, path: str) -> Dict[str, Any]:
    """Execute SQL against a SQLite file. Returns {summary, error}."""
    if not path.lower().endswith(".db") and not path.lower().endswith(".sqlite"):
        return {
            "summary": "",
            "error": "STAT_DATASOURCE_PATH must point to a .db file for execution.",
        }
    try:
        import sqlite3

        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(sql)
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return {"summary": "No rows match the criteria.", "error": None}
        # Build a short summary (e.g. table or first rows)
        cols = list(rows[0].keys()) if rows else []
        lines = [" | ".join(cols)]
        for row in rows[:20]:
            lines.append(" | ".join(str(row[c]) for c in cols))
        if len(rows) > 20:
            lines.append(f"... and {len(rows) - 20} more rows.")
        return {"summary": "\n".join(lines), "error": None}
    except Exception as e:
        return {"summary": "", "error": str(e)}


def _stat_fallback_message(context: Optional[str], constraints: Optional[Dict]) -> str:
    """Message when STAT path cannot produce a full answer."""
    msg = (
        "**STAT path** (schema + SQL) is active but could not generate a full answer. "
        "Ensure you have indexed documents with table schema and SQL examples (e.g. payload `doc_type`: schema, sql_template). "
        "For database results, set `STAT_DATASOURCE_PATH` to a .db file."
    )
    if constraints:
        msg += f"\n\nFilters extracted from question: {constraints}."
    return msg
