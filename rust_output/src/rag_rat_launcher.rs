/// rag_rat_launcher::py — RAG_RAT Windows Launcher
/// 
/// When frozen by PyInstaller this becomes rag_rat.exe.
/// It:
/// 1. Resolves the app root (works both frozen and from source)
/// 2. Starts streamlit run app_new.py in a subprocess
/// 3. Waits for the server to be ready (polls /healthz)
/// 4. Opens the browser to http://localhost:8501
/// 5. Shows a system-tray icon; right-click → Quit kills everything

use anyhow::{Result, Context};

pub static LOG: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub const PORT: i64 = 8501;

pub const URL: &str = "f'http://localhost:{PORT}";

pub const APP_SCRIPT: &str = "APP_ROOT / 'app_new.py";

/// Return true if something is listening on localhost:port.
pub fn _port_open(port: i64) -> Result<bool> {
    // Return true if something is listening on localhost:port.
    // try:
    {
        let _ctx = socket::create_connection(("127.0.0.1".to_string(), port), /* timeout= */ 1);
        {
            true
        }
    }
    // except OSError as _e:
}

/// Poll until the server is up or timeout expires.
pub fn _wait_for_server(port: i64, timeout: f64) -> Result<bool> {
    // Poll until the server is up or timeout expires.
    let mut deadline = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() + timeout);
    while std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() < deadline {
        if _port_open(port) {
            true
        }
        std::thread::sleep(std::time::Duration::from_secs_f64(0.5_f64));
    }
    Ok(false)
}

/// Create a simple 64×64 tray icon (blue circle with 🔬 text).
pub fn _make_icon_image() -> Result<()> {
    // Create a simple 64×64 tray icon (blue circle with 🔬 text).
    // try:
    {
        // TODO: from PIL import Image, ImageDraw
        let mut img = Image.new("RGBA".to_string(), (64, 64), (0, 0, 0, 0));
        let mut draw = ImageDraw.Draw(img);
        draw.ellipse(vec![4, 4, 60, 60], /* fill= */ (59, 130, 246, 255));
        draw.text((18, 18), "R".to_string(), /* fill= */ "white".to_string());
        img
    }
    // except Exception as _e:
}

/// Run the system-tray icon (blocks until Quit is chosen).
pub fn _run_tray(proc: subprocess::Popen) -> Result<()> {
    // Run the system-tray icon (blocks until Quit is chosen).
    // try:
    {
        // TODO: import pystray
        // TODO: from PIL import Image
        let mut icon_img = _make_icon_image();
        if icon_img.is_none() {
            log.warning("Could not create tray icon image — skipping tray".to_string());
            return;
        }
        let on_open = |_icon, _item| {
            webbrowser.open(URL);
        };
        let on_quit = |_icon, _item| {
            log.info("Quit requested — stopping RAG_RAT…".to_string());
            _icon.stop();
            proc.terminate();
            // try:
            {
                proc.wait(/* timeout= */ 10);
            }
            // except subprocess::TimeoutExpired as _e:
            os::_exit(0);
        };
        let mut menu = pystray.Menu(pystray.MenuItem("Open RAG_RAT".to_string(), on_open, /* default= */ true), pystray.MenuItem("Quit".to_string(), on_quit));
        let mut icon = pystray.Icon("RAG_RAT".to_string(), icon_img, "RAG_RAT Pro".to_string(), menu);
        log.info("System tray icon running — right-click to quit".to_string());
        icon.run();
    }
    // except ImportError as _e:
}

pub fn main() -> Result<()> {
    log.info(("=".to_string() * 60));
    log.info("  RAG_RAT Pro — Starting…".to_string());
    log.info(format!("  App root : {}", APP_ROOT));
    log.info(format!("  Script   : {}", APP_SCRIPT));
    log.info(format!("  URL      : {}", URL));
    log.info(("=".to_string() * 60));
    if !APP_SCRIPT.exists() {
        log.error(format!("app_new.py not found at {}", APP_SCRIPT));
        input("Press Enter to exit…".to_string());
        std::process::exit(1);
    }
    let mut cmd = (STREAMLIT_CMD + vec!["run".to_string(), APP_SCRIPT.to_string(), "--server::port".to_string(), PORT.to_string(), "--server::headless".to_string(), "true".to_string(), "--server::enableCORS".to_string(), "false".to_string(), "--server::enableXsrfProtection".to_string(), "false".to_string(), "--browser.gatherUsageStats".to_string(), "false".to_string()]);
    log.info(format!("Launching: {}", cmd.join(&" ".to_string())));
    let mut env = os::environ.clone();
    env["PYTHONPATH".to_string()] = ((APP_ROOT.to_string() + os::pathsep) + env.get(&"PYTHONPATH".to_string()).cloned().unwrap_or("".to_string()));
    let mut proc = subprocess::Popen(cmd, /* cwd= */ APP_ROOT.to_string(), /* env= */ env, /* stdout= */ subprocess::PIPE, /* stderr= */ subprocess::STDOUT, /* text= */ true, /* bufsize= */ 1, /* shell= */ false);
    let _stream_logs = || {
        for line in proc.stdout.iter() {
            let mut line = line.trim_end().to_string();
            if line {
                log.info(format!("[streamlit] {}", line));
            }
        }
    };
    std::thread::spawn(|| {});
    log.info(format!("Waiting for server on port {}…", PORT));
    let mut ready = _wait_for_server(PORT, /* timeout= */ 120);
    if ready {
        log.info("Server ready — opening browser".to_string());
        webbrowser.open(URL);
    } else {
        log.warning("Server did not start in 120s — opening browser anyway".to_string());
        webbrowser.open(URL);
    }
    Ok(_run_tray(proc))
}
