/// Download a GGUF model into MODEL_CACHE_DIR (default: ./models).
/// 
/// Presets (when MODEL_REPO_ID is not set):
/// llama32   — DEFAULT: Llama-3.2-3B-Instruct Q4_K_M (~2 GB; may need HF token if gated)
/// tinyllama — TinyLlama-1.1B chat (~0.6 GB)
/// gccl      — GCCL-Medical-LLM-8B Q4_K_M (~4.7 GB)
/// 
/// Usage:
/// python download_model::py                  # Llama-3.2-3B-Instruct (default)
/// python download_model::py llama32
/// python download_model::py tinyllama
/// python download_model::py gccl
/// 
/// Env override (wins over preset):
/// MODEL_REPO_ID    Hugging Face repo id
/// MODEL_FILENAME   file in repo (required for custom repos not listed in presets; if omitted, filename
/// is inferred when MODEL_REPO_ID matches a preset repo, else defaults to Llama 3.2 Q4 name)
/// MODEL_CACHE_DIR  root directory for models (default: ./models)
/// 
/// Gated models: accept the license on huggingface.co and set HF_TOKEN or run
/// `huggingface-cli login` if download fails with 401/403.
/// 
/// Progress: tqdm is enabled on stderr; Docker logs also get **newline** ``[model] … X%`` lines because
/// ``\r`` updates often look "stuck". Chunk size is reduced (default 1 MiB) so the bar moves sooner on slow links.
/// 
/// Env: ``HF_HUB_DISABLE_PROGRESS_BARS=1`` (quiet), ``HF_HUB_DOWNLOAD_TIMEOUT`` (seconds between stream reads,
/// default **120** here), ``ZENAI_HF_DOWNLOAD_CHUNK_MB`` (1–10, default **1**).

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::path::PathBuf;

pub const _DEFAULT_HF_READ_TIMEOUT_SEC: &str = "120";

pub const _DEFAULT_HF_CHUNK_MB: &str = "1";

pub static PRESETS: std::sync::LazyLock<HashMap<String, (String, String)>> = std::sync::LazyLock::new(|| HashMap::new());

pub static MODEL_PROFILES: std::sync::LazyLock<HashMap<String, HashMap>> = std::sync::LazyLock::new(|| HashMap::new());

pub const DEFAULT_PRESET: &str = "llama32";

/// Make tqdm/http_get show a bar in Docker (no TTY) by reporting isatty() true on stderr.
#[derive(Debug, Clone)]
pub struct _StderrActsAsTTY {
}

impl _StderrActsAsTTY {
    pub fn new(real: TextIO) -> Self {
        Self {
        }
    }
    pub fn isatty(&self) -> bool {
        true
    }
    pub fn __getattr__(&self, name: String) -> Box<dyn std::any::Any> {
        /* getattr(self._real, name) */ Default::default()
    }
}

/// huggingface_hub disables tqdm when stderr is not a TTY (common in ``docker run`` without ``-t``).
/// Also avoids ``disable=true`` when the hub logger level is logging::NOTSET.
/// Respect ``HF_HUB_DISABLE_PROGRESS_BARS=1`` to keep output quiet.
pub fn _cli_download_progress() -> Result<Iterator<()>> {
    // huggingface_hub disables tqdm when stderr is not a TTY (common in ``docker run`` without ``-t``).
    // Also avoids ``disable=true`` when the hub logger level is logging::NOTSET.
    // Respect ``HF_HUB_DISABLE_PROGRESS_BARS=1`` to keep output quiet.
    let mut off = ("1".to_string(), "true".to_string(), "yes".to_string()).contains(&std::env::var(&"HF_HUB_DISABLE_PROGRESS_BARS".to_string()).unwrap_or_default().cloned().unwrap_or("".to_string()).trim().to_string().to_lowercase());
    if off {
        /* yield */;
        return;
    }
    logging::getLogger("huggingface_hub".to_string()).setLevel(logging::INFO);
    // try:
    {
        // TODO: from huggingface_hub.utils import enable_progress_bars
        enable_progress_bars();
    }
    // except (ImportError, AttributeError) as _e:
    let mut real_err = sys::stderr;
    sys::stderr = _StderrActsAsTTY(real_err);
    // try:
    {
        /* yield */;
    }
    // finally:
        sys::stderr = real_err;
        // try:
        {
            real_err.flush();
        }
        // except OSError as _e:
}

/// Larger read timeout + smaller HTTP chunks → fewer false 'stuck at 0%%' impressions.
pub fn _apply_hf_hub_download_tweaks() -> Result<()> {
    // Larger read timeout + smaller HTTP chunks → fewer false 'stuck at 0%%' impressions.
    os::environ.entry("HF_HUB_DOWNLOAD_TIMEOUT".to_string()).or_insert(_DEFAULT_HF_READ_TIMEOUT_SEC);
    os::environ.entry("HF_HUB_ENABLE_HF_TRANSFER".to_string()).or_insert("0".to_string());
    // try:
    {
        let mut mb = int(std::env::var(&"ZENAI_HF_DOWNLOAD_CHUNK_MB".to_string()).unwrap_or_default().cloned().unwrap_or(_DEFAULT_HF_CHUNK_MB), 10);
    }
    // except ValueError as _e:
    let mut mb = 1.max(10.min(mb));
    let mut chunk = ((mb * 1024) * 1024);
    // try:
    {
        // TODO: import huggingface_hub.constants as hf_constants
        hf_constants.DOWNLOAD_CHUNK_SIZE = chunk;
    }
    // except (ImportError, AttributeError) as _e:
}

/// Hugging Face http_get uses tqdm with carriage-return refresh; Docker log drivers often show one frozen line.
/// Subclass tqdm and emit newline status to stdout every few percent / MiB.
pub fn _install_line_logged_tqdm() -> Result<Box<dyn std::any::Any>> {
    // Hugging Face http_get uses tqdm with carriage-return refresh; Docker log drivers often show one frozen line.
    // Subclass tqdm and emit newline status to stdout every few percent / MiB.
    // try:
    {
        // TODO: import huggingface_hub.file_download as fd
    }
    // except ImportError as _e:
    let mut _Base = fd.tqdm;
    // TODO: nested class _LineLoggedTqdm
    fd.tqdm = _LineLoggedTqdm;
    Ok(None)
}

/// Periodic message so operators know we did not exit (and bytes may still be trickling).
pub fn _download_heartbeat() -> Result<Iterator<threading::Event>> {
    // Periodic message so operators know we did not exit (and bytes may still be trickling).
    let mut stop = /* Event */ ();
    let _run = || {
        let mut t0 = time::monotonic();
        let mut first = 30.0_f64;
        while !stop.wait(first) {
            let mut first = 60.0_f64;
            let mut elapsed = (time::monotonic() - t0).to_string().parse::<i64>().unwrap_or(0);
            println!("[model] … still downloading ({}s elapsed; if progress stays at 0% for many minutes, check network, VPN, or HF_TOKEN for gated repos)", elapsed);
        }
    };
    let mut th = std::thread::spawn(|| {});
    th.start();
    // try:
    {
        /* yield stop */;
    }
    // finally:
        Ok(stop.set())
}

/// Env MODEL_REPO_ID overrides preset.
/// 
/// If MODEL_FILENAME is set, use it. Otherwise, if MODEL_REPO_ID matches a PRESETS repo id,
/// use that preset's filename. Else default filename to the default preset (Llama-3.2-3B-Instruct Q4_K_M);
/// set MODEL_FILENAME explicitly for other repos.
pub fn resolve_repo_and_file(args: argparse::Namespace) -> (String, String) {
    // Env MODEL_REPO_ID overrides preset.
    // 
    // If MODEL_FILENAME is set, use it. Otherwise, if MODEL_REPO_ID matches a PRESETS repo id,
    // use that preset's filename. Else default filename to the default preset (Llama-3.2-3B-Instruct Q4_K_M);
    // set MODEL_FILENAME explicitly for other repos.
    let mut env_repo = std::env::var(&"MODEL_REPO_ID".to_string()).unwrap_or_default().cloned().unwrap_or("".to_string()).trim().to_string();
    if env_repo {
        let mut env_file = std::env::var(&"MODEL_FILENAME".to_string()).unwrap_or_default().cloned().unwrap_or("".to_string()).trim().to_string();
        if env_file {
            (env_repo, env_file)
        }
        for (repo_id, filename) in PRESETS.values().iter() {
            if repo_id == env_repo {
                (env_repo, filename)
            }
        }
        (env_repo, PRESETS[&DEFAULT_PRESET][1])
    }
    PRESETS[&args.preset]
}

pub fn main() -> Result<i64> {
    let mut parser = argparse.ArgumentParser(/* description= */ "Download a GGUF model for ZenAIos (llama-cpp / chat).".to_string(), /* epilog= */ format!("Default preset: {}. Set MODEL_REPO_ID (+ optional MODEL_FILENAME) to override.", DEFAULT_PRESET));
    parser.add_argument("preset".to_string(), /* nargs= */ "?".to_string(), /* default= */ DEFAULT_PRESET, /* choices= */ { let mut v = PRESETS.keys().clone(); v.sort(); v }, /* metavar= */ "PRESET".to_string(), /* help= */ format!("Model preset when MODEL_REPO_ID is unset (default: {}). Choices: {}.", DEFAULT_PRESET, { let mut v = PRESETS.clone(); v.sort(); v }.join(&", ".to_string())));
    parser.add_argument("--profile".to_string(), /* choices= */ { let mut v = MODEL_PROFILES.keys().clone(); v.sort(); v }, /* default= */ None, /* help= */ ("Use a named model profile (overrides preset). Profiles: ".to_string() + { let mut v = MODEL_PROFILES.clone(); v.sort(); v }.join(&", ".to_string())));
    let mut args = parser.parse_args();
    if args.profile {
        let mut profile = MODEL_PROFILES[&args.profile];
        args.preset = profile["preset".to_string()];
        println!("[model] profile: {} — {}", args.profile, profile["description".to_string()]);
        println!("[model]   recommended ctx: {}, temp: {}", profile["recommended_ctx".to_string()], profile["temperature".to_string()]);
        let mut bm = profile.get(&"benchmark".to_string()).cloned().unwrap_or(HashMap::new());
        if bm {
            println!("[model]   benchmark: ≥{} tok/s, ≤{}ms first token", bm.get(&"min_tokens_per_sec".to_string()).cloned().unwrap_or("?".to_string()), bm.get(&"max_first_token_ms".to_string()).cloned().unwrap_or("?".to_string()));
        }
    }
    _apply_hf_hub_download_tweaks();
    // try:
    {
        // TODO: from huggingface_hub import hf_hub_download
    }
    // except ImportError as _e:
    _install_line_logged_tqdm();
    let (mut repo_id, mut filename) = resolve_repo_and_file(args);
    let mut cache_root = PathBuf::from(std::env::var(&"MODEL_CACHE_DIR".to_string()).unwrap_or_default().cloned().unwrap_or("./models".to_string())).expanduser().canonicalize().unwrap_or_default();
    let mut model_stem = PathBuf::from(filename).file_stem().unwrap_or_default().to_str().unwrap_or("");
    let mut target_dir = (cache_root / model_stem);
    target_dir.create_dir_all();
    let mut target_file = (target_dir / filename);
    if target_file.is_file() {
        println!("[model] already present: {}", target_file);
        0
    }
    println!("[model] repo: {}", repo_id);
    println!("[model] file: {}", filename);
    println!("[model] target: {}", target_dir);
    println!("{}", "[model] downloading (tqdm + periodic [model] … lines below)…".to_string());
    let _ctx = _cli_download_progress();
    let _ctx = _download_heartbeat();
    {
        let mut local_path = hf_hub_download(/* repo_id= */ repo_id, /* filename= */ filename, /* local_dir= */ target_dir.to_string(), /* local_dir_use_symlinks= */ false);
    }
    println!("[model] downloaded: {}", local_path);
    Ok(0)
}
