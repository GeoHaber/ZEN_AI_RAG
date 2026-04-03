/// X_RAY_Claude.py — Smart AI-Powered Code Analyzer (X-Ray 4.0)
/// =============================================================
/// 
/// Builds on top of x_ray_project.py's static analysis with deep AI features:
/// 
/// --smell            Code smell detection (AST heuristics + targeted LLM)
/// --duplicates       Cross-file function similarity (TF-IDF + SequenceMatcher + LLM)
/// --suggest-library  Groups similar functions → suggests shared library extraction
/// --full-scan        Runs all AI features in one pass
/// --report FILE      Save full JSON report to FILE
/// 
/// Architecture
/// ------------
/// - CodeSmellDetector  — AST-based heuristics flag suspects, LLM rates & advises
/// - DuplicateFinder    — Token cosine pre-filter → SequenceMatcher → optional LLM confirm
/// - LibraryAdvisor     — Consumes duplicate clusters → LLM designs unified APIs
/// - SmartGraph         — Enhanced graph with health-colored nodes + smell/duplicate tooltips
/// 
/// All features work WITHOUT an LLM (fast heuristic mode).
/// LLM enrichment is optional and uses Core.services.inference_engine if available.
/// 
/// Usage::
/// 
/// python X_RAY_Claude.py --path .                     # default scan + smells
/// python X_RAY_Claude.py --smell                      # code smell detection only
/// python X_RAY_Claude.py --duplicates                 # find similar functions
/// python X_RAY_Claude.py --suggest-library             # library extraction advisor
/// python X_RAY_Claude.py --full-scan                   # everything
/// python X_RAY_Claude.py --full-scan --use-llm         # everything with LLM enrichment
/// python X_RAY_Claude.py --report scan_results.json    # save JSON report

use anyhow::{Result, Context};
use regex::Regex;
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::collections::HashSet;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;
use tokio;

pub static UNICODE_OK: std::sync::LazyLock<_supports_unicode> = std::sync::LazyLock::new(|| Default::default());

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub const __VERSION__: &str = "4.0.0";

pub const SEP: &str = "-";

pub const BANNER: &str = "f\"\\n{'=' * 64}\\n  X-RAY Claude v{__version__} — Smart AI Code Analyzer\\n  Powered by AST heuristics + optional Local LLM\\n{'=' * 64}\\n";

pub static _ALWAYS_SKIP: std::sync::LazyLock<frozenset> = std::sync::LazyLock::new(|| Default::default());

pub static _STOP_WORDS: std::sync::LazyLock<frozenset> = std::sync::LazyLock::new(|| Default::default());

pub static _SPLIT_RE: std::sync::LazyLock<String /* re::compile */> = std::sync::LazyLock::new(|| Default::default());

pub static SMELL_THRESHOLDS: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

/// Severity levels for issues.
#[derive(Debug, Clone)]
pub struct Severity {
}

impl Severity {
    pub fn icon(level: String) -> String {
        let mut icons = if UNICODE_OK { Severity._ICONS_UNICODE } else { Severity._ICONS_ASCII };
        icons::get(&level).cloned().unwrap_or("?".to_string())
    }
}

/// Extracted function metadata from AST.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FunctionRecord {
    pub name: String,
    pub file_path: String,
    pub line_start: i64,
    pub line_end: i64,
    pub size_lines: i64,
    pub parameters: Vec<String>,
    pub return_type: Option<String>,
    pub decorators: Vec<String>,
    pub docstring: Option<String>,
    pub calls_to: Vec<String>,
    pub complexity: i64,
    pub nesting_depth: i64,
    pub code_hash: String,
    pub code: String,
    pub is_async: bool,
}

impl FunctionRecord {
    pub fn key(&self) -> &String {
        let mut stem = PathBuf::from(self.file_path).file_stem().unwrap_or_default().to_str().unwrap_or("");
        format!("{}.{}", stem, self.name)
    }
    pub fn location(&self) -> &String {
        format!("{}:{}", self.file_path, self.line_start)
    }
    pub fn signature(&self) -> &String {
        let mut params = self.parameters.join(&", ".to_string());
        let mut ret = if self.return_type { format!(" -> {}", self.return_type) } else { "".to_string() };
        format!("{}({}){}", self.name, params, ret)
    }
}

/// Extracted class metadata from AST.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClassRecord {
    pub name: String,
    pub file_path: String,
    pub line_start: i64,
    pub line_end: i64,
    pub size_lines: i64,
    pub method_count: i64,
    pub base_classes: Vec<String>,
    pub docstring: Option<String>,
    pub methods: Vec<String>,
    pub has_init: bool,
}

/// A detected code smell.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SmellIssue {
    pub file_path: String,
    pub line: i64,
    pub end_line: i64,
    pub category: String,
    pub severity: String,
    pub message: String,
    pub suggestion: String,
    pub name: String,
    pub metric_value: i64,
    pub llm_analysis: String,
}

/// A group of similar/duplicate functions.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DuplicateGroup {
    pub group_id: i64,
    pub similarity_type: String,
    pub avg_similarity: f64,
    pub functions: Vec<HashMap<String, Box<dyn std::any::Any>>>,
    pub merge_suggestion: String,
}

/// A suggestion to extract functions into a shared library.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LibrarySuggestion {
    pub module_name: String,
    pub description: String,
    pub functions: Vec<HashMap<String, Box<dyn std::any::Any>>>,
    pub unified_api: String,
    pub rationale: String,
}

/// Lazy-loading wrapper around Core.services.inference_engine.
#[derive(Debug, Clone)]
pub struct LLMHelper {
    pub _root: String,
    pub _adapter: Option<serde_json::Value>,
    pub _available: Option<serde_json::Value>,
    pub _provider: Option<serde_json::Value>,
}

impl LLMHelper {
    pub fn new(root: PathBuf) -> Self {
        Self {
            _root: root,
            _adapter: None,
            _available: None,
            _provider: None,
        }
    }
    pub fn available(&self) -> bool {
        if self._available.is_none() {
            // try:
            {
                let mut project_dir = self._root.to_string();
                if !sys::path.contains(&project_dir) {
                    sys::path.insert(0, project_dir);
                }
                // TODO: from llm_adapters import LLMFactory
                self._available = true;
                true
            }
            // except ImportError as _e:
            // try:
            {
                // TODO: from Core.services.inference_engine import FIFOLlamaCppInference
                self._available = true;
            }
            // except ImportError as _e:
        }
        self._available
    }
    pub fn _ensure_loaded(&mut self) -> Result<()> {
        if self._adapter.is_some() {
            return;
        }
        if !self.available {
            return Err(anyhow::anyhow!("RuntimeError('LLM not available — install llm_adapters or Core.services.inference_engine')"));
        }
        // try:
        {
            // TODO: from llm_adapters import LLMFactory, LLMRequest, LLMResponse
            for provider in ("local".to_string(), "ollama".to_string()).iter() {
                // try:
                {
                    let mut adapter = LLMFactory.create(provider);
                    self._adapter = adapter;
                    self._provider = provider;
                    logger.info(format!("LLM: Using adapter layer ({})", provider));
                    return;
                }
                // except Exception as _e:
            }
        }
        // except ImportError as _e:
        // try:
        {
            // TODO: from Core.services.inference_engine import FIFOLlamaCppInference
            let mut model_path = None;
            let mut _env_model_dir = std::env::var(&"ZENAI_MODEL_DIR".to_string()).unwrap_or_default().cloned().unwrap_or("".to_string());
            let mut _central_dir = if _env_model_dir { PathBuf::from(_env_model_dir) } else { None };
            let mut possible_models = vec![];
            if (_central_dir && _central_dir.is_dir()) {
                possible_models.extend({ let mut v = _central_dir.glob("*.gguf".to_string()).clone(); v.sort(); v });
            }
            let mut models_dir = (self._root / "models".to_string());
            if models_dir.is_dir() {
                for gguf in models_dir.glob("*.gguf".to_string()).iter() {
                    possible_models.insert(0, gguf);
                }
            }
            for m in possible_models.iter() {
                if m.exists() {
                    logger.info(format!("LLM: Using FIFOLlamaCppInference with {}", m.name));
                    let mut model_path = m.to_string();
                    break;
                }
            }
            let mut llm = FIFOLlamaCppInference(/* model_path= */ model_path, /* lazy_load= */ false, /* verbose= */ false);
            llm._setup_llm();
            if !llm._initialized {
                return Err(anyhow::anyhow!("RuntimeError(f'LLM init failed: {llm._init_error}')"));
            }
            self._adapter = llm;
            self._provider = "fifo_legacy".to_string();
        }
        // except ImportError as _e:
    }
    /// Synchronous LLM query — works with adapter layer or legacy FIFO.
    pub fn query_sync(&mut self, prompt: String, max_tokens: i64, temperature: f64) -> Result<String> {
        // Synchronous LLM query — works with adapter layer or legacy FIFO.
        self._ensure_loaded();
        if ("local".to_string(), "ollama".to_string(), "openai".to_string(), "anthropic".to_string()).contains(&self._provider) {
            // TODO: from llm_adapters import LLMRequest
            let mut req = LLMRequest(/* messages= */ vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), prompt)])], /* model= */ "auto".to_string(), /* temperature= */ temperature, /* max_tokens= */ max_tokens);
            let mut resp = self._adapter.generate(req);
            if (resp && resp.content) { resp.content } else { "".to_string() }
        }
        // TODO: import asyncio
        let _run = || {
            let mut text = "".to_string();
            // async for
            while let Some(chunk) = self._adapter.query(prompt, /* max_tokens= */ max_tokens, /* temperature= */ temperature).next().await {
                text += chunk;
            }
            text
        };
        let mut r#loop = asyncio.new_event_loop();
        // try:
        {
            r#loop.run_until_complete(_run())
        }
        // finally:
            Ok(r#loop.close())
    }
}

/// Detects code smells via AST heuristics, optionally enriched by LLM.
/// 
/// Two-stage approach:
/// Stage 1 (fast):  AST metrics → flag suspects based on thresholds
/// Stage 2 (slow):  Send suspects to LLM for detailed analysis + fix suggestions
#[derive(Debug, Clone)]
pub struct CodeSmellDetector {
    pub thresholds: HashMap<String, serde_json::Value>,
    pub smells: Vec<SmellIssue>,
}

impl CodeSmellDetector {
    pub fn new(thresholds: HashMap<String, i64>) -> Self {
        Self {
            thresholds: HashMap::new(),
            smells: Vec::new(),
        }
    }
    /// Run all heuristic smell detectors. Returns sorted list of SmellIssues.
    pub fn detect(&mut self, functions: Vec<FunctionRecord>, classes: Vec<ClassRecord>) -> Vec<SmellIssue> {
        // Run all heuristic smell detectors. Returns sorted list of SmellIssues.
        self.smells = vec![];
        for func in functions.iter() {
            self._check_function(func);
        }
        for cls in classes.iter() {
            self._check_class(cls);
        }
        self.smells.sort(/* key= */ |s| (if s.severity == Severity.CRITICAL { 0 } else { if s.severity == Severity.WARNING { 1 } else { 2 } }, s.file_path, s.line));
        self.smells
    }
    pub fn _check_function(&mut self, func: FunctionRecord) -> () {
        let mut t = self.thresholds;
        if func.size_lines >= t["very_long_function".to_string()] {
            self.smells.push(SmellIssue(/* file_path= */ func.file_path, /* line= */ func.line_start, /* end_line= */ func.line_end, /* category= */ "very-long-function".to_string(), /* severity= */ Severity.CRITICAL, /* name= */ func.name, /* metric_value= */ func.size_lines, /* message= */ format!("Function '{}' is {} lines (limit: {})", func.name, func.size_lines, t["very_long_function".to_string()]), /* suggestion= */ "Split into smaller focused functions. Extract logical blocks.".to_string()));
        } else if func.size_lines >= t["long_function".to_string()] {
            self.smells.push(SmellIssue(/* file_path= */ func.file_path, /* line= */ func.line_start, /* end_line= */ func.line_end, /* category= */ "long-function".to_string(), /* severity= */ Severity.WARNING, /* name= */ func.name, /* metric_value= */ func.size_lines, /* message= */ format!("Function '{}' is {} lines (limit: {})", func.name, func.size_lines, t["long_function".to_string()]), /* suggestion= */ "Consider splitting into smaller functions.".to_string()));
        }
        if func.nesting_depth >= t["very_deep_nesting".to_string()] {
            self.smells.push(SmellIssue(/* file_path= */ func.file_path, /* line= */ func.line_start, /* end_line= */ func.line_end, /* category= */ "very-deep-nesting".to_string(), /* severity= */ Severity.CRITICAL, /* name= */ func.name, /* metric_value= */ func.nesting_depth, /* message= */ format!("Function '{}' has nesting depth {} (limit: {})", func.name, func.nesting_depth, t["very_deep_nesting".to_string()]), /* suggestion= */ "Use early returns, guard clauses, or extract nested blocks.".to_string()));
        } else if func.nesting_depth >= t["deep_nesting".to_string()] {
            self.smells.push(SmellIssue(/* file_path= */ func.file_path, /* line= */ func.line_start, /* end_line= */ func.line_end, /* category= */ "deep-nesting".to_string(), /* severity= */ Severity.WARNING, /* name= */ func.name, /* metric_value= */ func.nesting_depth, /* message= */ format!("Function '{}' has nesting depth {} (limit: {})", func.name, func.nesting_depth, t["deep_nesting".to_string()]), /* suggestion= */ "Flatten with early returns or extract helper functions.".to_string()));
        }
        if func.complexity >= t["very_high_complexity".to_string()] {
            self.smells.push(SmellIssue(/* file_path= */ func.file_path, /* line= */ func.line_start, /* end_line= */ func.line_end, /* category= */ "very-high-complexity".to_string(), /* severity= */ Severity.CRITICAL, /* name= */ func.name, /* metric_value= */ func.complexity, /* message= */ format!("Function '{}' has cyclomatic complexity {} (limit: {})", func.name, func.complexity, t["very_high_complexity".to_string()]), /* suggestion= */ "Decompose into smaller, single-responsibility functions.".to_string()));
        } else if func.complexity >= t["high_complexity".to_string()] {
            self.smells.push(SmellIssue(/* file_path= */ func.file_path, /* line= */ func.line_start, /* end_line= */ func.line_end, /* category= */ "high-complexity".to_string(), /* severity= */ Severity.WARNING, /* name= */ func.name, /* metric_value= */ func.complexity, /* message= */ format!("Function '{}' has cyclomatic complexity {} (limit: {})", func.name, func.complexity, t["high_complexity".to_string()]), /* suggestion= */ "Simplify branching logic. Consider lookup tables or strategy pattern.".to_string()));
        }
        if func.parameters.len() >= t["too_many_params".to_string()] {
            self.smells.push(SmellIssue(/* file_path= */ func.file_path, /* line= */ func.line_start, /* end_line= */ func.line_end, /* category= */ "too-many-params".to_string(), /* severity= */ Severity.WARNING, /* name= */ func.name, /* metric_value= */ func.parameters.len(), /* message= */ format!("Function '{}' has {} parameters (limit: {})", func.name, func.parameters.len(), t["too_many_params".to_string()]), /* suggestion= */ "Group related parameters into a dataclass or config object.".to_string()));
        }
        if (!func.docstring && func.size_lines >= t["missing_docstring_size".to_string()] && !func.name.starts_with(&*"_".to_string())) {
            self.smells.push(SmellIssue(/* file_path= */ func.file_path, /* line= */ func.line_start, /* end_line= */ func.line_end, /* category= */ "missing-docstring".to_string(), /* severity= */ Severity.INFO, /* name= */ func.name, /* metric_value= */ func.size_lines, /* message= */ format!("Function '{}' ({} lines) has no docstring", func.name, func.size_lines), /* suggestion= */ "Add a docstring explaining purpose, parameters, and return value.".to_string()));
        }
        let mut return_count = (func.code.iter().filter(|v| **v == "\n    return ".to_string()).count() + func.code.iter().filter(|v| **v == "\nreturn ".to_string()).count());
        if return_count >= t["too_many_returns".to_string()] {
            self.smells.push(SmellIssue(/* file_path= */ func.file_path, /* line= */ func.line_start, /* end_line= */ func.line_end, /* category= */ "too-many-returns".to_string(), /* severity= */ Severity.WARNING, /* name= */ func.name, /* metric_value= */ return_count, /* message= */ format!("Function '{}' has {} return statements (limit: {})", func.name, return_count, t["too_many_returns".to_string()]), /* suggestion= */ "Consolidate exit points. Consider a result variable.".to_string()));
        }
        if (func.return_type && func.return_type.to_lowercase().contains(&"bool".to_string()) && !("is_".to_string(), "has_".to_string(), "can_".to_string(), "should_".to_string(), "check_".to_string(), "validate_".to_string(), "contains_".to_string(), "exists_".to_string()).iter().map(|p| func.name.starts_with(&*p)).collect::<Vec<_>>().iter().any(|v| *v)) {
            self.smells.push(SmellIssue(/* file_path= */ func.file_path, /* line= */ func.line_start, /* end_line= */ func.line_end, /* category= */ "boolean-blindness".to_string(), /* severity= */ Severity.INFO, /* name= */ func.name, /* metric_value= */ 0, /* message= */ format!("Function '{}' returns bool but name doesn't indicate a question", func.name), /* suggestion= */ "Rename to is_/has_/can_/should_/check_ prefix for clarity.".to_string()));
        }
    }
    pub fn _check_class(&mut self, cls: ClassRecord) -> () {
        let mut t = self.thresholds;
        if cls.method_count >= t["god_class".to_string()] {
            self.smells.push(SmellIssue(/* file_path= */ cls.file_path, /* line= */ cls.line_start, /* end_line= */ cls.line_end, /* category= */ "god-class".to_string(), /* severity= */ Severity.CRITICAL, /* name= */ cls.name, /* metric_value= */ cls.method_count, /* message= */ format!("Class '{}' has {} methods (limit: {})", cls.name, cls.method_count, t["god_class".to_string()]), /* suggestion= */ "Split into smaller classes with single responsibility. Consider delegation or mixins.".to_string()));
        }
        if cls.size_lines >= t["large_class".to_string()] {
            self.smells.push(SmellIssue(/* file_path= */ cls.file_path, /* line= */ cls.line_start, /* end_line= */ cls.line_end, /* category= */ "large-class".to_string(), /* severity= */ Severity.WARNING, /* name= */ cls.name, /* metric_value= */ cls.size_lines, /* message= */ format!("Class '{}' is {} lines (limit: {})", cls.name, cls.size_lines, t["large_class".to_string()]), /* suggestion= */ "Extract logical groups of methods into separate classes or modules.".to_string()));
        }
        if (!cls.docstring && cls.size_lines > 30) {
            self.smells.push(SmellIssue(/* file_path= */ cls.file_path, /* line= */ cls.line_start, /* end_line= */ cls.line_end, /* category= */ "missing-class-docstring".to_string(), /* severity= */ Severity.INFO, /* name= */ cls.name, /* metric_value= */ cls.size_lines, /* message= */ format!("Class '{}' ({} lines) has no docstring", cls.name, cls.size_lines), /* suggestion= */ "Add a docstring explaining the class's responsibility.".to_string()));
        }
        if (cls.method_count <= 3 && cls.has_init && !cls.base_classes) {
            self.smells.push(SmellIssue(/* file_path= */ cls.file_path, /* line= */ cls.line_start, /* end_line= */ cls.line_end, /* category= */ "dataclass-candidate".to_string(), /* severity= */ Severity.INFO, /* name= */ cls.name, /* metric_value= */ cls.method_count, /* message= */ format!("Class '{}' has only {} methods — consider @dataclass", cls.name, cls.method_count), /* suggestion= */ "If this class mainly holds data, convert to @dataclass for less boilerplate.".to_string()));
        }
    }
    /// Send the worst smells to LLM for detailed analysis.
    pub fn enrich_with_llm(&mut self, llm: LLMHelper, max_calls: i64) -> Result<()> {
        // Send the worst smells to LLM for detailed analysis.
        let mut critical_smells = self.smells.iter().filter(|s| ((Severity.CRITICAL, Severity.WARNING).contains(&s.severity) && !s.llm_analysis)).map(|s| s).collect::<Vec<_>>()[..max_calls];
        if !critical_smells {
            return;
        }
        logger.info(format!("Enriching {} smells with LLM...", critical_smells.len()));
        for smell in critical_smells.iter() {
            let mut prompt = format!("You are a Senior Python Architect reviewing code.\nIssue: {}\nCategory: {}\nFile: {}:{}\n\nGive a 2-3 sentence actionable recommendation to fix this. Be specific about WHAT to extract or refactor.\n\nRecommendation:", smell.message, smell.category, smell.file_path, smell.line);
            // try:
            {
                let mut response = llm.query_sync(prompt, /* max_tokens= */ 150);
                smell.llm_analysis = response.trim().to_string();
            }
            // except Exception as e:
        }
    }
    /// Return a summary dict of all smells.
    pub fn summary(&mut self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Return a summary dict of all smells.
        let mut by_severity = Counter(self.smells.iter().map(|s| s.severity).collect::<Vec<_>>());
        let mut by_category = Counter(self.smells.iter().map(|s| s.category).collect::<Vec<_>>());
        let mut by_file = Counter(self.smells.iter().map(|s| s.file_path).collect::<Vec<_>>());
        HashMap::from([("total".to_string(), self.smells.len()), ("critical".to_string(), by_severity.get(&Severity.CRITICAL).cloned().unwrap_or(0)), ("warning".to_string(), by_severity.get(&Severity.WARNING).cloned().unwrap_or(0)), ("info".to_string(), by_severity.get(&Severity.INFO).cloned().unwrap_or(0)), ("by_category".to_string(), /* dict(by_category) */ HashMap::new()), ("worst_files".to_string(), /* dict(by_file.most_common(10)) */ HashMap::new())])
    }
}

/// Cross-file function similarity detector.
/// 
/// Three-stage pipeline:
/// 1. Exact hash match  → identical code
/// 2. Token cosine + SequenceMatcher pre-filter → near-duplicates
/// 3. Optional LLM confirmation → semantic duplicates
#[derive(Debug, Clone)]
pub struct DuplicateFinder {
    pub groups: Vec<DuplicateGroup>,
    pub _tokens: HashMap<String, Counter>,
}

impl DuplicateFinder {
    pub fn new() -> Self {
        Self {
            groups: Vec::new(),
            _tokens: HashMap::new(),
        }
    }
    /// Find duplicate/similar function groups.
    pub fn find(&mut self, functions: Vec<FunctionRecord>, cross_file_only: bool) -> Vec<DuplicateGroup> {
        // Find duplicate/similar function groups.
        self.groups = vec![];
        let mut group_id = 0;
        for func in functions.iter() {
            let mut text = vec![func.name, (func.docstring || "".to_string()), func.parameters.join(&" ".to_string()), (func.return_type || "".to_string()), func.calls_to.join(&" ".to_string()), (func.code || "".to_string())].join(&" ".to_string());
            self._tokens[func.key] = _term_freq(tokenize(text));
        }
        let mut hash_groups = defaultdict(list);
        for func in functions.iter() {
            if !self._BOILERPLATE.contains(&func.name) {
                hash_groups[&func.code_hash].push(func);
            }
        }
        let mut seen_keys = HashSet::new();
        for (code_hash, group) in hash_groups.iter().iter() {
            if group.len() < 2 {
                continue;
            }
            if cross_file_only {
                let mut files = group.iter().map(|f| f.file_path).collect::<HashSet<_>>();
                if files.len() < 2 {
                    continue;
                }
            }
            self.groups.push(DuplicateGroup(/* group_id= */ group_id, /* similarity_type= */ "exact".to_string(), /* avg_similarity= */ 1.0_f64, /* functions= */ group.iter().map(|f| HashMap::from([("key".to_string(), f.key), ("name".to_string(), f.name), ("file".to_string(), f.file_path), ("line".to_string(), f.line_start), ("size".to_string(), f.size_lines), ("similarity".to_string(), 1.0_f64)])).collect::<Vec<_>>()));
            seen_keys.extend(group.iter().map(|f| f.key).collect::<Vec<_>>());
            group_id += 1;
        }
        let mut func_list = functions.iter().filter(|f| (!seen_keys.contains(&f.key) && !self._BOILERPLATE.contains(&f.name) && f.size_lines >= 5)).map(|f| f).collect::<Vec<_>>();
        let mut candidates = vec![];
        for (i, f1) in func_list.iter().enumerate().iter() {
            for f2 in func_list[(i + 1)..].iter() {
                if (cross_file_only && f1.file_path == f2.file_path) {
                    continue;
                }
                let mut ratio = (f1.size_lines.min(f2.size_lines) / f1.size_lines.max(f2.size_lines));
                if ratio < self.SIZE_RATIO_MIN {
                    continue;
                }
                let mut tok_sim = cosine_similarity(self._tokens.get(&f1.key).cloned().unwrap_or(Counter()), self._tokens.get(&f2.key).cloned().unwrap_or(Counter()));
                if tok_sim >= self.TOKEN_PREFILTER {
                    candidates.push((f1, f2, tok_sim));
                }
            }
        }
        logger.info(format!("Duplicate pre-filter: {} candidates from {} functions", candidates.len(), func_list.len()));
        let mut near_pairs = vec![];
        for (f1, f2, tok_sim) in candidates.iter() {
            let mut sim = code_similarity(f1.code, f2.code);
            if sim >= self.NEAR_DUP_THRESHOLD {
                near_pairs.push((f1, f2, sim));
            }
        }
        let mut parent = HashMap::new();
        let find_root = |x| {
            while parent.get(&x).cloned().unwrap_or(x) != x {
                parent[x] = parent.get(&parent[&x]).cloned().unwrap_or(parent[&x]);
                let mut x = parent[&x];
            }
            x
        };
        let union = |a, b| {
            let (mut ra, mut rb) = (find_root(a), find_root(b));
            if ra != rb {
                parent[ra] = rb;
            }
        };
        for (f1, f2, sim) in near_pairs.iter() {
            parent.entry(f1.key).or_insert(f1.key);
            parent.entry(f2.key).or_insert(f2.key);
            union(f1.key, f2.key);
        }
        let mut clusters = defaultdict(list);
        let mut func_map = functions.iter().map(|f| (f.key, f)).collect::<HashMap<_, _>>();
        let mut pair_sims = near_pairs.iter().map(|(f1, f2, sim)| ((f1.key, f2.key), sim)).collect::<HashMap<_, _>>();
        for (f1, f2, sim) in near_pairs.iter() {
            let mut root = find_root(f1.key);
            if !clusters[&root].iter().map(|x| x[0].key == f1.key).collect::<Vec<_>>().iter().any(|v| *v) {
                clusters[&root].push((f1, 1.0_f64));
            }
            if !clusters[&root].iter().map(|x| x[0].key == f2.key).collect::<Vec<_>>().iter().any(|v| *v) {
                clusters[&root].push((f2, sim));
            }
        }
        for (root_key, members) in clusters.iter().iter() {
            if members.len() < 2 {
                continue;
            }
            let mut sims = members.iter().map(|(_, s)| s).collect::<Vec<_>>();
            let mut avg = if sims { (sims.iter().sum::<i64>() / sims.len()) } else { 0 };
            self.groups.push(DuplicateGroup(/* group_id= */ group_id, /* similarity_type= */ "near".to_string(), /* avg_similarity= */ ((avg as f64) * 10f64.powi(3)).round() / 10f64.powi(3), /* functions= */ members.iter().map(|(f, sim)| HashMap::from([("key".to_string(), f.key), ("name".to_string(), f.name), ("file".to_string(), f.file_path), ("line".to_string(), f.line_start), ("size".to_string(), f.size_lines), ("similarity".to_string(), ((sim as f64) * 10f64.powi(3)).round() / 10f64.powi(3)), ("signature".to_string(), f.signature)])).collect::<Vec<_>>()));
            group_id += 1;
        }
        self.groups.sort(/* key= */ |g| g.avg_similarity, /* reverse= */ true);
        self.groups
    }
    /// Ask LLM if near-duplicates should be merged.
    pub fn enrich_with_llm(&mut self, llm: LLMHelper, functions: Vec<FunctionRecord>, max_calls: i64) -> Result<()> {
        // Ask LLM if near-duplicates should be merged.
        let mut func_map = functions.iter().map(|f| (f.key, f)).collect::<HashMap<_, _>>();
        let mut enriched = 0;
        for group in self.groups.iter() {
            if enriched >= max_calls {
                break;
            }
            if group.similarity_type == "exact".to_string() {
                group.merge_suggestion = "Identical code — extract to a shared module.".to_string();
                continue;
            }
            if group.functions.len() < 2 {
                continue;
            }
            let mut flist = group.functions[..2];
            let mut f1 = func_map.get(&flist[0]["key".to_string()]).cloned();
            let mut f2 = func_map.get(&flist[1]["key".to_string()]).cloned();
            if (!f1 || !f2) {
                continue;
            }
            let mut prompt = format!("You are a refactoring expert.\nFunction A: {} ({}:{})\n```python\n{}\n```\n\nFunction B: {} ({}:{})\n```python\n{}\n```\n\nShould these be merged? If yes, suggest a unified function name and signature. If no, explain why they're different.\n\nAnswer (2-3 sentences):", f1.name, f1.file_path, f1.line_start, f1.code[..500], f2.name, f2.file_path, f2.line_start, f2.code[..500]);
            // try:
            {
                let mut response = llm.query_sync(prompt, /* max_tokens= */ 200);
                group.merge_suggestion = response.trim().to_string();
                enriched += 1;
            }
            // except Exception as e:
        }
    }
    /// Return a summary of duplicate findings.
    pub fn summary(&mut self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Return a summary of duplicate findings.
        let mut exact = self.groups.iter().filter(|g| g.similarity_type == "exact".to_string()).map(|g| g).collect::<Vec<_>>();
        let mut near = self.groups.iter().filter(|g| g.similarity_type == "near".to_string()).map(|g| g).collect::<Vec<_>>();
        let mut total_funcs = self.groups.iter().map(|g| g.functions.len()).collect::<Vec<_>>().iter().sum::<i64>();
        HashMap::from([("total_groups".to_string(), self.groups.len()), ("exact_duplicates".to_string(), exact.len()), ("near_duplicates".to_string(), near.len()), ("total_functions_involved".to_string(), total_funcs), ("avg_similarity".to_string(), if self.groups { (((self.groups.iter().map(|g| g.avg_similarity).collect::<Vec<_>>().iter().sum::<i64>() / self.groups.len()) as f64) * 10f64.powi(3)).round() / 10f64.powi(3) } else { 0 })])
    }
}

/// Analyzes duplicate clusters and suggests shared library extraction.
/// 
/// Works in two modes:
/// - Heuristic: Groups by function name patterns and cross-file spread
/// - LLM: Generates unified API proposals
#[derive(Debug, Clone)]
pub struct LibraryAdvisor {
    pub suggestions: Vec<LibrarySuggestion>,
}

impl LibraryAdvisor {
    pub fn new() -> Self {
        Self {
            suggestions: Vec::new(),
        }
    }
    /// Generate library extraction suggestions from duplicate analysis.
    pub fn analyze(&mut self, duplicate_groups: Vec<DuplicateGroup>, functions: Vec<FunctionRecord>) -> Vec<LibrarySuggestion> {
        // Generate library extraction suggestions from duplicate analysis.
        self.suggestions = vec![];
        let mut func_map = functions.iter().map(|f| (f.key, f)).collect::<HashMap<_, _>>();
        for group in duplicate_groups.iter() {
            if group.functions.len() < self.MIN_GROUP_SIZE {
                continue;
            }
            let mut files = group.functions.iter().map(|f| f["file".to_string()]).collect::<HashSet<_>>();
            if files.len() < self.MIN_CROSS_FILE_SPREAD {
                continue;
            }
            let mut best = group.functions.max(/* key= */ |f| (if (func_map.get(&f["key".to_string()]).cloned().unwrap_or(None) && func_map[f["key".to_string()]].docstring) { 1 } else { 0 }, f.get(&"size".to_string()).cloned().unwrap_or(0)));
            let mut best_func = func_map.get(&best["key".to_string()]).cloned();
            if !best_func {
                continue;
            }
            let mut names = group.functions.iter().map(|f| f["name".to_string()]).collect::<Vec<_>>();
            let mut module_name = self._suggest_module_name(names);
            self.suggestions.push(LibrarySuggestion(/* module_name= */ module_name, /* description= */ format!("Consolidate {} similar implementations of '{}'", names.len(), names[0]), /* functions= */ group.functions.iter().map(|f| HashMap::from([("name".to_string(), f["name".to_string()]), ("file".to_string(), f["file".to_string()]), ("line".to_string(), f["line".to_string()]), ("similarity".to_string(), f.get(&"similarity".to_string()).cloned().unwrap_or(1.0_f64))])).collect::<Vec<_>>(), /* unified_api= */ best_func.signature, /* rationale= */ format!("Found in {} files ({}{}). Average similarity: {:.0%}. {}", files.len(), { let mut v = files.clone(); v.sort(); v }[..3].join(&", ".to_string()), if files.len() > 3 { "...".to_string() } else { "".to_string() }, group.avg_similarity, if group.merge_suggestion { ("Merge suggestion: ".to_string() + group.merge_suggestion) } else { "".to_string() })));
        }
        let mut name_files = defaultdict(list);
        for func in functions.iter() {
            if !DuplicateFinder._BOILERPLATE.contains(&func.name) {
                name_files[&func.name].push(func);
            }
        }
        let mut already_suggested = self.suggestions.iter().map(|s| f["name".to_string()]).collect::<HashSet<_>>();
        for (name, funcs) in name_files.iter().iter() {
            if already_suggested.contains(&name) {
                continue;
            }
            let mut files = funcs.iter().map(|f| f.file_path).collect::<HashSet<_>>();
            if files.len() < self.MIN_CROSS_FILE_SPREAD {
                continue;
            }
            if funcs.len() < self.MIN_GROUP_SIZE {
                continue;
            }
            let mut best_func = funcs.max(/* key= */ |f| (if f.docstring { 1 } else { 0 }, f.size_lines));
            let mut module_name = self._suggest_module_name(vec![name]);
            self.suggestions.push(LibrarySuggestion(/* module_name= */ module_name, /* description= */ format!("Function '{}' reimplemented in {} files", name, files.len()), /* functions= */ funcs.iter().map(|f| HashMap::from([("name".to_string(), f.name), ("file".to_string(), f.file_path), ("line".to_string(), f.line_start), ("similarity".to_string(), 1.0_f64)])).collect::<Vec<_>>(), /* unified_api= */ best_func.signature, /* rationale= */ format!("Identical name across: {}. Consider extracting to a shared utilities module.", { let mut v = files.clone(); v.sort(); v }[..4].join(&", ".to_string()))));
        }
        self.suggestions.sort(/* key= */ |s| s.functions.len(), /* reverse= */ true);
        self.suggestions
    }
    /// LLM generates unified API proposals for each suggestion.
    pub fn enrich_with_llm(&mut self, llm: LLMHelper, functions: Vec<FunctionRecord>, max_calls: i64) -> Result<()> {
        // LLM generates unified API proposals for each suggestion.
        let mut func_map = functions.iter().map(|f| (f.key, f)).collect::<HashMap<_, _>>();
        let mut enriched = 0;
        for suggestion in self.suggestions.iter() {
            if enriched >= max_calls {
                break;
            }
            let mut snippets = vec![];
            for finfo in suggestion.functions[..3].iter() {
                let mut key = format!("{}.{}", PathBuf::from(finfo["file".to_string()]).file_stem().unwrap_or_default().to_str().unwrap_or(""), finfo["name".to_string()]);
                let mut func = func_map.get(&key).cloned();
                if func {
                    snippets.push(format!("# From {}\n{}", func.file_path, func.code[..400]));
                }
            }
            if !snippets {
                continue;
            }
            let mut prompt = ((format!("You are designing a shared Python library.\nModule name: {}\n\nThese similar functions exist across multiple files:\n\n", suggestion.module_name) + snippets.join(&"\n---\n".to_string())) + "\n\nDesign a unified function that covers all use cases.\nOutput:\n1. Function signature (def ...)\n2. One-line docstring\n3. Key design decisions (2 sentences)\n".to_string());
            // try:
            {
                let mut response = llm.query_sync(prompt, /* max_tokens= */ 250);
                suggestion.unified_api = response.trim().to_string();
                enriched += 1;
            }
            // except Exception as e:
        }
    }
    /// Suggest a module name from function naming patterns.
    pub fn _suggest_module_name(&self, func_names: Vec<String>) -> String {
        // Suggest a module name from function naming patterns.
        let mut name = func_names[0].to_lowercase();
        let mut patterns = HashMap::from([("utils".to_string(), vec!["format".to_string(), "convert".to_string(), "parse".to_string(), "clean".to_string(), "normalize".to_string(), "strip".to_string()]), ("io_helpers".to_string(), vec!["read".to_string(), "write".to_string(), "load".to_string(), "save".to_string(), "dump".to_string(), "export".to_string(), "import".to_string()]), ("validators".to_string(), vec!["validate".to_string(), "check".to_string(), "verify".to_string(), "assert".to_string(), "ensure".to_string()]), ("search".to_string(), vec!["search".to_string(), "find".to_string(), "query".to_string(), "lookup".to_string(), "filter".to_string(), "match".to_string()]), ("config".to_string(), vec!["config".to_string(), "setting".to_string(), "option".to_string(), "default".to_string(), "setup".to_string()]), ("cache".to_string(), vec!["cache".to_string(), "store".to_string(), "memo".to_string(), "persist".to_string()]), ("display".to_string(), vec!["render".to_string(), "display".to_string(), "show".to_string(), "print".to_string(), "format".to_string(), "draw".to_string()]), ("network".to_string(), vec!["fetch".to_string(), "request".to_string(), "download".to_string(), "upload".to_string(), "connect".to_string()])]);
        for (module, keywords) in patterns.iter().iter() {
            if keywords.iter().map(|kw| name.contains(&kw)).collect::<Vec<_>>().iter().any(|v| *v) {
                module
            }
        }
        "shared_utils".to_string()
    }
    pub fn summary(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        HashMap::from([("total_suggestions".to_string(), self.suggestions.len()), ("total_functions".to_string(), self.suggestions.iter().map(|s| s.functions.len()).collect::<Vec<_>>().iter().sum::<i64>()), ("modules_proposed".to_string(), self.suggestions.iter().map(|s| s.module_name).collect::<Vec<_>>().into_iter().collect::<HashSet<_>>().into_iter().collect::<Vec<_>>())])
    }
}

/// Generates an interactive HTML graph with:
/// - Health-colored file nodes (green/yellow/red based on smell count)
/// - Enriched tooltips (smells, duplicates)
/// - Duplicate connections shown as edges
#[derive(Debug, Clone)]
pub struct SmartGraph {
    pub nodes: Vec<HashMap>,
    pub edges: Vec<HashMap>,
    pub _smells: Vec<SmellIssue>,
    pub _duplicates: Vec<DuplicateGroup>,
    pub _root_name: String,
}

impl SmartGraph {
    pub fn new() -> Self {
        Self {
            nodes: Vec::new(),
            edges: Vec::new(),
            _smells: Vec::new(),
            _duplicates: Vec::new(),
            _root_name: String::new(),
        }
    }
    /// Build graph data from analysis results.
    pub fn build(&mut self, functions: Vec<FunctionRecord>, smells: Vec<SmellIssue>, duplicates: Vec<DuplicateGroup>, root: PathBuf) -> () {
        // Build graph data from analysis results.
        self.nodes = vec![];
        self.edges = vec![];
        self._smells = smells.into_iter().collect::<Vec<_>>();
        self._duplicates = duplicates.into_iter().collect::<Vec<_>>();
        self._root_name = root.name;
        let mut file_smells = defaultdict(list);
        for s in smells.iter() {
            file_smells[&s.file_path].push(s);
        }
        let mut file_funcs = Counter(functions.iter().map(|f| f.file_path).collect::<Vec<_>>());
        let mut all_files = { let mut v = functions.iter().map(|f| f.file_path).collect::<Vec<_>>().into_iter().collect::<HashSet<_>>().clone(); v.sort(); v };
        let mut node_ids = HashMap::new();
        for (i, fpath) in all_files.iter().enumerate().iter() {
            let mut fsmells = file_smells.get(&fpath).cloned().unwrap_or(vec![]);
            let mut n_critical = fsmells.iter().filter(|s| s.severity == Severity.CRITICAL).map(|s| 1).collect::<Vec<_>>().iter().sum::<i64>();
            let mut n_warning = fsmells.iter().filter(|s| s.severity == Severity.WARNING).map(|s| 1).collect::<Vec<_>>().iter().sum::<i64>();
            let mut n_info = fsmells.iter().filter(|s| s.severity == Severity.INFO).map(|s| 1).collect::<Vec<_>>().iter().sum::<i64>();
            if n_critical > 0 {
                let mut color = "#e74c3c".to_string();
                let mut health = "critical".to_string();
            } else if n_warning > 0 {
                let mut color = "#f39c12".to_string();
                let mut health = "warning".to_string();
            } else {
                let mut color = "#2ecc71".to_string();
                let mut health = "healthy".to_string();
            }
            let mut tooltip_lines = vec![format!("<b>{}</b>", fpath)];
            tooltip_lines.push(format!("Functions: {}", file_funcs.get(&fpath).cloned().unwrap_or(0)));
            if fsmells {
                tooltip_lines.push(format!("<br/><b>Issues:</b>"));
                for s in fsmells[..5].iter() {
                    let mut html_icon = Severity._ICONS_UNICODE.get(&s.severity).cloned().unwrap_or("?".to_string());
                    tooltip_lines.push(format!("  {} {}: {}", html_icon, s.category, s.name));
                }
                if fsmells.len() > 5 {
                    tooltip_lines.push(format!("  ...+{} more", (fsmells.len() - 5)));
                }
            }
            node_ids[fpath] = i;
            self.nodes.push(HashMap::from([("id".to_string(), i), ("label".to_string(), PathBuf::from(fpath).name), ("title".to_string(), tooltip_lines.join(&"<br/>".to_string())), ("color".to_string(), color), ("shape".to_string(), "dot".to_string()), ("size".to_string(), 10.max(40.min((file_funcs.get(&fpath).cloned().unwrap_or(1) * 3)))), ("health".to_string(), health), ("full_path".to_string(), fpath)]));
        }
        for group in duplicates.iter() {
            let mut files_in_group = group.functions.iter().map(|f| f["file".to_string()]).collect::<Vec<_>>().into_iter().collect::<HashSet<_>>().into_iter().collect::<Vec<_>>();
            for (i, f1) in files_in_group.iter().enumerate().iter() {
                for f2 in files_in_group[(i + 1)..].iter() {
                    if (node_ids.contains(&f1) && node_ids.contains(&f2)) {
                        self.edges.push(HashMap::from([("from".to_string(), node_ids[&f1]), ("to".to_string(), node_ids[&f2]), ("label".to_string(), format!("{:.0%}", group.avg_similarity)), ("color".to_string(), if group.similarity_type == "near".to_string() { "#e67e22".to_string() } else { "#e74c3c".to_string() }), ("dashes".to_string(), group.similarity_type == "near".to_string()), ("title".to_string(), format!("Duplicate: {}", group.functions[..3].iter().map(|f| f["name".to_string()]).collect::<Vec<_>>().join(&", ".to_string())))]));
                    }
                }
            }
        }
    }
    /// Write the interactive graph with side-panel lists to an HTML file.
    pub fn write_html(&mut self, output_path: PathBuf) -> () {
        // Write the interactive graph with side-panel lists to an HTML file.
        let mut nodes_json = serde_json::to_string(&self.nodes).unwrap();
        let mut edges_json = serde_json::to_string(&self.edges).unwrap();
        let mut n_healthy = self.nodes.iter().filter(|n| n.get(&"health".to_string()).cloned() == "healthy".to_string()).map(|n| 1).collect::<Vec<_>>().iter().sum::<i64>();
        let mut n_warning = self.nodes.iter().filter(|n| n.get(&"health".to_string()).cloned() == "warning".to_string()).map(|n| 1).collect::<Vec<_>>().iter().sum::<i64>();
        let mut n_critical = self.nodes.iter().filter(|n| n.get(&"health".to_string()).cloned() == "critical".to_string()).map(|n| 1).collect::<Vec<_>>().iter().sum::<i64>();
        let mut dup_rows = vec![];
        for g in self._duplicates.iter() {
            dup_rows.push(HashMap::from([("id".to_string(), g.group_id), ("type".to_string(), g.similarity_type), ("sim".to_string(), ((g.avg_similarity * 100) as f64).round()), ("funcs".to_string(), g.functions.iter().map(|f| HashMap::from([("name".to_string(), f["name".to_string()]), ("file".to_string(), f["file".to_string()]), ("line".to_string(), f.get(&"line".to_string()).cloned().unwrap_or(0))])).collect::<Vec<_>>()), ("merge".to_string(), (g.merge_suggestion || "".to_string()))]));
        }
        let mut dup_json = serde_json::to_string(&dup_rows).unwrap();
        let mut smell_rows = vec![];
        for s in self._smells.iter() {
            smell_rows.push(HashMap::from([("sev".to_string(), s.severity), ("cat".to_string(), s.category), ("name".to_string(), s.name), ("file".to_string(), s.file_path), ("line".to_string(), s.line), ("msg".to_string(), s.message), ("sug".to_string(), s.suggestion)]));
        }
        let mut smell_json = serde_json::to_string(&smell_rows).unwrap();
        let mut html = format!("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"UTF-8\">\n<title>X-RAY Claude v{} — Smart Code Graph</title>\n<script src=\"https://unpkg.com/vis-network/standalone/umd/vis-network.min.js\"></script>\n<style>\n  * {{ margin: 0; padding: 0; box-sizing: border-box; }}\n  body {{ background: #1a1a2e; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; overflow: hidden; }}\n\n  /* ── Header ── */\n  #header {{\n    height: 52px; padding: 0 20px; background: linear-gradient(135deg, #0f3460 0%, #16213e 100%);\n    display: flex; justify-content: space-between; align-items: center;\n    box-shadow: 0 2px 10px rgba(0,0,0,.5); z-index: 100; position: relative;\n  }}\n  #header h1 {{ font-size: 17px; color: #00d4ff; white-space: nowrap; }}\n  .tab-bar {{ display: flex; gap: 6px; }}\n  .tab-btn {{\n    padding: 6px 16px; background: rgba(255,255,255,.08); border: none;\n    color: #ccc; cursor: pointer; border-radius: 5px; font-size: 13px; font-weight: 500;\n    transition: .2s;\n  }}\n  .tab-btn:hover {{ background: rgba(255,255,255,.18); color: #fff; }}\n  .tab-btn.active {{ background: #00d4ff; color: #000; }}\n\n  /* ── Panels ── */\n  .panel {{ display: none; width: 100%; height: calc(100vh - 52px); }}\n  .panel.active {{ display: flex; }}\n\n  /* Graph panel */\n  #panel-graph {{ position: relative; }}\n  #graph {{ width: 100%; height: 100%; }}\n  .graph-legend {{\n    position: absolute; bottom: 16px; right: 16px;\n    background: rgba(0,0,0,.82); padding: 12px 16px; border-radius: 8px;\n    font-size: 12px; line-height: 1.8;\n  }}\n  .ldot {{ width: 11px; height: 11px; border-radius: 50%; display: inline-block; margin-right: 6px; vertical-align: middle; }}\n\n  /* List panels (duplicates + smells) */\n  .list-panel {{ flex-direction: column; overflow: hidden; }}\n  .list-panel .toolbar {{\n    padding: 10px 20px; background: #16213e; display: flex; gap: 12px; align-items: center;\n    flex-shrink: 0;\n  }}\n  .search-input {{\n    flex: 1; max-width: 500px; padding: 8px 12px; background: rgba(255,255,255,.08);\n    border: 1px solid #333; border-radius: 5px; color: #fff; font-size: 13px;\n  }}\n  .search-input:focus {{ outline: none; border-color: #00d4ff; }}\n  .stat-chip {{\n    padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;\n  }}\n  .stat-chip.exact {{ background: #e74c3c; }}\n  .stat-chip.near {{ background: #e67e22; }}\n  .stat-chip.crit {{ background: #e74c3c; }}\n  .stat-chip.warn {{ background: #f39c12; color: #111; }}\n  .stat-chip.info {{ background: #2ecc71; color: #111; }}\n\n  .list-scroll {{ flex: 1; overflow-y: auto; padding: 0 20px 20px 20px; }}\n\n  /* Duplicate group cards */\n  .dup-group {{\n    margin: 12px 0; background: rgba(255,255,255,.04); border-radius: 8px;\n    border-left: 4px solid #e74c3c; overflow: hidden;\n  }}\n  .dup-group.near {{ border-left-color: #e67e22; }}\n  .dup-group-header {{\n    padding: 10px 14px; display: flex; justify-content: space-between; align-items: center;\n    cursor: pointer; user-select: none;\n  }}\n  .dup-group-header:hover {{ background: rgba(255,255,255,.04); }}\n  .dup-type {{ font-weight: 700; font-size: 11px; text-transform: uppercase; letter-spacing: .5px; }}\n  .dup-type.exact {{ color: #e74c3c; }}\n  .dup-type.near {{ color: #e67e22; }}\n  .dup-sim {{ color: #aaa; font-size: 12px; }}\n  .dup-funcs {{ padding: 0 14px 10px 14px; }}\n  .dup-func {{\n    display: flex; gap: 10px; padding: 4px 0; font-size: 13px; align-items: baseline;\n  }}\n  .func-name {{ font-family: 'Cascadia Code', 'Fira Code', monospace; color: #00d4ff; font-weight: 600; min-width: 200px; }}\n  .func-file {{ color: #888; font-size: 12px; }}\n  .dup-merge {{ padding: 6px 14px 10px 14px; font-size: 12px; color: #f39c12; font-style: italic; }}\n\n  /* Smell table */\n  .smell-table {{ width: 100%; border-collapse: collapse; }}\n  .smell-table th {{\n    position: sticky; top: 0; background: #16213e; padding: 10px 12px;\n    text-align: left; font-size: 12px; font-weight: 600; cursor: pointer; user-select: none;\n    border-bottom: 2px solid #0f3460;\n  }}\n  .smell-table th:hover {{ background: #1a4d7a; }}\n  .smell-table td {{ padding: 8px 12px; font-size: 13px; border-bottom: 1px solid rgba(255,255,255,.06); }}\n  .smell-table tr:hover {{ background: rgba(0,212,255,.08); }}\n  .sev-badge {{\n    display: inline-block; padding: 2px 8px; border-radius: 10px;\n    font-size: 10px; font-weight: 700; text-transform: uppercase;\n  }}\n  .sev-badge.critical {{ background: #e74c3c; }}\n  .sev-badge.warning {{ background: #f39c12; color: #111; }}\n  .sev-badge.info {{ background: #2ecc71; color: #111; }}\n  .cat-cell {{ font-family: monospace; color: #00d4ff; }}\n  .msg-cell {{ color: #aaa; font-size: 12px; max-width: 350px; }}\n</style>\n</head>\n<body>\n\n<div id=\"header\">\n  <h1>&#x1F50D; X-RAY Claude v{} — {}</h1>\n  <div class=\"tab-bar\">\n    <button class=\"tab-btn active\" onclick=\"showTab('graph')\">&#x1F30D; Graph</button>\n    <button class=\"tab-btn\" onclick=\"showTab('dups')\">&#x1F534; Duplicates</button>\n    <button class=\"tab-btn\" onclick=\"showTab('smells')\">&#x1F9EA; Smells</button>\n  </div>\n</div>\n\n<!-- ── Graph Panel ── -->\n<div id=\"panel-graph\" class=\"panel active\">\n  <div id=\"graph\"></div>\n  <div class=\"graph-legend\">\n    <div><span class=\"ldot\" style=\"background:#2ecc71\"></span>Healthy ({})</div>\n    <div><span class=\"ldot\" style=\"background:#f39c12\"></span>Warnings ({})</div>\n    <div><span class=\"ldot\" style=\"background:#e74c3c\"></span>Critical ({})</div>\n    <div style=\"margin-top:6px;color:#e67e22;font-size:11px\">--- Duplicate links ({})</div>\n    <div style=\"margin-top:8px;color:#666;font-size:11px\">Scroll to zoom &middot; Drag to pan</div>\n  </div>\n</div>\n\n<!-- ── Duplicates Panel ── -->\n<div id=\"panel-dups\" class=\"panel list-panel\">\n  <div class=\"toolbar\">\n    <input class=\"search-input\" id=\"dupSearch\" placeholder=\"&#x1F50D; Search function name or file...\" oninput=\"filterDups()\">\n    <span class=\"stat-chip exact\" id=\"dupExactChip\"></span>\n    <span class=\"stat-chip near\" id=\"dupNearChip\"></span>\n  </div>\n  <div class=\"list-scroll\" id=\"dupList\"></div>\n</div>\n\n<!-- ── Smells Panel ── -->\n<div id=\"panel-smells\" class=\"panel list-panel\">\n  <div class=\"toolbar\">\n    <input class=\"search-input\" id=\"smellSearch\" placeholder=\"&#x1F50D; Search name, file, category...\" oninput=\"filterSmells()\">\n    <span class=\"stat-chip crit\" id=\"smCritChip\"></span>\n    <span class=\"stat-chip warn\" id=\"smWarnChip\"></span>\n    <span class=\"stat-chip info\" id=\"smInfoChip\"></span>\n  </div>\n  <div class=\"list-scroll\" id=\"smellList\">\n    <table class=\"smell-table\">\n      <thead><tr>\n        <th onclick=\"sortSmells(0)\">Sev</th>\n        <th onclick=\"sortSmells(1)\">Category</th>\n        <th onclick=\"sortSmells(2)\">Name</th>\n        <th onclick=\"sortSmells(3)\">File</th>\n        <th onclick=\"sortSmells(4)\">Line</th>\n        <th onclick=\"sortSmells(5)\">Issue</th>\n      </tr></thead>\n      <tbody id=\"smellBody\"></tbody>\n    </table>\n  </div>\n</div>\n\n<script>\n// ── Data ──\nconst nodesData = {};\nconst edgesData = {};\nconst dupData   = {};\nconst smellData = {};\n\n// ── Tab switching ──\nfunction showTab(name) {{\n  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));\n  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));\n  document.getElementById('panel-' + name).classList.add('active');\n  const idx = {{'graph':0,'dups':1,'smells':2}}[name];\n  document.querySelectorAll('.tab-btn')[idx].classList.add('active');\n}}\n\n// ── Graph ──\nconst container = document.getElementById('graph');\nconst network = new vis.Network(container,\n  {{ nodes: new vis.DataSet(nodesData), edges: new vis.DataSet(edgesData) }},\n  {{\n    physics: {{ solver:'barnesHut', barnesHut:{{ gravitationalConstant:-3000, springLength:150, damping:.3 }} }},\n    interaction: {{ hover:true, tooltipDelay:100 }},\n    edges: {{ width:2, font:{{ size:10, color:'#888' }} }},\n  }}\n);\n\n// ── Duplicates list ──\nconst dupExact = dupData.filter(g => g.type==='exact').length;\nconst dupNear  = dupData.filter(g => g.type==='near').length;\ndocument.getElementById('dupExactChip').textContent = dupExact + ' exact';\ndocument.getElementById('dupNearChip').textContent  = dupNear + ' near';\n\nfunction renderDups(data) {{\n  const el = document.getElementById('dupList');\n  if (!data.length) {{ el.innerHTML = '<p style=\"padding:20px;color:#888\">No duplicates match your search.</p>'; return; }}\n  let html = '';\n  data.forEach(g => {{\n    const cls = g.type === 'near' ? 'near' : '';\n    html += '<div class=\"dup-group ' + cls + '\">';\n    html += '<div class=\"dup-group-header\">';\n    html += '<span><span class=\"dup-type ' + g.type + '\">' + g.type + '</span> &nbsp;Group #' + g.id + ' &mdash; ' + g.funcs.length + ' functions</span>';\n    html += '<span class=\"dup-sim\">' + g.sim + '% similar</span>';\n    html += '</div>';\n    html += '<div class=\"dup-funcs\">';\n    g.funcs.forEach(f => {{\n      html += '<div class=\"dup-func\"><span class=\"func-name\">' + f.name + '</span><span class=\"func-file\">' + f.file + ':' + f.line + '</span></div>';\n    }});\n    html += '</div>';\n    if (g.merge) html += '<div class=\"dup-merge\">&#x1F4A1; ' + g.merge + '</div>';\n    html += '</div>';\n  }});\n  el.innerHTML = html;\n}}\nrenderDups(dupData);\n\nfunction filterDups() {{\n  const q = document.getElementById('dupSearch').value.toLowerCase();\n  if (!q) {{ renderDups(dupData); return; }}\n  renderDups(dupData.filter(g => g.funcs.some(f => f.name.toLowerCase().includes(q) || f.file.toLowerCase().includes(q))));\n}}\n\n// ── Smells table ──\nconst smCrit = smellData.filter(s => s.sev==='critical').length;\nconst smWarn = smellData.filter(s => s.sev==='warning').length;\nconst smInfo = smellData.filter(s => s.sev==='info').length;\ndocument.getElementById('smCritChip').textContent = smCrit + ' critical';\ndocument.getElementById('smWarnChip').textContent = smWarn + ' warning';\ndocument.getElementById('smInfoChip').textContent = smInfo + ' info';\n\nlet smellSorted = [...smellData];\nconst sevOrder = {{'critical':0,'warning':1,'info':2}};\n\nfunction renderSmells(data) {{\n  const tbody = document.getElementById('smellBody');\n  if (!data.length) {{ tbody.innerHTML = '<tr><td colspan=\"6\" style=\"padding:20px;color:#888\">No smells match.</td></tr>'; return; }}\n  tbody.innerHTML = data.map(s =>\n    '<tr>' +\n    '<td><span class=\"sev-badge ' + s.sev + '\">' + s.sev + '</span></td>' +\n    '<td class=\"cat-cell\">' + s.cat + '</td>' +\n    '<td style=\"font-weight:600\">' + s.name + '</td>' +\n    '<td style=\"color:#aaa;font-size:12px\">' + s.file + '</td>' +\n    '<td>' + s.line + '</td>' +\n    '<td class=\"msg-cell\">' + s.msg + '</td>' +\n    '</tr>'\n  ).join('');\n}}\nrenderSmells(smellSorted);\n\nlet smellSortDir = {{}};\nfunction sortSmells(col) {{\n  const keys = ['sev','cat','name','file','line','msg'];\n  const key = keys[col];\n  const dir = smellSortDir[col] === 'asc' ? 'desc' : 'asc';\n  smellSortDir = {{}}; smellSortDir[col] = dir;\n  smellSorted.sort((a,b) => {{\n    let av = key==='sev' ? sevOrder[a.sev] : (key==='line' ? a.line : a[key].toLowerCase());\n    let bv = key==='sev' ? sevOrder[b.sev] : (key==='line' ? b.line : b[key].toLowerCase());\n    if (av < bv) return dir==='asc' ? -1 : 1;\n    if (av > bv) return dir==='asc' ? 1 : -1;\n    return 0;\n  }});\n  renderSmells(smellSorted);\n}}\n\nfunction filterSmells() {{\n  const q = document.getElementById('smellSearch').value.toLowerCase();\n  if (!q) {{ renderSmells(smellSorted); return; }}\n  renderSmells(smellSorted.filter(s => s.name.toLowerCase().includes(q) || s.file.toLowerCase().includes(q) || s.cat.toLowerCase().includes(q)));\n}}\n</script>\n</body>\n</html>", __version__, __version__, self._root_name, n_healthy, n_warning, n_critical, self.edges.len(), nodes_json, edges_json, dup_json, smell_json);
        output_pathstd::fs::write(&html));
        logger.info(format!("Smart graph written to {}", output_path));
    }
}

/// Detect whether the current stdout can handle full Unicode.
pub fn _supports_unicode() -> Result<bool> {
    // Detect whether the current stdout can handle full Unicode.
    let mut enc = (/* getattr */ None || "".to_string());
    if ("utf8".to_string(), "utf8".to_string()).contains(&enc.to_lowercase().replace(&*"-".to_string(), &*"".to_string()).replace(&*"_".to_string(), &*"".to_string())) {
        true
    }
    // try:
    {
        sys::stdout.reconfigure(/* encoding= */ "utf-8".to_string(), /* errors= */ "replace".to_string());
        sys::stderr.reconfigure(/* encoding= */ "utf-8".to_string(), /* errors= */ "replace".to_string());
        true
    }
    // except Exception as _e:
    // TODO: import io
    // try:
    {
        if /* hasattr(sys::stdout, "buffer".to_string()) */ true {
            sys::stdout = io.TextIOWrapper(sys::stdout.buffer, /* encoding= */ "utf-8".to_string(), /* errors= */ "replace".to_string(), /* line_buffering= */ true);
        }
        if /* hasattr(sys::stderr, "buffer".to_string()) */ true {
            sys::stderr = io.TextIOWrapper(sys::stderr.buffer, /* encoding= */ "utf-8".to_string(), /* errors= */ "replace".to_string(), /* line_buffering= */ true);
        }
        true
    }
    // except Exception as _e:
}

/// Walk root and return .py files respecting include/exclude rules.
pub fn collect_py_files(root: PathBuf, exclude: Vec<String>, include: Vec<String>) -> Vec<PathBuf> {
    // Walk root and return .py files respecting include/exclude rules.
    let mut exclude = (exclude || vec![]);
    let mut include = (include || vec![]);
    let mut results = vec![];
    for (dirpath, dirnames, filenames) in os::walk(root).iter() {
        let mut rel_dir = os::path.relpath(dirpath, root);
        dirnames[..] = dirnames.iter().filter(|d| (!_ALWAYS_SKIP.contains(&d) && !d.ends_with(&*".egg-info".to_string()) && !(exclude && exclude.iter().map(|p| if rel_dir != ".".to_string() { PathBuf::from(rel_dir).join(d) } else { d }.starts_with(&*p)).collect::<Vec<_>>().iter().any(|v| *v)))).map(|d| d).collect::<Vec<_>>();
        if include {
            let mut top = if rel_dir != ".".to_string() { rel_dir.split(os::sep).map(|s| s.to_string()).collect::<Vec<String>>()[0] } else { ".".to_string() };
            if (top != ".".to_string() && !include.iter().map(|p| top.starts_with(&*p)).collect::<Vec<_>>().iter().any(|v| *v)) {
                continue;
            }
        }
        for r#fn in filenames.iter() {
            if r#fn.ends_with(&*".py".to_string()) {
                results.push((PathBuf::from(dirpath) / r#fn));
            }
        }
    }
    results
}

/// Compute maximum nesting depth of control flow in a function.
pub fn _compute_nesting_depth(node: ast::AST) -> i64 {
    // Compute maximum nesting depth of control flow in a function.
    let mut max_depth = 0;
    let _walk = |n, depth| {
        // global/nonlocal max_depth
        let mut nesting_types = (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.ExceptHandler);
        for child in ast.iter_child_nodes(n).iter() {
            if /* /* isinstance(child, nesting_types) */ */ true {
                let mut new_depth = (depth + 1);
                let mut max_depth = max_depth.max(new_depth);
                _walk(child, new_depth);
            } else {
                _walk(child, depth);
            }
        }
    };
    _walk(node, 0);
    max_depth
}

/// Cyclomatic complexity approximation.
pub fn _compute_complexity(node: ast::AST) -> i64 {
    // Cyclomatic complexity approximation.
    ast.walk(node).iter().filter(|c| /* /* isinstance(c, (ast.If, ast.For, ast.While, ast.Try, ast.ExceptHandler, ast.BoolOp, ast.Assert, ast.comprehension) */) */ true).map(|c| 1).collect::<Vec<_>>().iter().sum::<i64>()
}

/// Parse one file and extract all functions and classes.
pub fn _extract_functions_from_file(fpath: PathBuf, root: PathBuf) -> Result<(Vec<FunctionRecord>, Vec<ClassRecord>, Option<String>)> {
    // Parse one file and extract all functions and classes.
    // try:
    {
        let mut source = fpath.read_to_string(), /* errors= */ "ignore".to_string());
    }
    // except Exception as e:
    // try:
    {
        let mut tree = ast.parse(source, /* filename= */ fpath.to_string());
    }
    // except SyntaxError as e:
    let mut rel_path = fpath.relative_to(root).to_string().replace(&*"\\".to_string(), &*"/".to_string());
    let mut lines = source.lines().map(|s| s.to_string()).collect::<Vec<String>>();
    let mut functions = vec![];
    let mut classes = vec![];
    for node in ast.walk(tree).iter() {
        if /* /* isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef) */) */ true {
            let mut start = (node.lineno - 1).max(0);
            let mut end = (node.end_lineno || (start + 1));
            let mut code = lines[start..end].join(&"\n".to_string());
            let mut code_hash = hashlib::md5(code.as_bytes().to_vec()).hexdigest();
            let mut params = node.args.args.iter().filter(|a| a.arg != "self".to_string()).map(|a| a.arg).collect::<Vec<_>>();
            let mut ret = if (node.returns && /* hasattr(ast, "unparse".to_string()) */ true) { ast.unparse(node.returns) } else { None };
            // try:
            {
                let mut decorators = node.decorator_list.iter().map(|d| ast.unparse(d)).collect::<Vec<_>>();
            }
            // except Exception as _e:
            let mut calls = vec![];
            for child in ast.walk(node).iter() {
                if /* /* isinstance(child, ast.Call) */ */ true {
                    if /* /* isinstance(child.func, ast.Name) */ */ true {
                        calls.push(child.func.id);
                    } else if /* /* isinstance(child.func, ast.Attribute) */ */ true {
                        calls.push(child.func.attr);
                    }
                }
            }
            functions.push(FunctionRecord(/* name= */ node.name, /* file_path= */ rel_path, /* line_start= */ node.lineno, /* line_end= */ end, /* size_lines= */ (end - start), /* parameters= */ params, /* return_type= */ ret, /* decorators= */ decorators, /* docstring= */ (ast.get_docstring(node) || None), /* calls_to= */ calls.into_iter().collect::<HashSet<_>>().into_iter().collect::<Vec<_>>(), /* complexity= */ _compute_complexity(node), /* nesting_depth= */ _compute_nesting_depth(node), /* code_hash= */ code_hash, /* code= */ code, /* is_async= */ /* /* isinstance(node, ast.AsyncFunctionDef) */ */ true));
        } else if /* /* isinstance(node, ast.ClassDef) */ */ true {
            let mut start = (node.lineno - 1).max(0);
            let mut end = (node.end_lineno || (start + 1));
            let mut methods = ast.walk(node).iter().filter(|n| /* /* isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef) */) */ true).map(|n| n.name).collect::<Vec<_>>();
            let mut bases = vec![];
            for b in node.bases.iter() {
                // try:
                {
                    bases.push(ast.unparse(b));
                }
                // except Exception as _e:
            }
            classes.push(ClassRecord(/* name= */ node.name, /* file_path= */ rel_path, /* line_start= */ node.lineno, /* line_end= */ end, /* size_lines= */ (end - start), /* method_count= */ methods.len(), /* base_classes= */ bases, /* docstring= */ (ast.get_docstring(node) || None), /* methods= */ methods, /* has_init= */ methods.contains(&"__init__".to_string())));
        }
    }
    Ok((functions, classes, None))
}

/// Parallel-scan the codebase, returning functions, classes, and errors.
pub fn scan_codebase(root: PathBuf, exclude: Vec<String>, include: Vec<String>) -> (Vec<FunctionRecord>, Vec<ClassRecord>, Vec<String>) {
    // Parallel-scan the codebase, returning functions, classes, and errors.
    let mut py_files = collect_py_files(root, exclude, include);
    let mut all_functions = vec![];
    let mut all_classes = vec![];
    let mut errors = vec![];
    let mut executor = concurrent.futures.ThreadPoolExecutor();
    {
        let mut futures = py_files.iter().map(|f| (executor.submit(_extract_functions_from_file, f, root), f)).collect::<HashMap<_, _>>();
        for future in concurrent.futures.as_completed(futures).iter() {
            let (mut funcs, mut clses, mut err) = future.result();
            all_functions.extend(funcs);
            all_classes.extend(clses);
            if err {
                errors.push(format!("{}: {}", futures[&future], err));
            }
        }
    }
    (all_functions, all_classes, errors)
}

/// Split text into meaningful lowercase tokens (camelCase/snake_case aware).
pub fn tokenize(text: String) -> Vec<String> {
    // Split text into meaningful lowercase tokens (camelCase/snake_case aware).
    if !text {
        vec![]
    }
    let mut cleaned = regex::Regex::new(&"[^a-zA-Z0-9]".to_string()).unwrap().replace_all(&" ".to_string(), text).to_string();
    let mut raw = vec![];
    for word in cleaned.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().iter() {
        raw.extend(_SPLIT_RE.finditer(word).iter().map(|m| m.group().to_lowercase()).collect::<Vec<_>>());
        if (word.islower() || word.isupper()) {
            raw.push(word.to_lowercase());
        }
    }
    raw.iter().filter(|t| (t.len() > 1 && !_STOP_WORDS.contains(&t))).map(|t| t).collect::<Vec<_>>()
}

pub fn _term_freq(tokens: Vec<String>) -> Counter {
    Counter(tokens)
}

/// Cosine similarity between two term-frequency vectors.
pub fn cosine_similarity(a: Counter, b: Counter) -> f64 {
    // Cosine similarity between two term-frequency vectors.
    let mut common = (a.into_iter().collect::<HashSet<_>>() & b.into_iter().collect::<HashSet<_>>());
    if !common {
        0.0_f64
    }
    let mut dot = common.iter().map(|k| (a[&k] * b[&k])).collect::<Vec<_>>().iter().sum::<i64>();
    let mut mag_a = math::sqrt(a.values().iter().map(|v| (v * v)).collect::<Vec<_>>().iter().sum::<i64>());
    let mut mag_b = math::sqrt(b.values().iter().map(|v| (v * v)).collect::<Vec<_>>().iter().sum::<i64>());
    if (mag_a == 0 || mag_b == 0) {
        0.0_f64
    }
    (dot / (mag_a * mag_b))
}

/// Structural similarity between two code blocks (0–1).
pub fn code_similarity(code_a: String, code_b: String) -> f64 {
    // Structural similarity between two code blocks (0–1).
    if (!code_a || !code_b) {
        0.0_f64
    }
    SequenceMatcher(None, code_a, code_b).ratio()
}

/// Pretty-print the code smell report.
pub fn print_smell_report(smells: Vec<SmellIssue>, summary: HashMap<String, Box<dyn std::any::Any>>) -> () {
    // Pretty-print the code smell report.
    println!("\n  {}", ("=".to_string() * 58));
    println!("    CODE SMELL REPORT");
    println!("  {}", ("=".to_string() * 58));
    println!("    Total issues: {}  ({} {}  {} {}  {} {})", summary["total".to_string()], Severity.icon(Severity.CRITICAL), summary["critical".to_string()], Severity.icon(Severity.WARNING), summary["warning".to_string()], Severity.icon(Severity.INFO), summary["info".to_string()]);
    println!("  {}", (SEP * 58));
    if !smells {
        println!("    No code smells detected! Clean code.");
        println!("  {}\n", ("=".to_string() * 58));
        return;
    }
    let mut by_file = defaultdict(list);
    for s in smells.iter() {
        by_file[&s.file_path].push(s);
    }
    for (fpath, file_smells) in { let mut v = by_file.iter().clone(); v.sort(); v }.iter() {
        let mut n_cr = file_smells.iter().filter(|s| s.severity == Severity.CRITICAL).map(|s| 1).collect::<Vec<_>>().iter().sum::<i64>();
        let mut n_wr = file_smells.iter().filter(|s| s.severity == Severity.WARNING).map(|s| 1).collect::<Vec<_>>().iter().sum::<i64>();
        let mut n_in = file_smells.iter().filter(|s| s.severity == Severity.INFO).map(|s| 1).collect::<Vec<_>>().iter().sum::<i64>();
        let mut counts = format!("{}{} {}{} {}{}", Severity.icon(Severity.CRITICAL), n_cr, Severity.icon(Severity.WARNING), n_wr, Severity.icon(Severity.INFO), n_in);
        println!("\n    {}  [{}]", fpath, counts);
        for s in file_smells.iter() {
            let mut icon = Severity.icon(s.severity);
            println!("      {} L{:>4}  {:<25} {}", icon, s.line, s.category, s.name);
            println!("              {}", s.message);
            println!("              -> {}", s.suggestion);
            if s.llm_analysis {
                for line in textwrap.wrap(s.llm_analysis, 65).iter() {
                    println!("              [AI] {}", line);
                    // pass
                }
            }
        }
    }
    if summary["worst_files".to_string()] {
        println!("\n    WORST FILES (by issue count)");
        for (fpath, count) in { let mut v = summary["worst_files".to_string()].iter().clone(); v.sort(); v }[..5].iter() {
            println!("      {:>3} issues  {}", count, fpath);
            // pass
        }
    }
    if summary["by_category".to_string()] {
        println!("\n    CATEGORY BREAKDOWN");
        for (cat, count) in { let mut v = summary["by_category".to_string()].iter().clone(); v.sort(); v }.iter() {
            println!("      {:>3}  {}", count, cat);
            // pass
        }
    }
    println!("\n  {}\n", ("=".to_string() * 58));
}

/// Pretty-print the duplicate finder report.
pub fn print_duplicate_report(groups: Vec<DuplicateGroup>, summary: HashMap<String, Box<dyn std::any::Any>>) -> () {
    // Pretty-print the duplicate finder report.
    println!("\n  {}", ("=".to_string() * 58));
    println!("    SIMILAR FUNCTIONS REPORT");
    println!("  {}", ("=".to_string() * 58));
    println!("    Groups found:     {}", summary["total_groups".to_string()]);
    println!("    Exact duplicates: {}", summary["exact_duplicates".to_string()]);
    println!("    Near duplicates:  {}", summary["near_duplicates".to_string()]);
    println!("    Functions involved: {}", summary["total_functions_involved".to_string()]);
    println!("  {}", (SEP * 58));
    if !groups {
        println!("    No duplicates detected!");
        println!("  {}\n", ("=".to_string() * 58));
        return;
    }
    for group in groups[..20].iter() {
        let mut type_icon = if group.similarity_type == "exact".to_string() { Severity.icon(Severity.CRITICAL) } else { Severity.icon(Severity.WARNING) };
        println!("\n    {} Group #{} [{}] (avg: {:.0%})", type_icon, group.group_id, group.similarity_type.to_uppercase(), group.avg_similarity);
        for func in group.functions.iter() {
            println!("      {:<30} {}:{}", func["name".to_string()], func["file".to_string()], func["line".to_string()]);
            if func.get(&"signature".to_string()).cloned() {
                println!("        {}", func["signature".to_string()]);
                // pass
            }
        }
        if group.merge_suggestion {
            println!("      [MERGE] {}", group.merge_suggestion);
            // pass
        }
    }
    if groups.len() > 20 {
        println!("\n    ... and {} more groups", (groups.len() - 20));
        // pass
    }
    println!("\n  {}\n", ("=".to_string() * 58));
}

/// Pretty-print the library extraction suggestions.
pub fn print_library_report(suggestions: Vec<LibrarySuggestion>, summary: HashMap<String, Box<dyn std::any::Any>>) -> () {
    // Pretty-print the library extraction suggestions.
    println!("\n  {}", ("=".to_string() * 58));
    println!("    LIBRARY EXTRACTION ADVISOR");
    println!("  {}", ("=".to_string() * 58));
    println!("    Suggestions:       {}", summary["total_suggestions".to_string()]);
    println!("    Functions to merge: {}", summary["total_functions".to_string()]);
    println!("    Proposed modules:  {}", summary["modules_proposed".to_string()][..5].join(&", ".to_string()));
    println!("  {}", (SEP * 58));
    if !suggestions {
        println!("    No library extraction opportunities found.");
        println!("  {}\n", ("=".to_string() * 58));
        return;
    }
    for (i, sug) in suggestions[..15].iter().enumerate().iter() {
        println!("\n    {}. Module: {}", i, sug.module_name);
        println!("       {}", sug.description);
        println!("       API: {}", sug.unified_api);
        for func in sug.functions[..5].iter() {
            println!("         - {}  ({}:{})", func["name".to_string()], func["file".to_string()], func["line".to_string()]);
            // pass
        }
        if sug.functions.len() > 5 {
            println!("         ... +{} more", (sug.functions.len() - 5));
            // pass
        }
        println!("       Rationale: {}", sug.rationale);
    }
    if suggestions.len() > 15 {
        println!("\n    ... and {} more suggestions", (suggestions.len() - 15));
        // pass
    }
    println!("\n  {}\n", ("=".to_string() * 58));
}

/// Build a comprehensive JSON report.
pub fn build_json_report(root: PathBuf, functions: Vec<FunctionRecord>, classes: Vec<ClassRecord>, smells: Vec<SmellIssue>, duplicates: Vec<DuplicateGroup>, library_suggestions: Vec<LibrarySuggestion>, scan_time: f64) -> HashMap<String, Box<dyn std::any::Any>> {
    // Build a comprehensive JSON report.
    HashMap::from([("version".to_string(), __version__), ("timestamp".to_string(), datetime::now().isoformat()), ("root".to_string(), root.to_string()), ("scan_time_seconds".to_string(), ((scan_time as f64) * 10f64.powi(2)).round() / 10f64.powi(2)), ("stats".to_string(), HashMap::from([("total_functions".to_string(), functions.len()), ("total_classes".to_string(), classes.len()), ("total_files".to_string(), functions.iter().map(|f| f.file_path).collect::<Vec<_>>().into_iter().collect::<HashSet<_>>().len()), ("total_lines".to_string(), functions.iter().map(|f| f.size_lines).collect::<Vec<_>>().iter().sum::<i64>()), ("avg_function_size".to_string(), if functions { (((functions.iter().map(|f| f.size_lines).collect::<Vec<_>>().iter().sum::<i64>() / functions.len()) as f64) * 10f64.powi(1)).round() / 10f64.powi(1) } else { 0 }), ("avg_complexity".to_string(), if functions { (((functions.iter().map(|f| f.complexity).collect::<Vec<_>>().iter().sum::<i64>() / functions.len()) as f64) * 10f64.powi(1)).round() / 10f64.powi(1) } else { 0 })])), ("smells".to_string(), HashMap::from([("summary".to_string(), (CodeSmellDetector().detect(functions, classes) && None)), ("total".to_string(), smells.len()), ("issues".to_string(), smells.iter().map(|s| HashMap::from([("file".to_string(), s.file_path), ("line".to_string(), s.line), ("category".to_string(), s.category), ("severity".to_string(), s.severity), ("name".to_string(), s.name), ("message".to_string(), s.message), ("suggestion".to_string(), s.suggestion), ("metric".to_string(), s.metric_value), ("llm_analysis".to_string(), (s.llm_analysis || None))])).collect::<Vec<_>>())])), ("duplicates".to_string(), HashMap::from([("total_groups".to_string(), duplicates.len()), ("groups".to_string(), duplicates.iter().map(|g| HashMap::from([("id".to_string(), g.group_id), ("type".to_string(), g.similarity_type), ("avg_similarity".to_string(), g.avg_similarity), ("functions".to_string(), g.functions), ("merge_suggestion".to_string(), (g.merge_suggestion || None))])).collect::<Vec<_>>())])), ("library_suggestions".to_string(), HashMap::from([("total".to_string(), library_suggestions.len()), ("suggestions".to_string(), library_suggestions.iter().map(|s| HashMap::from([("module".to_string(), s.module_name), ("description".to_string(), s.description), ("unified_api".to_string(), s.unified_api), ("functions".to_string(), s.functions), ("rationale".to_string(), s.rationale)])).collect::<Vec<_>>())]))])
}

pub fn parse_args() -> () {
    let mut p = argparse.ArgumentParser(/* prog= */ "X_RAY_Claude".to_string(), /* description= */ "Smart AI-Powered Code Analyzer (X-Ray 4.0)".to_string(), /* formatter_class= */ argparse.RawDescriptionHelpFormatter, /* epilog= */ textwrap.dedent("        Examples:\n          python X_RAY_Claude.py --path .           # scan current dir\n          python X_RAY_Claude.py --smell            # code smell detection\n          python X_RAY_Claude.py --duplicates       # find similar functions\n          python X_RAY_Claude.py --suggest-library  # library extraction advisor\n          python X_RAY_Claude.py --full-scan        # run everything\n          python X_RAY_Claude.py --full-scan --use-llm  # with LLM enrichment\n        ".to_string()));
    p.add_argument("--path".to_string(), /* type= */ str, /* default= */ None, /* help= */ "Project root to scan (default: directory of this script)".to_string());
    p.add_argument("--exclude".to_string(), /* nargs= */ "*".to_string(), /* default= */ vec![], /* help= */ "Folder prefixes to skip".to_string());
    p.add_argument("--include".to_string(), /* nargs= */ "*".to_string(), /* default= */ vec![], /* help= */ "Only scan these folder prefixes".to_string());
    p.add_argument("--smell".to_string(), /* action= */ "store_true".to_string(), /* help= */ "[AI] Detect code smells (long functions, god classes, deep nesting, etc.)".to_string());
    p.add_argument("--duplicates".to_string(), /* action= */ "store_true".to_string(), /* help= */ "[AI] Find cross-file similar/duplicate functions".to_string());
    p.add_argument("--suggest-library".to_string(), /* action= */ "store_true".to_string(), /* help= */ "[AI] Suggest shared library extraction from duplicates".to_string());
    p.add_argument("--full-scan".to_string(), /* action= */ "store_true".to_string(), /* help= */ "[AI] Run all analysis features".to_string());
    p.add_argument("--graph".to_string(), /* action= */ "store_true".to_string(), /* help= */ "Generate interactive health-colored code graph (HTML)".to_string());
    p.add_argument("--use-llm".to_string(), /* action= */ "store_true".to_string(), /* help= */ "Enable LLM enrichment for deeper analysis (requires local model)".to_string());
    p.add_argument("--max-llm-calls".to_string(), /* type= */ int, /* default= */ 20, /* help= */ "Max LLM calls per feature (default: 20)".to_string());
    p.add_argument("--report".to_string(), /* type= */ str, /* metavar= */ "FILE".to_string(), /* help= */ "Save full JSON report to FILE".to_string());
    p.add_argument("--quiet".to_string(), "-q".to_string(), /* action= */ "store_true".to_string(), /* help= */ "Suppress detailed output (only show summary)".to_string());
    p.add_argument("--version".to_string(), /* action= */ "version".to_string(), /* version= */ format!("%(prog)s {}", __version__));
    p.parse_args()
}

pub fn main() -> () {
    let mut args = parse_args();
    println!("{}", BANNER);
    if args.path {
        let mut root = PathBuf::from(args.path).canonicalize().unwrap_or_default();
    } else {
        let mut root = PathBuf::from(file!()).parent().unwrap_or(std::path::Path::new("")).canonicalize().unwrap_or_default();
    }
    if !root.exists() {
        println!("  Error: Path {} does not exist.", root);
        std::process::exit(1);
    }
    if args.full_scan {
        args.smell = true;
        args.duplicates = true;
        args.suggest_library = true;
        args.graph = true;
    }
    if !(args.smell || args.duplicates || args.suggest_library || args.graph) {
        args.smell = true;
        args.duplicates = true;
    }
    let mut llm = if args.use_llm { LLMHelper(root) } else { None };
    let mut start_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    println!("  Scanning {}/...", root.name);
    let (mut functions, mut classes, mut errors) = scan_codebase(root, args.exclude, args.include);
    let mut scan_time = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_time);
    println!("  Found {} functions, {} classes in {} files ({:.2}s)", functions.len(), classes.len(), functions.iter().map(|f| f.file_path).collect::<Vec<_>>().into_iter().collect::<HashSet<_>>().len(), scan_time);
    if errors {
        println!("  Skipped {} files with errors", errors.len());
        // pass
    }
    if !functions {
        println!("{}", "  No functions found — nothing to analyze.".to_string());
        return;
    }
    let mut smells = vec![];
    let mut smell_summary = HashMap::new();
    if args.smell {
        println!("\n  Running code smell detection...");
        let mut detector = CodeSmellDetector();
        let mut smells = detector.detect(functions, classes);
        let mut smell_summary = detector.summary();
        if (args.use_llm && llm) {
            detector.enrich_with_llm(llm, args.max_llm_calls);
        }
        if !args.quiet {
            print_smell_report(smells, smell_summary);
        } else {
            println!("    {} {}  {} {}  {} {}", Severity.icon(Severity.CRITICAL), smell_summary["critical".to_string()], Severity.icon(Severity.WARNING), smell_summary["warning".to_string()], Severity.icon(Severity.INFO), smell_summary["info".to_string()]);
        }
    }
    let mut duplicates = vec![];
    let mut dup_summary = HashMap::new();
    if args.duplicates {
        println!("\n  Running duplicate detection...");
        let mut finder = DuplicateFinder();
        let mut duplicates = finder.find(functions, /* cross_file_only= */ true);
        let mut dup_summary = finder.summary();
        if (args.use_llm && llm) {
            finder.enrich_with_llm(llm, functions, args.max_llm_calls);
        }
        if !args.quiet {
            print_duplicate_report(duplicates, dup_summary);
        } else {
            println!("    {} groups, {} functions", dup_summary["total_groups".to_string()], dup_summary["total_functions_involved".to_string()]);
            // pass
        }
    }
    let mut library_suggestions = vec![];
    let mut lib_summary = HashMap::new();
    if args.suggest_library {
        println!("\n  Running library extraction analysis...");
        let mut advisor = LibraryAdvisor();
        let mut library_suggestions = advisor.analyze(duplicates, functions);
        let mut lib_summary = advisor.summary();
        if (args.use_llm && llm) {
            advisor.enrich_with_llm(llm, functions, args.max_llm_calls);
        }
        if !args.quiet {
            print_library_report(library_suggestions, lib_summary);
        } else {
            println!("    {} suggestions", lib_summary["total_suggestions".to_string()]);
            // pass
        }
    }
    if args.graph {
        println!("\n  Generating smart code graph...");
        let mut graph = SmartGraph();
        graph.build(functions, smells, duplicates, root);
        let mut graph_path = (root / "xray_claude_graph.html".to_string());
        graph.write_html(graph_path);
        println!("    Written to {}", graph_path);
    }
    let mut total_time = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_time);
    if args.report {
        let mut report = build_json_report(root, functions, classes, smells, duplicates, library_suggestions, total_time);
        let mut report_path = PathBuf::from(args.report);
        if !report_path.is_absolute() {
            let mut report_path = (root / args.report);
        }
        report_pathstd::fs::write(&serde_json::to_string(&report).unwrap(), /* encoding= */ "utf-8".to_string());
        println!("\n  JSON report saved to {}", report_path);
    }
    println!("\n  {}", ("=".to_string() * 58));
    println!("    SCAN COMPLETE ({:.2}s)", total_time);
    println!("  {}", (SEP * 58));
    println!("    Files:      {:>6}", functions.iter().map(|f| f.file_path).collect::<Vec<_>>().into_iter().collect::<HashSet<_>>().len());
    println!("    Functions:  {:>6}", functions.len());
    println!("    Classes:    {:>6}", classes.len());
    if smells {
        println!("    Smells:     {:>6}  ({}{} {}{} {}{})", smells.len(), Severity.icon(Severity.CRITICAL), smell_summary.get(&"critical".to_string()).cloned().unwrap_or(0), Severity.icon(Severity.WARNING), smell_summary.get(&"warning".to_string()).cloned().unwrap_or(0), Severity.icon(Severity.INFO), smell_summary.get(&"info".to_string()).cloned().unwrap_or(0));
    }
    if duplicates {
        println!("    Duplicates: {:>6} groups", duplicates.len());
        // pass
    }
    if library_suggestions {
        println!("    Library:    {:>6} suggestions", library_suggestions.len());
        // pass
    }
    println!("    LLM:        {}", if args.use_llm { "enabled".to_string() } else { "disabled".to_string() });
    println!("  {}\n", ("=".to_string() * 58));
}
