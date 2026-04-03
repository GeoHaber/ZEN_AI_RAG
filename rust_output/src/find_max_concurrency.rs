use anyhow::{Result, Context};
use crate::test_utils::{_default_models_dir};
use std::collections::HashMap;

pub static ROOT_DIR: std::sync::LazyLock<String /* Path.parent().unwrap_or(std::path::Path::new("")).parent().unwrap_or(std::path::Path::new("")).resolve */> = std::sync::LazyLock::new(|| Default::default());

pub const BIN_DIR: &str = "ROOT_DIR / '_bin";

pub const CLI_EXE: &str = "BIN_DIR / 'llama-cli.exe";

pub static MODELS_DIR: std::sync::LazyLock<_default_models_dir> = std::sync::LazyLock::new(|| Default::default());

pub const REPORT_FILE: &str = "ROOT_DIR / 'concurrency_report.csv";

pub const PROMPT: &str = "Write a short poem about the concept of infinity.";

/// MaxConcurrencyTester class.
#[derive(Debug, Clone)]
pub struct MaxConcurrencyTester {
    pub max_cap: String,
    pub models: String /* self._scan_models */,
    pub baseline_latency: i64,
}

impl MaxConcurrencyTester {
    /// Initialize instance.
    pub fn new(max_cap: String) -> Self {
        Self {
            max_cap,
            models: self._scan_models(),
            baseline_latency: 0,
        }
    }
    pub fn _scan_models(&self) -> () {
        if !MODELS_DIR.exists() {
            vec![]
        }
        { let mut v = MODELS_DIR.glob("*.gguf".to_string()).into_iter().collect::<Vec<_>>().clone(); v.sort(); v }
    }
    /// Run single.
    pub fn run_single(&self, index: String, model: String, prompt: String) -> Result<()> {
        // Run single.
        let mut start_t = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        let mut cmd = vec![CLI_EXE.to_string(), "-m".to_string(), model.to_string(), "-p".to_string(), prompt, "-n".to_string(), "128".to_string(), "-c".to_string(), "2048".to_string(), "--temp".to_string(), "0.7".to_string()];
        // try:
        {
            let mut res = std::process::Command::new("sh").arg("-c").arg(cmd, /* cwd= */ BIN_DIR, /* capture_output= */ true, /* text= */ true, /* encoding= */ "utf-8".to_string().output().unwrap(), /* errors= */ "replace".to_string(), /* timeout= */ 180, /* shell= */ false);
            let mut duration = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_t);
            let mut success = (res.returncode == 0 && res.stdout.len() > 10);
            if !success {
                println!("[Err] Model {} Failed. Exit: {}", model.name, res.returncode);
                println!("STDERR: {}", res.stderr[..200]);
                // pass
            }
            HashMap::from([("index".to_string(), index), ("model".to_string(), model.name), ("duration".to_string(), duration), ("success".to_string(), success), ("output".to_string(), (res.stdout[..50].replace(&*"\n".to_string(), &*" ".to_string()) + "...".to_string()))])
        }
        // except Exception as e:
    }
    /// Run.
    pub fn run(&mut self) -> () {
        // Run.
        println!("--- THOUGHPUT TEST: SEQUENTIAL VS PARALLEL (Models: {}) ---", self.models::len());
        println!("{:<3} | {:<10} | {:<10} | {:<8} | {}", "N".to_string(), "Seq Time".to_string(), "Par Time".to_string(), "Speedup".to_string(), "Status".to_string());
        println!("{}", ("-".to_string() * 60));
        for n in 1..(self.max_cap + 1).iter() {
            let mut current_models = vec![];
            for i in 0..n.iter() {
                current_models.push(self.models[(i % self.models::len())]);
            }
            let mut seq_start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            for (i, model) in current_models.iter().enumerate().iter() {
                self.run_single(i, model, PROMPT);
            }
            let mut seq_duration = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - seq_start);
            std::thread::sleep(std::time::Duration::from_secs_f64(1));
            let mut par_start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            let mut futures = vec![];
            let mut results = vec![];
            let mut executor = ThreadPoolExecutor(/* max_workers= */ n);
            {
                for (i, model) in current_models.iter().enumerate().iter() {
                    futures.push(executor.submit(self.run_single, i, model, PROMPT));
                }
                for ft in as_completed(futures).iter() {
                    let mut res = ft.result();
                    results.push(res);
                    if res["success".to_string()] {
                        // pass
                    }
                }
            }
            let mut par_duration = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - par_start);
            let mut speedup = if par_duration > 0 { (seq_duration / par_duration) } else { 0 };
            let mut status = "GAINING".to_string();
            if speedup < 0.8_f64 {
                let mut status = "THRASHING".to_string();
            } else if speedup < 1.2_f64 {
                let mut status = "SATURATED".to_string();
            } else if speedup > 1.5_f64 {
                let mut status = "EFFICIENT".to_string();
            }
            println!("{:<3} | {:<9.2}s | {:<9.2}s | {:<7.2}x | {}", n, seq_duration, par_duration, speedup, status);
            if (results && results[0]["success".to_string()]) {
                // pass
            }
            std::thread::sleep(std::time::Duration::from_secs_f64(2));
        }
        println!("{}", ("-".to_string() * 60));
        println!("{}", "Test Complete.".to_string());
    }
}
