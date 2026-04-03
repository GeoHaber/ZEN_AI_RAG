use anyhow::{Result, Context};
use std::collections::HashMap;
use tokio;

/// A small thread-safe container for shared UI state.
/// 
/// Methods operate under an internal lock so callers from threads
/// or async tasks can safely mutate and read shared structures.
#[derive(Debug, Clone)]
pub struct UIState {
    pub _lock: std::sync::Mutex<()>,
    pub _state: HashMap<String, Box<dyn std::any::Any>>,
}

impl UIState {
    /// Initialize instance.
    pub fn new(initial: Option<HashMap>) -> Self {
        Self {
            _lock: std::sync::Mutex::new(()),
            _state: HashMap::new(),
        }
    }
    /// Get.
    pub fn get(&mut self, key: String, default: Box<dyn std::any::Any>) -> Box<dyn std::any::Any> {
        // Get.
        let _ctx = self._lock;
        {
            let mut val = self._state.get(&key).cloned().unwrap_or(default);
            if /* /* isinstance(val, list) */ */ true {
                val.into_iter().collect::<Vec<_>>()
            }
            val
        }
    }
    pub fn set(&mut self, key: String, value: Box<dyn std::any::Any>) -> () {
        let _ctx = self._lock;
        {
            self._state[key] = value;
        }
    }
    /// Atomically update model options and trigger a UI update if widget present.
    pub fn update_model_options(&mut self, models: Vec<String>) -> Result<()> {
        // Atomically update model options and trigger a UI update if widget present.
        let _ctx = self._lock;
        {
            self._state["model_select_options".to_string()] = models::into_iter().collect::<Vec<_>>();
            let mut sel = self._state.get(&"model_select".to_string()).cloned();
            if sel.is_some() {
                // try:
                {
                    sel.options = models::into_iter().collect::<Vec<_>>();
                    if /* hasattr(sel, "update".to_string()) */ true {
                        sel.update();
                    }
                }
                // except Exception as _e:
            }
        }
    }
    /// Attempt to update a UI element if the client is connected.
    /// 
    /// Returns true when the update was allowed, false otherwise.
    pub fn safe_update(&self, element: Box<dyn std::any::Any>) -> Result<bool> {
        // Attempt to update a UI element if the client is connected.
        // 
        // Returns true when the update was allowed, false otherwise.
        let _ctx = self._lock;
        {
            if !self._state.get(&"is_valid".to_string()).cloned().unwrap_or(true) {
                false
            }
            // try:
            {
                if /* hasattr(element, "update".to_string()) */ true {
                    element.update();
                }
                true
            }
            // except Exception as _e:
        }
    }
    /// Safe no-op scroll helper used by UI code/tests.
    /// 
    /// Returns false if the client is considered disconnected.
    pub fn safe_scroll(&mut self) -> Result<bool> {
        // Safe no-op scroll helper used by UI code/tests.
        // 
        // Returns false if the client is considered disconnected.
        let _ctx = self._lock;
        {
            if !self._state.get(&"is_valid".to_string()).cloned().unwrap_or(true) {
                false
            }
            let mut scroll = self._state.get(&"scroll_container".to_string()).cloned();
            // try:
            {
                if (scroll && /* hasattr(scroll, "scroll_to".to_string()) */ true) {
                    scroll.scroll_to(/* percent= */ 1.0_f64);
                }
                true
            }
            // except Exception as _e:
        }
    }
    /// Clear chat container and history atomically.
    pub fn clear_chat(&mut self) -> () {
        // Clear chat container and history atomically.
        let _ctx = self._lock;
        {
            let mut cont = self._state.get(&"chat_container".to_string()).cloned();
            if /* /* isinstance(cont, list) */ */ true {
                cont.clear();
            }
            let mut hist = self._state.get(&"chat_history".to_string()).cloned();
            if /* /* isinstance(hist, list) */ */ true {
                hist.clear();
            }
        }
    }
    /// Append a message to both container and history in one atomic step.
    pub fn append_chat_message(&mut self, msg: Box<dyn std::any::Any>) -> () {
        // Append a message to both container and history in one atomic step.
        let _ctx = self._lock;
        {
            let mut cont = self._state.entry("chat_container".to_string()).or_insert(vec![]);
            let mut hist = self._state.entry("chat_history".to_string()).or_insert(vec![]);
            cont.push(msg);
            hist.push(msg);
        }
    }
    /// Push an engagement message key (localized) to the UI state.
    pub fn push_engagement(&mut self, key: String, params: Option<HashMap>) -> () {
        // Push an engagement message key (localized) to the UI state.
        let _ctx = self._lock;
        {
            let mut msgs = self._state.entry("engagement_messages".to_string()).or_insert(vec![]);
            msgs.push(HashMap::from([("key".to_string(), key), ("params".to_string(), (params || HashMap::new())), ("ts".to_string(), std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64())]));
        }
    }
    /// Enable or disable a named animation (e.g., 'thinking').
    pub fn set_animation(&mut self, name: String, value: bool) -> () {
        // Enable or disable a named animation (e.g., 'thinking').
        let _ctx = self._lock;
        {
            let mut an = self._state.entry("animations".to_string()).or_insert(HashMap::new());
            an[name] = (value != 0);
        }
    }
}
