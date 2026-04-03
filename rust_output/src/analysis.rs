use anyhow::{Result, Context};
use crate::config_system::{config};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub fn analyze_file(path: PathBuf) -> Result<HashMap<String, Box<dyn std::any::Any>>> {
    let mut result = HashMap::from([("path".to_string(), path.to_string()), ("issues".to_string(), vec![])]);
    // try:
    {
        if (!path.exists() || !path.is_file()) {
            result["issues".to_string()].push(HashMap::from([("severity".to_string(), "error".to_string()), ("message".to_string(), "File not found".to_string())]));
            result
        }
        if !(".py".to_string(), ".txt".to_string(), ".md".to_string()).contains(&path.extension().unwrap_or_default().to_str().unwrap_or("")) {
            result["issues".to_string()].push(HashMap::from([("severity".to_string(), "info".to_string()), ("message".to_string(), "Non-text file skipped".to_string())]));
            result
        }
        let mut src = path.read_to_string(), /* errors= */ "ignore".to_string());
        // try:
        {
            let mut tree = ast.parse(src);
            for node in ast.walk(tree).iter() {
                if /* /* isinstance(node, ast.Global) */ */ true {
                    result["issues".to_string()].push(HashMap::from([("severity".to_string(), "warning".to_string()), ("message".to_string(), "global usage found".to_string()), ("line".to_string(), node.lineno)]));
                }
                if (/* /* isinstance(node, ast.Call) */ */ true && ("eval".to_string(), "exec".to_string()).contains(&/* getattr */ "".to_string())) {
                    result["issues".to_string()].push(HashMap::from([("severity".to_string(), "error".to_string()), ("message".to_string(), format!("uses {}()", node.func.id)), ("line".to_string(), node.lineno)]));
                }
            }
        }
        // except Exception as e:
        if src.contains(&"threading::Thread".to_string()) {
            result["issues".to_string()].push(HashMap::from([("severity".to_string(), "warning".to_string()), ("message".to_string(), "threading::Thread usage".to_string())]));
        }
        if src.contains(&"asyncio.to_thread".to_string()) {
            result["issues".to_string()].push(HashMap::from([("severity".to_string(), "info".to_string()), ("message".to_string(), "asyncio.to_thread detected".to_string())]));
        }
        if src.contains(&"subprocess".to_string()) {
            result["issues".to_string()].push(HashMap::from([("severity".to_string(), "warning".to_string()), ("message".to_string(), "subprocess usage".to_string())]));
        }
    }
    // except Exception as e:
    Ok(result)
}

pub fn analyze_and_write_report(files: Vec<String>, job_id: String) -> Result<HashMap<String, Box<dyn std::any::Any>>> {
    let mut report = HashMap::from([("job_id".to_string(), job_id), ("files".to_string(), vec![]), ("summary".to_string(), HashMap::new())]);
    for f in files.iter() {
        // try:
        {
            let mut p = PathBuf::from(f).canonicalize().unwrap_or_default();
            let mut base = PathBuf::from(config::BASE_DIR).canonicalize().unwrap_or_default();
            if !p.to_string().starts_with(&*base::to_string()) {
                report["files".to_string()].push(HashMap::from([("path".to_string(), f), ("issues".to_string(), vec![HashMap::from([("severity".to_string(), "error".to_string()), ("message".to_string(), "Path not allowed".to_string())])])]));
                continue;
            }
        }
        // except Exception as _e:
        let mut res = analyze_file(p);
        report["files".to_string()].push(res);
    }
    let mut counts = HashMap::from([("error".to_string(), 0), ("warning".to_string(), 0), ("info".to_string(), 0)]);
    for entry in report["files".to_string()].iter() {
        for iss in entry.get(&"issues".to_string()).cloned().unwrap_or(vec![]).iter() {
            let mut sev = iss.get(&"severity".to_string()).cloned().unwrap_or("info".to_string());
            counts[sev] = (counts.get(&sev).cloned().unwrap_or(0) + 1);
        }
    }
    report["summary".to_string()] = counts;
    let mut out = (config::BASE_DIR / "_zena_analisis".to_string());
    // try:
    {
        let mut fh = File::create(out)?;
        {
            json::dump(report, fh, /* indent= */ 2);
        }
    }
    // except Exception as e:
    Ok(report)
}
