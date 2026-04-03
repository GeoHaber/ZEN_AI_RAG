/// Core/prompt_focus::py — Focus-Mode Prompt Injection for Small LLMs
/// 
/// Constrains and focuses the LLM (especially ≤13B models via llama.cpp)
/// toward specific data-understanding tasks by injecting:
/// 
/// 1. **System prompt** (BEFORE the user query) — sets persona + output rules
/// 2. **Query wrapper** (AROUND the user query) — tells the LLM *how* to
/// process the retrieved RAG context for this specific task
/// 
/// Design principles for small-model effectiveness:
/// - System prompts ≤ 200 tokens (longer → coherence loss)
/// - Imperative verbs: "Extract", "List", "Compare" (not soft requests)
/// - Explicit format constraints: "Output as: ..."
/// - Negative constraints: "Do NOT ..." (prevents rambling)
/// - Language-aware: responds in user's language
/// 
/// Usage:
/// from Core.prompt_focus import FocusMode, get_focus_config, apply_focus
/// 
/// # Get all available modes for UI dropdown
/// modes = FocusMode.choices()
/// 
/// # Apply focus to a user query before sending to LLM
/// system_prompt, wrapped_query = apply_focus(
/// FocusMode.DATA_EXTRACTION, user_query, language="en"
/// )
/// 
/// # Use a template from the example library
/// from Core.prompt_focus import PromptTemplateLibrary
/// lib = PromptTemplateLibrary()
/// templates = lib.list_templates()            # all built-in + custom
/// tpl = lib.get_template("medical_symptoms")  # grab a specific one
/// system, query = lib.apply_template("medical_symptoms", user_query)
/// 
/// # Create your own custom prompt
/// lib.save_custom(
/// name="my_legal_prompt",
/// system_prompt="You are a legal analyst. ...",
/// query_prefix="ANALYZE the legal implications of: ",
/// query_suffix="\nList each legal risk with severity.",
/// temperature=0.2,
/// icon="⚖️",
/// description="Legal risk analysis from documents",
/// category="Legal",
/// )

use anyhow::{Result, Context};
use regex::Regex;
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::collections::HashSet;
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static _FOCUS_CONFIGS: std::sync::LazyLock<HashMap<FocusMode, FocusConfig>> = std::sync::LazyLock::new(|| HashMap::new());

pub static _BUILTIN_TEMPLATES: std::sync::LazyLock<HashMap<String, PromptTemplate>> = std::sync::LazyLock::new(|| HashMap::new());

pub const _CUSTOM_PROMPTS_FILE: &str = "Path('data') / 'custom_prompts.json";

pub const _MAX_SYSTEM_PROMPT_TOKENS: i64 = 200;

pub const _MAX_SYSTEM_PROMPT_CHARS: i64 = 800;

pub static _LIBRARY_INSTANCE: std::sync::LazyLock<Option<PromptTemplateLibrary>> = std::sync::LazyLock::new(|| None);

/// Available LLM focus modes for data understanding tasks.
#[derive(Debug, Clone)]
pub struct FocusMode {
}

impl FocusMode {
    /// Return (value, icon, label) tuples for UI dropdowns.
    pub fn choices() -> Vec<(String, String, String)> {
        // Return (value, icon, label) tuples for UI dropdowns.
        vec![(cls.GENERAL.value, "💬".to_string(), "General Assistant".to_string()), (cls.DATA_EXTRACTION.value, "📊".to_string(), "Data Extraction".to_string()), (cls.SUMMARIZATION.value, "📝".to_string(), "Summarization".to_string()), (cls.COMPARISON.value, "⚖️".to_string(), "Comparison".to_string()), (cls.FACT_CHECK.value, "✅".to_string(), "Fact Checking".to_string()), (cls.TIMELINE.value, "📅".to_string(), "Timeline Builder".to_string()), (cls.DEEP_ANALYSIS.value, "🔬".to_string(), "Deep Analysis".to_string())]
    }
    /// Safe conversion from string, defaults to GENERAL.
    pub fn from_string(value: String) -> Result<()> {
        // Safe conversion from string, defaults to GENERAL.
        // try:
        {
            cls(value)
        }
        // except ValueError as _e:
    }
}

/// Immutable configuration for a single focus mode.
/// 
/// Attributes:
/// mode:           The FocusMode enum value
/// icon:           Emoji icon for UI display
/// label:          Human-readable label
/// system_prompt:  Injected as the system message (persona + rules)
/// query_prefix:   Prepended to the user query (task directive)
/// query_suffix:   Appended after the user query (output format)
/// temperature:    Suggested temperature override (None = use default)
/// description:    Short help text for the UI tooltip
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FocusConfig {
    pub mode: FocusMode,
    pub icon: String,
    pub label: String,
    pub system_prompt: String,
    pub query_prefix: String,
    pub query_suffix: String,
    pub temperature: Option<f64>,
    pub description: String,
}

/// A reusable prompt template (built-in or user-created).
/// 
/// Each template follows the Small-LLM Design Rules:
/// ✓ System prompt ≤ 200 tokens
/// ✓ Imperative verbs ("Extract", "List", "Compare")
/// ✓ Format constraints ("Output as: ...")
/// ✓ Negative constraints ("Do NOT ...")
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PromptTemplate {
    pub name: String,
    pub label: String,
    pub icon: String,
    pub category: String,
    pub system_prompt: String,
    pub query_prefix: String,
    pub query_suffix: String,
    pub temperature: f64,
    pub description: String,
    pub is_builtin: bool,
    pub example_query: String,
}

impl PromptTemplate {
    /// Serialize for JSON persistence.
    pub fn to_dict(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Serialize for JSON persistence.
        HashMap::from([("name".to_string(), self.name), ("label".to_string(), self.label), ("icon".to_string(), self.icon), ("category".to_string(), self.category), ("system_prompt".to_string(), self.system_prompt), ("query_prefix".to_string(), self.query_prefix), ("query_suffix".to_string(), self.query_suffix), ("temperature".to_string(), self.temperature), ("description".to_string(), self.description), ("is_builtin".to_string(), self.is_builtin), ("example_query".to_string(), self.example_query)])
    }
    /// Deserialize from JSON.
    pub fn from_dict(d: HashMap<String, Box<dyn std::any::Any>>) -> () {
        // Deserialize from JSON.
        cls(/* ** */ d.iter().iter().filter(|(k, v)| cls.__dataclass_fields__.contains(&k)).map(|(k, v)| (k, v)).collect::<HashMap<_, _>>())
    }
}

/// Manages both built-in templates and user-created custom prompts.
/// 
/// Built-in templates are read-only examples. Users can:
/// 1. Use them as-is  (apply_template)
/// 2. Clone + edit them  (clone_as_custom)
/// 3. Create from scratch  (save_custom)
/// 4. Delete custom ones  (delete_custom)
/// 
/// Custom prompts are persisted to data/custom_prompts.json.
#[derive(Debug, Clone)]
pub struct PromptTemplateLibrary {
    pub _builtins: HashMap<String, serde_json::Value>,
    pub _customs: HashMap<String, PromptTemplate>,
    pub _storage: String,
}

impl PromptTemplateLibrary {
    pub fn new(storage_dir: Option<PathBuf>) -> Self {
        Self {
            _builtins: /* dict(_BUILTIN_TEMPLATES) */ HashMap::new(),
            _customs: HashMap::new(),
            _storage: (storage_dir || _CUSTOM_PROMPTS_FILE),
        }
    }
    /// List templates, optionally filtered by category.
    pub fn list_templates(&mut self, category: Option<String>, include_builtins: bool, include_customs: bool) -> Vec<PromptTemplate> {
        // List templates, optionally filtered by category.
        let mut result = vec![];
        if include_builtins {
            result.extend(self._builtins.values());
        }
        if include_customs {
            result.extend(self._customs.values());
        }
        if category {
            let mut result = result.iter().filter(|t| t.category.to_lowercase() == category.to_lowercase()).map(|t| t).collect::<Vec<_>>();
        }
        { let mut v = result.clone(); v.sort(); v }
    }
    /// List unique categories across all templates.
    pub fn list_categories(&mut self) -> Vec<String> {
        // List unique categories across all templates.
        let mut cats = HashSet::new();
        for t in self._builtins.values().iter() {
            cats.insert(t.category);
        }
        for t in self._customs.values().iter() {
            cats.insert(t.category);
        }
        { let mut v = cats.clone(); v.sort(); v }
    }
    /// Get a template by name (checks customs first, then builtins).
    pub fn get_template(&self, name: String) -> Option<PromptTemplate> {
        // Get a template by name (checks customs first, then builtins).
        (self._customs.get(&name).cloned() || self._builtins.get(&name).cloned())
    }
    pub fn builtin_count(&self) -> i64 {
        self._builtins.len()
    }
    pub fn custom_count(&self) -> i64 {
        self._customs.len()
    }
    /// Apply a template to a query. Returns (system_prompt, wrapped_query).
    pub fn apply_template(&mut self, name: String, user_query: String) -> (String, String) {
        // Apply a template to a query. Returns (system_prompt, wrapped_query).
        let mut tpl = self.get_template(name);
        if !tpl {
            logger.warning(format!("[PromptTemplateLibrary] Unknown template '{}', using passthrough", name));
            ("".to_string(), user_query)
        }
        let mut wrapped = user_query;
        if (tpl.query_prefix || tpl.query_suffix) {
            let mut wrapped = format!("{}{}{}", tpl.query_prefix, user_query, tpl.query_suffix);
        }
        logger.info(format!("[PromptTemplate] Applied '{}' ({}), query {}→{} chars", name, tpl.category, user_query.len(), wrapped.len()));
        (tpl.system_prompt, wrapped)
    }
    /// Create or update a custom prompt template.
    /// 
    /// Returns:
    /// (template, warnings) — warnings are advisory from validate_prompt.
    pub fn save_custom(&mut self, name: String, label: String, system_prompt: String, category: String, icon: String, query_prefix: String, query_suffix: String, temperature: f64, description: String, example_query: String) -> (PromptTemplate, Vec<String>) {
        // Create or update a custom prompt template.
        // 
        // Returns:
        // (template, warnings) — warnings are advisory from validate_prompt.
        let mut slug = regex::Regex::new(&"[^a-z0-9_]".to_string()).unwrap().replace_all(&"_".to_string(), name.to_lowercase().trim().to_string()).to_string();
        if !slug {
            let mut slug = "custom_prompt".to_string();
        }
        if self._builtins.contains(&slug) {
            let mut slug = format!("custom_{}", slug);
        }
        let mut warnings = validate_prompt(system_prompt);
        let mut tpl = PromptTemplate(/* name= */ slug, /* label= */ label, /* icon= */ icon, /* category= */ category, /* system_prompt= */ system_prompt, /* query_prefix= */ query_prefix, /* query_suffix= */ query_suffix, /* temperature= */ temperature, /* description= */ description, /* is_builtin= */ false, /* example_query= */ example_query);
        self._customs[slug] = tpl;
        self._save_customs();
        logger.info(format!("[PromptTemplateLibrary] Saved custom template '{}' ({})", slug, category));
        (tpl, warnings)
    }
    /// Delete a custom template. Returns true if deleted.
    pub fn delete_custom(&self, name: String) -> bool {
        // Delete a custom template. Returns true if deleted.
        if self._customs.contains(&name) {
            drop(self._customs[name]);
            self._save_customs();
            logger.info(format!("[PromptTemplateLibrary] Deleted custom template '{}'", name));
            true
        }
        false
    }
    /// Clone a built-in template as a custom one for editing.
    pub fn clone_as_custom(&mut self, source_name: String, new_name: Option<String>) -> Option<PromptTemplate> {
        // Clone a built-in template as a custom one for editing.
        let mut source = self.get_template(source_name);
        if !source {
            None
        }
        let mut slug = (new_name || format!("custom_{}", source.name));
        let mut slug = regex::Regex::new(&"[^a-z0-9_]".to_string()).unwrap().replace_all(&"_".to_string(), slug.to_lowercase().trim().to_string()).to_string();
        let mut tpl = PromptTemplate(/* name= */ slug, /* label= */ format!("{} (Custom)", source.label), /* icon= */ source.icon, /* category= */ source.category, /* system_prompt= */ source.system_prompt, /* query_prefix= */ source.query_prefix, /* query_suffix= */ source.query_suffix, /* temperature= */ source.temperature, /* description= */ source.description, /* is_builtin= */ false, /* example_query= */ source.example_query);
        self._customs[slug] = tpl;
        self._save_customs();
        tpl
    }
    /// Load custom prompts from disk.
    pub fn _load_customs(&mut self) -> Result<()> {
        // Load custom prompts from disk.
        // try:
        {
            if self._storage.exists() {
                let mut data = serde_json::from_str(&self._storage.read_to_string())).unwrap();
                for entry in data.iter() {
                    // try:
                    {
                        let mut tpl = PromptTemplate.from_dict(entry);
                        self._customs[tpl.name] = tpl;
                    }
                    // except Exception as e:
                }
                logger.info(format!("[PromptTemplateLibrary] Loaded {} custom templates", self._customs.len()));
            }
        }
        // except Exception as e:
    }
    /// Persist custom prompts to disk.
    pub fn _save_customs(&mut self) -> Result<()> {
        // Persist custom prompts to disk.
        // try:
        {
            self._storage.parent().unwrap_or(std::path::Path::new("")).create_dir_all();
            let mut data = self._customs.values().iter().map(|tpl| tpl.to_dict()).collect::<Vec<_>>();
            self._storagestd::fs::write(&serde_json::to_string(&data).unwrap(), /* encoding= */ "utf-8".to_string());
        }
        // except Exception as e:
    }
}

/// Get the configuration for a focus mode.
pub fn get_focus_config(mode: FocusMode) -> FocusConfig {
    // Get the configuration for a focus mode.
    _FOCUS_CONFIGS.get(&mode).cloned().unwrap_or(_FOCUS_CONFIGS[&FocusMode.GENERAL])
}

/// Get all focus mode configurations (for UI listing).
pub fn get_all_configs() -> HashMap<FocusMode, FocusConfig> {
    // Get all focus mode configurations (for UI listing).
    /* dict(_FOCUS_CONFIGS) */ HashMap::new()
}

/// Apply focus mode to a query.
/// 
/// Returns:
/// (system_prompt, wrapped_query) — ready to send to the LLM.
/// 
/// The system_prompt REPLACES the default one (not appends) because small
/// models get confused by contradictory instructions. The wrapped_query
/// is the user query with task-specific prefix/suffix.
/// 
/// If mode is GENERAL, returns the existing_system_prompt unchanged
/// and the query unmodified (backwards compatible).
pub fn apply_focus(mode: FocusMode, user_query: String, existing_system_prompt: Option<String>) -> (String, String) {
    // Apply focus mode to a query.
    // 
    // Returns:
    // (system_prompt, wrapped_query) — ready to send to the LLM.
    // 
    // The system_prompt REPLACES the default one (not appends) because small
    // models get confused by contradictory instructions. The wrapped_query
    // is the user query with task-specific prefix/suffix.
    // 
    // If mode is GENERAL, returns the existing_system_prompt unchanged
    // and the query unmodified (backwards compatible).
    let mut config = get_focus_config(mode);
    if (mode == FocusMode.GENERAL && existing_system_prompt) {
        let mut system_prompt = existing_system_prompt;
    } else {
        let mut system_prompt = config::system_prompt;
    }
    if (config::query_prefix || config::query_suffix) {
        let mut wrapped_query = format!("{}{}{}", config::query_prefix, user_query, config::query_suffix);
    } else {
        let mut wrapped_query = user_query;
    }
    if mode != FocusMode.GENERAL {
        logger.info(format!("[PromptFocus] Mode={}, system={} chars, query={}→{} chars", mode.value, system_prompt.len(), user_query.len(), wrapped_query.len()));
    }
    (system_prompt, wrapped_query)
}

/// Get the suggested temperature for a mode, or None for default.
pub fn get_suggested_temperature(mode: FocusMode) -> Option<f64> {
    // Get the suggested temperature for a mode, or None for default.
    let mut config = get_focus_config(mode);
    config::temperature
}

/// Get the help text for a mode.
pub fn get_mode_description(mode: FocusMode) -> String {
    // Get the help text for a mode.
    let mut config = get_focus_config(mode);
    config::description
}

/// Get the icon for a mode.
pub fn get_mode_icon(mode: FocusMode) -> String {
    // Get the icon for a mode.
    let mut config = get_focus_config(mode);
    config::icon
}

pub fn _register(tpl: PromptTemplate) -> PromptTemplate {
    _BUILTIN_TEMPLATES[tpl.name] = tpl;
    tpl
}

/// Rough token estimate (≈ 0.75 words per token for English).
pub fn _estimate_tokens(text: String) -> i64 {
    // Rough token estimate (≈ 0.75 words per token for English).
    1.max((text.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().len() / 0.75_f64).to_string().parse::<i64>().unwrap_or(0))
}

/// Validate a prompt against small-LLM design rules.
/// 
/// Returns a list of warnings (empty = all good).
/// These are advisory, not blocking — user can still save.
pub fn validate_prompt(system_prompt: String) -> Vec<String> {
    // Validate a prompt against small-LLM design rules.
    // 
    // Returns a list of warnings (empty = all good).
    // These are advisory, not blocking — user can still save.
    let mut warnings = vec![];
    let mut tokens = _estimate_tokens(system_prompt);
    if tokens > _MAX_SYSTEM_PROMPT_TOKENS {
        warnings.push(format!("System prompt ~{} tokens (recommended ≤{}). Small models may lose coherence with long instructions.", tokens, _MAX_SYSTEM_PROMPT_TOKENS));
    }
    if system_prompt.len() > _MAX_SYSTEM_PROMPT_CHARS {
        warnings.push(format!("System prompt {} chars — consider trimming.", system_prompt.len()));
    }
    let mut _IMPERATIVES = regex::Regex::new(&"\\b(extract|list|compare|identify|find|check|analyze|verify|summarize|output|determine|map|review|flag|cite|note)\\b".to_string()).unwrap();
    if !_IMPERATIVES.search(system_prompt) {
        warnings.push("No imperative verbs found. Small LLMs respond better to direct commands like 'Extract', 'List', 'Compare'.".to_string());
    }
    if !regex::Regex::new(&"(output|format|respond|structure)".to_string()).unwrap().is_match(&system_prompt) {
        warnings.push("No format constraint detected. Add 'Output as: ...' to force structured responses from small models.".to_string());
    }
    if !regex::Regex::new(&"(do not|don\\'t|never|avoid|skip)".to_string()).unwrap().is_match(&system_prompt) {
        warnings.push("No negative constraint. Adding 'Do NOT ...' prevents the #1 small-LLM failure: rambling off-topic.".to_string());
    }
    warnings
}

/// Get the singleton PromptTemplateLibrary instance.
pub fn get_template_library() -> PromptTemplateLibrary {
    // Get the singleton PromptTemplateLibrary instance.
    // global/nonlocal _library_instance
    if _library_instance.is_none() {
        let mut _library_instance = PromptTemplateLibrary();
    }
    _library_instance
}
