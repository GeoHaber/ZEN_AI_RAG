/// ModelCard and ModelRegistry - GGUF Model discovery, categorization, and metadata
/// 
/// Discovers GGUF models, extracts metadata, categorizes by performance, detects
/// duplicates, and generates rich UI cards.
/// 
/// Thread-safe with RLock for concurrent access.

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Model size/performance categories
#[derive(Debug, Clone)]
pub struct ModelCategory {
}

/// GGUF quantization types
#[derive(Debug, Clone)]
pub struct QuantizationType {
}

/// Model capabilities/tags
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelCapabilities {
    pub chat: bool,
    pub coding: bool,
    pub reasoning: bool,
    pub math: bool,
    pub multilingual: bool,
    pub vision: bool,
}

impl ModelCapabilities {
    /// Convert to list of capability names
    pub fn to_list(&mut self) -> Vec<String> {
        // Convert to list of capability names
        let mut caps = vec![];
        if self.chat {
            caps.push("Chat".to_string());
        }
        if self.coding {
            caps.push("Coding".to_string());
        }
        if self.reasoning {
            caps.push("Reasoning".to_string());
        }
        if self.math {
            caps.push("Math".to_string());
        }
        if self.multilingual {
            caps.push("Multilingual".to_string());
        }
        if self.vision {
            caps.push("Vision".to_string());
        }
        caps
    }
}

/// Complete model metadata for display
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelCard {
    pub id: String,
    pub name: String,
    pub filename: String,
    pub path: PathBuf,
    pub size: String,
    pub size_bytes: i64,
    pub base_model: String,
    pub quantization: Option<String>,
    pub category: ModelCategory,
    pub context: i64,
    pub estimated_speed: i64,
    pub recommended_ram: i64,
    pub description: String,
    pub capabilities: ModelCapabilities,
    pub source: String,
    pub url: String,
    pub version: Option<String>,
    pub release_date: Option<String>,
    pub last_updated: Option<String>,
}

impl ModelCard {
    /// Convert to UI card dict
    pub fn to_card_dict(&self) -> HashMap {
        // Convert to UI card dict
        HashMap::from([("id".to_string(), self.id), ("name".to_string(), self.name), ("filename".to_string(), self.filename), ("size".to_string(), self.size), ("base_model".to_string(), self.base_model), ("quantization".to_string(), self.quantization), ("category".to_string(), self.category.value), ("context".to_string(), self.context), ("estimated_speed".to_string(), self.estimated_speed), ("recommended_ram".to_string(), self.recommended_ram), ("description".to_string(), self.description), ("capabilities".to_string(), self.capabilities.to_list()), ("source".to_string(), self.source), ("url".to_string(), self.url), ("version".to_string(), self.version), ("path".to_string(), self.path.to_string())])
    }
}

/// Discover, categorize, and manage GGUF models
#[derive(Debug, Clone)]
pub struct ModelRegistry {
    pub _lock: RLock,
    pub model_dir: String,
    pub models: Vec<ModelCard>,
    pub _model_groups: HashMap<String, Vec<ModelCard>>,
}

impl ModelRegistry {
    /// Initialize registry
    /// 
    /// Args:
    /// model_dir: Directory to scan for models (default: C:\AI\Models)
    pub fn new(model_dir: Option<PathBuf>) -> Self {
        Self {
            _lock: RLock(),
            model_dir: (model_dir || PathBuf::from("C:\\AI\\Models".to_string())),
            models: Vec::new(),
            _model_groups: HashMap::new(),
        }
    }
    /// Discover all GGUF models in model directory
    /// 
    /// Returns:
    /// List of ModelCard objects
    pub fn discover(&mut self) -> Result<Vec<ModelCard>> {
        // Discover all GGUF models in model directory
        // 
        // Returns:
        // List of ModelCard objects
        let _ctx = self._lock;
        {
            self.models = vec![];
            self._model_groups = HashMap::new();
            if !self.model_dir.exists() {
                logger.warning(format!("Model directory not found: {}", self.model_dir));
                self.models
            }
            let mut gguf_files = self.model_dir.glob("*.gguf".to_string()).into_iter().collect::<Vec<_>>();
            logger.info(format!("Discovering models in {}", self.model_dir));
            logger.info(format!("Found {} GGUF files", gguf_files.len()));
            for file_path in gguf_files.iter() {
                // try:
                {
                    let mut card = self._create_card(file_path);
                    self.models::push(card);
                }
                // except Exception as e:
            }
            self._group_by_base_model();
            logger.info(format!("Created {} model cards", self.models::len()));
            logger.info(format!("Organized into {} base model groups", self._model_groups.len()));
            self.models
        }
    }
    /// Create ModelCard from GGUF file
    /// 
    /// Args:
    /// file_path: Path to .gguf file
    /// 
    /// Returns:
    /// ModelCard with metadata
    pub fn _create_card(&mut self, file_path: PathBuf) -> ModelCard {
        // Create ModelCard from GGUF file
        // 
        // Args:
        // file_path: Path to .gguf file
        // 
        // Returns:
        // ModelCard with metadata
        let mut filename = file_path.file_name().unwrap_or_default().to_str().unwrap_or("");
        let mut base_model = self._extract_base_model(filename);
        let mut quantization = self._extract_quantization(filename);
        let mut size_bytes = file_path.stat().st_size;
        let mut size_str = self._format_size(size_bytes);
        let mut metadata = self.MODEL_METADATA.get(&base_model).cloned().unwrap_or(HashMap::new());
        let mut category = self._determine_category(size_bytes, base_model);
        let mut caps_dict = metadata.get(&"capabilities".to_string()).cloned().unwrap_or(HashMap::new());
        let mut caps = ModelCapabilities(/* chat= */ caps_dict.get(&"chat".to_string()).cloned().unwrap_or(false), /* coding= */ caps_dict.get(&"coding".to_string()).cloned().unwrap_or(false), /* reasoning= */ caps_dict.get(&"reasoning".to_string()).cloned().unwrap_or(false), /* math= */ caps_dict.get(&"math".to_string()).cloned().unwrap_or(false), /* multilingual= */ caps_dict.get(&"multilingual".to_string()).cloned().unwrap_or(false), /* vision= */ caps_dict.get(&"vision".to_string()).cloned().unwrap_or(false));
        ModelCard(/* id= */ base_model, /* name= */ filename.replace(&*".gguf".to_string(), &*"".to_string()).replace(&*".".to_string(), &*" ".to_string()), /* filename= */ filename, /* path= */ file_path, /* size= */ size_str, /* size_bytes= */ size_bytes, /* base_model= */ base_model, /* quantization= */ quantization, /* category= */ category, /* context= */ metadata.get(&"context".to_string()).cloned().unwrap_or(4096), /* estimated_speed= */ metadata.get(&"estimated_speed".to_string()).cloned().unwrap_or(10), /* recommended_ram= */ metadata.get(&"recommended_ram".to_string()).cloned().unwrap_or(8), /* description= */ metadata.get(&"description".to_string()).cloned().unwrap_or(format!("{} model", base_model)), /* capabilities= */ caps, /* source= */ metadata.get(&"source".to_string()).cloned().unwrap_or(base_model), /* url= */ metadata.get(&"url".to_string()).cloned().unwrap_or(format!("https://huggingface.co/{}", base_model)))
    }
    /// Extract base model name from filename
    /// 
    /// Args:
    /// filename: GGUF filename
    /// 
    /// Returns:
    /// Normalized base model name
    pub fn _extract_base_model(&self, filename: String) -> String {
        // Extract base model name from filename
        // 
        // Args:
        // filename: GGUF filename
        // 
        // Returns:
        // Normalized base model name
        let mut name = filename.replace(&*".gguf".to_string(), &*"".to_string());
        let mut parts = name.split(".".to_string()).map(|s| s.to_string()).collect::<Vec<String>>();
        let mut base = if parts { parts[0] } else { name };
        let mut base = base::to_lowercase();
        let mut replacements = HashMap::from([("mistral".to_string(), "mistral".to_string()), ("llama".to_string(), "llama".to_string()), ("qwen".to_string(), "qwen2.5".to_string()), ("deepseek".to_string(), "deepseek-coder".to_string()), ("phi".to_string(), "phi".to_string()), ("tinyllama".to_string(), "tinyllama".to_string()), ("openchat".to_string(), "openchat".to_string()), ("zephyr".to_string(), "zephyr".to_string()), ("neural".to_string(), "neural-chat".to_string()), ("nous".to_string(), "nous-hermes".to_string())]);
        for (key, val) in replacements.iter().iter() {
            if base::contains(&key) {
                val
            }
        }
        base
    }
    /// Extract quantization type from filename
    /// 
    /// Args:
    /// filename: GGUF filename
    /// 
    /// Returns:
    /// Quantization type or None
    pub fn _extract_quantization(&self, filename: String) -> Option<String> {
        // Extract quantization type from filename
        // 
        // Args:
        // filename: GGUF filename
        // 
        // Returns:
        // Quantization type or None
        let mut quant_types = vec!["Q2_K".to_string(), "Q3_K".to_string(), "Q4_K".to_string(), "Q4_1".to_string(), "Q5_K".to_string(), "Q5_1".to_string(), "Q6_K".to_string(), "Q8_0".to_string(), "F16".to_string(), "F32".to_string()];
        let mut filename_upper = filename.to_uppercase();
        for quant in quant_types.iter() {
            if filename_upper.contains(&quant) {
                quant
            }
        }
        None
    }
    /// Determine category by model size or name hints
    /// 
    /// Args:
    /// size_bytes: File size in bytes
    /// base_model: Base model name
    /// 
    /// Returns:
    /// ModelCategory
    pub fn _determine_category(&self, size_bytes: i64, base_model: String) -> ModelCategory {
        // Determine category by model size or name hints
        // 
        // Args:
        // size_bytes: File size in bytes
        // base_model: Base model name
        // 
        // Returns:
        // ModelCategory
        let mut size_gb = (size_bytes / (1024).pow(3 as u32));
        if vec!["tiny".to_string(), "small".to_string(), "mini".to_string()].iter().map(|x| base_model.to_lowercase().contains(&x)).collect::<Vec<_>>().iter().any(|v| *v) {
            ModelCategory.FAST
        }
        if (base_model.to_lowercase().contains(&"large".to_string()) || base_model.to_lowercase().contains(&"xl".to_string())) {
            ModelCategory.LARGE
        }
        if size_gb < 1.5_f64 {
            ModelCategory.FAST
        } else if size_gb > 10 {
            ModelCategory.LARGE
        } else {
            ModelCategory.BALANCED
        }
    }
    /// Format bytes to human-readable size
    pub fn _format_size(&self, size_bytes: i64) -> String {
        // Format bytes to human-readable size
        for unit in vec!["B".to_string(), "KB".to_string(), "MB".to_string(), "GB".to_string()].iter() {
            if size_bytes < 1024 {
                format!("~{:.1}{}", size_bytes, unit)
            }
            size_bytes /= 1024;
        }
        format!("~{:.1}TB", size_bytes)
    }
    /// Group models by base model name
    pub fn _group_by_base_model(&mut self) -> () {
        // Group models by base model name
        self._model_groups = HashMap::new();
        for model in self.models::iter() {
            let mut base = model.base_model;
            if !self._model_groups.contains(&base) {
                self._model_groups[base] = vec![];
            }
            self._model_groups[&base].push(model);
        }
    }
    /// Get models with same base but different quantizations
    /// 
    /// Returns:
    /// Dict of base_model: [variants...]
    pub fn get_duplicates(&mut self) -> HashMap<String, Vec<ModelCard>> {
        // Get models with same base but different quantizations
        // 
        // Returns:
        // Dict of base_model: [variants...]
        let _ctx = self._lock;
        {
            let mut duplicates = HashMap::new();
            for (base, models) in self._model_groups.iter().iter() {
                if models::len() > 1 {
                    duplicates[base] = models;
                }
            }
            duplicates
        }
    }
    /// Get models in specific category
    pub fn get_cards_by_category(&mut self, category: ModelCategory) -> Vec<ModelCard> {
        // Get models in specific category
        let _ctx = self._lock;
        {
            self.models::iter().filter(|m| m.category == category).map(|m| m).collect::<Vec<_>>()
        }
    }
    /// Get model recommendations for use case
    /// 
    /// Args:
    /// use_case: 'fast', 'balanced', 'quality', 'coding', 'reasoning'
    /// 
    /// Returns:
    /// Recommended models
    pub fn get_recommendations(&mut self, use_case: String) -> Vec<ModelCard> {
        // Get model recommendations for use case
        // 
        // Args:
        // use_case: 'fast', 'balanced', 'quality', 'coding', 'reasoning'
        // 
        // Returns:
        // Recommended models
        let _ctx = self._lock;
        {
            if use_case == "fast".to_string() {
                self.get_cards_by_category(ModelCategory.FAST)
            } else if use_case == "balanced".to_string() {
                self.get_cards_by_category(ModelCategory.BALANCED)
            } else if use_case == "quality".to_string() {
                { let mut v = self.get_cards_by_category(ModelCategory.LARGE).clone(); v.sort(); v }
            } else if use_case == "coding".to_string() {
                { let mut v = self.models::iter().filter(|m| m.capabilities.coding).map(|m| m).collect::<Vec<_>>().clone(); v.sort(); v }
            } else if use_case == "reasoning".to_string() {
                { let mut v = self.models::iter().filter(|m| m.capabilities.reasoning).map(|m| m).collect::<Vec<_>>().clone(); v.sort(); v }
            }
            self.models
        }
    }
    /// Get all models as UI-ready card dicts
    pub fn get_all_cards(&self) -> Vec<HashMap> {
        // Get all models as UI-ready card dicts
        let _ctx = self._lock;
        {
            self.models::iter().map(|m| m.to_card_dict()).collect::<Vec<_>>()
        }
    }
}
