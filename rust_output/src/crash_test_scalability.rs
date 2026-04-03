use anyhow::{Result, Context};
use crate::test_utils::{_default_models_dir};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};

pub static ROOT_DIR: std::sync::LazyLock<String /* Path.parent().unwrap_or(std::path::Path::new("")).parent().unwrap_or(std::path::Path::new("")).resolve */> = std::sync::LazyLock::new(|| Default::default());

pub const START_SCRIPT: &str = "ROOT_DIR / 'start_llm::py";

pub static _MODELS_DIR: std::sync::LazyLock<_default_models_dir> = std::sync::LazyLock::new(|| Default::default());

pub const MODEL_PATH: &str = "_MODELS_DIR / 'qwen2.5-0.5b-instruct-q5_k_m.gguf";

pub const REPORT_FILE: &str = "ROOT_DIR / 'scalability_report.csv";

pub const START_PORT: i64 = 9000;

/// ScalabilityTester class.
#[derive(Debug, Clone)]
pub struct ScalabilityTester {
    pub procs: Vec<serde_json::Value>,
    pub metrics: Vec<serde_json::Value>,
    pub max_instances: String,
    pub safe_mode: String,
    pub active_ports: Vec<serde_json::Value>,
}

impl ScalabilityTester {
    /// Initialize instance.
    pub fn new(max_instances: String, safe_mode: String) -> Self {
        Self {
            procs: vec![],
            metrics: vec![],
            max_instances,
            safe_mode,
            active_ports: vec![],
        }
    }
    pub fn log(&self, msg: String) -> () {
        println!("[CrashTest] {}", msg);
        // pass
    }
    /// Clean all.
    pub fn clean_all(&mut self) -> Result<()> {
        // Clean all.
        self.log("Cleaning up processes...".to_string());
        for p in self.procs.iter() {
            // try:
            {
                p.terminate();
            }
            // except Exception as _e:
        }
        for p in psutil.process_iter(vec!["pid".to_string(), "name".to_string()]).iter() {
            if p.info["name".to_string()] != "llama-server::exe".to_string() {
                continue;
            }
            // try:
            {
                p.terminate();
            }
            // except Exception as _e:
        }
        self.procs = vec![];
        self.active_ports = vec![];
        Ok(std::thread::sleep(std::time::Duration::from_secs_f64(2)))
    }
    /// Launch instance.
    pub fn launch_instance(&self, port: String) -> Result<()> {
        // Launch instance.
        let mut env = os::environ.clone();
        env["LLM_PORT".to_string()] = port.to_string();
        let mut cmd = vec![sys::executable, START_SCRIPT.to_string(), "--model".to_string(), MODEL_PATH.to_string(), "--guard-bypass".to_string()];
        let mut proc = subprocess::Popen(cmd, /* cwd= */ ROOT_DIR, /* stdout= */ subprocess::DEVNULL, /* stderr= */ subprocess::DEVNULL, /* env= */ env, /* stdin= */ subprocess::PIPE, /* shell= */ false);
        Ok(proc)
    }
    /// Wait health.
    pub fn wait_health(&self, port: String, timeout_sec: String) -> Result<()> {
        // Wait health.
        let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        while (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start) < timeout_sec {
            // try:
            {
                let mut r = /* reqwest::get( */&format!("http://127.0.0.1:{}/health", port)).cloned().unwrap_or(/* timeout= */ 1);
                if r.status_code == 200 {
                    true
                }
            }
            // except Exception as _e:
        }
        Ok(false)
    }
    /// Measure inference time on a single instance
    pub fn benchmark_single(&self, port: String, question: String) -> Result<()> {
        // Measure inference time on a single instance
        let mut start_t = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        let mut end_t = 0;
        let mut payload = HashMap::from([("prompt".to_string(), format!("<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant\n", question)), ("n_predict".to_string(), 128), ("temperature".to_string(), 0.7_f64), ("stream".to_string(), false)]);
        // try:
        {
            let mut resp = /* reqwest::post( */format!("http://127.0.0.1:{}/completion", port), /* json= */ payload, /* timeout= */ 60);
            let mut end_t = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            if resp.status_code == 200 {
                HashMap::from([("success".to_string(), true), ("duration".to_string(), (end_t - start_t)), ("tokens".to_string(), resp.json().get(&"timings".to_string()).cloned().unwrap_or(HashMap::new()).get(&"predicted_n".to_string()).cloned().unwrap_or(0)), ("port".to_string(), port)])
            }
        }
        // except Exception as _e:
        Ok(HashMap::from([("success".to_string(), false), ("port".to_string(), port)]))
    }
}

/// Helper: setup phase for _do_run_cycle_setup.
pub fn _do_do_run_cycle_setup_setup(count: String) -> () {
    // Helper: setup phase for _do_run_cycle_setup.
    self.log(format!("--- Starting Cycle N={} ---", count));
    let mut cycle_ports = 0..count.iter().map(|i| (START_PORT + i)).collect::<Vec<_>>();
    let mut launch_start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    for p in cycle_ports.iter() {
        let mut proc = self.launch_instance(p);
        self.procs.push(proc);
    }
    let mut ready_count = 0;
    for p in cycle_ports.iter() {
        if self.wait_health(p) {
            ready_count += 1;
        } else {
            self.log(format!("Port {} failed to start", p));
        }
    }
    let mut launch_duration = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - launch_start);
    self.log(format!("Ready: {}/{} (Launch took {:.2}s)", ready_count, count, launch_duration));
    if ready_count < count {
        self.log("CRITICAL: Not all instances started. System limit reached?".to_string());
        false
    }
    (cycle_ports, i, launch_duration, p)
    (cycle_ports, i, launch_duration, p)
}

/// Do run cycle setup part 1.
pub fn _do_run_cycle_setup_part1() -> Result<()> {
    // Do run cycle setup part 1.
    let run = || {
        // Run.
        let mut f = File::create(REPORT_FILE)?;
        {
            let mut writer = csv::DictWriter(f, /* fieldnames= */ vec!["instances".to_string(), "success_rate".to_string(), "avg_latency".to_string(), "launch_overhead".to_string(), "cpu_usage".to_string(), "ram_usage".to_string()]);
            writer.writeheader();
        }
        for n in 1..(self.max_instances + 1).iter() {
            if self.run_cycle(n) {
                continue;
            }
            self.log("Stopping due to failure.".to_string());
            break;
            let mut f = File::create(REPORT_FILE)?;
            {
                let mut writer = csv::DictWriter(f, /* fieldnames= */ vec!["instances".to_string(), "success_rate".to_string(), "avg_latency".to_string(), "launch_overhead".to_string(), "cpu_usage".to_string(), "ram_usage".to_string()]);
                writer.writerow(self.metrics[-1]);
            }
            self.clean_all();
            if (self.safe_mode && n >= 2) {
                self.log("Safe Mode: Stopping at N=2".to_string());
                break;
            }
        }
        self.log(format!("Test Complete. Report saved to {}", REPORT_FILE));
    Ok(})
}

/// Helper: setup phase for run_cycle.
pub fn _do_run_cycle_setup(count: String) -> () {
    // Helper: setup phase for run_cycle.
    let (mut cycle_ports, mut i, mut launch_duration, mut p) = _do_do_run_cycle_setup_setup(count);
    let run_cycle = |count| {
        // Run cycle.
        let (mut cycle_ports, mut i, mut launch_duration, mut p) = _do_run_cycle_setup(count);
        self.log("Generating Parallel Load...".to_string());
        let mut questions = vec!["Explain quantum physics roughly.".to_string(), "Write a poem about rust.".to_string(), "Calculate fibonacci 10.".to_string(), "Describe the solar system.".to_string(), "Why is the sky blue?".to_string(), "How does a CPU work?".to_string(), "What is DNA?".to_string(), "History of Rome.".to_string()];
        let mut results = vec![];
        let mut executor = ThreadPoolExecutor(/* max_workers= */ count);
        {
            let mut futures = vec![];
            for (i, p) in cycle_ports.iter().enumerate().iter() {
                let mut q = questions[(i % questions.len())];
                futures.push(executor.submit(self.benchmark_single, p, q));
            }
            for ft in as_completed(futures).iter() {
                results.push(ft.result());
            }
        }
        let mut successes = results.iter().filter(|r| r["success".to_string()]).map(|r| r).collect::<Vec<_>>();
        let mut avg_time = if successes { statistics.mean(successes.iter().map(|r| r["duration".to_string()]).collect::<Vec<_>>()) } else { 0 };
        let mut total_tokens = successes.iter().map(|r| r.get(&"tokens".to_string()).cloned().unwrap_or(0)).collect::<Vec<_>>().iter().sum::<i64>();
        if avg_time > 0 { (total_tokens / avg_time) } else { 0 };
        let mut row = HashMap::from([("instances".to_string(), count), ("success_rate".to_string(), (successes.len() / count)), ("avg_latency".to_string(), avg_time), ("launch_overhead".to_string(), launch_duration), ("cpu_usage".to_string(), psutil.cpu_percent()), ("ram_usage".to_string(), psutil.virtual_memory().percent)]);
        self.metrics.push(row);
        self.log(format!("Cycle Result: {}", serde_json::to_string(&row).unwrap()));
        successes.len() == count
    };
    _do_run_cycle_setup_part1();
}
