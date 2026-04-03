use anyhow::{Result, Context};
use crate::test_utils::{_default_models_dir};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};

pub static ROOT_DIR: std::sync::LazyLock<String /* Path.parent().unwrap_or(std::path::Path::new("")).parent().unwrap_or(std::path::Path::new("")).resolve */> = std::sync::LazyLock::new(|| Default::default());

pub const BIN_DIR: &str = "ROOT_DIR / '_bin";

pub const CLI_EXE: &str = "BIN_DIR / 'llama-cli.exe";

pub static MODELS_DIR: std::sync::LazyLock<_default_models_dir> = std::sync::LazyLock::new(|| Default::default());

pub const LOG_FILE: &str = "ROOT_DIR / 'soak_report.log";

pub static PROMPTS: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

/// SoakTester class.
#[derive(Debug, Clone)]
pub struct SoakTester {
    pub target_duration: String,
    pub start_time: String /* time::time */,
    pub models: String /* self._scan_models */,
    pub cycle_count: i64,
    pub total_requests: i64,
    pub failed_requests: i64,
}

impl SoakTester {
    /// Initialize instance.
    pub fn new(hours: String) -> Self {
        Self {
            target_duration: (hours * 3600),
            start_time: std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64(),
            models: self._scan_models(),
            cycle_count: 0,
            total_requests: 0,
            failed_requests: 0,
        }
    }
    /// Log.
    pub fn log(&self, msg: String) -> Result<()> {
        // Log.
        let mut ts = datetime::datetime.now().strftime("%Y-%m-%d %H:%M:%S".to_string());
        let mut line = format!("[{}] {}", ts, msg);
        println!("{}", line);
        let mut f = File::create(LOG_FILE)?;
        {
            f.write((line + "\n".to_string()));
        }
    }
    pub fn _scan_models(&self) -> () {
        if !MODELS_DIR.exists() {
            vec![]
        }
        MODELS_DIR.glob("*.gguf".to_string()).into_iter().collect::<Vec<_>>()
    }
    /// Run a single chaos instance
    pub fn run_instance(&self, worker_id: String, model: String, prompt: String) -> Result<()> {
        // Run a single chaos instance
        let mut temp = ((random.uniform(0.5_f64, 0.9_f64) as f64) * 10f64.powi(1)).round() / 10f64.powi(1);
        let mut cmd = vec![CLI_EXE.to_string(), "-m".to_string(), model.to_string(), "-p".to_string(), prompt, "-n".to_string(), random.randint(64, 256).to_string(), "-c".to_string(), "2048".to_string(), "--temp".to_string(), temp.to_string()];
        let mut start_t = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        // try:
        {
            let mut res = std::process::Command::new("sh").arg("-c").arg(cmd, /* cwd= */ BIN_DIR, /* capture_output= */ true, /* text= */ true, /* encoding= */ "utf-8".to_string().output().unwrap(), /* errors= */ "replace".to_string(), /* timeout= */ 600, /* shell= */ false);
            let mut duration = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_t);
            let mut success = (res.returncode == 0 && res.stdout.len() > 10);
            let mut result_data = HashMap::from([("worker_id".to_string(), (worker_id + 1)), ("success".to_string(), success), ("duration".to_string(), duration), ("model".to_string(), model.name), ("prompt".to_string(), prompt), ("answer".to_string(), if success { (res.stdout[..200].replace(&*"\n".to_string(), &*" ".to_string()) + "...".to_string()) } else { "N/A".to_string() }), ("error".to_string(), None)]);
            if !success {
                result_data["error".to_string()] = format!("Exit {}", res.returncode);
            }
            result_data
        }
        // except Exception as e:
    }
    /// Run.
    pub fn run(&mut self) -> () {
        // Run.
        self.log(format!("--- STARTING NIGHTLY SOAK TEST (Target: {:.1} hours) ---", (self.target_duration / 3600)));
        self.log(format!("Models Available: {}", self.models::len()));
        while (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - self.start_time) < self.target_duration {
            self.cycle_count += 1;
            let mut N = random.choice(vec![1, 2, 2, 3, 3, 4, 6]);
            self.log(format!("\n--- Cycle {} | Threads: {} ---", self.cycle_count, N));
            let mut futures = vec![];
            let mut results = vec![];
            std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            let mut executor = ThreadPoolExecutor(/* max_workers= */ N);
            {
                for i in 0..N.iter() {
                    let mut model = random.choice(self.models);
                    let mut prompt = random.choice(PROMPTS);
                    futures.push(executor.submit(self.run_instance, i, model, prompt));
                }
                for ft in as_completed(futures).iter() {
                    let mut res = ft.result();
                    results.push(res);
                    let mut wid = res.get(&"worker_id".to_string()).cloned().unwrap_or("?".to_string());
                    let mut r#mod = res.get(&"model".to_string()).cloned().unwrap_or("Unknown".to_string());
                    let mut qst = res.get(&"prompt".to_string()).cloned().unwrap_or("Unknown".to_string());
                    let mut ans = res.get(&"answer".to_string()).cloned().unwrap_or("No Answer".to_string());
                    let mut dur = res.get(&"duration".to_string()).cloned().unwrap_or(0);
                    let mut log_block = format!("\n====== {} llama.cpp =====\nLLM model conected to: {}\nQuestion asked: {}\nAnswer received: {}\nTime stats: {:.2}s\n", wid, r#mod, qst, ans, dur);
                    self.log(log_block);
                }
            }
            let mut successes = results.iter().filter(|r| r["success".to_string()]).map(|r| r).collect::<Vec<_>>();
            let mut failures = results.iter().filter(|r| !r["success".to_string()]).map(|r| r).collect::<Vec<_>>();
            self.total_requests += results.len();
            self.failed_requests += failures.len();
            let mut avg_time = 0;
            if successes {
                let mut avg_time = (successes.iter().map(|r| r["duration".to_string()]).collect::<Vec<_>>().iter().sum::<i64>() / successes.len());
            }
            let mut elapsed_total = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - self.start_time);
            self.log(format!("Cycle Complete. Succ: {} Fail: {} AvgT: {:.2}s", successes.len(), failures.len(), avg_time));
            self.log(format!("Stats: TotalReq={} FailRate={:.1}% Elapsed={:.2}h", self.total_requests, ((self.failed_requests / self.total_requests) * 100), (elapsed_total / 3600)));
            if failures {
                self.log(format!("Errors this cycle: {}", failures.iter().map(|f| f["error".to_string()]).collect::<Vec<_>>()));
            }
            let mut delay = random.randint(1, 10);
            std::thread::sleep(std::time::Duration::from_secs_f64(delay));
        }
        self.log("--- SOAK TEST COMPLETE ---".to_string());
    }
}
