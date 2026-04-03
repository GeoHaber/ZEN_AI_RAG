use anyhow::{Result, Context};
use crate::test_utils::{_default_models_dir};

pub static _MODELS_DIR: std::sync::LazyLock<_default_models_dir> = std::sync::LazyLock::new(|| Default::default());

pub const MODEL_PATH: &str = "_MODELS_DIR / 'qwen2.5-0.5b-instruct-q5_k_m.gguf";

pub static ROOT_DIR: std::sync::LazyLock<String /* Path.parent().unwrap_or(std::path::Path::new("")).parent().unwrap_or(std::path::Path::new("")).resolve */> = std::sync::LazyLock::new(|| Default::default());

pub const BIN_DIR: &str = "ROOT_DIR / '_bin";

pub const PARALLEL_EXE: &str = "BIN_DIR / 'llama-parallel.exe";

/// Run llama-parallel.exe to stress test the decoding engine.
/// This simulates multiple users generating text simultaneously.
pub fn test_parallel_stress() -> Result<()> {
    // Run llama-parallel.exe to stress test the decoding engine.
    // This simulates multiple users generating text simultaneously.
    if !PARALLEL_EXE.exists() {
        pytest.fail(format!("llama-parallel.exe not found at {}", PARALLEL_EXE));
    }
    if !MODEL_PATH.exists() {
        pytest.skip(format!("Test Model not found at {}", MODEL_PATH));
    }
    println!("\n[Stress] Running Parallel Decoding Test...");
    println!("Model: {}", MODEL_PATH.name);
    let mut cmd = vec![PARALLEL_EXE.to_string(), "--model".to_string(), MODEL_PATH.to_string(), "-ns".to_string(), "4".to_string(), "-n".to_string(), "64".to_string(), "-c".to_string(), "2048".to_string(), "-p".to_string(), "The future of AI is".to_string(), "--temp".to_string(), "0.7".to_string()];
    // try:
    {
        let mut result = std::process::Command::new("sh").arg("-c").arg(cmd, /* cwd= */ BIN_DIR, /* capture_output= */ true, /* text= */ true, /* timeout= */ 120, /* shell= */ false).output().unwrap();
        if result.returncode != 0 {
            println!("{}", "STDOUT:".to_string(), result.stdout);
            println!("{}", "STDERR:".to_string(), result.stderr);
            pytest.fail(format!("llama-parallel failed with code {}", result.returncode));
        }
        println!("[Stress] Success! Output sample:\n{}...", result.stdout[..200]);
    }
    // except subprocess::TimeoutExpired as _e:
}
