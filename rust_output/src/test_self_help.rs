use anyhow::{Result, Context};
use crate::arbitrage::{SwarmArbitrator};
use crate::rag_pipeline::{LocalRAG};
use std::collections::HashMap;
use std::path::PathBuf;

/// TestSelfHelpRAG class.
#[derive(Debug, Clone)]
pub struct TestSelfHelpRAG {
}

impl TestSelfHelpRAG {
    /// Setup.
    pub fn setUp(&mut self) -> () {
        // Setup.
        self.test_cache = PathBuf::from("./test_self_help_cache".to_string());
        if self.test_cache.exists() {
            std::fs::remove_dir_all(self.test_cache).ok();
        }
        self.test_cache.create_dir_all();
        self.rag = LocalRAG(/* cache_dir= */ self.test_cache);
        self.arbitrator = SwarmArbitrator();
        self.manual_path = PathBuf::from("USER_MANUAL.md".to_string());
        let mut content = "".to_string();
        let mut candidates = vec![PathBuf::from("USER_MANUAL.md".to_string()), (PathBuf::from(file!()).canonicalize().unwrap_or_default().parent().unwrap_or(std::path::Path::new("")).parent().unwrap_or(std::path::Path::new("")) / "USER_MANUAL.md".to_string())];
        for p in candidates.iter() {
            if !p.exists() {
                continue;
            }
            let mut content = p.read_to_string());
            break;
        }
        if !content {
            let mut content = "# ZenAI User Manual\n## 2. Model Manager\nExpand this section to view and manage your local LLMs.\n- Catalog: Shows a list of popular models.".to_string();
        }
        let mut doc = HashMap::from([("url".to_string(), "internal://USER_MANUAL.md".to_string()), ("title".to_string(), "ZenAI User Manual".to_string()), ("content".to_string(), content)]);
        self.rag.build_index(vec![doc], /* filter_junk= */ false);
    }
    /// Teardown.
    pub fn tearDown(&self) -> Result<()> {
        // Teardown.
        self.rag.close();
        if self.test_cache.exists() {
            // try:
            {
                std::fs::remove_dir_all(self.test_cache).ok();
            }
            // except Exception as _e:
        }
    }
    /// Test if 'how to switch models' retrieves the Model Manager section.
    pub fn test_manual_retrieval(&mut self) -> () {
        // Test if 'how to switch models' retrieves the Model Manager section.
        let mut query = "How do I switch models?".to_string();
        let mut results = self.rag.search(query, /* k= */ 3);
        assert!(results.len() > 0, "No results found for manual query".to_string());
        let mut top_text = results[0]["text".to_string()].to_lowercase();
        println!("DEBUG: Top Result: {}", top_text);
        assert!(vec!["model".to_string(), "catalog".to_string(), "manager".to_string(), "download".to_string()].iter().map(|x| top_text.contains(&x)).collect::<Vec<_>>().iter().any(|v| *v), format!("Top result did not contain expected keywords. Got: {}", top_text));
    }
    /// Test if 'audio not working' hits troubleshooting.
    pub fn test_troubleshooting_retrieval(&mut self) -> () {
        // Test if 'audio not working' hits troubleshooting.
        let mut query = "My audio is not working".to_string();
        let mut results = self.rag.search(query, /* k= */ 3);
        let mut found_troubleshooting = false;
        for res in results.iter() {
            if !(res["text".to_string()].to_lowercase().contains(&"troubleshooting".to_string()) || res["text".to_string()].to_lowercase().contains(&"microphone".to_string()) || res["text".to_string()].to_lowercase().contains(&"audio".to_string())) {
                continue;
            }
            let mut found_troubleshooting = true;
            break;
        }
        assert!(found_troubleshooting, "Did not find troubleshooting info for audio issue".to_string());
    }
    /// Verify that the Arbitrator confirms the answer matches the manual.
    pub fn test_verification_shield(&mut self) -> () {
        // Verify that the Arbitrator confirms the answer matches the manual.
        let mut context = vec!["The Model Manager allows you to switch local LLMs from the catalog.".to_string()];
        let mut ans_good = "You can switch models using the Model Manager.".to_string();
        let mut res_good = self.arbitrator.verify_hallucination(ans_good, context);
        self.assertGreaterEqual(res_good["score".to_string()], 0.6_f64, "Good answer should pass verification".to_string());
        let mut ans_bad = "You switch models by restarting your computer 10 times.".to_string();
        let mut res_bad = self.arbitrator.verify_hallucination(ans_bad, context);
        self.assertLess(res_bad["score".to_string()], 0.6_f64, "Hallucination should fail verification".to_string());
    }
}
