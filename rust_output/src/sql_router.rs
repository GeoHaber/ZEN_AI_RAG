/// Core/sql_router::py — Statistical/Analytical Query Router for ZEN_RAG.
/// 
/// Phase 2.2: Detects queries that require data aggregation (count, sum, average, max/min)
/// and routes them through an LLM-powered SQL generation path rather than pure semantic search.
/// 
/// Architecture:
/// 1. SQLRouter.classify(query) → "sql" | "rag" | "hybrid"
/// 2. SQLRouter.generate_sql(query, schema) → SQL string
/// 3. SQLRouter.execute(sql, db_path) → results dict
/// 4. SQLRouter.format_answer(query, results) → natural language answer
/// 
/// The STAT path is especially valuable for:
/// - Hospital/medical operational data (beds, patients, occupancy rates)
/// - Financial data (totals, averages, trends by date/category)
/// - Any Excel-imported tabular datasets
/// 
/// Usage:
/// router = SQLRouter(llm=my_llm)
/// kind = router.classify("How many free beds are in Pediatrics today?")
/// if kind == "sql":
/// sql = router.generate_sql(query, schema=router.get_schema(db_path))
/// results = router.execute(sql, db_path)
/// answer = router.format_answer(query, results)
/// else:
/// results = rag.hybrid_search(query, k=5)

use anyhow::{Result, Context};
use regex::Regex;
use std::collections::HashMap;
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static _STAT_PATTERNS: std::sync::LazyLock<Vec<re::compile>> = std::sync::LazyLock::new(|| Vec::new());

pub static _RAG_PATTERNS: std::sync::LazyLock<Vec<re::compile>> = std::sync::LazyLock::new(|| Vec::new());

pub const _SQL_GEN_PROMPT: &str = "You are a SQL expert. Given the database schema and user question, write a valid SQLite SQL query.\\n\\nRules:\\n- Use ONLY tables and columns that exist in the schema\\n- Keep the query simple and readable\\n- For date comparisons, use SQLite date functions\\n- Return ONLY the SQL query, no explanation\\n- Do not use markdown code blocks\\n\\nSchema:\\n{schema}\\n\\nUser question: \"{question}\"\\n\\nSQL query:";

pub const _ANSWER_FORMAT_PROMPT: &str = "Convert this SQL result to a clear, concise natural language answer.\\n\\nQuestion: \"{question}\"\\nSQL result (as text): {result}\\n\\nAnswer in 1-3 sentences:";

/// Routes statistical queries through SQL generation and execution.
/// 
/// For ZEN_RAG, the primary SQL target is the knowledge_graph::db SQLite database
/// and any Excel data that has been imported into SQLite via the content_extractor.
#[derive(Debug, Clone)]
pub struct SQLRouter {
    pub llm: String,
    pub default_db_path: String,
}

impl SQLRouter {
    /// Args:
    /// llm: LLM adapter for SQL generation and answer formatting.
    /// default_db_path: Default SQLite database path.
    pub fn new(llm: Box<dyn std::any::Any>, default_db_path: Option<String>) -> Self {
        Self {
            llm,
            default_db_path,
        }
    }
    /// Classify query as 'sql', 'rag', or 'hybrid'.
    pub fn classify(&self, query: String) -> String {
        // Classify query as 'sql', 'rag', or 'hybrid'.
        classify_query(query)
    }
    /// Get schema from the target SQLite database.
    pub fn get_schema(&mut self, db_path: String) -> String {
        // Get schema from the target SQLite database.
        let mut path = (db_path || self.default_db_path);
        if !path {
            "".to_string()
        }
        get_sqlite_schema(path.to_string())
    }
    /// Generate SQL for the given query using the LLM.
    /// 
    /// Args:
    /// query: User natural language query.
    /// schema: Database schema (from get_schema()).
    /// db_path: Optional override for database path.
    /// 
    /// Returns:
    /// SQL string or None if generation failed.
    pub fn generate_sql(&mut self, query: String, schema: String, db_path: String) -> Result<Option<String>> {
        // Generate SQL for the given query using the LLM.
        // 
        // Args:
        // query: User natural language query.
        // schema: Database schema (from get_schema()).
        // db_path: Optional override for database path.
        // 
        // Returns:
        // SQL string or None if generation failed.
        if !schema {
            logger.warning("[SQLRouter] No schema available for SQL generation.".to_string());
            None
        }
        if self.llm.is_none() {
            logger.warning("[SQLRouter] No LLM configured. Cannot generate SQL.".to_string());
            None
        }
        let mut prompt = format!(_SQL_GEN_PROMPT, /* schema= */ schema, /* question= */ query);
        // try:
        {
            if /* hasattr(self.llm, "query_sync".to_string()) */ true {
                let mut sql = self.llm.query_sync(prompt, /* max_tokens= */ 300, /* temperature= */ 0.0_f64);
            } else if /* hasattr(self.llm, "generate".to_string()) */ true {
                let mut sql = self.llm.generate(prompt);
            } else {
                None
            }
            let mut sql = sql.trim().to_string();
            let mut sql = regex::Regex::new(&"```(?:sql)?\\s*".to_string()).unwrap().replace_all(&"".to_string(), sql).to_string();
            let mut sql = regex::Regex::new(&"```\\s*$".to_string()).unwrap().replace_all(&"".to_string(), sql).to_string().trim().to_string();
            let mut danger = regex::Regex::new(&"\\b(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE)\\b".to_string()).unwrap();
            if danger.search(sql) {
                logger.warning(format!("[SQLRouter] Generated SQL contains dangerous statement, rejecting: {}", sql[..100]));
                None
            }
            logger.debug(format!("[SQLRouter] Generated SQL: {}", sql[..200]));
            sql
        }
        // except Exception as e:
    }
    /// Execute SQL against the target SQLite database.
    /// 
    /// Args:
    /// sql: SQL query to execute.
    /// db_path: Database path (uses default_db_path if None).
    /// max_rows: Maximum rows to return.
    /// 
    /// Returns:
    /// Dict with 'columns', 'rows', 'row_count', 'error' keys.
    pub fn execute(&mut self, sql: String, db_path: String, max_rows: i64) -> Result<HashMap> {
        // Execute SQL against the target SQLite database.
        // 
        // Args:
        // sql: SQL query to execute.
        // db_path: Database path (uses default_db_path if None).
        // max_rows: Maximum rows to return.
        // 
        // Returns:
        // Dict with 'columns', 'rows', 'row_count', 'error' keys.
        let mut path = (db_path || self.default_db_path);
        if !path {
            HashMap::from([("error".to_string(), "No database path configured.".to_string()), ("rows".to_string(), vec![]), ("columns".to_string(), vec![])])
        }
        if !PathBuf::from(path).exists() {
            HashMap::from([("error".to_string(), format!("Database not found: {}", path)), ("rows".to_string(), vec![]), ("columns".to_string(), vec![])])
        }
        // try:
        {
            let mut conn = /* sqlite3 */ path, /* timeout= */ 10;
            {
                conn.row_factory = sqlite3::Row;
                let mut cursor = conn.execute(sql);
                let mut columns = if cursor.description { cursor.description.iter().map(|d| d[0]).collect::<Vec<_>>() } else { vec![] };
                let mut all_rows = cursor.fetchmany(max_rows);
                let mut rows = all_rows.iter().map(|row| /* dict(row) */ HashMap::new()).collect::<Vec<_>>();
                HashMap::from([("columns".to_string(), columns), ("rows".to_string(), rows), ("row_count".to_string(), rows.len()), ("error".to_string(), None)])
            }
        }
        // except sqlite3::Error as e:
    }
    /// Format SQL result as a natural language answer using the LLM.
    /// 
    /// Falls back to a structured text representation if LLM is unavailable.
    pub fn format_answer(&mut self, query: String, sql_result: HashMap<String, serde_json::Value>) -> Result<String> {
        // Format SQL result as a natural language answer using the LLM.
        // 
        // Falls back to a structured text representation if LLM is unavailable.
        if sql_result.get(&"error".to_string()).cloned() {
            format!("I couldn't retrieve the data: {}", sql_result["error".to_string()])
        }
        let mut rows = sql_result.get(&"rows".to_string()).cloned().unwrap_or(vec![]);
        let mut columns = sql_result.get(&"columns".to_string()).cloned().unwrap_or(vec![]);
        let mut row_count = sql_result.get(&"row_count".to_string()).cloned().unwrap_or(0);
        if !rows {
            "The query returned no results.".to_string()
        }
        let mut result_text = format!("{} row(s) found.\n", row_count);
        result_text += (columns.join(&" | ".to_string()) + "\n".to_string());
        result_text += rows[..10].iter().map(|row| columns.iter().map(|c| row.get(&c).cloned().unwrap_or("".to_string()).to_string()).collect::<Vec<_>>().join(&" | ".to_string())).collect::<Vec<_>>().join(&"\n".to_string());
        if row_count > 10 {
            result_text += format!("\n... and {} more rows.", (row_count - 10));
        }
        if self.llm.is_some() {
            // try:
            {
                let mut prompt = format!(_ANSWER_FORMAT_PROMPT, /* question= */ query, /* result= */ result_text[..2000]);
                if /* hasattr(self.llm, "query_sync".to_string()) */ true {
                    self.llm.query_sync(prompt, /* max_tokens= */ 200, /* temperature= */ 0.1_f64).trim().to_string()
                } else if /* hasattr(self.llm, "generate".to_string()) */ true {
                    self.llm.generate(prompt).trim().to_string()
                }
            }
            // except Exception as e:
        }
        Ok((format!("Found {} result(s):\n\n", row_count) + result_text))
    }
    /// Complete routing pipeline: classify → generate SQL or RAG → return answer.
    /// 
    /// Args:
    /// query: User query.
    /// rag: LocalRAG instance for semantic search fallback.
    /// db_path: SQLite database path.
    /// schema: Pre-computed schema string (optional, avoids repeated introspection).
    /// k: Number of RAG results for hybrid/rag path.
    /// 
    /// Returns:
    /// Dict with keys: 'answer', 'path' ('sql'|'rag'|'hybrid'), 'sql', 'results', 'chunks'
    pub fn route_and_answer(&mut self, query: String, rag: Box<dyn std::any::Any>, db_path: String, schema: String, k: i64) -> Result<HashMap> {
        // Complete routing pipeline: classify → generate SQL or RAG → return answer.
        // 
        // Args:
        // query: User query.
        // rag: LocalRAG instance for semantic search fallback.
        // db_path: SQLite database path.
        // schema: Pre-computed schema string (optional, avoids repeated introspection).
        // k: Number of RAG results for hybrid/rag path.
        // 
        // Returns:
        // Dict with keys: 'answer', 'path' ('sql'|'rag'|'hybrid'), 'sql', 'results', 'chunks'
        let mut route = self.classify(query);
        logger.info(format!("[SQLRouter] Query classified as: {} | '{}'", route, query[..60]));
        let mut output = HashMap::from([("path".to_string(), route), ("answer".to_string(), "".to_string()), ("sql".to_string(), None), ("sql_results".to_string(), None), ("chunks".to_string(), vec![])]);
        if ("sql".to_string(), "hybrid".to_string()).contains(&route) {
            let mut _schema = (schema || self.get_schema(db_path));
            let mut sql = self.generate_sql(query, _schema, db_path);
            if sql {
                output["sql".to_string()] = sql;
                let mut sql_results = self.execute(sql, db_path);
                output["sql_results".to_string()] = sql_results;
                if (!sql_results.get(&"error".to_string()).cloned() && sql_results.get(&"rows".to_string()).cloned()) {
                    output["answer".to_string()] = self.format_answer(query, sql_results);
                    if route == "sql".to_string() {
                        output
                    }
                } else {
                    logger.info("[SQLRouter] SQL path returned no results, falling back to RAG.".to_string());
                }
            }
        }
        if rag.is_some() {
            // try:
            {
                let mut chunks = rag.hybrid_search(query, /* k= */ k);
                output["chunks".to_string()] = chunks;
                if !output["answer".to_string()] {
                    output["answer".to_string()] = "".to_string();
                }
            }
            // except Exception as e:
        }
        Ok(output)
    }
}

/// Classify query as 'sql', 'rag', or 'hybrid'.
/// 
/// Returns:
/// 'sql'    — statistical/aggregation query → use SQL path
/// 'rag'    — qualitative/semantic query → use vector search
/// 'hybrid' — could benefit from both
pub fn classify_query(query: String) -> String {
    // Classify query as 'sql', 'rag', or 'hybrid'.
    // 
    // Returns:
    // 'sql'    — statistical/aggregation query → use SQL path
    // 'rag'    — qualitative/semantic query → use vector search
    // 'hybrid' — could benefit from both
    let mut stat_hits = _STAT_PATTERNS.iter().filter(|p| p.search(query)).map(|p| 1).collect::<Vec<_>>().iter().sum::<i64>();
    let mut rag_hits = _RAG_PATTERNS.iter().filter(|p| p.search(query)).map(|p| 1).collect::<Vec<_>>().iter().sum::<i64>();
    if stat_hits >= 2 {
        "sql".to_string()
    }
    if (stat_hits == 1 && rag_hits == 0) {
        "sql".to_string()
    }
    if (stat_hits >= 1 && rag_hits >= 1) {
        "hybrid".to_string()
    }
    "rag".to_string()
}

/// Return CREATE TABLE statements from a SQLite database as a string.
pub fn get_sqlite_schema(db_path: String) -> Result<String> {
    // Return CREATE TABLE statements from a SQLite database as a string.
    // try:
    {
        let mut conn = /* sqlite3 */ db_path;
        {
            let mut rows = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL".to_string()).fetchall();
            rows.iter().map(|(name, sql)| format!("-- Table: {}\n{}", name, sql)).collect::<Vec<_>>().join(&"\n\n".to_string())
        }
    }
    // except Exception as e:
}
