use anyhow::{Result, Context};
use std::fs::File;
use std::io::{self, Read, Write};

pub static TRACE_FILE: std::sync::LazyLock<PathBuf> = std::sync::LazyLock::new(|| Default::default());

/// Log.
pub fn log(msg: String) -> Result<()> {
    // Log.
    let mut timestamp = time::strftime("%H:%M:%S".to_string());
    let mut line = format!("[{}] {}", timestamp, msg);
    println!("{}", line);
    // try:
    {
        let mut f = File::create(TRACE_FILE)?;
        {
            f.write((line + "\n".to_string()));
        }
    }
    // except Exception as _e:
}
