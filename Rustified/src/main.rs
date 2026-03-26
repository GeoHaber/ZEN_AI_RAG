// ============================================================================
// RAG_RAT Pro Launcher — Rust executable that bootstraps Streamlit app
//
// This binary:
// 1. Detects CPU capabilities (AVX2, SSE2, baseline)
// 2. Downloads optimized Python bundle (one-time)
// 3. Extracts to ~/.rag_rat/venv/
// 4. Spawns Python Streamlit process
// 5. Waits for port 8501 to be ready
// 6. Opens browser automatically
// 7. Keeps process alive until user closes
//
// ============================================================================

use std::env;
use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::thread;
use std::time::Duration;
use std::net::TcpStream;

mod cpu;
use cpu::detect_cpu_features;

// ============================================================================
// CONSTANTS
// ============================================================================

const APP_NAME: &str = "RAG_RAT Pro";
const APP_VERSION: &str = "3.3.0";
const LOCALHOST: &str = "127.0.0.1";
const STREAMLIT_PORT: u16 = 8501;

// ============================================================================
// MAIN
// ============================================================================

fn main() {
    println!("\n🚀 {} {} Launching...", APP_NAME, APP_VERSION);
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");

    // Step 1: Detect CPU
    print!("  ✓ Detecting CPU capabilities... ");
    io::stdout().flush().unwrap();
    let cpu_features = detect_cpu_features();
    println!("{}\n", cpu_features.display());

    // Step 2: Get or prepare Python
    print!("  ✓ Setting up Python environment... ");
    io::stdout().flush().unwrap();
    let python_path = match setup_python(&cpu_features) {
        Ok(path) => {
            println!("✓");
            path
        }
        Err(e) => {
            eprintln!("✗");
            eprintln!("\n❌ Error: {}", e);
            std::process::exit(1);
        }
    };

    // Step 3: Get app directory
    let app_dir = get_app_directory()
        .expect("Failed to determine app directory");

    // Step 4: Start Streamlit
    print!("  ✓ Starting Streamlit server... ");
    io::stdout().flush().unwrap();

    let _streamlit_proc = spawn_streamlit(&python_path, &app_dir);
    println!("✓\n");

    // Step 5: Wait for port to be ready
    print!("  ✓ Waiting for connection... ");
    io::stdout().flush().unwrap();
    thread::sleep(Duration::from_millis(500));

    if wait_for_port(LOCALHOST, STREAMLIT_PORT, 30) {
        println!("✓\n");
    } else {
        eprintln!("✗");
        eprintln!("\n❌ Streamlit failed to start");
        std::process::exit(1);
    }

    // Step 6: Open browser
    print!("  ✓ Opening browser... ");
    io::stdout().flush().unwrap();
    let url = format!("http://{}:{}", LOCALHOST, STREAMLIT_PORT);
    open_browser(&url);
    println!("✓\n");

    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("✨ {} is ready at: {}", APP_NAME, url);
    println!("   (Close this window to stop the app)\n");

    // Keep process alive
    loop {
        thread::sleep(Duration::from_secs(1));
    }
}

// ============================================================================
// PYTHON SETUP
// ============================================================================

fn setup_python(cpu_features: &cpu::CpuFeatures) -> Result<PathBuf, String> {
    // For MVP: use system Python
    // In production, would download optimized bundle based on cpu_features.bundle_variant()
    
    let python_exe = if cfg!(windows) {
        "python.exe"
    } else {
        "python3"
    };

    println!("(using system Python - variant: {})", cpu_features.bundle_variant());
    Ok(PathBuf::from(python_exe))
}

fn get_app_directory() -> Result<PathBuf, String> {
    // Find where the Python source files are
    // In a real app, they'd be bundled with the executable
    // For now, check current directory
    
    let cwd = std::env::current_dir()
        .map_err(|e| format!("Cannot get current directory: {}", e))?;
    
    if cwd.join("app_new.py").exists() {
        return Ok(cwd);
    }
    
    // Try parent directory (in case we're in Rustified/)
    if let Some(parent) = cwd.parent() {
        if parent.join("app_new.py").exists() {
            return Ok(parent.to_path_buf());
        }
    }
    
    Ok(cwd)
}

// ============================================================================
// STREAMLIT PROCESS
// ============================================================================

fn spawn_streamlit(python_exe: &Path, app_dir: &Path) -> std::process::Child {
    let app_file = app_dir.join("app_new.py");

    Command::new(python_exe)
        .arg("-m")
        .arg("streamlit")
        .arg("run")
        .arg(&app_file)
        .arg("--logger.level=error")
        .arg("--client.showErrorDetails=false")
        .arg("--client.toolbarMode=minimal")
        .arg("--server.headless=true")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .expect("Failed to spawn Streamlit process")
}

// ============================================================================
// PORT MONITORING
// ============================================================================

fn wait_for_port(host: &str, port: u16, timeout_secs: u64) -> bool {
    let start = std::time::Instant::now();
    let timeout = Duration::from_secs(timeout_secs);

    loop {
        if TcpStream::connect(format!("{}:{}", host, port)).is_ok() {
            return true;
        }

        if start.elapsed() > timeout {
            return false;
        }

        thread::sleep(Duration::from_millis(100));
    }
}

// ============================================================================
// BROWSER OPENING
// ============================================================================

fn open_browser(url: &str) {
    let _cmd = if cfg!(target_os = "windows") {
        Command::new("rundll32")
            .arg("url.dll,FileProtocolHandler")
            .arg(url)
            .spawn()
    } else if cfg!(target_os = "macos") {
        Command::new("open")
            .arg(url)
            .spawn()
    } else {
        Command::new("xdg-open")
            .arg(url)
            .spawn()
    };
}

