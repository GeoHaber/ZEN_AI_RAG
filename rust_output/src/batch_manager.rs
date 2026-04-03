use anyhow::{Result, Context};
use crate::config_system::{config};
use crate::resource_manager::{resource_manager};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static BATCH_MANAGER: std::sync::LazyLock<BatchManager> = std::sync::LazyLock::new(|| Default::default());

/// Simple persistent job queue for batch jobs.
/// 
/// - Jobs persisted to `jobs.json` in config::BASE_DIR
/// - Uses resource_manager to run blocking tasks in threads
#[derive(Debug, Clone)]
pub struct BatchManager {
    pub _lock: std::sync::Mutex<()>,
    pub path: String,
    pub _jobs: HashMap<String, HashMap<String, Box<dyn std::any::Any>>>,
}

impl BatchManager {
    pub fn new(path: PathBuf) -> Self {
        Self {
            _lock: std::sync::Mutex::new(()),
            path: (path || (config::BASE_DIR / "jobs.json".to_string())),
            _jobs: HashMap::new(),
        }
    }
    pub fn _load(&mut self) -> Result<()> {
        // try:
        {
            if self.path.exists() {
                let mut f = File::open(self.path)?;
                {
                    let mut data = json::load(f);
                    self._jobs = data.iter().map(|j| (j["id".to_string()], j)).collect::<HashMap<_, _>>();
                }
            }
        }
        // except Exception as e:
    }
    pub fn _save(&mut self) -> Result<()> {
        let mut tmp = (self.path.to_string() + ".tmp".to_string());
        // try:
        {
            let mut f = File::create(tmp)?;
            {
                json::dump(self._jobs.values().into_iter().collect::<Vec<_>>(), f, /* indent= */ 2);
            }
            PathBuf::from(tmp).replace(self.path);
        }
        // except Exception as e:
    }
    pub fn enqueue(&mut self, job_type: String, params: HashMap<String, Box<dyn std::any::Any>>) -> String {
        let _ctx = self._lock;
        {
            let mut jid = /* uuid */ "00000000-0000-0000-0000-000000000000".to_string().to_string();
            let mut job = HashMap::from([("id".to_string(), jid), ("type".to_string(), job_type), ("params".to_string(), params), ("status".to_string(), "queued".to_string()), ("created_at".to_string(), std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64()), ("updated_at".to_string(), std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64()), ("result".to_string(), None), ("logs".to_string(), vec![])]);
            self._jobs[jid] = job;
            self._save();
            self.start_job(jid);
            jid
        }
    }
    pub fn list_jobs(&self) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
        let _ctx = self._lock;
        {
            self._jobs.values().into_iter().collect::<Vec<_>>()
        }
    }
    pub fn get_job(&self, jid: String) -> HashMap<String, Box<dyn std::any::Any>> {
        self._jobs.get(&jid).cloned()
    }
    pub fn start_job(&mut self, jid: String) -> Result<()> {
        let mut job = self._jobs.get(&jid).cloned();
        if !job {
            return;
        }
        if ("running".to_string(), "completed".to_string()).contains(&job["status".to_string()]) {
            return;
        }
        let _run = || {
            // try:
            {
                job["status".to_string()] = "running".to_string();
                job["updated_at".to_string()] = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
                self._save();
                if job["type".to_string()] == "code_review".to_string() {
                    // TODO: from zena_mode.analysis import analyze_and_write_report
                    let mut res = analyze_and_write_report(job["params".to_string()].get(&"files".to_string()).cloned().unwrap_or(vec![]), /* job_id= */ jid);
                    job["result".to_string()] = res;
                    job["status".to_string()] = "completed".to_string();
                } else {
                    job["logs".to_string()].push(format!("Unknown job type: {}", job["type".to_string()]));
                    job["status".to_string()] = "failed".to_string();
                }
            }
            // except Exception as e:
            // finally:
                job["updated_at".to_string()] = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
                self._save();
        };
        Ok(resource_manager::add_worker_thread(_run, /* daemon= */ true))
    }
}
