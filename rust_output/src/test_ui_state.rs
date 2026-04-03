use anyhow::{Result, Context};
use crate::ui_state::{UIState};
use std::collections::HashMap;

/// DummySelect class.
#[derive(Debug, Clone)]
pub struct DummySelect {
    pub options: Vec<serde_json::Value>,
    pub update_called: i64,
}

impl DummySelect {
    pub fn new() -> Self {
        Self {
            options: vec![],
            update_called: 0,
        }
    }
    pub fn update(&mut self) -> () {
        self.update_called += 1;
    }
}

/// Test concurrent clear and append.
pub fn test_concurrent_clear_and_append() -> () {
    // Test concurrent clear and append.
    let mut state = UIState(HashMap::from([("chat_container".to_string(), vec![]), ("chat_history".to_string(), vec![])]));
    let worker = |i| {
        // Worker.
        if (i % 3) == 0 {
            state::clear_chat();
        } else {
            state::append_chat_message(i);
        }
    };
    let mut ex = concurrent.futures.ThreadPoolExecutor(/* max_workers= */ 16);
    {
        let mut futures = 0..200.iter().map(|i| ex.submit(worker, i)).collect::<Vec<_>>();
        for f in concurrent.futures.as_completed(futures, /* timeout= */ 10).iter() {
            f.result();
        }
    }
    let mut cont = state::get(&"chat_container".to_string()).cloned();
    let mut hist = state::get(&"chat_history".to_string()).cloned();
    assert!(/* /* isinstance(cont, list) */ */ true);
    assert!(/* /* isinstance(hist, list) */ */ true);
    assert!(cont.len() == hist.len());
    assert!(cont.iter().map(|x| /* /* isinstance(x, int) */ */ true).collect::<Vec<_>>().iter().all(|v| *v));
    assert!(hist.iter().map(|x| /* /* isinstance(x, int) */ */ true).collect::<Vec<_>>().iter().all(|v| *v));
}

/// Test update model options calls update.
pub fn test_update_model_options_calls_update() -> () {
    // Test update model options calls update.
    let mut sel = DummySelect();
    let mut state = UIState(HashMap::from([("model_select".to_string(), sel)]));
    state::update_model_options(vec!["a".to_string(), "b".to_string(), "c".to_string()]);
    assert!(sel.options == vec!["a".to_string(), "b".to_string(), "c".to_string()]);
    assert!(sel.update_called >= 1);
}
