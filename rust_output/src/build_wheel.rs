/// build_wheel::py — One-command build for the compiled ZenAI Core wheel.
/// 
/// Handles:
/// 1. Prerequisites check (Cython, setuptools, wheel)
/// 2. Staging source from local_llm, rag_core, Core, adapters
/// 3. Cython compilation → .pyd/.so
/// 4. Wheel packaging (no .py source inside)
/// 5. Cleanup
/// 
/// Usage:
/// python dist_build/build_wheel::py              # default build
/// python dist_build/build_wheel::py --clean      # remove all build artifacts
/// python dist_build/build_wheel::py --pyc-only   # skip Cython, .pyc fallback
/// 
/// Output:
/// dist_build/dist/zenai_core-1.0.0-cp3XX-win_amd64.whl

use anyhow::{Result, Context};
use std::fs::File;
use std::io::{self, Read, Write};

pub static HERE: std::sync::LazyLock<String /* Path.parent().unwrap_or(std::path::Path::new("")).resolve */> = std::sync::LazyLock::new(|| Default::default());

pub const PROJECT_ROOT: &str = "HERE.parent";

pub const STAGE: &str = "HERE / '_staging";

pub const DIST: &str = "HERE / 'dist";

/// Verify build tools are available.
pub fn check_prereqs() -> Result<()> {
    // Verify build tools are available.
    let mut missing = vec![];
    for pkg in vec!["cython".to_string(), "setuptools".to_string(), "wheel".to_string()].iter() {
        // try:
        {
            __import__(pkg);
        }
        // except ImportError as _e:
    }
    if missing {
        println!("Installing missing build tools: {}", missing.join(&", ".to_string()));
        subprocess::check_call({ let mut _v = Vec::new(); _v.push(sys::executable); _v.push("-m".to_string()); _v.push("pip".to_string()); _v.push("install".to_string()); _v.extend(missing); _v.push("--quiet".to_string()); _v });
    }
    if sys::platform == "win32".to_string() {
        // try:
        {
            // TODO: from setuptools._distutils.msvccompiler import MSVCCompiler
            println!("{}", "  C compiler: MSVC (Visual Studio Build Tools)".to_string());
        }
        // except ImportError as _e:
    }
    Ok(println!("{}", "  Prerequisites: OK\n".to_string()))
}

/// Remove all build artifacts.
pub fn clean() -> () {
    // Remove all build artifacts.
    for d in vec![STAGE, DIST, (HERE / "build".to_string()), (HERE / "zenai_core.egg-info".to_string())].iter() {
        if d.exists() {
            std::fs::remove_dir_all(d, /* ignore_errors= */ true).ok();
            println!("  Removed: {}", d);
        }
    }
    for c_file in HERE.rglob("*.c".to_string()).iter() {
        c_file.remove_file().ok();
    }
    println!("{}", "  Clean complete.\n".to_string());
}

/// Run the full build pipeline.
pub fn build_wheel(pyc_only: bool) -> () {
    // Run the full build pipeline.
    println!("{}", ("=".to_string() * 60));
    println!("{}", "  ZenAI Core — Compiled Wheel Builder".to_string());
    println!("{}", ("=".to_string() * 60));
    println!("{}", "\n[1/4] Checking prerequisites...".to_string());
    if !pyc_only {
        check_prereqs();
    } else {
        println!("{}", "  Skipping Cython (--pyc-only mode)\n".to_string());
    }
    println!("{}", "[2/4] Cleaning previous artifacts...".to_string());
    clean();
    println!("{}", "[3/4] Building wheel...".to_string());
    let mut setup_script = (HERE / "setup_zenai_core::py".to_string());
    if !setup_script.exists() {
        println!("  ERROR: {} not found!", setup_script);
        std::process::exit(1);
    }
    let mut env = os::environ.clone();
    if pyc_only {
        env["ZENAI_NO_CYTHON".to_string()] = "1".to_string();
    }
    let mut cmd = vec![sys::executable, setup_script.to_string(), "bdist_wheel".to_string(), "--dist-dir".to_string(), DIST.to_string()];
    let mut result = std::process::Command::new("sh").arg("-c").arg(cmd, /* env= */ env, /* cwd= */ HERE.to_string().output().unwrap());
    if result.returncode != 0 {
        println!("{}", "\n  BUILD FAILED. Check errors above.".to_string());
        println!("{}", "  Common fixes:".to_string());
        println!("{}", "    - Install Visual Studio Build Tools (C++ build tools)".to_string());
        println!("{}", "    - pip install cython setuptools wheel".to_string());
        std::process::exit(1);
    }
    println!("{}", "\n[4/4] Verifying output...".to_string());
    let mut wheels = DIST.glob("zenai_core-*.whl".to_string()).into_iter().collect::<Vec<_>>();
    if !wheels {
        println!("{}", "  ERROR: No wheel produced!".to_string());
        std::process::exit(1);
    }
    let mut whl = wheels[0];
    let mut whl_size = (whl.stat().st_size / 1024);
    println!("\n  {}", ("=".to_string() * 56));
    println!("    BUILD SUCCESSFUL");
    println!("  {}", ("-".to_string() * 56));
    println!("    Wheel:  {}", whl.name);
    println!("    Size:   {:.0} KB", whl_size);
    println!("    Path:   {}", whl);
    println!("  {}", ("-".to_string() * 56));
    println!("    Install command for collaborators:");
    println!("      pip install {}", whl.name);
    println!("  {}", ("-".to_string() * 56));
    println!("    Usage in their code:");
    println!("      from rag_core import RAGEngine, HybridSearcher");
    println!("      from local_llm import LlamaCppManager, ModelRegistry");
    println!("      from Core import QueryRequest, ChatResponse");
    println!("      from zenai_adapters import LLMFactory, RAGIntegration");
    println!("  {}\n", ("=".to_string() * 56));
    // TODO: import zipfile
    let mut zf = zipfile.ZipFile(whl);
    {
        let mut py_files = zf.namelist().iter().filter(|n| (n.ends_with(&*".py".to_string()) && !n.contains(&"__init__".to_string()))).map(|n| n).collect::<Vec<_>>();
        if py_files {
            println!("  WARNING: {} .py files found in wheel:", py_files.len());
            for f in py_files[..5].iter() {
                println!("    - {}", f);
                // pass
            }
            println!("{}", "  These should be compiled .pyd/.so in production.".to_string());
        } else {
            println!("{}", "  Verified: No source .py files in wheel (only __init__::py stubs + .pyd/.so)".to_string());
        }
    }
    if STAGE.exists() {
        std::fs::remove_dir_all(STAGE, /* ignore_errors= */ true).ok();
    }
    whl
}

pub fn main() -> () {
    let mut parser = argparse.ArgumentParser(/* description= */ "Build compiled ZenAI Core wheel".to_string());
    parser.add_argument("--clean".to_string(), /* action= */ "store_true".to_string(), /* help= */ "Remove all build artifacts".to_string());
    parser.add_argument("--pyc-only".to_string(), /* action= */ "store_true".to_string(), /* help= */ "Skip Cython, produce .pyc-only wheel (less secure)".to_string());
    let mut args = parser.parse_args();
    if args.clean {
        clean();
        return;
    }
    build_wheel(/* pyc_only= */ args.pyc_only);
}
