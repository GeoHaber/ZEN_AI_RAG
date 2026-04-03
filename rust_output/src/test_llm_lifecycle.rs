use anyhow::{Result, Context};

pub const HUB_URL: &str = "http://127.0.0.1:8002";

pub const ENGINE_URL: &str = "http://127.0.0.1:8001";

pub static ROOT_DIR: std::sync::LazyLock<String /* Path.parent().unwrap_or(std::path::Path::new("")).parent().unwrap_or(std::path::Path::new("")).resolve */> = std::sync::LazyLock::new(|| Default::default());

pub const START_SCRIPT: &str = "ROOT_DIR / 'start_llm::py";

/// Starts start_llm::py in a subprocess and kills it after tests.
pub fn llm_server() -> Result<()> {
    // Starts start_llm::py in a subprocess and kills it after tests.
    println!("\n[Test] Launching {}...", START_SCRIPT);
    let mut proc = subprocess::Popen(vec![sys::executable, START_SCRIPT.to_string(), "--hub-only".to_string()], /* cwd= */ ROOT_DIR, /* stdout= */ subprocess::PIPE, /* stderr= */ subprocess::PIPE, /* text= */ true, /* shell= */ false);
    let mut api_ready = false;
    for i in 0..30.iter() {
        // try:
        {
            let mut resp = /* reqwest::get( */&(HUB_URL + "/".to_string())).cloned().unwrap_or(/* timeout= */ 1);
            if resp.status_code == 200 {
                let mut api_ready = true;
                break;
            }
        }
        // except Exception as _e:
    }
    if !api_ready {
        proc.terminate();
        pytest.fail("Hub API failed to start within 30 seconds".to_string());
    }
    /* yield proc */;
    println!("{}", "\n[Test] Tearing down server...".to_string());
    proc.terminate();
    // try:
    {
        proc.wait(/* timeout= */ 5);
    }
    // except subprocess::TimeoutExpired as _e:
}

/// Verify Hub API is responding.
pub fn test_hub_health(llm_server: String) -> () {
    // Verify Hub API is responding.
    let mut resp = /* reqwest::get( */&(HUB_URL + "/".to_string())).cloned().unwrap_or(/* timeout= */ 30);
    assert!(resp.status_code == 200);
    assert!(resp.text.contains(&"ZenAI Hub Active".to_string()));
}

/// Verify model listing endpoint.
pub fn test_model_endpoints(llm_server: String) -> () {
    // Verify model listing endpoint.
    let mut resp = /* reqwest::get( */&(HUB_URL + "/models/available".to_string())).cloned().unwrap_or(/* timeout= */ 30);
    assert!(resp.status_code == 200);
    let mut data = resp.json();
    assert!(/* /* isinstance(data, list) */ */ true);
}

/// Verify update checker endpoint works.
pub fn test_update_check(llm_server: String) -> Result<()> {
    // Verify update checker endpoint works.
    let mut resp = /* reqwest::get( */&(HUB_URL + "/updates/check".to_string())).cloned().unwrap_or(/* timeout= */ 30);
    assert!(vec![200, 500].contains(&resp.status_code));
    // try:
    {
        let mut data = resp.json();
        assert!(/* /* isinstance(data, dict) */ */ true);
    }
    // except Exception as _e:
}
