/// Core/data_analyst_agent::py — ZEN_RAG Data Analyst Agent
/// =========================================================
/// Natural-language CSV/Excel analysis using DataSchema inference,
/// LLM-generated pandas code, safe execution, and LLM synthesis.
/// 
/// Usage:
/// from Core.data_analyst_agent import DataAnalystAgent, DataSchema
/// import pandas as pd
/// 
/// df = pd.read_csv("data.csv")
/// agent = DataAnalystAgent()
/// schema = agent.infer_schema(df)
/// result = agent.analyze("What is the average sales per region?", df, llm_fn=my_llm)
/// print(result.answer)

use anyhow::{Result, Context};
use regex::Regex;
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Metadata for a single DataFrame column.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ColumnInfo {
    pub name: String,
    pub dtype: String,
    pub role: String,
    pub nunique: i64,
    pub sample_values: Vec<Box<dyn std::any::Any>>,
    pub min_val: Option<f64>,
    pub max_val: Option<f64>,
    pub mean_val: Option<f64>,
    pub std_val: Option<f64>,
    pub top_values: Vec<(Box<dyn std::any::Any>, i64)>,
    pub null_count: i64,
    pub null_pct: f64,
}

impl ColumnInfo {
    /// Human-readable one-line description for LLM prompt.
    pub fn describe(&mut self) -> String {
        // Human-readable one-line description for LLM prompt.
        let mut parts = vec![format!("`{}` ({}, {})", self.name, self.dtype, self.role)];
        if (self.role == "numeric".to_string() && self.min_val.is_some()) {
            parts.push(format!("range [{:.2g}…{:.2g}], mean={:.2g}", self.min_val, self.max_val, self.mean_val));
        } else if (self.role == "categorical".to_string() && self.top_values) {
            let mut top = self.top_values[..5].iter().map(|(v, _)| format!("'{}'", v)).collect::<Vec<_>>().join(&", ".to_string());
            parts.push(format!("top values: {}", top));
        } else if self.role == "date".to_string() {
            if self.sample_values {
                parts.push(format!("sample: {}", self.sample_values[0]));
            }
        }
        if self.null_pct > 0 {
            parts.push(format!("{:.0}% null", self.null_pct));
        }
        parts.join(&" — ".to_string())
    }
}

/// Complete schema for a DataFrame.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataSchema {
    pub columns: Vec<ColumnInfo>,
    pub row_count: i64,
    pub col_count: i64,
    pub sheet_name: Option<String>,
    pub file_name: Option<String>,
}

impl DataSchema {
    /// Compact schema representation for LLM prompts.
    pub fn to_prompt_str(&mut self) -> String {
        // Compact schema representation for LLM prompts.
        let mut lines = vec![((format!("DataFrame: {} rows × {} columns", self.row_count, self.col_count) + if self.sheet_name { format!(" (sheet: {})", self.sheet_name) } else { "".to_string() }) + if self.file_name { format!(" from {}", self.file_name) } else { "".to_string() }), "".to_string(), "Columns:".to_string()];
        for col in self.columns.iter() {
            lines.push(format!("  • {}", col.describe()));
        }
        lines.join(&"\n".to_string())
    }
    pub fn column_names(&self) -> Vec<String> {
        self.columns.iter().map(|c| c.name).collect::<Vec<_>>()
    }
}

/// Result of a data analysis query.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalysisResult {
    pub question: String,
    pub answer: String,
    pub pandas_code: String,
    pub raw_result: Box<dyn std::any::Any>,
    pub result_type: String,
    pub error: Option<String>,
    pub chart_data: Option<Box<dyn std::any::Any>>,
    pub sources_used: i64,
}

/// Analyzes tabular data via natural language questions.
/// 
/// Pipeline:
/// 1. infer_schema(df)             → DataSchema
/// 2. nl_to_pandas_code(q, schema) → Python/pandas code string (via LLM)
/// 3. execute_safely(code, df)     → (result, error)
/// 4. synthesize_answer(...)       → natural language answer (via LLM)
#[derive(Debug, Clone)]
pub struct DataAnalystAgent {
    pub max_rows_in_prompt: String,
    pub max_code_retries: String,
}

impl DataAnalystAgent {
    pub fn new(max_rows_in_prompt: i64, max_code_retries: i64) -> Self {
        Self {
            max_rows_in_prompt,
            max_code_retries,
        }
    }
    /// Auto-detect column roles and statistics from a DataFrame.
    pub fn infer_schema(&mut self, df: String, sheet_name: Option<String>, file_name: Option<String>) -> Result<DataSchema> {
        // Auto-detect column roles and statistics from a DataFrame.
        if !_PANDAS {
            return Err(anyhow::anyhow!("RuntimeError('pandas is required for DataAnalystAgent')"));
        }
        let mut columns = vec![];
        let mut n_rows = df.len();
        for col_name in df.columns.iter() {
            let mut series = df[&col_name];
            let mut dtype_str = series.dtype.to_string();
            let mut null_count = series.isna().sum().to_string().parse::<i64>().unwrap_or(0);
            let mut null_pct = ((((100 * null_count) / n_rows.max(1)) as f64) * 10f64.powi(1)).round() / 10f64.powi(1);
            let mut nunique = series.nunique(/* dropna= */ true).to_string().parse::<i64>().unwrap_or(0);
            let mut sample = series.dropna().head(3).tolist().iter().filter(|v| v.is_some()).map(|v| v).collect::<Vec<_>>();
            let mut role = self._detect_role(series, col_name, nunique, n_rows);
            let mut col_info = ColumnInfo(/* name= */ col_name, /* dtype= */ dtype_str, /* role= */ role, /* nunique= */ nunique, /* sample_values= */ sample, /* null_count= */ null_count, /* null_pct= */ null_pct);
            if role == "numeric".to_string() {
                // try:
                {
                    let mut numeric = pd.to_numeric(series, /* errors= */ "coerce".to_string()).dropna();
                    if numeric.len() > 0 {
                        col_info.min_val = numeric.min().to_string().parse::<f64>().unwrap_or(0.0);
                        col_info.max_val = numeric.max().to_string().parse::<f64>().unwrap_or(0.0);
                        col_info.mean_val = numeric.mean().to_string().parse::<f64>().unwrap_or(0.0);
                        col_info.std_val = numeric.std().to_string().parse::<f64>().unwrap_or(0.0);
                    }
                }
                // except Exception as exc:
            } else if role == "categorical".to_string() {
                // try:
                {
                    let mut vc = series.value_counts().head(10);
                    col_info.top_values = vc.iter().iter().map(|(v, c)| (v, c.to_string().parse::<i64>().unwrap_or(0))).collect::<Vec<_>>();
                }
                // except Exception as exc:
            }
            columns.push(col_info);
        }
        Ok(DataSchema(/* columns= */ columns, /* row_count= */ n_rows, /* col_count= */ df.columns.len(), /* sheet_name= */ sheet_name, /* file_name= */ file_name))
    }
    /// Heuristic column role detection.
    pub fn _detect_role(&self, series: String, col_name: String, nunique: i64, n_rows: i64) -> Result<String> {
        // Heuristic column role detection.
        let mut name_lower = col_name.to_lowercase();
        let mut dtype_str = series.dtype.to_string();
        if (dtype_str.contains(&"datetime".to_string()) || dtype_str.contains(&"timestamp".to_string())) {
            "date".to_string()
        }
        if vec!["date".to_string(), "time".to_string(), "year".to_string(), "month".to_string(), "day".to_string(), "data".to_string(), "zi".to_string(), "luna".to_string(), "an".to_string()].iter().map(|kw| name_lower.contains(&kw)).collect::<Vec<_>>().iter().any(|v| *v) {
            // try:
            {
                let mut sample = series.dropna().head(20);
                pd.to_datetime(sample, /* errors= */ "raise".to_string(), /* infer_datetime_format= */ true);
                "date".to_string()
            }
            // except Exception as exc:
        }
        if (dtype_str.contains(&"int".to_string()) || dtype_str.contains(&"float".to_string())) {
            if (nunique == n_rows && name_lower.contains(&"id".to_string())) {
                "id".to_string()
            }
            "numeric".to_string()
        }
        if dtype_str == "object".to_string() {
            // try:
            {
                let mut numeric_count = pd.to_numeric(series.dropna().head(50), /* errors= */ "coerce".to_string()).notna().sum();
                if numeric_count > 40 {
                    "numeric".to_string()
                }
            }
            // except Exception as exc:
        }
        if nunique <= 20.max((n_rows * 0.05_f64)) {
            "categorical".to_string()
        }
        if nunique == n_rows {
            let mut avg_len = series.dropna().astype(str).str.len().mean();
            if avg_len < 20 {
                "id".to_string()
            }
        }
        Ok("text".to_string())
    }
    /// Convert a natural language question into pandas code.
    /// 
    /// Args:
    /// question: User's question about the data
    /// schema:   DataSchema from infer_schema()
    /// llm_fn:   Callable(prompt: str) -> str, or None (returns template code)
    /// 
    /// Returns:
    /// Python code string that operates on a variable named `df`
    /// and assigns the result to `result`
    pub fn nl_to_pandas_code(&mut self, question: String, schema: DataSchema, llm_fn: Option<Box<dyn Fn(serde_json::Value)>>) -> Result<String> {
        // Convert a natural language question into pandas code.
        // 
        // Args:
        // question: User's question about the data
        // schema:   DataSchema from infer_schema()
        // llm_fn:   Callable(prompt: str) -> str, or None (returns template code)
        // 
        // Returns:
        // Python code string that operates on a variable named `df`
        // and assigns the result to `result`
        if llm_fn.is_none() {
            self._fallback_code(question, schema)
        }
        let mut prompt = self._build_code_prompt(question, schema);
        // try:
        {
            let mut raw = llm_fn(prompt);
            let mut code = self._extract_code(raw);
            code
        }
        // except Exception as e:
    }
    pub fn _build_code_prompt(&self, question: String, schema: DataSchema) -> String {
        format!("You are a pandas expert. Generate Python code to answer the user's question about a DataFrame.\n\n{}\n\nUser question: {}\n\nRules:\n- The DataFrame is named `df` and is already loaded\n- Assign the final answer to a variable named `result`\n- Keep code minimal (1-5 lines)\n- Use only pandas (pd) and numpy (np) — no imports needed\n- Do NOT use print(), display(), or plt — just assign to `result`\n- If the question asks for a count/sum/mean, return a scalar\n- If the question asks to compare groups, return a Series or small DataFrame\n- Return ONLY the code block, nothing else\n\nExample for \"total sales by region\":\n```python\nresult = df.groupby('region')['sales'].sum().sort_values(ascending=false)\n```\n\nNow write code for: {}\n```python", schema.to_prompt_str(), question, question)
    }
    /// Extract Python code block from LLM response.
    pub fn _extract_code(&self, llm_output: String) -> String {
        // Extract Python code block from LLM response.
        let mut patterns = vec!["```python\\n(.*?)```".to_string(), "```\\n(.*?)```".to_string(), "`(.*?)`".to_string()];
        for pattern in patterns.iter() {
            let mut r#match = regex::Regex::new(&pattern).unwrap().is_match(&llm_output);
            if r#match {
                let mut code = r#match.group(1).trim().to_string();
                if (code.contains(&"result".to_string()) || code.contains(&"df".to_string())) {
                    code
                }
            }
        }
        let mut lines = vec![];
        for line in llm_output.trim().to_string().lines().map(|s| s.to_string()).collect::<Vec<String>>().iter() {
            let mut stripped = line.trim().to_string();
            if (stripped && !stripped.starts_with(&*"#".to_string()) && !stripped.starts_with(&*"//".to_string())) {
                if (stripped.contains(&"=".to_string()) || stripped.starts_with(&*"result".to_string()) || stripped.starts_with(&*"df".to_string())) {
                    lines.push(stripped);
                }
            }
        }
        if lines { lines.join(&"\n".to_string()) } else { "result = df.describe()".to_string() }
    }
    /// Template-based fallback when LLM is unavailable.
    pub fn _fallback_code(&self, question: String, schema: DataSchema) -> String {
        // Template-based fallback when LLM is unavailable.
        let mut q = question.to_lowercase();
        let mut numeric_cols = schema.columns.iter().filter(|c| c.role == "numeric".to_string()).map(|c| c.name).collect::<Vec<_>>();
        let mut cat_cols = schema.columns.iter().filter(|c| c.role == "categorical".to_string()).map(|c| c.name).collect::<Vec<_>>();
        let mut date_cols = schema.columns.iter().filter(|c| c.role == "date".to_string()).map(|c| c.name).collect::<Vec<_>>();
        if vec!["count".to_string(), "how many".to_string(), "câte".to_string(), "câți".to_string()].iter().map(|w| q.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) {
            "result = len(df)".to_string()
        }
        if (vec!["average".to_string(), "mean".to_string(), "medie".to_string()].iter().map(|w| q.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) && numeric_cols) {
            format!("result = df[{}].mean()", numeric_cols)
        }
        if (vec!["sum".to_string(), "total".to_string(), "sumă".to_string()].iter().map(|w| q.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) && numeric_cols) {
            let mut col = numeric_cols[0];
            if cat_cols {
                format!("result = df.groupby('{}')['{}'].sum().sort_values(ascending=false)", cat_cols[0], col)
            }
            format!("result = df['{}'].sum()", col)
        }
        if (vec!["max".to_string(), "maximum".to_string(), "maxim".to_string()].iter().map(|w| q.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) && numeric_cols) {
            format!("result = df['{}'].max()", numeric_cols[0])
        }
        if (vec!["min".to_string(), "minimum".to_string(), "minim".to_string()].iter().map(|w| q.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) && numeric_cols) {
            format!("result = df['{}'].min()", numeric_cols[0])
        }
        if (vec!["unique".to_string(), "distinct".to_string(), "unice".to_string()].iter().map(|w| q.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) && cat_cols) {
            format!("result = df['{}'].value_counts()", cat_cols[0])
        }
        if vec!["missing".to_string(), "null".to_string(), "nan".to_string(), "lipsă".to_string()].iter().map(|w| q.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) {
            "result = df.isna().sum()".to_string()
        }
        if vec!["describe".to_string(), "summary".to_string(), "statistics".to_string(), "statistici".to_string()].iter().map(|w| q.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) {
            "result = df.describe()".to_string()
        }
        "result = df.describe(include='all').T[['count','mean','min','max']].dropna(how='all')".to_string()
    }
    /// Execute pandas code in a restricted namespace.
    /// 
    /// Returns:
    /// (result, error_message) — error is None on success
    pub fn execute_safely(&mut self, code: String, df: String) -> Result<(Box<dyn std::any::Any>, Option<String>)> {
        // Execute pandas code in a restricted namespace.
        // 
        // Returns:
        // (result, error_message) — error is None on success
        for pattern in self._FORBIDDEN_PATTERNS.iter() {
            if regex::Regex::new(&pattern).unwrap().is_match(&code) {
                (None, format!("Forbidden pattern detected: {}", pattern))
            }
        }
        let mut namespace = HashMap::from([("df".to_string(), df.clone()), ("pd".to_string(), pd), ("np".to_string(), if _PANDAS { np } else { None }), ("result".to_string(), None)]);
        // try:
        {
            exec(compile(code, "<analyst>".to_string(), "exec".to_string()), namespace);
            let mut result = namespace.get(&"result".to_string()).cloned();
            (result, None)
        }
        // except Exception as e:
    }
    /// Determine result type and extract chart-ready data.
    /// 
    /// Returns:
    /// (result_type, chart_data)
    /// result_type: "scalar" | "series" | "dataframe" | "none"
    /// chart_data: pandas Series or None
    pub fn classify_result(&self, result: Box<dyn std::any::Any>) -> (String, Option<Box<dyn std::any::Any>>) {
        // Determine result type and extract chart-ready data.
        // 
        // Returns:
        // (result_type, chart_data)
        // result_type: "scalar" | "series" | "dataframe" | "none"
        // chart_data: pandas Series or None
        if result.is_none() {
            ("none".to_string(), None)
        }
        if _PANDAS {
            if /* /* isinstance(result, pd.DataFrame) */ */ true {
                let mut chart_data = None;
                let mut num_cols = result.select_dtypes(/* include= */ "number".to_string()).columns.tolist();
                if (num_cols.len() == 1 && result.len() <= 50) {
                    let mut chart_data = result[num_cols[0]];
                } else if (num_cols.len() >= 1 && result.len() <= 20) {
                    let mut chart_data = result[num_cols[0]];
                }
                ("dataframe".to_string(), chart_data)
            }
            if /* /* isinstance(result, pd.Series) */ */ true {
                let mut chart_data = if ((float, int).contains(&result.dtype) || result.dtype.to_string().starts_with(&*("int".to_string(), "float".to_string()))) { result } else { None };
                if (chart_data.is_some() && chart_data.len() > 20) {
                    let mut chart_data = chart_data.head(20);
                }
                ("series".to_string(), chart_data)
            }
        }
        if /* /* isinstance(result, (int, float, str, bool) */) */ true {
            ("scalar".to_string(), None)
        }
        if /* /* isinstance(result, (list, dict) */) */ true {
            ("scalar".to_string(), None)
        }
        ("scalar".to_string(), None)
    }
    /// Synthesize a natural language answer from the pandas result.
    /// 
    /// Falls back to a formatted string if LLM is unavailable.
    pub fn synthesize_answer(&mut self, question: String, result: Box<dyn std::any::Any>, schema: DataSchema, result_type: String, llm_fn: Option<Box<dyn Fn(serde_json::Value)>>, error: Option<String>) -> Result<String> {
        // Synthesize a natural language answer from the pandas result.
        // 
        // Falls back to a formatted string if LLM is unavailable.
        if error {
            format!("⚠️ Could not compute the answer: {}", error)
        }
        if result.is_none() {
            "The query returned no results.".to_string()
        }
        let mut result_str = self._result_to_str(result, result_type);
        if llm_fn.is_none() {
            self._fallback_answer(question, result_str, result_type)
        }
        let mut prompt = format!("You are a data analyst. Summarize the following query result in plain language.\n\nQuestion: {}\nData: {} ({} rows)\n\nResult ({}):\n{}\n\nWrite a clear, concise answer (2-4 sentences). Include specific numbers.\nIf the result is a table/series, highlight the key insight.\nAnswer in the same language as the question.", question, (schema.file_name || "the dataset".to_string()), schema.row_count, result_type, result_str);
        // try:
        {
            llm_fn(prompt).trim().to_string()
        }
        // except Exception as e:
    }
    /// Convert result to a compact string for prompts.
    pub fn _result_to_str(&self, result: Box<dyn std::any::Any>, result_type: String) -> String {
        // Convert result to a compact string for prompts.
        if result_type == "scalar".to_string() {
            if /* /* isinstance(result, float) */ */ true {
                format!("{:,.4g}", result)
            }
            result.to_string()
        }
        if (_PANDAS && /* /* isinstance(result, pd.Series) */ */ true) {
            result.head(20).to_string()
        }
        if (_PANDAS && /* /* isinstance(result, pd.DataFrame) */ */ true) {
            result.head(10).to_string()
        }
        result.to_string()[..500]
    }
    /// Plain-text answer without LLM.
    pub fn _fallback_answer(&self, question: String, result_str: String, result_type: String) -> String {
        // Plain-text answer without LLM.
        if result_type == "scalar".to_string() {
            format!("**Result:** {}", result_str)
        }
        if ("series".to_string(), "dataframe".to_string()).contains(&result_type) {
            let mut lines = result_str.trim().to_string().lines().map(|s| s.to_string()).collect::<Vec<String>>();
            let mut preview = lines[..10].join(&"\n".to_string());
            let mut suffix = if lines.len() > 10 { format!("\n…({} more rows)", (lines.len() - 10)) } else { "".to_string() };
            format!("**Result:**\n```\n{}{}\n```", preview, suffix)
        }
        result_str
    }
    /// Full NL→pandas→answer pipeline.
    /// 
    /// Args:
    /// question:   Natural language question
    /// df:         The DataFrame to analyze
    /// schema:     Pre-computed schema (inferred if None)
    /// llm_fn:     Callable(prompt) -> str for code gen + synthesis
    /// retry_on_error: Re-ask LLM to fix code if execution fails
    pub fn analyze(&mut self, question: String, df: String, schema: Option<DataSchema>, llm_fn: Option<Box<dyn Fn(serde_json::Value)>>, sheet_name: Option<String>, file_name: Option<String>, retry_on_error: bool) -> Result<AnalysisResult> {
        // Full NL→pandas→answer pipeline.
        // 
        // Args:
        // question:   Natural language question
        // df:         The DataFrame to analyze
        // schema:     Pre-computed schema (inferred if None)
        // llm_fn:     Callable(prompt) -> str for code gen + synthesis
        // retry_on_error: Re-ask LLM to fix code if execution fails
        if !_PANDAS {
            AnalysisResult(/* question= */ question, /* answer= */ "pandas not installed".to_string(), /* pandas_code= */ "".to_string(), /* raw_result= */ None, /* result_type= */ "error".to_string(), /* error= */ "pandas not installed".to_string())
        }
        if schema.is_none() {
            let mut schema = self.infer_schema(df, /* sheet_name= */ sheet_name, /* file_name= */ file_name);
        }
        let mut code = self.nl_to_pandas_code(question, schema, /* llm_fn= */ llm_fn);
        let (mut result, mut error) = self.execute_safely(code, df);
        if (error && retry_on_error && llm_fn) {
            let mut retry_prompt = format!("The previous pandas code failed:\n```python\n{}\n```\nError: {}\n\nFix it for the question: {}\nDataFrame schema:\n{}\n\nWrite corrected code only:\n```python", code, error, question, schema.to_prompt_str());
            // try:
            {
                let mut fixed_raw = llm_fn(retry_prompt);
                let mut code = self._extract_code(fixed_raw);
                let (mut result, mut error) = self.execute_safely(code, df);
            }
            // except Exception as exc:
        }
        let (mut result_type, mut chart_data) = self.classify_result(result);
        let mut answer = self.synthesize_answer(question, result, schema, result_type, /* llm_fn= */ llm_fn, /* error= */ error);
        Ok(AnalysisResult(/* question= */ question, /* answer= */ answer, /* pandas_code= */ code, /* raw_result= */ result, /* result_type= */ result_type, /* error= */ error, /* chart_data= */ chart_data))
    }
}

/// Load a CSV or Excel file into a pandas DataFrame.
/// 
/// Returns:
/// (df, sheet_name_used, error_message)
pub fn load_file_to_dataframe(file_path: /* Union(String, PathBuf) */ Box<dyn std::any::Any>, sheet_name: Option<String>) -> Result<(Option</* unknown */>, String, Option<String>)> {
    // Load a CSV or Excel file into a pandas DataFrame.
    // 
    // Returns:
    // (df, sheet_name_used, error_message)
    if !_PANDAS {
        (None, "".to_string(), "pandas not installed".to_string())
    }
    let mut path = PathBuf::from(file_path);
    let mut suffix = path.extension().unwrap_or_default().to_str().unwrap_or("").to_lowercase();
    // try:
    {
        if suffix == ".csv".to_string() {
            let mut df = pd.read_csv(path, /* encoding_errors= */ "replace".to_string());
            (df, "".to_string(), None)
        } else if (".tsv".to_string(), ".txt".to_string()).contains(&suffix) {
            let mut df = pd.read_csv(path, /* sep= */ "\t".to_string(), /* encoding_errors= */ "replace".to_string());
            (df, "".to_string(), None)
        } else if (".xlsx".to_string(), ".xls".to_string(), ".xlsm".to_string()).contains(&suffix) {
            let mut xls = pd.ExcelFile(path);
            let mut sheets = xls.sheet_names;
            if !sheets {
                (None, "".to_string(), "Excel file has no sheets".to_string())
            }
            let mut target = if sheets.contains(&sheet_name) { sheet_name } else { sheets[0] };
            let mut df = xls.parse(target);
            (df, target, None)
        } else {
            (None, "".to_string(), format!("Unsupported file type: {}", suffix))
        }
    }
    // except Exception as e:
}

/// Load a Streamlit UploadedFile into a DataFrame.
/// 
/// Returns:
/// (df, sheet_name_used, error_message, available_sheets)
pub fn load_uploaded_file(uploaded_file: Box<dyn std::any::Any>, sheet_name: Option<String>) -> Result<(Option</* unknown */>, String, Option<String>, Vec<String>)> {
    // Load a Streamlit UploadedFile into a DataFrame.
    // 
    // Returns:
    // (df, sheet_name_used, error_message, available_sheets)
    if !_PANDAS {
        (None, "".to_string(), "pandas not installed".to_string(), vec![])
    }
    let mut name = uploaded_file.name.to_lowercase();
    let mut data = uploaded_file.read();
    // try:
    {
        if (name.ends_with(&*".csv".to_string()) || name.ends_with(&*".tsv".to_string())) {
            let mut sep = if name.ends_with(&*".tsv".to_string()) { "\t".to_string() } else { ",".to_string() };
            let mut df = pd.read_csv(io.BytesIO(data), /* sep= */ sep, /* encoding_errors= */ "replace".to_string());
            (df, "".to_string(), None, vec![])
        } else if name.ends_with(&*(".xlsx".to_string(), ".xls".to_string(), ".xlsm".to_string())) {
            let mut xls = pd.ExcelFile(io.BytesIO(data));
            let mut sheets = xls.sheet_names;
            let mut target = if sheets.contains(&sheet_name) { sheet_name } else { sheets[0] };
            let mut df = xls.parse(target);
            (df, target, None, sheets)
        } else {
            (None, "".to_string(), format!("Unsupported: {}", uploaded_file.name), vec![])
        }
    }
    // except Exception as e:
}
