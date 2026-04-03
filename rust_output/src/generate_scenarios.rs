/// Generate medical scenario documents for RAG indexing.
/// Writes text files to medical_scenarios/data/.

use anyhow::{Result, Context};

pub const SCRIPT_DIR: &str = "Path(file!()).resolve().parent";

pub const DATA_DIR: &str = "SCRIPT_DIR / 'data";

pub static SCENARIOS: std::sync::LazyLock<Vec<HashMap<String, serde_json::Value>>> = std::sync::LazyLock::new(|| Vec::new());

pub fn main() -> () {
    println!("{}", "Generating medical scenario documents...".to_string());
    for s in SCENARIOS.iter() {
        let mut path = (DATA_DIR / format!("{}.txt", s["id".to_string()]));
        let mut text = ((s["title".to_string()] + "\n\n".to_string()) + s["content".to_string()].trim().to_string()).trim().to_string();
        pathstd::fs::write(&text));
        println!("  Written: {} ({} chars)", path.file_name().unwrap_or_default().to_str().unwrap_or(""), text.len());
    }
    println!("Done. {} files in {}", SCENARIOS.len(), DATA_DIR);
}
