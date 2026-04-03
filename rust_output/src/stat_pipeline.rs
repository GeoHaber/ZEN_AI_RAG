/// STAT pipeline — schema + examples from Qdrant → constraints → SQL generation → optional execute.
/// 
/// For queries like "What was the bed occupancy rate per section on 10.02.2026?"
/// Retrieves schema-like context from RAG, builds constraints, asks LLM for SQL, optionally runs it.
/// See docs/GOLDEN_INTERACTION_FLOW.md.

use anyhow::{Result, Context};
use regex::Regex;
use std::collections::HashMap;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static STAT_DATASOURCE_PATH: std::sync::LazyLock<String /* os::environ.get */> = std::sync::LazyLock::new(|| Default::default());

pub const STAT_CONTEXT_MAX_CHARS: i64 = 80000;

/// Extract date, metric, and group-by from the user query.
pub fn _extract_constraints(query: String) -> HashMap<String, Box<dyn std::any::Any>> {
    // Extract date, metric, and group-by from the user query.
    let mut constraints = HashMap::from([("date".to_string(), None), ("metric".to_string(), None), ("group_by".to_string(), None), ("raw".to_string(), query.trim().to_string())]);
    let mut q = query.trim().to_string().to_lowercase();
    let mut date_patterns = vec!["(?:în\\s+)?data\\s+de\\s+(\\d{1,2}[./]\\d{1,2}[./]\\d{2,4})".to_string(), "(\\d{1,2}[./]\\d{1,2}[./]\\d{2,4})".to_string(), "(\\d{4}-\\d{2}-\\d{2})".to_string()];
    for pat in date_patterns.iter() {
        let mut m = regex::Regex::new(&pat).unwrap().is_match(&q);
        if m {
            constraints["date".to_string()] = m.group(1).replace(&*".".to_string(), &*"-".to_string());
            break;
        }
    }
    if ((q.contains(&"rata".to_string()) && q.contains(&"ocupare".to_string())) || (q.contains(&"rate".to_string()) && q.contains(&"occupancy".to_string()))) {
        constraints["metric".to_string()] = "bed occupancy rate".to_string();
    } else if (q.contains(&"ocupare".to_string()) || q.contains(&"occupancy".to_string())) {
        constraints["metric".to_string()] = "bed occupancy".to_string();
    } else if (q.contains(&"număr".to_string()) || q.contains(&"numar".to_string()) || q.contains(&"count".to_string()) || q.contains(&"number".to_string())) {
        constraints["metric".to_string()] = "count".to_string();
    }
    if (q.contains(&"secție".to_string()) || q.contains(&"sectie".to_string()) || q.contains(&"secți".to_string()) || q.contains(&"section".to_string())) {
        constraints["group_by".to_string()] = "section".to_string();
    }
    constraints
}

/// Build a search query to retrieve the right table/sheet and schema from the knowledge base.
/// User query is put first so semantic search returns chunks from the table that matches the question
/// (e.g. occupancy by section, date); then schema/structure hints so table definitions are also considered.
pub fn _build_schema_query(user_query: String) -> String {
    // Build a search query to retrieve the right table/sheet and schema from the knowledge base.
    // User query is put first so semantic search returns chunks from the table that matches the question
    // (e.g. occupancy by section, date); then schema/structure hints so table definitions are also considered.
    let mut q = (user_query || "".to_string()).trim().to_string();
    if !q {
        "schema table section beds occupancy".to_string()
    }
    let mut out = q[..400];
    let mut hints = vec!["schema".to_string(), "structure".to_string(), "table".to_string(), "section".to_string(), "beds".to_string(), "occupancy".to_string()];
    let mut q_lower = q.to_lowercase();
    if (q_lower.contains(&"rate".to_string()) || q_lower.contains(&"occupancy".to_string()) || q_lower.contains(&"rata".to_string()) || q_lower.contains(&"ocupare".to_string())) {
        hints.extend(vec!["occupancy rate".to_string(), "indicator".to_string()]);
    }
    if (q_lower.contains(&"section".to_string()) || q_lower.contains(&"secție".to_string()) || q_lower.contains(&"sectie".to_string())) {
        hints.push("section department".to_string());
    }
    ((out + " ".to_string()) + hints.join(&" ".to_string()))
}

/// Run the STAT path: retrieve schema context → build constraints → generate SQL → optional execute.
/// 
/// Returns:
/// dict with: response (str), sources (list), applied_filters (dict), sql_generated (str or None),
/// error (str or None), from_stat (true).
pub async fn run_stat_pipeline(query: String, get_rag_integration: String, llm_config: HashMap<String, Box<dyn std::any::Any>>, get_llm_response: String) -> Result<HashMap<String, Box<dyn std::any::Any>>> {
    // Run the STAT path: retrieve schema context → build constraints → generate SQL → optional execute.
    // 
    // Returns:
    // dict with: response (str), sources (list), applied_filters (dict), sql_generated (str or None),
    // error (str or None), from_stat (true).
    let mut result = HashMap::from([("response".to_string(), "".to_string()), ("sources".to_string(), vec![]), ("applied_filters".to_string(), HashMap::new()), ("sql_generated".to_string(), None), ("error".to_string(), None), ("from_stat".to_string(), true)]);
    // try:
    {
        let mut rag = if callable(get_rag_integration) { get_rag_integration() } else { get_rag_integration };
        if (!rag || !/* getattr */ None) {
            result["error".to_string()] = "RAG not available for STAT path.".to_string();
            result["response".to_string()] = _stat_fallback_message(None, None);
            result
        }
        let mut schema_query = _build_schema_query(query);
        // try:
        {
            let mut top_k = 30;
            // try:
            {
                // TODO: from config_enhanced import Config
                let mut top_k = /* getattr */ 30;
            }
            // except Exception as exc:
            let mut schema_results = rag.search_context(schema_query, /* top_k= */ top_k).await;
        }
        // except Exception as e:
        let mut context_parts = vec![];
        let mut total_len = 0;
        for r in schema_results.iter() {
            let mut text = (r.get(&"text".to_string()).cloned() || r.get(&"content".to_string()).cloned() || "".to_string()).trim().to_string();
            if !text {
                continue;
            }
            let mut prefix = "".to_string();
            if r.get(&"sheet_name".to_string()).cloned().is_some() {
                let mut prefix = format!("[Sheet: {}] ", r.get(&"sheet_name".to_string()).cloned());
            }
            if r.get(&"date".to_string()).cloned().is_some() {
                prefix += format!("[Date: {}] ", r.get(&"date".to_string()).cloned());
            }
            if r.get(&"row_index".to_string()).cloned().is_some() {
                prefix += format!("[Row: {}] ", r.get(&"row_index".to_string()).cloned());
            }
            let mut block = (prefix + text).trim().to_string();
            if (((total_len + block.len()) + 2) > STAT_CONTEXT_MAX_CHARS && total_len > 0) {
                break;
            }
            context_parts.push(block);
            total_len += (block.len() + 2);
        }
        let mut context_text = context_parts.join(&"\n\n".to_string()).trim().to_string();
        result["sources".to_string()] = schema_results.iter().map(|r| HashMap::from([("text".to_string(), (r.get(&"text".to_string()).cloned() || r.get(&"content".to_string()).cloned() || "".to_string())[..2000]), ("source".to_string(), r.get(&"source".to_string()).cloned().unwrap_or("?".to_string())), ("sheet_name".to_string(), r.get(&"sheet_name".to_string()).cloned()), ("date".to_string(), r.get(&"date".to_string()).cloned())])).collect::<Vec<_>>();
        let mut constraints = _extract_constraints(query);
        result["applied_filters".to_string()] = constraints.iter().iter().filter(|(k, v)| (v && k != "raw".to_string())).map(|(k, v)| (k, v)).collect::<HashMap<_, _>>();
        let mut system = "You are an assistant that generates SQL or answers from schema and examples. Context contains table/sheet rows; each block may have [Sheet: name] [Date: ...] [Row: ...]. Identify the correct table/sheet from context and use only tables/columns from that context. Reply concis. If there is not enough context, say what is missing.".to_string();
        let mut user_block = format!("Question: {}\n\n", query);
        if context_text {
            user_block += format!("Context (schema/examples — use only the relevant tables/sheets from this context):\n{}\n\n", context_text);
        }
        user_block += format!("Extracted constraints: {}\n\n", constraints);
        user_block += "Generate SQL (SELECT ...) to answer the question, or answer directly from context if sufficient.".to_string();
        let mut messages = vec![HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), system)]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), user_block)])];
        // try:
        {
            let mut sql_or_answer = get_llm_response(messages, /* provider= */ llm_config.get(&"provider".to_string()).cloned(), /* model= */ llm_config.get(&"model".to_string()).cloned(), /* api_key= */ llm_config.get(&"api_key".to_string()).cloned(), /* temperature= */ 0.3_f64, /* max_tokens= */ 512).await;
        }
        // except Exception as e:
        let mut sql_candidate = (sql_or_answer || "".to_string()).trim().to_string();
        if regex::Regex::new(&"\\bSELECT\\b".to_string()).unwrap().is_match(&sql_candidate) {
            result["sql_generated".to_string()] = sql_candidate;
            if (STAT_DATASOURCE_PATH && os::path.exists(STAT_DATASOURCE_PATH)) {
                let mut exec_result = _execute_sql_if_sqlite(sql_candidate, STAT_DATASOURCE_PATH);
                if exec_result.get(&"error".to_string()).cloned() {
                    result["response".to_string()] = format!("SQL was generated but execution failed: {}\n\n**SQL:**\n```sql\n{}\n```\n\nApplied filters: {}", exec_result["error".to_string()], sql_candidate[..800], result["applied_filters".to_string()]);
                } else {
                    result["response".to_string()] = format!("**Result:**\n{}\n\n**Applied filters:** {}\n\n*(Details from database)*", exec_result.get(&"summary".to_string()).cloned().unwrap_or("".to_string()), result["applied_filters".to_string()]);
                }
            } else {
                result["response".to_string()] = format!("**STAT path:** SQL was generated from the knowledge-base schema. To execute and return numbers from the database, set the environment variable `STAT_DATASOURCE_PATH` to a SQLite (.db) file or data directory.\n\n**Generated SQL:**\n```sql\n{}\n```\n\n**Applied filters:** {}", sql_candidate[..1000], result["applied_filters".to_string()]);
            }
        } else {
            result["response".to_string()] = (sql_or_answer || _stat_fallback_message(context_text, constraints));
        }
    }
    // except Exception as e:
    Ok(result)
}

/// Execute SQL against a SQLite file. Returns {summary, error}.
pub fn _execute_sql_if_sqlite(sql: String, path: String) -> Result<HashMap<String, Box<dyn std::any::Any>>> {
    // Execute SQL against a SQLite file. Returns {summary, error}.
    if (!path.to_lowercase().ends_with(&*".db".to_string()) && !path.to_lowercase().ends_with(&*".sqlite".to_string())) {
        HashMap::from([("summary".to_string(), "".to_string()), ("error".to_string(), "STAT_DATASOURCE_PATH must point to a .db file for execution.".to_string())])
    }
    // try:
    {
        // TODO: import sqlite3
        let mut conn = /* sqlite3 */ path;
        conn.row_factory = sqlite3::Row;
        let mut cur = conn.execute(sql);
        let mut rows = cur.fetchall();
        conn.close();
        if !rows {
            HashMap::from([("summary".to_string(), "No rows match the criteria.".to_string()), ("error".to_string(), None)])
        }
        let mut cols = if rows { rows[0].keys().into_iter().collect::<Vec<_>>() } else { vec![] };
        let mut lines = vec![cols.join(&" | ".to_string())];
        for row in rows[..20].iter() {
            lines.push(cols.iter().map(|c| row[&c].to_string()).collect::<Vec<_>>().join(&" | ".to_string()));
        }
        if rows.len() > 20 {
            lines.push(format!("... and {} more rows.", (rows.len() - 20)));
        }
        HashMap::from([("summary".to_string(), lines.join(&"\n".to_string())), ("error".to_string(), None)])
    }
    // except Exception as e:
}

/// Message when STAT path cannot produce a full answer.
pub fn _stat_fallback_message(context: Option<String>, constraints: Option<HashMap>) -> String {
    // Message when STAT path cannot produce a full answer.
    let mut msg = "**STAT path** (schema + SQL) is active but could not generate a full answer. Ensure you have indexed documents with table schema and SQL examples (e.g. payload `doc_type`: schema, sql_template). For database results, set `STAT_DATASOURCE_PATH` to a .db file.".to_string();
    if constraints {
        msg += format!("\n\nFilters extracted from question: {}.", constraints);
    }
    msg
}
