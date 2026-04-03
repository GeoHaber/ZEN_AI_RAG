/// X_Ray Analysis for Rustification
/// Analyzes RAG_RAT codebase to identify modules for Rust conversion
/// Generates metrics: complexity, performance impact, async requirements

use anyhow::{Result, Context};
use regex::Regex;
use std::collections::HashMap;
use std::collections::HashSet;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;
use tokio;

#[derive(Debug, Clone)]
pub struct CodeAnalyzer {
    pub root: PathBuf,
    pub metrics: HashMap<String, serde_json::Value>,
    pub exclude_dirs: HashSet<serde_json::Value>,
}

impl CodeAnalyzer {
    pub fn new(root_dir: String) -> Self {
        Self {
            root: PathBuf::from(root_dir),
            metrics: HashMap::from([("total_files".to_string(), 0), ("total_lines".to_string(), 0), ("total_functions".to_string(), 0), ("total_classes".to_string(), 0), ("modules".to_string(), HashMap::new()), ("complexity_metrics".to_string(), HashMap::new()), ("async_functions".to_string(), vec![]), ("io_bound_operations".to_string(), vec![]), ("cpu_bound_operations".to_string(), vec![]), ("performance_critical".to_string(), vec![])]),
            exclude_dirs: HashSet::from(["__pycache__".to_string(), ".git".to_string(), "venv".to_string(), "env".to_string(), ".pytest_cache".to_string(), "node_modules".to_string(), "build".to_string(), "dist".to_string(), "target".to_string(), ".streamlit".to_string()]),
        }
    }
    pub fn is_python_file(&self, path: PathBuf) -> bool {
        (path.extension().unwrap_or_default().to_str().unwrap_or("") == ".py".to_string() && path.file_name().unwrap_or_default().to_str().unwrap_or("") != "__init__::py".to_string())
    }
    pub fn should_skip(&self, path: PathBuf) -> bool {
        for exclude in self.exclude_dirs.iter() {
            if path.parts.contains(&exclude) {
                true
            }
        }
        false
    }
    /// Analyze a single Python file
    pub fn analyze_file(&mut self, file_path: PathBuf) -> Result<HashMap> {
        // Analyze a single Python file
        // try:
        {
            let mut f = File::open(file_path)?;
            {
                let mut content = f.read();
            }
            let mut lines = content.split("\n".to_string()).map(|s| s.to_string()).collect::<Vec<String>>();
            let mut file_metrics = HashMap::from([("path".to_string(), file_path.relative_to(self.root).to_string()), ("lines".to_string(), lines.len()), ("functions".to_string(), 0), ("classes".to_string(), 0), ("async_functions".to_string(), vec![]), ("io_operations".to_string(), vec![]), ("cpu_intensive".to_string(), vec![]), ("complexity_score".to_string(), 0), ("cyclomatic_complexity".to_string(), 0)]);
            let mut tree = ast.parse(content);
            let mut functions = ast.walk(tree).iter().filter(|node| /* /* isinstance(node, ast.FunctionDef) */ */ true).map(|node| node).collect::<Vec<_>>();
            let mut async_functions = ast.walk(tree).iter().filter(|node| /* /* isinstance(node, ast.AsyncFunctionDef) */ */ true).map(|node| node).collect::<Vec<_>>();
            let mut classes = ast.walk(tree).iter().filter(|node| /* /* isinstance(node, ast.ClassDef) */ */ true).map(|node| node).collect::<Vec<_>>();
            file_metrics["functions".to_string()] = functions.len();
            file_metrics["classes".to_string()] = classes.len();
            for func in async_functions.iter() {
                file_metrics["async_functions".to_string()].push(func.name);
                self.metrics["async_functions".to_string()].push(HashMap::from([("file".to_string(), file_path.relative_to(self.root).as_posix()), ("function".to_string(), func.name)]));
            }
            let mut io_patterns = HashMap::from([("file".to_string(), vec!["open".to_string(), "read".to_string(), "write".to_string(), "seek".to_string()]), ("network".to_string(), vec!["requests".to_string(), "socket".to_string(), "http".to_string(), "urllib".to_string(), "aiohttp".to_string()]), ("database".to_string(), vec!["sql".to_string(), "query".to_string(), "execute".to_string(), "fetch".to_string(), "db".to_string()]), ("async".to_string(), vec!["await".to_string(), "asyncio".to_string(), "aio".to_string()])]);
            for (pattern_type, keywords) in io_patterns.iter().iter() {
                for keyword in keywords.iter() {
                    if content.to_lowercase().contains(&keyword) {
                        file_metrics["io_operations".to_string()].push(pattern_type);
                    }
                }
            }
            let mut cpu_patterns = vec!["numpy".to_string(), "pandas".to_string(), "scipy".to_string(), "tensorflow".to_string(), "torch".to_string(), "ml".to_string(), "math".to_string(), "hash".to_string(), "crypto".to_string()];
            for pattern in cpu_patterns.iter() {
                if regex::Regex::new(&format!("\\b{}\\b", pattern)).unwrap().is_match(&content) {
                    file_metrics["cpu_intensive".to_string()].push(pattern);
                }
            }
            file_metrics["complexity_score".to_string()] = ((functions.len() * 3) + (classes.len() * 5));
            let mut if_count = (content.iter().filter(|v| **v == " if ".to_string()).count() + content.iter().filter(|v| **v == "\nif ".to_string()).count());
            let mut for_count = (content.iter().filter(|v| **v == " for ".to_string()).count() + content.iter().filter(|v| **v == "\nfor ".to_string()).count());
            let mut while_count = (content.iter().filter(|v| **v == " while ".to_string()).count() + content.iter().filter(|v| **v == "\nwhile ".to_string()).count());
            let mut exception_count = content.iter().filter(|v| **v == "except".to_string()).count();
            file_metrics["cyclomatic_complexity".to_string()] = ((((1 + if_count) + for_count) + while_count) + exception_count);
            file_metrics
        }
        // except Exception as _e:
    }
    /// Recursively analyze all Python files
    pub fn analyze_directory(&mut self) -> () {
        // Recursively analyze all Python files
        println!("Starting X_Ray analysis of {}...", self.root);
        println!("{}", ("-".to_string() * 80));
        for py_file in { let mut v = self.root.rglob("*.py".to_string()).clone(); v.sort(); v }.iter() {
            if self.should_skip(py_file) {
                continue;
            }
            self.metrics["total_files".to_string()] += 1;
            let mut metrics = self.analyze_file(py_file);
            if metrics {
                let mut module_name = py_file.relative_to(self.root).to_string().replace(&*"\\".to_string(), &*"/".to_string());
                self.metrics["modules".to_string()][module_name] = metrics;
                self.metrics["total_lines".to_string()] += metrics["lines".to_string()];
                self.metrics["total_functions".to_string()] += metrics["functions".to_string()];
                self.metrics["total_classes".to_string()] += metrics["classes".to_string()];
                println!("✓ {:60} | {:3} fn | {:2} cls | {:4} cx", module_name, metrics["functions".to_string()], metrics["classes".to_string()], metrics["complexity_score".to_string()]);
            }
        }
        println!("{}", ("-".to_string() * 80));
        self._identify_priority_modules();
    }
    /// Identify modules with highest rustification priority
    pub fn _identify_priority_modules(&mut self) -> () {
        // Identify modules with highest rustification priority
        let mut priority_scores = HashMap::new();
        for (module, metrics) in self.metrics["modules".to_string()].iter().iter() {
            let mut score = 0;
            let mut reasons = vec![];
            if metrics["async_functions".to_string()] {
                score += (metrics["async_functions".to_string()].len() * 100);
                reasons.push(format!("async ({} funcs)", metrics["async_functions".to_string()].len()));
            }
            if metrics["cpu_intensive".to_string()] {
                score += (metrics["cpu_intensive".to_string()].len() * 80);
                reasons.push(format!("cpu-intensive ({} types)", metrics["cpu_intensive".to_string()].len()));
            }
            if metrics["io_operations".to_string()] {
                score += (metrics["io_operations".to_string()].into_iter().collect::<HashSet<_>>().len() * 50);
                reasons.push(format!("i/o ({} types)", metrics["io_operations".to_string()].into_iter().collect::<HashSet<_>>().len()));
            }
            if metrics["complexity_score".to_string()] > 50 {
                score += (metrics["complexity_score".to_string()] / 10);
                reasons.push(format!("high-complexity ({})", metrics["complexity_score".to_string()]));
            }
            if score > 0 {
                priority_scores[module] = HashMap::from([("score".to_string(), score), ("reasons".to_string(), reasons)]);
            }
        }
        let mut sorted_priorities = { let mut v = priority_scores.iter().clone(); v.sort(); v };
        self.metrics["performance_critical".to_string()] = sorted_priorities[..20].iter().map(|(module, data)| HashMap::from([("module".to_string(), module), ("score".to_string(), data["score".to_string()]), ("reasons".to_string(), data["reasons".to_string()])])).collect::<Vec<_>>();
    }
    /// Generate rustification analysis report
    pub fn generate_report(&mut self, output_file: String) -> Result<()> {
        // Generate rustification analysis report
        let mut report = HashMap::from([("analysis_date".to_string(), Path.cwd().to_string()), ("summary".to_string(), HashMap::from([("total_files".to_string(), self.metrics["total_files".to_string()]), ("total_lines".to_string(), self.metrics["total_lines".to_string()]), ("total_functions".to_string(), self.metrics["total_functions".to_string()]), ("total_classes".to_string(), self.metrics["total_classes".to_string()]), ("avg_lines_per_file".to_string(), (self.metrics["total_lines".to_string()] / 1.max(self.metrics["total_files".to_string()]))), ("avg_complexity".to_string(), (self.metrics["modules".to_string()].values().iter().map(|m| m.get(&"complexity_score".to_string()).cloned().unwrap_or(0)).collect::<Vec<_>>().iter().sum::<i64>() / 1.max(self.metrics["total_files".to_string()])))])), ("async_count".to_string(), self.metrics["async_functions".to_string()].len()), ("priority_modules".to_string(), self.metrics["performance_critical".to_string()]), ("async_modules".to_string(), self.metrics["async_functions".to_string()][..50].iter().map(|item| HashMap::from([("file".to_string(), item["file".to_string()]), ("function".to_string(), item["function".to_string()])])).collect::<Vec<_>>()), ("rustification_strategy".to_string(), self.generate_strategy())]);
        let mut f = File::create(output_file)?;
        {
            json::dump(report, f, /* indent= */ 2);
        }
        Ok(report)
    }
    /// Generate rustification strategy
    pub fn generate_strategy(&self) -> HashMap {
        // Generate rustification strategy
        HashMap::from([("phase_1_analysis".to_string(), HashMap::from([("description".to_string(), "Basic module identification and dependency mapping".to_string()), ("priority".to_string(), "critical_path_modules".to_string()), ("estimated_effort".to_string(), "1-2 weeks".to_string())])), ("phase_2_bindings".to_string(), HashMap::from([("description".to_string(), "Create Rust bindings via PyO3/maturin for high-impact modules".to_string()), ("candidates".to_string(), vec!["Core modules".to_string(), "performance_critical functions".to_string()]), ("estimated_effort".to_string(), "2-3 weeks".to_string())])), ("phase_3_benchmark".to_string(), HashMap::from([("description".to_string(), "Benchmark Python vs Rust implementations".to_string()), ("metrics".to_string(), vec!["execution_time".to_string(), "memory_usage".to_string(), "throughput".to_string()]), ("estimated_effort".to_string(), "1 week".to_string())])), ("phase_4_migration".to_string(), HashMap::from([("description".to_string(), "Gradual migration to Rust implementations".to_string()), ("rollback_capability".to_string(), "Keep Python fallbacks".to_string()), ("estimated_effort".to_string(), "ongoing".to_string())]))])
    }
}

pub fn main() -> () {
    let mut rag_rat_dir = PathBuf::from(file!()).parent().unwrap_or(std::path::Path::new("")).parent().unwrap_or(std::path::Path::new("")).parent().unwrap_or(std::path::Path::new(""));
    let mut analyzer = CodeAnalyzer(rag_rat_dir.to_string());
    analyzer.analyze_directory();
    let mut report_file = (PathBuf::from(file!()).parent().unwrap_or(std::path::Path::new("")) / "rustification_analysis.json".to_string());
    let mut report = analyzer.generate_report(report_file.to_string());
    println!("{}", ("\n".to_string() + ("=".to_string() * 80)));
    println!("{}", "RUSTIFICATION ANALYSIS REPORT".to_string());
    println!("{}", ("=".to_string() * 80));
    println!("Total Files: {}", report["summary".to_string()]["total_files".to_string()]);
    println!("Total Lines: {}", report["summary".to_string()]["total_lines".to_string()]);
    println!("Total Functions: {}", report["summary".to_string()]["total_functions".to_string()]);
    println!("Total Classes: {}", report["summary".to_string()]["total_classes".to_string()]);
    println!("Async Functions: {}", report["async_count".to_string()]);
    println!("{}", "\nTop Priority Modules (for Rustification):".to_string());
    println!("{}", ("-".to_string() * 80));
    for item in report["priority_modules".to_string()][..10].iter() {
        println!("  {:50} | Score: {:5} | {}", item["module".to_string()], item["score".to_string()], item["reasons".to_string()].join(&", ".to_string()));
    }
    println!("\nReport saved to: {}", report_file);
    println!("{}", ("=".to_string() * 80));
}
