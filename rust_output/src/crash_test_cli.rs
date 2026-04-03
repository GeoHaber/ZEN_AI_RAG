use anyhow::{Result, Context};
use crate::test_utils::{_default_models_dir};
use crate::test_utils::{scan_model};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};

pub static ROOT_DIR: std::sync::LazyLock<String /* Path.parent().unwrap_or(std::path::Path::new("")).parent().unwrap_or(std::path::Path::new("")).resolve */> = std::sync::LazyLock::new(|| Default::default());

pub const BIN_DIR: &str = "ROOT_DIR / '_bin";

pub const CLI_EXE: &str = "BIN_DIR / 'llama-cli.exe";

pub const REPORT_FILE: &str = "ROOT_DIR / 'cli_crash_report.csv";

pub static MODELS_DIR: std::sync::LazyLock<_default_models_dir> = std::sync::LazyLock::new(|| Default::default());

pub static PROMPTS: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

/// CLITester class.
#[derive(Debug, Clone)]
pub struct CLITester {
    pub max_N: String,
    pub safe_mode: String,
    pub models: scan_models,
    pub results: Vec<serde_json::Value>,
}

impl CLITester {
    /// Initialize instance.
    pub fn new(max_N: String, safe_mode: String) -> Self {
        Self {
            max_N,
            safe_mode,
            models: scan_models(MODELS_DIR),
            results: vec![],
        }
    }
    /// Run one standalone llama-cli process
    pub fn run_single_cli(&self, index: String, model_path: String, prompt: String) -> Result<()> {
        // Run one standalone llama-cli process
        let mut start_t = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        let mut cmd = vec![CLI_EXE.to_string(), "-m".to_string(), model_path.to_string(), "-p".to_string(), prompt, "-n".to_string(), "64".to_string(), "-c".to_string(), "2048".to_string()];
        // try:
        {
            let mut res = std::process::Command::new("sh").arg("-c").arg(cmd, /* cwd= */ BIN_DIR, /* capture_output= */ true, /* text= */ true, /* encoding= */ "utf-8".to_string().output().unwrap(), /* errors= */ "replace".to_string(), /* timeout= */ 300, /* shell= */ false);
            let mut end_t = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            let mut duration = (end_t - start_t);
            let mut success = res.returncode == 0;
            if (success && res.stdout.len() < 10) {
                let mut success = false;
                println!("[Err] Output too short for {}", model_path.file_name().unwrap_or_default().to_str().unwrap_or(""));
            }
            if !success {
                println!("[Err] {} Failed. Exit:{}", model_path.file_name().unwrap_or_default().to_str().unwrap_or(""), res.returncode);
                println!("--- STDERR ---\n{}\n--- STDOUT ---\n{}", res.stderr[..500], res.stdout[..500]);
                // pass
            }
            HashMap::from([("index".to_string(), index), ("model".to_string(), model_path.file_name().unwrap_or_default().to_str().unwrap_or("")), ("prompt".to_string(), (prompt[..20] + "...".to_string())), ("duration".to_string(), duration), ("success".to_string(), success), ("stdout".to_string(), res.stdout[..100].replace(&*"\n".to_string(), &*" ".to_string()))])
        }
        // except subprocess::TimeoutExpired as _e:
        // except Exception as e:
    }
    /// Run cycle.
    pub fn run_cycle(&mut self, N: String) -> Result<()> {
        // Run cycle.
        println!("\n[CLI-Test] Starting Cycle N={} (Parallel Instances) ---", N);
        let mut futures = vec![];
        let mut cycle_results = vec![];
        let mut start_cycle = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        let mut executor = ThreadPoolExecutor(/* max_workers= */ N);
        {
            for i in 0..N.iter() {
                if !self.models {
                    println!("{}", "[Error] No models found!".to_string());
                    false
                }
                let mut model = self.models[(i % self.models::len())];
                let mut prompt = PROMPTS[(i % PROMPTS.len())];
                futures.push(executor.submit(self.run_single_cli, i, model, prompt));
            }
            for ft in as_completed(futures).iter() {
                cycle_results.push(ft.result());
            }
        }
        let mut end_cycle = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        let mut total_cycle_time = (end_cycle - start_cycle);
        let mut success_count = cycle_results.iter().filter(|r| r["success".to_string()]).map(|r| 1).collect::<Vec<_>>().iter().sum::<i64>();
        let mut avg_time = 0;
        if success_count > 0 {
            let mut avg_time = statistics.mean(cycle_results.iter().filter(|r| r["success".to_string()]).map(|r| r["duration".to_string()]).collect::<Vec<_>>());
        }
        println!("[CLI-Test] Cycle N={} Complete in {:.2}s", N, total_cycle_time);
        println!("           Success: {}/{}", success_count, N);
        println!("           Avg Duration Per Instance: {:.2}s", avg_time);
        let mut row = HashMap::from([("instances".to_string(), N), ("success_rate".to_string(), (success_count / N)), ("avg_latency".to_string(), avg_time), ("total_wall_time".to_string(), total_cycle_time), ("models_used".to_string(), cycle_results.iter().map(|r| r["model".to_string()]).collect::<Vec<_>>().join(&"|".to_string()))]);
        self.results.push(row);
        let mut file_exists = REPORT_FILE.exists();
        let mut f = File::create(REPORT_FILE)?;
        {
            let mut w = csv::DictWriter(f, /* fieldnames= */ row.keys());
            if !file_exists {
                w.writeheader();
            }
            w.writerow(row);
        }
        Ok(success_count == N)
    }
    /// Run.
    pub fn run(&mut self) -> () {
        // Run.
        if REPORT_FILE.exists() {
            std::fs::remove_file(REPORT_FILE).ok();
        }
        for n in 1..(self.max_N + 1).iter() {
            let mut success = self.run_cycle(n);
            if !success {
                println!("[CLI-Test] Crash/Failure detected at N={}. Stopping.", n);
                break;
            }
            if (self.safe_mode && n >= 2) {
                println!("{}", "[CLI-Test] Safe Mode: Stopping at N=2.".to_string());
                break;
            }
            std::thread::sleep(std::time::Duration::from_secs_f64(2));
        }
    }
}
