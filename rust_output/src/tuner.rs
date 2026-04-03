use anyhow::{Result, Context};
use crate::utils::{safe_print};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Benchmarks the system to find the 'Saturation Point'.
/// Where T_parallel ≈ T_serial, adding more experts is useless.
#[derive(Debug, Clone)]
pub struct SwarmTuner {
    pub endpoints: String,
    pub config_path: PathBuf,
}

impl SwarmTuner {
    pub fn new(endpoints: Vec<String>) -> Self {
        Self {
            endpoints,
            config_path: PathBuf::from("config::json".to_string()),
        }
    }
    /// Measure time to complete parallel query and return content.
    pub async fn _probe_parallel(&self, client: httpx::AsyncClient, active_endpoints: Vec<String>, prompt: String) -> HashMap {
        // Measure time to complete parallel query and return content.
        let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        let mut tasks = vec![];
        let mut payload = HashMap::from([("messages".to_string(), vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), prompt)])]), ("max_tokens".to_string(), 64), ("stream".to_string(), false)]);
        for ep in active_endpoints.iter() {
            tasks.push(client.post(ep, /* json= */ payload, /* timeout= */ 60));
        }
        let mut responses = asyncio.gather(/* *tasks */).await;
        let mut duration = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start);
        let mut results = vec![];
        for r in responses.iter() {
            if r.status_code == 200 {
                results.push(r.json()["choices".to_string()][0]["message".to_string()]["content".to_string()].trim().to_string());
            } else {
                results.push(format!("Error: {}", r.status_code));
            }
        }
        HashMap::from([("duration".to_string(), duration), ("content".to_string(), results)])
    }
    /// Step through N=1 to N_max and find the performance 'Knee'.
    pub async fn find_optimal_n(&mut self) -> i64 {
        // Step through N=1 to N_max and find the performance 'Knee'.
        if !self.endpoints {
            safe_print("[Tuner] !!! No experts discovered. Initialization failed?".to_string());
            1
        }
        let mut prompt = "Write a 20-word logic puzzle about a hat.".to_string();
        safe_print(format!("\n[Tuner] QUESTION: {}", prompt));
        safe_print(format!("[Tuner] Starting Hardware-In-The-Loop Benchmark on {} slots...", self.endpoints.len()));
        let mut results_stats = vec![];
        let mut client = httpx.AsyncClient();
        {
            let mut probe1 = self._probe_parallel(client, self.endpoints[..1], prompt).await;
            let mut t1 = probe1["duration".to_string()];
            safe_print(format!("[Tuner] Baseline (N=1): {:.2}s | Answer: '{}...'", t1, probe1["content".to_string()][0][..50]));
            results_stats.push(t1);
            let mut optimal_n = 1;
            for n in 2..(self.endpoints.len() + 1).iter() {
                let mut probe_n = self._probe_parallel(client, self.endpoints[..n], prompt).await;
                let mut tn = probe_n["duration".to_string()];
                let mut seq_total = (t1 * n);
                let mut speedup = (seq_total / tn);
                let mut efficiency = (speedup / n);
                safe_print(format!("[Tuner] Tier N={}: Time={:.2}s | Speedup={:.2}x | Efficiency={:.1%}", n, tn, speedup, efficiency));
                for (i, ans) in probe_n["content".to_string()].iter().enumerate().iter() {
                    safe_print(format!("    - Expert {} Result: {}...", (i + 1), ans[..60]));
                }
                if efficiency > 0.5_f64 {
                    let mut optimal_n = n;
                }
                std::thread::sleep(std::time::Duration::from_secs_f64(1));
            }
        }
        safe_print(format!("\n[Tuner] Optimization Complete. Optimal Expert Swarm Size: {}", optimal_n));
        self._save_to_config(optimal_n);
        optimal_n
    }
    /// Persist the optimal swarm size to config::json.
    pub fn _save_to_config(&mut self, n: i64) -> Result<()> {
        // Persist the optimal swarm size to config::json.
        let mut config_data = HashMap::new();
        if self.config_path.exists() {
            let mut f = File::open(self.config_path)?;
            {
                // try:
                {
                    let mut config_data = json::load(f);
                }
                // except json::JSONDecodeError as _e:
            }
        }
        if !config_data.contains(&"zena_mode".to_string()) {
            config_data["zena_mode".to_string()] = HashMap::new();
        }
        config_data["zena_mode".to_string()]["optimal_experts".to_string()] = n;
        let mut f = File::create(self.config_path)?;
        {
            json::dump(config_data, f, /* indent= */ 4);
        }
        Ok(safe_print(format!("[Tuner] Saved optimal_experts={} to {}", n, self.config_path)))
    }
}

pub async fn run_auto_tune(arb: String) -> () {
    let mut tuner = SwarmTuner(arb.endpoints);
    tuner::find_optimal_n().await
}
