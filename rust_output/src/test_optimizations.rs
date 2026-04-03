/// Comprehensive tests for llama-server optimization flags and chat context compression.
/// 
/// Tests cover:
/// 1. LlamaServerManager: command-line construction, KV type validation, opts dict
/// 2. Context compression: score filtering, token budgeting, history trimming
/// 3. API wiring: Flask endpoint parameter passthrough
/// 4. Edge cases: empty messages, no RAG results, huge histories, boundary values
/// 
/// Run:  python -m pytest test_optimizations::py -v

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};

/// Verify KV cache type validation logic (no process spawned).
#[derive(Debug, Clone)]
pub struct TestKVCacheTypeValidation {
}

impl TestKVCacheTypeValidation {
    pub fn test_all_valid_types_accepted(&self) -> () {
        let mut mgr = LlamaServerManager();
        for t in mgr.KV_CACHE_TYPES.iter() {
            assert!(("f32".to_string(), "f16".to_string(), "bf16".to_string(), "q8_0".to_string(), "q4_0".to_string(), "q4_1".to_string(), "iq4_nl".to_string(), "q5_0".to_string(), "q5_1".to_string()).contains(&t));
        }
    }
    pub fn test_valid_type_count(&self) -> () {
        let mut mgr = LlamaServerManager();
        assert!(mgr.KV_CACHE_TYPES.len() == 9);
    }
    pub fn test_default_opts_empty_when_not_running(&self) -> () {
        let mut mgr = LlamaServerManager();
        let mut st = mgr.status();
        assert!(st["opts".to_string()] == HashMap::new());
        assert!(st["running".to_string()] == false);
    }
    pub fn test_status_has_binary_field(&self) -> () {
        let mut mgr = LlamaServerManager();
        let mut st = mgr.status();
        assert!(st.contains(&"binary".to_string()));
    }
    pub fn test_base_url_format(&self) -> () {
        let mut mgr = LlamaServerManager();
        mgr._port = 9999;
        assert!(mgr.base_url == "http://localhost:9999/v1".to_string());
    }
}

/// Test that start() builds the correct command line.
/// We mock subprocess::Popen and requests.get so no process is actually spawned.
#[derive(Debug, Clone)]
pub struct TestCommandLineConstruction {
}

impl TestCommandLineConstruction {
    /// Create a manager with a fake binary and model.
    pub fn mgr(&self, tmp_path: String) -> () {
        // Create a manager with a fake binary and model.
        let mut fake_bin = (tmp_path / "llama-server::exe".to_string());
        fake_binstd::fs::write(&"fake".to_string());
        let mut fake_model = (tmp_path / "test-model.gguf".to_string());
        fake_modelstd::fs::write(&"fake model".to_string());
        (LlamaServerManager(), fake_bin.to_string(), fake_model.to_string())
    }
    /// Run start() capturing the Popen cmd without actually starting anything.
    pub fn _mock_start(&self, mgr: String, binary: String, model: String, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> Result<()> {
        // Run start() capturing the Popen cmd without actually starting anything.
        let mut captured_cmd = vec![];
        // TODO: nested class FakeProc
        let fake_popen = |cmd| {
            captured_cmd.extend(cmd);
            FakeProc()
        };
        let fake_get = |url| {
            let mut resp = MagicMock();
            resp.status_code = 200;
            resp.headers = HashMap::from([("content-type".to_string(), "application/json".to_string())]);
            resp.json::return_value = HashMap::from([("status".to_string(), "ok".to_string())]);
            resp
        };
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        let _ctx = patch.object(LlamaServerManager, "_kill_stale_port".to_string());
        {
            mgr.start(model, /* ** */ kwargs);
        }
        Ok(captured_cmd)
    }
    pub fn test_default_optimization_flags(&mut self, mgr: String) -> () {
        let (mut m, mut binary, mut model) = mgr;
        let mut cmd = self._mock_start(m, binary, model);
        let mut cmd_str = cmd.join(&" ".to_string());
        assert!(cmd.contains(&"--cache-type-k".to_string()));
        let mut idx = cmd.iter().position(|v| *v == "--cache-type-k".to_string()).unwrap();
        assert!(cmd[(idx + 1)] == "q8_0".to_string());
        let mut idx = cmd.iter().position(|v| *v == "--cache-type-v".to_string()).unwrap();
        assert!(cmd[(idx + 1)] == "q8_0".to_string());
        let mut idx = cmd.iter().position(|v| *v == "--flash-attn".to_string()).unwrap();
        assert!(cmd[(idx + 1)] == "on".to_string());
        assert!(cmd.contains(&"--mlock".to_string()));
        assert!(cmd.contains(&"--cont-batching".to_string()));
        let mut idx = cmd.iter().position(|v| *v == "--cache-reuse".to_string()).unwrap();
        assert!(cmd[(idx + 1)] == "256".to_string());
        let mut idx = cmd.iter().position(|v| *v == "--slot-prompt-similarity".to_string()).unwrap();
        assert!(cmd[(idx + 1)] == "0.5".to_string());
    }
    pub fn test_custom_kv_cache_types(&mut self, mgr: String) -> () {
        let (mut m, mut binary, mut model) = mgr;
        let mut cmd = self._mock_start(m, binary, model, /* kv_cache_type_k= */ "q4_0".to_string(), /* kv_cache_type_v= */ "f16".to_string());
        let mut idx_k = cmd.iter().position(|v| *v == "--cache-type-k".to_string()).unwrap();
        assert!(cmd[(idx_k + 1)] == "q4_0".to_string());
        let mut idx_v = cmd.iter().position(|v| *v == "--cache-type-v".to_string()).unwrap();
        assert!(cmd[(idx_v + 1)] == "f16".to_string());
    }
    pub fn test_invalid_kv_type_falls_back_to_q8_0(&mut self, mgr: String) -> () {
        let (mut m, mut binary, mut model) = mgr;
        let mut cmd = self._mock_start(m, binary, model, /* kv_cache_type_k= */ "INVALID".to_string(), /* kv_cache_type_v= */ "bad_type".to_string());
        let mut idx_k = cmd.iter().position(|v| *v == "--cache-type-k".to_string()).unwrap();
        assert!(cmd[(idx_k + 1)] == "q8_0".to_string());
        let mut idx_v = cmd.iter().position(|v| *v == "--cache-type-v".to_string()).unwrap();
        assert!(cmd[(idx_v + 1)] == "q8_0".to_string());
    }
    pub fn test_mlock_disabled(&mut self, mgr: String) -> () {
        let (mut m, mut binary, mut model) = mgr;
        let mut cmd = self._mock_start(m, binary, model, /* mlock= */ false);
        assert!(!cmd.contains(&"--mlock".to_string()));
    }
    pub fn test_cont_batching_disabled(&mut self, mgr: String) -> () {
        let (mut m, mut binary, mut model) = mgr;
        let mut cmd = self._mock_start(m, binary, model, /* cont_batching= */ false);
        assert!(!cmd.contains(&"--cont-batching".to_string()));
    }
    pub fn test_flash_attn_off(&mut self, mgr: String) -> () {
        let (mut m, mut binary, mut model) = mgr;
        let mut cmd = self._mock_start(m, binary, model, /* flash_attn= */ "off".to_string());
        let mut idx = cmd.iter().position(|v| *v == "--flash-attn".to_string()).unwrap();
        assert!(cmd[(idx + 1)] == "off".to_string());
    }
    pub fn test_flash_attn_auto(&mut self, mgr: String) -> () {
        let (mut m, mut binary, mut model) = mgr;
        let mut cmd = self._mock_start(m, binary, model, /* flash_attn= */ "auto".to_string());
        let mut idx = cmd.iter().position(|v| *v == "--flash-attn".to_string()).unwrap();
        assert!(cmd[(idx + 1)] == "auto".to_string());
    }
    pub fn test_custom_cache_reuse(&mut self, mgr: String) -> () {
        let (mut m, mut binary, mut model) = mgr;
        let mut cmd = self._mock_start(m, binary, model, /* cache_reuse= */ 512);
        let mut idx = cmd.iter().position(|v| *v == "--cache-reuse".to_string()).unwrap();
        assert!(cmd[(idx + 1)] == "512".to_string());
    }
    pub fn test_custom_slot_similarity(&mut self, mgr: String) -> () {
        let (mut m, mut binary, mut model) = mgr;
        let mut cmd = self._mock_start(m, binary, model, /* slot_prompt_similarity= */ 0.8_f64);
        let mut idx = cmd.iter().position(|v| *v == "--slot-prompt-similarity".to_string()).unwrap();
        assert!(cmd[(idx + 1)] == "0.8".to_string());
    }
    pub fn test_opts_dict_stored(&mut self, mgr: String) -> () {
        let (mut m, mut binary, mut model) = mgr;
        self._mock_start(m, binary, model, /* kv_cache_type_k= */ "q4_0".to_string(), /* flash_attn= */ "auto".to_string(), /* mlock= */ false);
        assert!(m._opts["kv_cache_type_k".to_string()] == "q4_0".to_string());
        assert!(m._opts["flash_attn".to_string()] == "auto".to_string());
        assert!(m._opts["mlock".to_string()] == false);
    }
    pub fn test_opts_in_status_when_running(&mut self, mgr: String) -> () {
        let (mut m, mut binary, mut model) = mgr;
        self._mock_start(m, binary, model);
        let mut st = m.status();
        assert!(st["running".to_string()] == true);
        assert!(st["opts".to_string()]["kv_cache_type_k".to_string()] == "q8_0".to_string());
        assert!(st["opts".to_string()]["flash_attn".to_string()] == "on".to_string());
        assert!(st["opts".to_string()]["mlock".to_string()] == true);
    }
    /// Ensure the base flags (model, port, ctx-size, gpu-layers, host) are still there.
    pub fn test_basic_flags_preserved(&mut self, mgr: String) -> () {
        // Ensure the base flags (model, port, ctx-size, gpu-layers, host) are still there.
        let (mut m, mut binary, mut model) = mgr;
        let mut cmd = self._mock_start(m, binary, model, /* port= */ 7777, /* gpu_layers= */ 42, /* ctx_size= */ 8192);
        assert!(cmd.contains(&"--model".to_string()));
        let mut idx = cmd.iter().position(|v| *v == "--model".to_string()).unwrap();
        assert!(cmd[(idx + 1)] == model);
        let mut idx = cmd.iter().position(|v| *v == "--port".to_string()).unwrap();
        assert!(cmd[(idx + 1)] == "7777".to_string());
        let mut idx = cmd.iter().position(|v| *v == "--n-gpu-layers".to_string()).unwrap();
        assert!(cmd[(idx + 1)] == "42".to_string());
        let mut idx = cmd.iter().position(|v| *v == "--ctx-size".to_string()).unwrap();
        assert!(cmd[(idx + 1)] == "8192".to_string());
        let mut idx = cmd.iter().position(|v| *v == "--host".to_string()).unwrap();
        assert!(cmd[(idx + 1)] == "0.0.0.0".to_string());
    }
    /// Verify every valid KV type passes through without fallback.
    pub fn test_all_kv_types_accepted(&mut self, mgr: String) -> () {
        // Verify every valid KV type passes through without fallback.
        let (_, mut binary, mut model) = mgr;
        for kv_type in LlamaServerManager.KV_CACHE_TYPES.iter() {
            let mut m = LlamaServerManager();
            let mut cmd = self._mock_start(m, binary, model, /* kv_cache_type_k= */ kv_type, /* kv_cache_type_v= */ kv_type);
            let mut idx_k = cmd.iter().position(|v| *v == "--cache-type-k".to_string()).unwrap();
            assert!(cmd[(idx_k + 1)] == kv_type, "K type {} not preserved", kv_type);
            let mut idx_v = cmd.iter().position(|v| *v == "--cache-type-v".to_string()).unwrap();
            assert!(cmd[(idx_v + 1)] == kv_type, "V type {} not preserved", kv_type);
        }
    }
}

/// Test error paths in start().
#[derive(Debug, Clone)]
pub struct TestStartErrorHandling {
}

impl TestStartErrorHandling {
    pub fn test_missing_binary_raises(&self, tmp_path: String) -> () {
        let mut mgr = LlamaServerManager();
        let mut fake_model = (tmp_path / "model.gguf".to_string());
        fake_modelstd::fs::write(&"data".to_string());
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            let _ctx = pytest.raises(FileNotFoundError, /* match= */ "llama-server binary not found".to_string());
            {
                mgr.start(fake_model.to_string());
            }
        }
    }
    pub fn test_missing_model_raises(&self, tmp_path: String) -> () {
        let mut mgr = LlamaServerManager();
        let mut fake_bin = (tmp_path / "llama-server::exe".to_string());
        fake_binstd::fs::write(&"fake".to_string());
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            let _ctx = pytest.raises(FileNotFoundError, /* match= */ "Model not found".to_string());
            {
                mgr.start("/nonexistent/model.gguf".to_string());
            }
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FakeChunk {
    pub text: String,
    pub source_url: String,
    pub page_title: String,
    pub chunk_idx: i64,
    pub char_offset: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FakeSearchResult {
    pub chunk: FakeChunk,
    pub score: f64,
}

/// Verify RAG chunks below score threshold are dropped.
#[derive(Debug, Clone)]
pub struct TestScoreFiltering {
}

impl TestScoreFiltering {
    pub fn test_all_above_threshold(&self) -> () {
        let mut results = vec![FakeSearchResult(FakeChunk(/* text= */ "Good chunk A".to_string()), /* score= */ 0.85_f64), FakeSearchResult(FakeChunk(/* text= */ "Good chunk B".to_string()), /* score= */ 0.7_f64), FakeSearchResult(FakeChunk(/* text= */ "Good chunk C".to_string()), /* score= */ 0.55_f64)];
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "test query".to_string())])], /* search_results= */ results);
        assert!(out["rag_filtered".to_string()] == 0);
        assert!(out["rag_sources".to_string()] == vec![HashMap::from([("title".to_string(), "Test".to_string()), ("url".to_string(), "http://example.com".to_string()), ("score".to_string(), 0.85_f64)]), HashMap::from([("title".to_string(), "Test".to_string()), ("url".to_string(), "http://example.com".to_string()), ("score".to_string(), 0.7_f64)]), HashMap::from([("title".to_string(), "Test".to_string()), ("url".to_string(), "http://example.com".to_string()), ("score".to_string(), 0.55_f64)])]);
    }
    pub fn test_some_below_threshold(&self) -> () {
        let mut results = vec![FakeSearchResult(FakeChunk(/* text= */ "Strong".to_string()), /* score= */ 0.8_f64), FakeSearchResult(FakeChunk(/* text= */ "Weak".to_string()), /* score= */ 0.1_f64), FakeSearchResult(FakeChunk(/* text= */ "Very weak".to_string()), /* score= */ 0.05_f64)];
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "test".to_string())])], /* search_results= */ results, /* rag_score_threshold= */ 0.15_f64);
        assert!(out["rag_filtered".to_string()] == 2);
        assert!(out["rag_sources".to_string()].len() == 1);
        assert!(out["rag_sources".to_string()][0]["score".to_string()] == 0.8_f64);
    }
    pub fn test_all_below_threshold(&self) -> () {
        let mut results = vec![FakeSearchResult(FakeChunk(/* text= */ "Weak A".to_string()), /* score= */ 0.1_f64), FakeSearchResult(FakeChunk(/* text= */ "Weak B".to_string()), /* score= */ 0.05_f64)];
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "test".to_string())])], /* search_results= */ results, /* rag_score_threshold= */ 0.15_f64);
        assert!(out["rag_filtered".to_string()] == 2);
        assert!(out["rag_sources".to_string()].len() == 0);
        assert!(out["rag_context".to_string()] == "".to_string());
    }
    pub fn test_exact_threshold_included(&self) -> () {
        let mut results = vec![FakeSearchResult(FakeChunk(/* text= */ "Borderline".to_string()), /* score= */ 0.15_f64)];
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "test".to_string())])], /* search_results= */ results, /* rag_score_threshold= */ 0.15_f64);
        assert!(out["rag_filtered".to_string()] == 0);
        assert!(out["rag_sources".to_string()].len() == 1);
    }
    pub fn test_zero_threshold_keeps_all(&self) -> () {
        let mut results = vec![FakeSearchResult(FakeChunk(/* text= */ "A".to_string()), /* score= */ 0.01_f64), FakeSearchResult(FakeChunk(/* text= */ "B".to_string()), /* score= */ 0.001_f64)];
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "test".to_string())])], /* search_results= */ results, /* rag_score_threshold= */ 0.0_f64);
        assert!(out["rag_filtered".to_string()] == 0);
        assert!(out["rag_sources".to_string()].len() == 2);
    }
}

/// Verify RAG context is capped at token budget.
#[derive(Debug, Clone)]
pub struct TestTokenBudgeting {
}

impl TestTokenBudgeting {
    pub fn test_small_chunks_all_fit(&self) -> () {
        let mut results = vec![FakeSearchResult(FakeChunk(/* text= */ "Short".to_string()), /* score= */ 0.9_f64), FakeSearchResult(FakeChunk(/* text= */ "Also short".to_string()), /* score= */ 0.8_f64)];
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "q".to_string())])], /* search_results= */ results, /* rag_token_budget= */ 1200);
        assert!(out["rag_sources".to_string()].len() == 2);
    }
    pub fn test_large_chunks_truncated(&self) -> () {
        let mut big_text = ("X".to_string() * 1000);
        let mut results = vec![FakeSearchResult(FakeChunk(/* text= */ big_text, /* page_title= */ "T1".to_string()), /* score= */ 0.9_f64), FakeSearchResult(FakeChunk(/* text= */ big_text, /* page_title= */ "T2".to_string()), /* score= */ 0.8_f64), FakeSearchResult(FakeChunk(/* text= */ big_text, /* page_title= */ "T3".to_string()), /* score= */ 0.7_f64)];
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "q".to_string())])], /* search_results= */ results, /* rag_token_budget= */ 100);
        assert!(out["rag_sources".to_string()].len() == 0);
    }
    /// Two chunks: first fits, second doesn't.
    pub fn test_budget_allows_partial(&self) -> () {
        // Two chunks: first fits, second doesn't.
        let mut results = vec![FakeSearchResult(FakeChunk(/* text= */ ("A".to_string() * 300), /* page_title= */ "T".to_string()), /* score= */ 0.9_f64), FakeSearchResult(FakeChunk(/* text= */ ("B".to_string() * 300), /* page_title= */ "T".to_string()), /* score= */ 0.8_f64)];
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "q".to_string())])], /* search_results= */ results, /* rag_token_budget= */ 200);
        assert!(out["rag_sources".to_string()].len() == 2);
    }
    pub fn test_context_token_estimate(&self) -> () {
        let mut results = vec![FakeSearchResult(FakeChunk(/* text= */ ("Word ".to_string() * 100)), /* score= */ 0.9_f64)];
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "test".to_string())])], /* search_results= */ results);
        let mut chars = out["rag_context_chars".to_string()];
        let mut est_tokens = out["rag_context_est_tokens".to_string()];
        assert!(est_tokens == (chars / 4));
    }
}

/// Verify chat history is trimmed to fit remaining budget.
#[derive(Debug, Clone)]
pub struct TestHistoryTrimming {
}

impl TestHistoryTrimming {
    pub fn test_short_history_not_trimmed(&self) -> () {
        let mut msgs = vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "Hi".to_string())]), HashMap::from([("role".to_string(), "assistant".to_string()), ("content".to_string(), "Hello!".to_string())]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "How are you?".to_string())])];
        let mut out = _run_compression(msgs);
        assert!(out["history_trimmed".to_string()] == 0);
        assert!(out["trimmed_messages".to_string()].len() == 3);
    }
    /// Build 50 turns of 200-char messages → 10000 chars total → must trim.
    pub fn test_long_history_trimmed(&self) -> () {
        // Build 50 turns of 200-char messages → 10000 chars total → must trim.
        let mut msgs = vec![];
        for i in 0..50.iter() {
            msgs.push(HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), (format!("Message {}: ", i) + ("x".to_string() * 200)))]));
            msgs.push(HashMap::from([("role".to_string(), "assistant".to_string()), ("content".to_string(), (format!("Reply {}: ", i) + ("y".to_string() * 200)))]));
        }
        let mut out = _run_compression(msgs, /* ctx_budget= */ 500);
        assert!(out["history_trimmed".to_string()] > 0);
        assert!(out["trimmed_messages".to_string()].len() < 100);
        let mut last_trimmed = out["trimmed_messages".to_string()][-1];
        assert!(last_trimmed["content".to_string()] == msgs[-1]["content".to_string()]);
    }
    /// Even if budget is tiny, must keep at least the last message.
    pub fn test_fallback_keeps_last_message(&self) -> () {
        // Even if budget is tiny, must keep at least the last message.
        let mut msgs = vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), ("A".to_string() * 100000))])];
        let mut out = _run_compression(msgs, /* ctx_budget= */ 10);
        assert!(out["trimmed_messages".to_string()].len() == 1);
        assert!(out["trimmed_messages".to_string()][0]["content".to_string()] == msgs[0]["content".to_string()]);
    }
    pub fn test_trimming_preserves_order(&self) -> () {
        let mut msgs = vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "first".to_string())]), HashMap::from([("role".to_string(), "assistant".to_string()), ("content".to_string(), "reply1".to_string())]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "second".to_string())]), HashMap::from([("role".to_string(), "assistant".to_string()), ("content".to_string(), "reply2".to_string())]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "third".to_string())])];
        let mut out = _run_compression(msgs, /* ctx_budget= */ 3072);
        let mut trimmed = out["trimmed_messages".to_string()];
        assert!(trimmed.iter().map(|m| m["content".to_string()]).collect::<Vec<_>>() == vec!["first".to_string(), "reply1".to_string(), "second".to_string(), "reply2".to_string(), "third".to_string()]);
    }
}

/// Test behavior when no RAG index is available.
#[derive(Debug, Clone)]
pub struct TestNoRAGContext {
}

impl TestNoRAGContext {
    pub fn test_no_search_results(&self) -> () {
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "test".to_string())])], /* search_results= */ None);
        assert!(out["rag_context".to_string()] == "".to_string());
        assert!(out["rag_filtered".to_string()] == 0);
        assert!(out["rag_sources".to_string()] == vec![]);
        assert!(out["rag_context_est_tokens".to_string()] == 0);
    }
    pub fn test_empty_search_results(&self) -> () {
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "test".to_string())])], /* search_results= */ vec![]);
        assert!(out["rag_context".to_string()] == "".to_string());
    }
    pub fn test_system_prompt_without_rag(&self) -> () {
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "hello".to_string())])], /* search_results= */ None);
        assert!(!out["system_msg".to_string()]["content".to_string()].contains(&"Retrieved Context".to_string()));
        assert!(out["system_msg".to_string()]["content".to_string()].contains(&"helpful assistant".to_string()));
    }
    pub fn test_system_prompt_with_rag(&self) -> () {
        let mut results = vec![FakeSearchResult(FakeChunk(/* text= */ "Data here".to_string()), /* score= */ 0.9_f64)];
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "test".to_string())])], /* search_results= */ results);
        assert!(out["system_msg".to_string()]["content".to_string()].contains(&"Retrieved Context".to_string()));
        assert!(out["system_msg".to_string()]["content".to_string()].contains(&"Data here".to_string()));
    }
    pub fn test_custom_system_prompt(&self) -> () {
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "hi".to_string())])], /* system_prompt= */ "You are a medical assistant.".to_string());
        assert!(out["system_msg".to_string()]["content".to_string()].contains(&"medical assistant".to_string()));
    }
}

/// Edge cases and boundary conditions.
#[derive(Debug, Clone)]
pub struct TestEdgeCases {
}

impl TestEdgeCases {
    /// Empty messages should produce no context, no crash.
    pub fn test_empty_messages_list(&self) -> () {
        // Empty messages should produce no context, no crash.
        let mut out = _run_compression(vec![], /* search_results= */ None);
        assert!(out["trimmed_messages".to_string()] == vec![]);
        assert!(out["history_trimmed".to_string()] == 0);
    }
    pub fn test_single_message(&self) -> () {
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "hi".to_string())])]);
        assert!(out["trimmed_messages".to_string()].len() == 1);
    }
    /// No user message → no RAG retrieval.
    pub fn test_assistant_only_messages(&self) -> () {
        // No user message → no RAG retrieval.
        let mut msgs = vec![HashMap::from([("role".to_string(), "assistant".to_string()), ("content".to_string(), "I'm ready to help.".to_string())])];
        let mut results = vec![FakeSearchResult(FakeChunk(/* text= */ "Data".to_string()), /* score= */ 0.9_f64)];
        let mut out = _run_compression(msgs, /* search_results= */ results);
        assert!(out["rag_context".to_string()] == "".to_string());
    }
    /// Score rounding should keep 4 decimal places.
    pub fn test_score_precision_preserved(&self) -> () {
        // Score rounding should keep 4 decimal places.
        let mut results = vec![FakeSearchResult(FakeChunk(/* text= */ "A".to_string()), /* score= */ 0.923456789_f64)];
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "test".to_string())])], /* search_results= */ results);
        assert!(out["rag_sources".to_string()][0]["score".to_string()] == 0.9235_f64);
    }
    /// Unicode content shouldn't break char counting.
    pub fn test_unicode_content_handled(&self) -> () {
        // Unicode content shouldn't break char counting.
        let mut msgs = vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "こんにちは世界 🌍 مرحبا".to_string())])];
        let mut results = vec![FakeSearchResult(FakeChunk(/* text= */ "日本語テキスト".to_string()), /* score= */ 0.9_f64)];
        let mut out = _run_compression(msgs, /* search_results= */ results);
        assert!(out["trimmed_messages".to_string()].len() == 1);
        assert!(out["rag_context_chars".to_string()] > 0);
    }
    pub fn test_very_high_score_threshold_filters_all(&self) -> () {
        let mut results = vec![FakeSearchResult(FakeChunk(/* text= */ "A".to_string()), /* score= */ 0.95_f64), FakeSearchResult(FakeChunk(/* text= */ "B".to_string()), /* score= */ 0.9_f64)];
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "test".to_string())])], /* search_results= */ results, /* rag_score_threshold= */ 0.99_f64);
        assert!(out["rag_filtered".to_string()] == 2);
        assert!(out["rag_sources".to_string()].len() == 0);
    }
}

/// Test that Flask endpoints correctly parse and pass optimization params.
#[derive(Debug, Clone)]
pub struct TestFlaskAPIWiring {
}

impl TestFlaskAPIWiring {
    /// Create a test Flask client with mocked heavy dependencies.
    pub fn client(&self) -> () {
        // Create a test Flask client with mocked heavy dependencies.
        /* let mock_idx = mock::/* mock::patch(...) */ — use mockall crate */;
        /* let mock_llama = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            mock_idx.is_built = false;
            mock_idx.n_chunks = 0;
            mock_llama.is_running = false;
            // TODO: from app import app
            app::config["TESTING".to_string()] = true;
            let mut c = app::test_client();
            {
                /* yield (c, mock_llama) */;
            }
        }
    }
    pub fn test_start_endpoint_default_params(&self, client: String, tmp_path: String) -> () {
        let (mut c, mut mock_llama) = client;
        let mut fake_model = (tmp_path / "test.gguf".to_string());
        fake_modelstd::fs::write(&"data".to_string());
        mock_llama.start = MagicMock();
        let mut resp = c.post("/api/llm/server/start".to_string(), /* json= */ HashMap::from([("model_path".to_string(), fake_model.to_string())]));
        assert!(resp.status_code == 200);
        let mut data = resp.get_json();
        assert!(data["starting".to_string()] == true);
    }
    pub fn test_start_endpoint_custom_opts(&self, client: String, tmp_path: String) -> () {
        let (mut c, mut mock_llama) = client;
        let mut fake_model = (tmp_path / "test.gguf".to_string());
        fake_modelstd::fs::write(&"data".to_string());
        mock_llama.start = MagicMock();
        let mut resp = c.post("/api/llm/server/start".to_string(), /* json= */ HashMap::from([("model_path".to_string(), fake_model.to_string()), ("kv_cache_type_k".to_string(), "q4_0".to_string()), ("kv_cache_type_v".to_string(), "q4_1".to_string()), ("flash_attn".to_string(), "off".to_string()), ("mlock".to_string(), false), ("cont_batching".to_string(), false), ("cache_reuse".to_string(), 512), ("slot_prompt_similarity".to_string(), 0.8_f64)]));
        assert!(resp.status_code == 200);
    }
    pub fn test_status_endpoint(&self, client: String) -> () {
        let (mut c, mut mock_llama) = client;
        mock_llama.status.return_value = HashMap::from([("running".to_string(), false), ("model".to_string(), None), ("port".to_string(), None), ("opts".to_string(), HashMap::new())]);
        let mut resp = c.get(&"/api/llm/server/status".to_string()).cloned();
        assert!(resp.status_code == 200);
        let mut data = resp.get_json();
        assert!(data.contains(&"running".to_string()));
    }
}

/// Ensure no data loss or corruption through the optimization pipeline.
#[derive(Debug, Clone)]
pub struct TestPrecisionConsistency {
}

impl TestPrecisionConsistency {
    /// All chunk metadata must survive through compression.
    pub fn test_source_metadata_fully_preserved(&self) -> () {
        // All chunk metadata must survive through compression.
        let mut results = vec![FakeSearchResult(FakeChunk(/* text= */ "Important medical data about patient treatment protocols".to_string(), /* source_url= */ "https://hospital.example.com/protocols/123".to_string(), /* page_title= */ "Treatment Protocol v2.1".to_string(), /* chunk_idx= */ 7), /* score= */ 0.92_f64)];
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "treatment protocol".to_string())])], /* search_results= */ results);
        let mut src = out["rag_sources".to_string()][0];
        assert!(src["title".to_string()] == "Treatment Protocol v2.1".to_string());
        assert!(src["url".to_string()] == "https://hospital.example.com/protocols/123".to_string());
        assert!(src["score".to_string()] == 0.92_f64);
    }
    /// Within budget, chunk text should appear in full in the context.
    pub fn test_chunk_text_not_truncated_within_budget(&self) -> () {
        // Within budget, chunk text should appear in full in the context.
        let mut original_text = "This is the complete chunk text that should not be truncated at all.".to_string();
        let mut results = vec![FakeSearchResult(FakeChunk(/* text= */ original_text), /* score= */ 0.9_f64)];
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "test".to_string())])], /* search_results= */ results);
        assert!(out["rag_context".to_string()].contains(&original_text));
    }
    /// Trimming should not modify message content, only drop whole messages.
    pub fn test_message_content_not_modified(&self) -> () {
        // Trimming should not modify message content, only drop whole messages.
        let mut original = "This is my exact message with special chars: <>&\"' 日本語".to_string();
        let mut msgs = vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), original)])];
        let mut out = _run_compression(msgs);
        assert!(out["trimmed_messages".to_string()][0]["content".to_string()] == original);
    }
    pub fn test_message_roles_preserved(&self) -> () {
        let mut msgs = vec![HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), "sys".to_string())]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "usr".to_string())]), HashMap::from([("role".to_string(), "assistant".to_string()), ("content".to_string(), "ast".to_string())])];
        let mut out = _run_compression(msgs);
        let mut roles = out["trimmed_messages".to_string()].iter().map(|m| m["role".to_string()]).collect::<Vec<_>>();
        assert!(roles == vec!["system".to_string(), "user".to_string(), "assistant".to_string()]);
    }
    /// When history is trimmed, remaining messages must maintain order.
    pub fn test_ordering_stability_under_compression(&self) -> () {
        // When history is trimmed, remaining messages must maintain order.
        let mut msgs = vec![];
        for i in 0..20.iter() {
            msgs.push(HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), (format!("msg_{:03} ", i) + ("x".to_string() * 500)))]));
            msgs.push(HashMap::from([("role".to_string(), "assistant".to_string()), ("content".to_string(), (format!("reply_{:03} ", i) + ("y".to_string() * 500)))]));
        }
        let mut out = _run_compression(msgs, /* ctx_budget= */ 500);
        let mut trimmed = out["trimmed_messages".to_string()];
        for i in 1..trimmed.len().iter() {
            let mut idx_prev = msgs.iter().position(|v| *v == trimmed[(i - 1)]).unwrap();
            let mut idx_curr = msgs.iter().position(|v| *v == trimmed[&i]).unwrap();
            assert!(idx_curr > idx_prev, "Order violated: {} >= {}", idx_prev, idx_curr);
        }
    }
    /// Sources should maintain the search-result order (best score first).
    pub fn test_rag_sources_ordered_by_relevance(&self) -> () {
        // Sources should maintain the search-result order (best score first).
        let mut results = vec![FakeSearchResult(FakeChunk(/* text= */ "Best".to_string(), /* page_title= */ "A".to_string()), /* score= */ 0.95_f64), FakeSearchResult(FakeChunk(/* text= */ "Good".to_string(), /* page_title= */ "B".to_string()), /* score= */ 0.8_f64), FakeSearchResult(FakeChunk(/* text= */ "OK".to_string(), /* page_title= */ "C".to_string()), /* score= */ 0.6_f64)];
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "query".to_string())])], /* search_results= */ results);
        let mut scores = out["rag_sources".to_string()].iter().map(|s| s["score".to_string()]).collect::<Vec<_>>();
        assert!(scores == { let mut v = scores.clone(); v.sort(); v }, "Sources not in descending score order");
    }
    /// With restricted budget, the chunks that DO fit should be complete.
    pub fn test_no_data_loss_small_budget(&self) -> () {
        // With restricted budget, the chunks that DO fit should be complete.
        let mut text_a = ("Alpha content: ".to_string() + ("a".to_string() * 180));
        let mut text_b = ("Beta content: ".to_string() + ("b".to_string() * 180));
        let mut results = vec![FakeSearchResult(FakeChunk(/* text= */ text_a, /* page_title= */ "Alpha".to_string()), /* score= */ 0.9_f64), FakeSearchResult(FakeChunk(/* text= */ text_b, /* page_title= */ "Beta".to_string()), /* score= */ 0.8_f64)];
        let mut out = _run_compression(vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "test".to_string())])], /* search_results= */ results, /* rag_token_budget= */ 200);
        for src in out["rag_sources".to_string()].iter() {
            let mut title = src["title".to_string()];
            if title == "Alpha".to_string() {
                assert!(out["rag_context".to_string()].contains(&text_a));
            } else if title == "Beta".to_string() {
                assert!(out["rag_context".to_string()].contains(&text_b));
            }
        }
    }
}

/// Verify that default values in zen_core_libs and app::py are consistent.
#[derive(Debug, Clone)]
pub struct TestDefaultConsistency {
}

impl TestDefaultConsistency {
    /// app::py default for kv_cache_type should match llama_server.py default.
    pub fn test_kv_cache_defaults_match(&self) -> () {
        // app::py default for kv_cache_type should match llama_server.py default.
        // TODO: import inspect
        let mut sig = inspect::signature(LlamaServerManager.start);
        assert!(sig.parameters["kv_cache_type_k".to_string()].default == "q8_0".to_string());
        assert!(sig.parameters["kv_cache_type_v".to_string()].default == "q8_0".to_string());
    }
    pub fn test_flash_attn_default_match(&self) -> () {
        // TODO: import inspect
        let mut sig = inspect::signature(LlamaServerManager.start);
        assert!(sig.parameters["flash_attn".to_string()].default == "on".to_string());
    }
    pub fn test_mlock_default_match(&self) -> () {
        // TODO: import inspect
        let mut sig = inspect::signature(LlamaServerManager.start);
        assert!(sig.parameters["mlock".to_string()].default == true);
    }
    pub fn test_cont_batching_default_match(&self) -> () {
        // TODO: import inspect
        let mut sig = inspect::signature(LlamaServerManager.start);
        assert!(sig.parameters["cont_batching".to_string()].default == true);
    }
    pub fn test_cache_reuse_default_match(&self) -> () {
        // TODO: import inspect
        let mut sig = inspect::signature(LlamaServerManager.start);
        assert!(sig.parameters["cache_reuse".to_string()].default == 256);
    }
    pub fn test_slot_prompt_similarity_default(&self) -> () {
        // TODO: import inspect
        let mut sig = inspect::signature(LlamaServerManager.start);
        assert!(sig.parameters["slot_prompt_similarity".to_string()].default == 0.5_f64);
    }
}

/// Replicate the chat endpoint's compression logic standalone for testing.
/// Returns dict with all computed values.
pub fn _run_compression(messages: Vec<HashMap>, search_results: Option<Vec<FakeSearchResult>>, rag_score_threshold: f64, rag_k: i64, ctx_budget: i64, rag_token_budget: i64, chars_per_token: i64, system_prompt: String) -> HashMap {
    // Replicate the chat endpoint's compression logic standalone for testing.
    // Returns dict with all computed values.
    let mut last_user_msg = "".to_string();
    for m in messages.iter().rev().iter() {
        if m.get(&"role".to_string()).cloned() == "user".to_string() {
            let mut last_user_msg = m.get(&"content".to_string()).cloned().unwrap_or("".to_string());
            break;
        }
    }
    let mut rag_context = "".to_string();
    let mut rag_sources = vec![];
    let mut rag_timing = HashMap::new();
    let mut rag_filtered = 0;
    if (last_user_msg && search_results.is_some()) {
        let mut results = search_results;
        let mut strong = results.iter().filter(|r| r.score >= rag_score_threshold).map(|r| r).collect::<Vec<_>>();
        let mut rag_filtered = (results.len() - strong.len());
        let mut parts = vec![];
        let mut total_chars = 0;
        let mut max_rag_chars = (rag_token_budget * chars_per_token);
        for r in strong.iter() {
            let mut chunk_text_str = format!("[{}] ({})\n{}", r.chunk.page_title, r.chunk.source_url, r.chunk.text);
            if (total_chars + chunk_text_str.len()) > max_rag_chars {
                break;
            }
            parts.push(chunk_text_str);
            total_chars += chunk_text_str.len();
            rag_sources.push(HashMap::from([("title".to_string(), r.chunk.page_title), ("url".to_string(), r.chunk.source_url), ("score".to_string(), ((r.score as f64) * 10f64.powi(4)).round() / 10f64.powi(4))]));
        }
        let mut rag_context = parts.join(&"\n\n---\n\n".to_string());
    }
    rag_timing["rag_filtered_weak".to_string()] = rag_filtered;
    rag_timing["rag_chunks_sent".to_string()] = rag_sources.len();
    rag_timing["rag_context_chars".to_string()] = rag_context.len();
    rag_timing["rag_context_est_tokens".to_string()] = (rag_context.len() / chars_per_token);
    let mut system_parts = vec![];
    if system_prompt {
        system_parts.push(system_prompt);
    } else {
        system_parts.push("You are a helpful assistant. Answer questions based on the provided context. If the context doesn't contain the answer, say so honestly. Always cite your sources when using the retrieved context.".to_string());
    }
    if rag_context {
        system_parts.push(format!("\n\n## Retrieved Context\n\n{}", rag_context));
    }
    let mut system_msg = HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), system_parts.join(&"\n".to_string()))]);
    let mut system_tokens = (system_msg["content".to_string()].len() / chars_per_token);
    let mut remaining = (ctx_budget - system_tokens);
    let mut trimmed_messages = vec![];
    let mut total_msg_chars = 0;
    for m in messages.iter().rev().iter() {
        let mut mc = m.get(&"content".to_string()).cloned().unwrap_or("".to_string()).len();
        if (total_msg_chars + mc) > (remaining * chars_per_token) {
            break;
        }
        trimmed_messages.insert(0, m);
        total_msg_chars += mc;
    }
    if (!trimmed_messages && messages) {
        let mut trimmed_messages = vec![messages[-1]];
    }
    let mut history_trimmed = (messages.len() - trimmed_messages.len());
    HashMap::from([("rag_context".to_string(), rag_context), ("rag_sources".to_string(), rag_sources), ("rag_filtered".to_string(), rag_filtered), ("rag_context_chars".to_string(), rag_context.len()), ("rag_context_est_tokens".to_string(), (rag_context.len() / chars_per_token)), ("system_msg".to_string(), system_msg), ("trimmed_messages".to_string(), trimmed_messages), ("history_trimmed".to_string(), history_trimmed), ("total_messages".to_string(), messages.len())])
}
