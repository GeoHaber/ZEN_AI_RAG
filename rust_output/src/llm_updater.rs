/// Core/llm_updater::py — ZEN_RAG LLM Package Freshness Checker
/// =============================================================
/// Checks PyPI for newer versions of llama-cpp-python (and optionally
/// other key inference backends) and provides a safe upgrade helper.
/// 
/// Usage (in sidebar::py):
/// from Core.llm_updater import check_llamacpp_update, run_upgrade
/// 
/// installed, latest = check_llamacpp_update()   # cached via Streamlit
/// if latest:
/// st.sidebar::info(f"llama.cpp {latest} available!")
/// if st.sidebar::button("Update"):
/// run_upgrade(progress_cb=st.sidebar::empty().text)

use anyhow::{Result, Context};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static WATCHED_PACKAGES: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

/// Return installed version of a package, or None if not found.
pub fn get_installed_version(package: String) -> Result<Option<String>> {
    // Return installed version of a package, or None if not found.
    // try:
    {
        // TODO: from importlib.metadata import version
        version(package)
    }
    // except Exception as exc:
    // try:
    {
        let mut result = std::process::Command::new("sh").arg("-c").arg(vec![sys::executable, "-m".to_string().output().unwrap(), "pip".to_string(), "show".to_string(), package], /* capture_output= */ true, /* text= */ true, /* timeout= */ 10, /* shell= */ false);
        for line in result.stdout.lines().map(|s| s.to_string()).collect::<Vec<String>>().iter() {
            if line.starts_with(&*"Version:".to_string()) {
                line.split(":".to_string(), 1)[1].trim().to_string()
            }
        }
    }
    // except Exception as exc:
    Ok(None)
}

/// Query PyPI JSON API for the latest release version.
pub fn get_latest_pypi_version(package: String, timeout: i64) -> Result<Option<String>> {
    // Query PyPI JSON API for the latest release version.
    // try:
    {
        // TODO: import requests
        let mut resp = /* reqwest::get( */&format!("https://pypi.org/pypi/{}/json", package)).cloned().unwrap_or(/* timeout= */ timeout);
        if resp.status_code == 200 {
            let mut data = resp.json();
            data["info".to_string()]["version".to_string()]
        }
    }
    // except Exception as e:
    Ok(None)
}

/// Return true if latest > installed.
pub fn is_newer(installed: String, latest: String) -> Result<bool> {
    // Return true if latest > installed.
    if (!installed || !latest) {
        false
    }
    // try:
    {
        if _PACKAGING {
            Version(latest) > Version(installed)
        }
        let _parts = |v| {
            /* tuple */ (v.split(".".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[..3].iter().filter(|x| x.chars().all(|c| c.is_ascii_digit())).map(|x| x.to_string().parse::<i64>().unwrap_or(0)).collect::<Vec<_>>())
        };
        _parts(latest) > _parts(installed)
    }
    // except Exception as _e:
}

/// Check if a newer llama-cpp-python is available on PyPI.
/// 
/// Returns:
/// (installed_version, latest_version)
/// If no update available or check fails: (installed, None)
pub fn check_llamacpp_update(timeout: i64) -> (Option<String>, Option<String>) {
    // Check if a newer llama-cpp-python is available on PyPI.
    // 
    // Returns:
    // (installed_version, latest_version)
    // If no update available or check fails: (installed, None)
    let mut pkg = "llama-cpp-python".to_string();
    let mut installed = get_installed_version(pkg);
    if !installed {
        logger.debug("llama-cpp-python not installed — skipping update check".to_string());
        (None, None)
    }
    let mut latest = get_latest_pypi_version(pkg, /* timeout= */ timeout);
    if (latest && is_newer(installed, latest)) {
        logger.info(format!("llama-cpp-python update available: {} → {}", installed, latest));
        (installed, latest)
    }
    (installed, None)
}

/// Check all WATCHED_PACKAGES for updates.
/// 
/// Returns:
/// dict of package_name → (installed_version, latest_version)
/// Only includes packages that have an update available.
pub fn check_all_updates(timeout: i64) -> HashMap<String, (String, String)> {
    // Check all WATCHED_PACKAGES for updates.
    // 
    // Returns:
    // dict of package_name → (installed_version, latest_version)
    // Only includes packages that have an update available.
    let mut updates = HashMap::new();
    for (pkg, meta) in WATCHED_PACKAGES.iter().iter() {
        let mut installed = get_installed_version(pkg);
        if !installed {
            continue;
        }
        let mut latest = get_latest_pypi_version(pkg, /* timeout= */ timeout);
        if (latest && is_newer(installed, latest)) {
            updates[pkg] = (installed, latest);
        }
    }
    updates
}

/// Run pip upgrade for a package.
/// 
/// Args:
/// package:        Package name (default: llama-cpp-python)
/// target_version: If set, installs that exact version
/// progress_cb:    Called with status strings during install
/// extra_pip_args: Extra args passed to pip (e.g. ["--no-deps"])
/// 
/// Returns:
/// (success, message)
pub fn run_upgrade(package: String, target_version: Option<String>, progress_cb: Option<Box<dyn Fn(serde_json::Value)>>, extra_pip_args: Option<Vec>) -> Result<(bool, String)> {
    // Run pip upgrade for a package.
    // 
    // Args:
    // package:        Package name (default: llama-cpp-python)
    // target_version: If set, installs that exact version
    // progress_cb:    Called with status strings during install
    // extra_pip_args: Extra args passed to pip (e.g. ["--no-deps"])
    // 
    // Returns:
    // (success, message)
    let mut spec = if target_version { format!("{}=={}", package, target_version) } else { format!("{}", package) };
    let mut cmd = vec![sys::executable, "-m".to_string(), "pip".to_string(), "install".to_string(), "--upgrade".to_string(), spec];
    if extra_pip_args {
        cmd.extend(extra_pip_args);
    }
    if progress_cb {
        progress_cb(format!("Running: {}", cmd.join(&" ".to_string())));
    }
    logger.info(format!("Running upgrade: {}", cmd));
    // try:
    {
        let mut proc = subprocess::Popen(cmd, /* stdout= */ subprocess::PIPE, /* stderr= */ subprocess::STDOUT, /* text= */ true, /* bufsize= */ 1, /* shell= */ false);
        let mut output_lines = vec![];
        for line in proc.stdout.iter() {
            let mut line = line.trim_end().to_string();
            output_lines.push(line);
            if progress_cb {
                progress_cb(line);
            }
            logger.debug(format!("pip: {}", line));
        }
        proc.wait(/* timeout= */ 300);
        let mut success = proc.returncode == 0;
        let mut msg = output_lines[-5..].join(&"\n".to_string());
        if success {
            logger.info(format!("Upgrade of {} succeeded", package));
            (true, format!("✅ {} upgraded successfully.\n{}", package, msg))
        } else {
            logger.error(format!("Upgrade of {} failed (rc={})", package, proc.returncode));
            (false, format!("❌ Upgrade failed (exit {}).\n{}", proc.returncode, msg))
        }
    }
    // except subprocess::TimeoutExpired as _e:
    // except Exception as e:
}

/// Return a PyPI changelog/release URL for the package.
pub fn get_changelog_url(package: String) -> String {
    // Return a PyPI changelog/release URL for the package.
    let mut url_map = HashMap::from([("llama-cpp-python".to_string(), "https://github.com/abetlen/llama-cpp-python/releases".to_string()), ("sentence-transformers".to_string(), "https://github.com/UKPLab/sentence-transformers/releases".to_string()), ("faster-whisper".to_string(), "https://github.com/SYSTRAN/faster-whisper/releases".to_string())]);
    url_map.get(&package).cloned().unwrap_or(format!("https://pypi.org/project/{}/#history", package))
}
