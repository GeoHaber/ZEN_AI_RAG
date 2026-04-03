use anyhow::{Result, Context};
use crate::config_system::{load_config, validate_path};
use crate::resource_detect::{HardwareProfiler};
use std::collections::HashSet;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;
use tokio;

pub static PROFILE: std::sync::LazyLock<String /* HardwareProfiler.get_profile */> = std::sync::LazyLock::new(|| Default::default());

pub static REQUIREMENTS_PATH: std::sync::LazyLock<find_requirements_file> = std::sync::LazyLock::new(|| Default::default());

pub static PATCHED_REQUIREMENTS: std::sync::LazyLock<patch_requirements_for_hardware> = std::sync::LazyLock::new(|| Default::default());

pub static _SCRIPT_DIR: std::sync::LazyLock<String /* Path.parent().unwrap_or(std::path::Path::new("")).resolve */> = std::sync::LazyLock::new(|| Default::default());

pub const _CRASH_LOG: &str = "_SCRIPT_DIR / 'crash_log.txt";

pub const _STAGING_DIR: &str = "_SCRIPT_DIR / 'dist_build' / '_staging";

pub const BASE_DIR: &str = "_SCRIPT_DIR";

pub static CONFIG: std::sync::LazyLock<validate_paths> = std::sync::LazyLock::new(|| Default::default());

/// Ensure all requirements are installed before app startup.
pub fn check_and_install_requirements(requirements_path: String) -> Result<()> {
    // Ensure all requirements are installed before app startup.
    // try:
    {
        std::process::Command::new("sh").arg("-c").arg(vec![sys::executable, "-m".to_string().output().unwrap(), "pip".to_string(), "--version".to_string()], /* check= */ true, /* stdout= */ subprocess::DEVNULL, /* shell= */ false);
    }
    // except Exception as _e:
    println!("🔍 Checking and installing dependencies from {}...", requirements_path);
    // try:
    {
        std::process::Command::new("sh").arg("-c").arg(vec![sys::executable, "-m".to_string().output().unwrap(), "pip".to_string(), "install".to_string(), "-r".to_string(), requirements_path], /* check= */ true, /* shell= */ false);
        println!("{}", "✅ Dependencies are up to date.".to_string());
    }
    // except subprocess::CalledProcessError as _e:
}

/// Find requirements file.
pub fn find_requirements_file() -> () {
    // Find requirements file.
    let mut candidates = vec![PathBuf::from(os::path.dirname(file!())).join("requirements.txt".to_string()), PathBuf::from(os::path.dirname(file!())).join("_sandbox".to_string()).join("requirements.txt".to_string()), PathBuf::from(os::path.dirname(file!())).join("_legacy_audit".to_string()).join("requirements.txt".to_string()), PathBuf::from(os::path.dirname(file!())).join("docs".to_string()).join("requirements.txt".to_string())];
    for path in candidates.iter() {
        if os::path.exists(path) {
            path
        }
    }
    println!("{}", "❌ FATAL: requirements.txt not found.".to_string());
    std::process::exit(1);
}

/// Patch requirements for hardware.
pub fn patch_requirements_for_hardware(req_path: String, hw_type: String) -> Result<()> {
    // Patch requirements for hardware.
    let mut f = File::open(req_path)?;
    {
        let mut lines = f.readlines();
    }
    let mut patched = vec![];
    for line in lines.iter() {
        let mut pkg = line.trim().to_string().to_lowercase();
        if hw_type == "AMD".to_string() {
            if (pkg.contains(&"cuda".to_string()) || pkg.contains(&"nvidia".to_string())) {
                continue;
            }
        } else if hw_type == "NVIDIA".to_string() {
            if (pkg.contains(&"rocm".to_string()) || pkg.contains(&"amd".to_string())) {
                continue;
            }
        } else if hw_type == "CPU".to_string() {
            if (pkg.contains(&"cuda".to_string()) || pkg.contains(&"nvidia".to_string()) || pkg.contains(&"rocm".to_string()) || pkg.contains(&"amd".to_string()) || pkg.contains(&"directml".to_string())) {
                continue;
            }
        }
        patched.push(line);
    }
    let mut accel_libs = vec![];
    if hw_type == "NVIDIA".to_string() {
        let mut accel_libs = vec!["onnxruntime-gpu".to_string(), "torch".to_string(), "torchvision".to_string(), "torchaudio".to_string()];
    } else if hw_type == "AMD".to_string() {
        if sys::platform == "win32".to_string() {
            let mut accel_libs = vec!["onnxruntime".to_string(), "torch".to_string(), "torchvision".to_string(), "torchaudio".to_string()];
        } else {
            let mut accel_libs = vec!["onnxruntime-rocm".to_string(), "torch".to_string(), "torchvision".to_string(), "torchaudio".to_string()];
        }
    } else if hw_type == "CPU".to_string() {
        let mut accel_libs = vec!["onnxruntime".to_string(), "torch".to_string(), "torchvision".to_string(), "torchaudio".to_string()];
    }
    if (sys::platform == "win32".to_string() && vec!["NVIDIA".to_string(), "AMD".to_string(), "CPU".to_string()].contains(&hw_type)) {
        accel_libs.push("onnxruntime-directml".to_string());
    }
    let mut patched_pkgs = patched.iter().filter(|l| (l.trim().to_string() && !l.trim().to_string().starts_with(&*"#".to_string()))).map(|l| l.trim().to_string().to_lowercase()).collect::<Vec<_>>().into_iter().collect::<HashSet<_>>();
    for lib in accel_libs.iter() {
        if !patched_pkgs.contains(&lib) {
            patched.push((lib + "\n".to_string()));
        }
    }
    let mut patched_path = (req_path + ".patched".to_string());
    let mut f = File::create(patched_path)?;
    {
        f.writelines(patched);
    }
    Ok(patched_path)
}

/// Catch import errors.
pub fn catch_import_errors() -> Result<()> {
    // Catch import errors.
    // try:
    {
        // TODO: from config_system import config, EMOJI
        // TODO: from utils import safe_print, HardwareProfiler, prune_zombies, kill_process_tree, logger, DiagnosticRunner
        (config, EMOJI, safe_print, HardwareProfiler, prune_zombies, kill_process_tree, logger, DiagnosticRunner)
    }
    // except Exception as e:
}

/// Checks for _bin/llama-server::exe.new and performs atomic swap.
pub fn atomic_update_check() -> Result<()> {
    // Checks for _bin/llama-server::exe.new and performs atomic swap.
    let mut exe_path = (config::BIN_DIR / "llama-server::exe".to_string());
    let mut new_path = (config::BIN_DIR / "llama-server::exe.new".to_string());
    let mut bak_path = (config::BIN_DIR / "llama-server::exe.bak".to_string());
    if new_path.exists() {
        safe_print(format!("{} Found engine update! Performing atomic swap...", EMOJI["loading".to_string()]));
        // try:
        {
            if exe_path.exists() {
                if bak_path.exists() {
                    std::fs::remove_file(bak_path).ok();
                }
                os::rename(exe_path, bak_path);
            }
            os::rename(new_path, exe_path);
            safe_print(format!("{} Engine updated successfully.", EMOJI["success".to_string()]));
        }
        // except Exception as e:
    }
}

/// Main.
pub async fn main() -> Result<()> {
    // Main.
    // try:
    {
        safe_print(format!("\n{} ZenAI v3.1 Orchestrator Starting...\n", EMOJI["sparkles".to_string()]));
        // try:
        {
            if !prune_zombies(/* auto_confirm= */ true) {
                safe_print(format!("{} Startup cancelled by user.", EMOJI["info".to_string()]));
                return;
            }
        }
        // except Exception as e:
        if !DiagnosticRunner.run_smoke_test().await {
            safe_print(format!("{} Critical System Health Check Failed. Attempting to proceed...", EMOJI["warning".to_string()]));
        }
        atomic_update_check();
        // TODO: from zena_mode import server
        safe_print(format!("{} Launching Engine on Port {}...", EMOJI["loading".to_string()], config::llm_port));
        server::start_server();
    }
    // except KeyboardInterrupt as _e:
    // except SystemExit as se:
    // except Exception as e:
    // finally:
        Ok(safe_print(format!("{} Cleaning up processes...", EMOJI["info".to_string()])))
}
