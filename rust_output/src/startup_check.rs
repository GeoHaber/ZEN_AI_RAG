/// 🐀 RAG_RAT - Pre-flight Checks Before App Start
/// ===============================================
/// This module runs before the Streamlit app to ensure all dependencies are ready.
/// If something is missing, it provides clear guidance on how to fix it.

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::path::PathBuf;

pub static CRITICAL_MODULES: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub static OPTIONAL_MODULES: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub static LOGGER: std::sync::LazyLock<StartupLogger> = std::sync::LazyLock::new(|| Default::default());

/// ANSI color codes.
#[derive(Debug, Clone)]
pub struct Color {
}

impl Color {
    /// Remove color codes from text.
    pub fn strip(text: String) -> String {
        // Remove color codes from text.
        for attr in dir(Color).iter() {
            if (!attr.starts_with(&*"_".to_string()) && attr != "strip".to_string()) {
                let mut text = text.replace(&*/* getattr(Color, attr) */ Default::default(), &*"".to_string());
            }
        }
        text
    }
}

/// Simple logger for startup checks.
#[derive(Debug, Clone)]
pub struct StartupLogger {
    pub checks: Vec<HashMap<String, String>>,
    pub errors: Vec<String>,
    pub warnings: Vec<String>,
}

impl StartupLogger {
    pub fn new() -> Self {
        Self {
            checks: Vec::new(),
            errors: Vec::new(),
            warnings: Vec::new(),
        }
    }
    /// Log success.
    pub fn success(&self, msg: String) -> () {
        // Log success.
        println!("{}✓{} {}", Color.GREEN, Color.END, msg);
        self.checks.push(HashMap::from([("status".to_string(), "ok".to_string()), ("message".to_string(), msg)]));
    }
    /// Log error.
    pub fn error(&self, msg: String) -> () {
        // Log error.
        println!("{}✗{} {}", Color.RED, Color.END, msg);
        self.checks.push(HashMap::from([("status".to_string(), "error".to_string()), ("message".to_string(), msg)]));
        self.errors.push(msg);
    }
    /// Log warning.
    pub fn warning(&self, msg: String) -> () {
        // Log warning.
        println!("{}⚠{} {}", Color.YELLOW, Color.END, msg);
        self.checks.push(HashMap::from([("status".to_string(), "warning".to_string()), ("message".to_string(), msg)]));
        self.warnings.push(msg);
    }
    /// Log info.
    pub fn info(&self, msg: String) -> () {
        // Log info.
        println!("{}ℹ{} {}", Color.CYAN, Color.END, msg);
        self.checks.push(HashMap::from([("status".to_string(), "info".to_string()), ("message".to_string(), msg)]));
    }
    /// Log section header.
    pub fn header(&self, msg: String) -> () {
        // Log section header.
        println!("\n{}{}{}{}", Color.BOLD, Color.CYAN, msg, Color.END);
    }
    /// Get summary report.
    pub fn get_report(&self) -> HashMap {
        // Get summary report.
        HashMap::from([("total".to_string(), self.checks.len()), ("errors".to_string(), self.errors.len()), ("warnings".to_string(), self.warnings.len()), ("checks".to_string(), self.checks)])
    }
}

/// Check Python version compatibility.
pub fn check_python_version() -> bool {
    // Check Python version compatibility.
    let (mut major, mut minor) = (sys::version_info.major, sys::version_info.minor);
    if (major < 3 || (major == 3 && minor < 9)) {
        logger.error(format!("Python {}.{} is too old (need 3.9+)", major, minor));
        logger.info("Download Python 3.11+: https://python.org/downloads/".to_string());
        false
    }
    logger.success(format!("Python {}.{}.{} (compatible)", major, minor, sys::version_info.micro));
    true
}

/// Check all critical module imports.
pub fn check_critical_imports() -> Result<bool> {
    // Check all critical module imports.
    logger.header("📦 Checking Critical Packages".to_string());
    let mut all_ok = true;
    let mut missing = vec![];
    for module in CRITICAL_MODULES.iter() {
        // try:
        {
            importlib.import_module(module);
            logger.success(format!("{}", module));
        }
        // except ImportError as _e:
    }
    if missing {
        logger.warning(format!("Missing {} critical package(s)", missing.len()));
        logger.info(format!("Run: pip install {}", missing.join(&" ".to_string())));
    }
    Ok(all_ok)
}

/// Check optional imports.
pub fn check_optional_imports() -> Result<()> {
    // Check optional imports.
    logger.header("📚 Checking Optional Packages".to_string());
    for module in OPTIONAL_MODULES.iter() {
        // try:
        {
            importlib.import_module(module);
            logger.success(format!("{} (available)", module));
        }
        // except ImportError as _e:
    }
}

/// Check for running local LLM servers.
pub fn check_local_llm_servers() -> Result<(bool, bool)> {
    // Check for running local LLM servers.
    logger.header("🖥️  Checking Local LLM Servers".to_string());
    let check_port = |host, port, name| {
        // Check port.
        // try:
        {
            let mut sock = socket::socket(socket::AF_INET, socket::SOCK_STREAM);
            sock.settimeout(2);
            let mut result = sock.connect_ex((host, port));
            sock.close();
            if result == 0 {
                logger.success(format!("{} running on {}:{}", name, host, port));
                true
            } else {
                logger.warning(format!("{} not found on {}:{}", name, host, port));
                false
            }
        }
        // except Exception as e:
    };
    let mut ollama = check_port("localhost".to_string(), 11434, "Ollama".to_string());
    let mut llama_cpp = check_port("localhost".to_string(), 8001, "llama-cpp".to_string());
    if !(ollama || llama_cpp) {
        logger.info("No local LLM servers found - will use External LLMs".to_string());
        logger.info("To use local models, install Ollama: https://ollama.ai".to_string());
    }
    Ok((ollama, llama_cpp))
}

/// Check required directories exist.
pub fn check_directories() -> bool {
    // Check required directories exist.
    logger.header("📁 Checking Directory Structure".to_string());
    let mut project_root = PathBuf::from(file!()).parent().unwrap_or(std::path::Path::new(""));
    let mut required_dirs = vec!["cache".to_string(), "logs".to_string(), "uploads".to_string()];
    let mut all_ok = true;
    for dir_name in required_dirs.iter() {
        let mut dir_path = (project_root / dir_name);
        if dir_path.exists() {
            logger.success(format!("{}/ exists", dir_name));
        } else {
            dir_path.create_dir_all();
            logger.success(format!("{}/ created", dir_name));
        }
    }
    all_ok
}

/// Check our custom modules can be imported.
pub fn check_custom_modules() -> Result<bool> {
    // Check our custom modules can be imported.
    logger.header("🐀 Checking RAG_RAT Modules".to_string());
    // try:
    {
        // TODO: from config_enhanced import LLMConfig
        logger.success("config_enhanced::py".to_string());
    }
    // except Exception as e:
    // try:
    {
        // TODO: from llm_adapters import LLMFactory, LLMProvider
        logger.success("llm_adapters::py".to_string());
    }
    // except Exception as e:
    // try:
    {
        // TODO: from ui_components_beautiful import apply_theme
        logger.success("ui_components_beautiful.py".to_string());
    }
    // except Exception as e:
    Ok(true)
}

/// Check for configured API keys.
pub fn check_api_keys() -> bool {
    // Check for configured API keys.
    logger.header("🔑 Checking API Keys".to_string());
    (PathBuf::from(file!()).parent().unwrap_or(std::path::Path::new("")) / ".env".to_string());
    let mut api_keys = HashMap::from([("OPENAI_API_KEY".to_string(), "OpenAI".to_string()), ("ANTHROPIC_API_KEY".to_string(), "Claude (Anthropic)".to_string()), ("HUGGINGFACE_API_KEY".to_string(), "HuggingFace".to_string()), ("GOOGLE_API_KEY".to_string(), "Google Gemini".to_string())]);
    let mut found_keys = vec![];
    let mut missing_keys = vec![];
    for (env_var, provider) in api_keys.iter().iter() {
        if os::getenv(env_var) {
            logger.success(format!("{} key configured", provider));
            found_keys.push(provider);
        } else {
            missing_keys.push(provider);
        }
    }
    if !found_keys {
        logger.warning("No external LLM API keys configured".to_string());
        logger.info("You can add API keys later in the startup screen".to_string());
    }
    found_keys.len() > 0
}

/// Run all startup checks.
pub fn run_startup_checks() -> (bool, HashMap) {
    // Run all startup checks.
    println!("\n{}{}{}{}", Color.BOLD, Color.CYAN, ("=".to_string() * 70), Color.END);
    println!("{}{}🐀 RAG_RAT - Pre-flight System Check{}", Color.BOLD, Color.CYAN, Color.END);
    println!("{}{}{}{}\n", Color.BOLD, Color.CYAN, ("=".to_string() * 70), Color.END);
    let mut checks_passed = true;
    if !check_python_version() {
        let mut checks_passed = false;
    }
    if !check_critical_imports() {
        let mut checks_passed = false;
    }
    check_optional_imports();
    check_directories();
    let (mut ollama, mut llama_cpp) = check_local_llm_servers();
    if !check_custom_modules() {
        let mut checks_passed = false;
    }
    check_api_keys();
    logger.header("📊 Summary".to_string());
    let mut report = logger.get_report();
    println!("\n{}Total checks: {}{}", Color.CYAN, report["total".to_string()], Color.END);
    if report["errors".to_string()] > 0 {
        println!("{}Errors: {}{}", Color.RED, report["errors".to_string()], Color.END);
    }
    if report["warnings".to_string()] > 0 {
        println!("{}Warnings: {}{}", Color.YELLOW, report["warnings".to_string()], Color.END);
    }
    (checks_passed, report)
}

/// Handle case of missing dependencies.
pub fn handle_missing_dependencies() -> () {
    // Handle case of missing dependencies.
    println!("\n{}{}⚠️  SETUP REQUIRED{}", Color.RED, Color.BOLD, Color.END);
    println!("{}{}{}\n", Color.RED, ("=".to_string() * 70), Color.END);
    println!("Some required packages are missing. Please run:\n");
    println!("  {}python install::py{}\n", Color.CYAN, Color.END);
    println!("This will:\n");
    println!("  • Auto-install all dependencies");
    println!("  • Create required directories");
    println!("  • Check for local LLM servers");
    println!("  • Test all imports\n");
    println!("{}{}\n", Color.RED, ("=".to_string() * 70));
}

/// Handle successful startup check.
pub fn handle_success() -> () {
    // Handle successful startup check.
    println!("\n{}{}✅ ALL CHECKS PASSED - READY TO START!{}", Color.GREEN, Color.BOLD, Color.END);
    println!("{}{}{}\n", Color.GREEN, ("=".to_string() * 70), Color.END);
}

/// Main entry point.
pub fn main() -> () {
    // Main entry point.
    let (mut checks_passed, mut report) = run_startup_checks();
    println!("\n{}{}{}{}\n", Color.BOLD, Color.CYAN, ("=".to_string() * 70), Color.END);
    if !checks_passed {
        handle_missing_dependencies();
        false
    } else {
        handle_success();
        true
    }
}
