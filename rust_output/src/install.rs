/// 🐀 RAG_RAT - Foolproof Auto-Installer for Virgin Systems
/// =========================================================
/// This script ensures RAG_RAT works on ANY system, even fresh Python installs.
/// 
/// Features:
/// ✓ Auto-detects Python version and warns if too old
/// ✓ Auto-installs missing dependencies
/// ✓ Creates required directories
/// ✓ Checks for external dependencies (Ollama, llama-cpp)
/// ✓ Provides installation guides for optional services
/// ✓ Handles virtual environments
/// ✓ Tests all imports after install

use anyhow::{Result, Context};
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;

/// Colors class.
#[derive(Debug, Clone)]
pub struct Colors {
}

impl Colors {
    pub fn green(text: String) -> () {
        format!("{}{}{}", Colors.OKGREEN, text, Colors.ENDC)
    }
    pub fn red(text: String) -> () {
        format!("{}{}{}", Colors.FAIL, text, Colors.ENDC)
    }
    pub fn yellow(text: String) -> () {
        format!("{}{}{}", Colors.WARNING, text, Colors.ENDC)
    }
    pub fn blue(text: String) -> () {
        format!("{}{}{}", Colors.OKBLUE, text, Colors.ENDC)
    }
    pub fn cyan(text: String) -> () {
        format!("{}{}{}", Colors.OKCYAN, text, Colors.ENDC)
    }
}

/// Display beautiful header.
pub fn print_header() -> () {
    // Display beautiful header.
    println!("{}", ("\n".to_string() + ("=".to_string() * 70)));
    println!("{}", Colors.cyan("🐀 RAG_RAT - Foolproof Setup & Installation".to_string()));
    println!("{}", ("=".to_string() * 70));
    println!("{}", "Setting up RAG_RAT on this system...\n".to_string());
}

/// Check if Python version is compatible.
pub fn check_python_version() -> bool {
    // Check if Python version is compatible.
    println!("📊 Checking Python version...");
    let (mut major, mut minor) = (sys::version_info.major, sys::version_info.minor);
    let mut version_str = format!("{}.{}", major, minor);
    if (major < 3 || (major == 3 && minor < 9)) {
        println!("{}", Colors.red(format!("  ❌ Python {} is too old! Need Python 3.9+", version_str)));
        println!("{}", Colors.yellow("  Get Python 3.11 or later from: https://python.org/downloads/".to_string()));
        false
    }
    println!("{}", Colors.green(format!("  ✓ Python {} is compatible", version_str)));
    true
}

/// Get the correct pip command for this environment.
pub fn get_pip_command() -> Result<String> {
    // Get the correct pip command for this environment.
    // try:
    {
        std::process::Command::new("sh").arg("-c").arg(vec!["pip".to_string().output().unwrap(), "--version".to_string()], /* capture_output= */ true, /* check= */ true, /* shell= */ false);
        "pip".to_string()
    }
    // except Exception as _e:
}

/// Read requirements from requirements.txt.
pub fn read_requirements() -> Result<Vec<String>> {
    // Read requirements from requirements.txt.
    let mut req_file = (PathBuf::from(file!()).parent().unwrap_or(std::path::Path::new("")) / "requirements.txt".to_string());
    if !req_file.exists() {
        println!("{}", Colors.yellow(format!("  ⚠ requirements.txt not found at {}", req_file)));
        vec![]
    }
    let mut packages = vec![];
    let mut f = File::open(req_file)?;
    {
        for line in f.iter() {
            let mut line = line.trim().to_string();
            if (line && !line.starts_with(&*"#".to_string())) {
                if vec![">=".to_string(), "<=".to_string(), "==".to_string(), "~=".to_string(), ">".to_string()].iter().map(|op| line.contains(&op)).collect::<Vec<_>>().iter().any(|v| *v) {
                    packages.push(line);
                } else {
                    packages.push(line);
                }
            }
        }
    }
    Ok(packages)
}

/// Install packages with error handling.
pub fn install_packages(packages: Vec<String>, pip_cmd: String) -> Result<bool> {
    // Install packages with error handling.
    if !packages {
        println!("{}", Colors.yellow("  ⚠ No packages to install".to_string()));
        true
    }
    println!("\n📦 Installing {} packages...", packages.len());
    println!("{}", "   (This may take a few minutes on first install)\n".to_string());
    let mut failed = vec![];
    for (i, package) in packages.iter().enumerate().iter() {
        let mut pkg_name = package.split(">=".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[0].split("==".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[0].split("<".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[0].split(">".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[0].trim().to_string();
        println!("   [{}/{}] Installing {}...", i, packages.len(), Colors.cyan(pkg_name));
        // try:
        {
            std::process::Command::new("sh").arg("-c").arg(vec![pip_cmd, "install".to_string().output().unwrap(), "-q".to_string(), package], /* check= */ true, /* capture_output= */ true, /* timeout= */ 300, /* shell= */ false);
            println!("{}", Colors.green("✓".to_string()));
        }
        // except subprocess::TimeoutExpired as _e:
        // except Exception as _e:
    }
    if failed {
        println!("\n{}", Colors.yellow("⚠ Some packages failed to install:".to_string()));
        for pkg in failed.iter() {
            println!("   - {}", pkg);
            // pass
        }
        println!("\nTry manually: {} install {}", pip_cmd, failed.join(&" ".to_string()));
        false
    }
    println!("{}", Colors.green("\n  ✓ All packages installed successfully!".to_string()));
    Ok(true)
}

/// Create required directories.
pub fn create_directories() -> () {
    // Create required directories.
    println!("\n📁 Creating required directories...");
    let mut dirs = vec!["cache".to_string(), "logs".to_string(), "uploads".to_string(), "models".to_string(), "qdrant_storage".to_string(), "rag_storage".to_string(), "rag_cache".to_string()];
    for dir_name in dirs.iter() {
        let mut dir_path = (PathBuf::from(file!()).parent().unwrap_or(std::path::Path::new("")) / dir_name);
        dir_path.create_dir_all();
        println!("   ✓ {}/", dir_name);
    }
    println!("{}", Colors.green("  ✓ All directories ready!".to_string()));
}

/// Check if local LLM servers are available.
pub fn check_local_llm_servers() -> Result<(bool, bool)> {
    // Check if local LLM servers are available.
    println!("\n🔍 Checking for local LLM servers...");
    // TODO: import socket
    let is_port_open = |port| {
        // Is port open.
        // try:
        {
            let mut sock = socket::socket(socket::AF_INET, socket::SOCK_STREAM);
            sock.settimeout(1);
            let mut result = sock.connect_ex(("localhost".to_string(), port));
            sock.close();
            result == 0
        }
        // except Exception as _e:
    };
    let mut ollama = is_port_open(11434);
    let mut llama_cpp = is_port_open(8001);
    if ollama {
        println!("   ✓ Ollama found on port 11434");
        // pass
    } else {
        println!("   ✗ Ollama not found (port 11434 closed)");
        // pass
    }
    if llama_cpp {
        println!("   ✓ llama-cpp found on port 8001");
        // pass
    } else {
        println!("   ✗ llama-cpp not found (port 8001 closed)");
        // pass
    }
    if !(ollama || llama_cpp) {
        println!("\n   {}", Colors.yellow("ℹ No local LLM servers found - that's OK!".to_string()));
        println!("   You can use External LLMs (OpenAI, Claude, etc.) instead");
        println!("   Or install Ollama: https://ollama.ai");
        // pass
    }
    Ok((ollama, llama_cpp))
}

/// Test critical imports.
pub fn test_imports() -> Result<bool> {
    // Test critical imports.
    println!("\n✅ Testing imports...");
    let mut critical_imports = vec![("streamlit".to_string(), "Streamlit (UI framework)".to_string()), ("httpx".to_string(), "httpx (HTTP client)".to_string()), ("requests".to_string(), "requests (HTTP library)".to_string()), ("sentence_transformers".to_string(), "sentence-transformers (Embeddings)".to_string()), ("qdrant_client".to_string(), "qdrant-client (Vector database)".to_string())];
    let mut optional_imports = vec![("ollama".to_string(), "Ollama (Optional - for local models)".to_string()), ("faster_whisper".to_string(), "faster-whisper (Optional - for audio)".to_string()), ("cv2".to_string(), "OpenCV (Optional - for vision)".to_string())];
    let mut all_ok = true;
    println!("\n   {}", Colors.bold("Critical packages:".to_string()));
    for (module, display_name) in critical_imports.iter() {
        // try:
        {
            __import__(module);
            println!("   ✓ {}", display_name);
        }
        // except ImportError as _e:
    }
    println!("\n   {}", Colors.bold("Optional packages:".to_string()));
    for (module, display_name) in optional_imports.iter() {
        // try:
        {
            __import__(module);
            println!("   ✓ {}", display_name);
        }
        // except ImportError as _e:
    }
    Ok(all_ok)
}

/// Create convenient startup scripts.
pub fn create_startup_script() -> () {
    // Create convenient startup scripts.
    println!("\n📝 Creating startup scripts...\n");
    let mut project_root = PathBuf::from(file!()).parent().unwrap_or(std::path::Path::new(""));
    if sys::platform == "win32".to_string() {
        let mut batch_content = "@echo off\nREM RAG_RAT Startup Script for Windows\ntitle RAG_RAT\ncd /d \"%~dp0\"\necho.\necho 🐀 Starting RAG_RAT...\necho.\npython -m streamlit run app_enhanced.py\npause\n".to_string();
        let mut batch_file = (project_root / "run_rag_rat.bat".to_string());
        batch_filestd::fs::write(&batch_content);
        println!("   ✓ Created {}", Colors.cyan("run_rag_rat.bat".to_string()));
    } else {
        let mut shell_content = "#!/bin/bash\n# RAG_RAT Startup Script for Linux/Mac\n\ncd \"$(dirname \"$0\")\"\necho \"\"\necho \"🐀 Starting RAG_RAT...\"\necho \"\"\npython -m streamlit run app_enhanced.py\n".to_string();
        let mut shell_file = (project_root / "run_rag_rat.sh".to_string());
        shell_filestd::fs::write(&shell_content);
        shell_file.chmod(493);
        println!("   ✓ Created {}", Colors.cyan("run_rag_rat.sh".to_string()));
    }
}

/// Print next steps.
pub fn print_next_steps() -> () {
    // Print next steps.
    println!("{}", ("\n".to_string() + ("=".to_string() * 70)));
    println!("{}", Colors.green("✅ Setup Complete!".to_string()));
    println!("{}", ("=".to_string() * 70));
    println!("\n{}", Colors.bold("🚀 To start RAG_RAT:".to_string()));
    if sys::platform == "win32".to_string() {
        println!("\n   Option 1: Double-click {}", Colors.cyan("run_rag_rat.bat".to_string()));
        println!("   Option 2: Run in terminal:");
        println!("             streamlit run app_enhanced.py");
        // pass
    } else {
        println!("\n   Option 1: Run the startup script:");
        println!("            ./run_rag_rat.sh");
        println!("   Option 2: Run directly:");
        println!("            streamlit run app_enhanced.py");
        // pass
    }
    println!("\n{}", Colors.bold("📚 Documentation:".to_string()));
    println!("   - QUICK_REFERENCE.txt - 2-minute quick start");
    println!("   - STARTUP_FLOW_GUIDE.md - Detailed setup guide");
    println!("   - INDEX.md - Complete documentation index");
    println!("\n{}", Colors.bold("⚙️  Next:".to_string()));
    println!("   1. Start the app");
    println!("   2. Choose: External LLM (easiest) or Local LLM");
    println!("   3. Paste API key or select local model");
    println!("   4. Start chatting! 🎉");
    println!("\n{}", Colors.yellow("ℹ  Need help?".to_string()));
    println!("   See: docs/TROUBLESHOOTING.md");
    println!("   GitHub: https://github.com/...");
    println!("{}", ((format!("\n") + ("=".to_string() * 70)) + "\n".to_string()));
}

/// Main installation flow.
pub fn main() -> () {
    // Main installation flow.
    print_header();
    if !check_python_version() {
        std::process::exit(1);
    }
    let mut pip_cmd = get_pip_command();
    println!("{}", Colors.green(format!("  ✓ Using {}", pip_cmd)));
    let mut packages = read_requirements();
    if packages {
        if !install_packages(packages, pip_cmd) {
            println!("{}", Colors.yellow("\n  ⚠ Some packages failed. Installation may still work.".to_string()));
        }
    }
    create_directories();
    check_local_llm_servers();
    if !test_imports() {
        println!("{}", Colors.red("\n  ✗ Some critical packages failed to import!".to_string()));
        println!("{}", Colors.yellow("  Try running: pip install --upgrade pip".to_string()));
        println!("{}", Colors.yellow(format!("  Then: {} install -r requirements.txt", pip_cmd)));
        std::process::exit(1);
    }
    create_startup_script();
    print_next_steps();
}
