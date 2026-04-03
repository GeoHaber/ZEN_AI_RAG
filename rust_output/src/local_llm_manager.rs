/// LocalLLMManager - Orchestration layer for local LLM infrastructure
/// 
/// Combines LlamaCppManager and ModelRegistry to provide unified interface
/// for managing local llama.cpp and GGUF models.
/// 
/// Main entry point for applications.

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Complete local LLM infrastructure status
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocalLLMStatus {
    pub llama_cpp_ready: bool,
    pub llama_cpp_status: HashMap<String, serde_json::Value>,
    pub models_discovered: i64,
    pub models: Vec<ModelCard>,
    pub duplicate_groups: Option<HashMap<String, Vec<ModelCard>>>,
}

impl LocalLLMStatus {
    /// Convert to JSON-serializable dict
    pub fn to_dict(&self) -> HashMap {
        // Convert to JSON-serializable dict
        HashMap::from([("llama_cpp_ready".to_string(), self.llama_cpp_ready), ("llama_cpp_status".to_string(), self.llama_cpp_status), ("models_discovered".to_string(), self.models_discovered), ("models".to_string(), self.models::iter().map(|m| m.to_card_dict()).collect::<Vec<_>>()), ("duplicate_groups".to_string(), (self.duplicate_groups || HashMap::new()).iter().iter().map(|(k, v)| (k, v.iter().map(|m| m.to_card_dict()).collect::<Vec<_>>())).collect::<HashMap<_, _>>())])
    }
}

/// Main orchestrator for local LLM infrastructure
#[derive(Debug, Clone)]
pub struct LocalLLMManager {
    pub _lock: RLock,
    pub llama_manager: LlamaCppManager,
    pub registry: ModelRegistry,
    pub _status: Option<serde_json::Value>,
    pub _selected_duplicates: HashMap<String, ModelCard>,
}

impl LocalLLMManager {
    /// Initialize manager
    /// 
    /// Args:
    /// model_dir: Directory containing GGUF models (default: C:\AI\Models)
    pub fn new(model_dir: Option<PathBuf>) -> Self {
        Self {
            _lock: RLock(),
            llama_manager: LlamaCppManager(),
            registry: ModelRegistry((model_dir || PathBuf::from("C:\\AI\\Models".to_string()))),
            _status: None,
            _selected_duplicates: HashMap::new(),
        }
    }
    /// Full initialization: find llama.cpp, discover models, handle duplicates
    /// 
    /// Args:
    /// check_updates: Whether to check for model updates (Phase 2)
    /// 
    /// Returns:
    /// LocalLLMStatus with complete system status
    pub fn initialize(&mut self, check_updates: bool) -> LocalLLMStatus {
        // Full initialization: find llama.cpp, discover models, handle duplicates
        // 
        // Args:
        // check_updates: Whether to check for model updates (Phase 2)
        // 
        // Returns:
        // LocalLLMStatus with complete system status
        let _ctx = self._lock;
        {
            logger.info("Initializing LocalLLMManager...".to_string());
            logger.info("Searching for llama-server executable...".to_string());
            let mut llama_status = self.llama_manager.get_status();
            let mut llama_ready = llama_status.installed;
            if llama_ready {
                logger.info(format!("Found llama.cpp version {}", llama_status.version));
                if llama_status.needs_update {
                    logger.warning(format!("Update available: {}", llama_status.latest_version));
                }
            } else {
                logger.warning("llama.cpp not found - models won't work without it".to_string());
            }
            logger.info(format!("Discovering models in {}", self.registry::model_dir));
            let mut models = self.registry::discover();
            logger.info(format!("Found {} models in {} groups", models::len(), self.registry::_model_groups.len()));
            let mut duplicates = self.registry::get_duplicates();
            if duplicates {
                for (base_name, variants) in duplicates.iter().iter() {
                    logger.warning(format!("Found {} variants of {} - choose which to keep", variants.len(), base_name));
                }
            }
            self._status = LocalLLMStatus(/* llama_cpp_ready= */ llama_ready, /* llama_cpp_status= */ llama_status.to_dict(), /* models_discovered= */ models::len(), /* models= */ models, /* duplicate_groups= */ if duplicates { duplicates } else { None });
            self._status
        }
    }
    /// Get current status (cached or fresh)
    /// 
    /// Returns:
    /// LocalLLMStatus
    pub fn get_status(&self) -> LocalLLMStatus {
        // Get current status (cached or fresh)
        // 
        // Returns:
        // LocalLLMStatus
        if self._status.is_none() {
            self.initialize()
        }
        self._status
    }
    /// Handle duplicate model variants (user chooses which to keep)
    /// 
    /// Args:
    /// duplicate_group: List of model variants
    /// 
    /// Returns:
    /// Selected ModelCard
    pub fn handle_duplicates(&mut self, duplicate_group: Vec<ModelCard>) -> Result<ModelCard> {
        // Handle duplicate model variants (user chooses which to keep)
        // 
        // Args:
        // duplicate_group: List of model variants
        // 
        // Returns:
        // Selected ModelCard
        if !duplicate_group {
            None
        }
        println!("{}", ("\n".to_string() + ("=".to_string() * 60)));
        println!("{}", "Duplicate Models Found".to_string());
        println!("{}", ("=".to_string() * 60));
        let mut base_name = duplicate_group[0].base_model;
        println!("\nBase Model: {}", base_name);
        println!("Found {} variants:\n", duplicate_group.len());
        for (i, model) in duplicate_group.iter().enumerate().iter() {
            let mut quant_info = if model.quantization { format!(" [{}]", model.quantization) } else { "".to_string() };
            println!("  {}. {}{}", i, model.filename, quant_info);
            println!("     Size: {}", model.size);
            println!("     Quantization: {}", (model.quantization || "Original".to_string()));
            println!();
        }
        while true {
            // try:
            {
                let mut choice = input(format!("Which variant to keep? (1-{0}): ".to_string(), duplicate_group.len())).trim().to_string();
                let mut choice_idx = (choice.to_string().parse::<i64>().unwrap_or(0) - 1);
                if (0 <= choice_idx) && (choice_idx < duplicate_group.len()) {
                    let mut selected = duplicate_group[&choice_idx];
                    self._selected_duplicates[base_name] = selected;
                    println!("✓ Selected: {}\n", selected.filename);
                    selected
                } else {
                    println!("Invalid choice. Enter 1-{}", duplicate_group.len());
                    // pass
                }
            }
            // except ValueError as _e:
        }
    }
    /// Check for model updates (Phase 2 - HuggingFace integration)
    /// 
    /// Returns:
    /// Dict of updates available
    pub fn check_model_updates(&self) -> HashMap {
        // Check for model updates (Phase 2 - HuggingFace integration)
        // 
        // Returns:
        // Dict of updates available
        logger.info("Model update checking not yet implemented (Phase 2)".to_string());
        HashMap::new()
    }
    /// Get models by performance category
    pub fn get_model_by_category(&self, category: ModelCategory) -> Vec<ModelCard> {
        // Get models by performance category
        self.registry::get_cards_by_category(category)
    }
    /// Get model recommendations for use case
    /// 
    /// Args:
    /// use_case: 'fast', 'balanced', 'quality', 'coding', 'reasoning'
    /// 
    /// Returns:
    /// List of recommended models
    pub fn get_recommendations(&self, use_case: String) -> Vec<ModelCard> {
        // Get model recommendations for use case
        // 
        // Args:
        // use_case: 'fast', 'balanced', 'quality', 'coding', 'reasoning'
        // 
        // Returns:
        // List of recommended models
        self.registry::get_recommendations(use_case)
    }
    /// Get all models as UI-ready cards
    pub fn get_all_cards(&self) -> Vec<HashMap> {
        // Get all models as UI-ready cards
        self.registry::get_all_cards()
    }
    /// Print human-readable status summary
    pub fn print_summary(&mut self) -> () {
        // Print human-readable status summary
        let mut status = self.get_status();
        println!("{}", ("\n".to_string() + ("=".to_string() * 70)));
        println!("{}", "LOCAL LLM MANAGER - STATUS SUMMARY".to_string());
        println!("{}", ("=".to_string() * 70));
        println!("{}", "\n[llama.cpp Server]".to_string());
        let mut llama = status.llama_cpp_status;
        if llama["installed".to_string()] {
            println!("  ✓ Installed: {}", llama["version".to_string()]);
            if llama["needs_update".to_string()] {
                println!("  ⚠ Update available: {}", llama["latest_version".to_string()]);
            }
            if llama["running".to_string()] {
                println!("  ✓ Running (PID: {})", llama["pid".to_string()]);
                // pass
            } else {
                println!("{}", "  ✗ Not running".to_string());
            }
        } else {
            println!("{}", "  ✗ Not installed".to_string());
            println!("  Download from: {}", self.llama_manager.get_download_url());
        }
        println!("\n[Models]");
        println!("  Total discovered: {}", status.models_discovered);
        println!("  Groups: {}", self.registry::_model_groups.len());
        let mut by_category = HashMap::new();
        for model in status.models::iter() {
            let mut cat = model.category.value;
            by_category[cat] = (by_category.get(&cat).cloned().unwrap_or(0) + 1);
        }
        for (cat, count) in { let mut v = by_category.iter().clone(); v.sort(); v }.iter() {
            println!("    - {}: {}", /* capitalize */ cat.to_string(), count);
            // pass
        }
        if status.duplicate_groups {
            println!("\n[Duplicates]");
            for (base_name, variants) in status.duplicate_groups.iter().iter() {
                println!("  • {}: {} variants", base_name, variants.len());
                for v in variants.iter() {
                    let mut marker = if self._selected_duplicates.values().contains(&v) { "✓".to_string() } else { " ".to_string() };
                    println!("    {} {}", marker, v.filename);
                }
            }
        }
        println!("\n[Model Recommendations]");
        let mut fast = self.get_recommendations("fast".to_string());
        println!("  Fast: {} models", fast.len());
        if fast {
            println!("    • {}", fast[0].name);
            // pass
        }
        let mut coding = self.get_recommendations("coding".to_string());
        println!("  Coding: {} models", coding.len());
        if coding {
            println!("    • {}", coding[0].name);
            // pass
        }
        let mut reasoning = self.get_recommendations("reasoning".to_string());
        println!("  Reasoning: {} models", reasoning.len());
        if reasoning {
            println!("    • {}", reasoning[0].name);
            // pass
        }
        println!("{}", (("\n".to_string() + ("=".to_string() * 70)) + "\n".to_string()));
    }
}
