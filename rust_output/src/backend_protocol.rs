/// backend_protocol::py — Shared Backend Interface
/// ================================================
/// 
/// Defines the `UIBackend` protocol: every backend operation that ANY UI
/// (NiceGUI, Flet, FastAPI, CLI) can call.  Both ``zena.py`` and ``app::py``
/// should route through a concrete implementation of this protocol so that
/// feature parity is guaranteed.
/// 
/// Usage::
/// 
/// from backend_protocol import UIBackend
/// from backend_impl import create_backend
/// 
/// backend: UIBackend = create_backend()
/// answer = await backend.chat("What is RAG?")

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Unified RAG query result returned by the backend.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RAGResult {
    pub answer: String,
    pub context: String,
    pub sources: Vec<HashMap<String, Box<dyn std::any::Any>>>,
    pub confidence: f64,
    pub hallucination_score: f64,
    pub conflicts: Vec<String>,
    pub mode: String,
    pub intent: String,
    pub stages: Vec<String>,
    pub latency_ms: f64,
    pub cached: bool,
}

/// Describes a local or remote LLM model.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelInfo {
    pub name: String,
    pub filename: String,
    pub description: String,
    pub size: String,
    pub icon: String,
    pub good_for: Vec<String>,
    pub speed: String,
    pub quality: String,
    pub repo_id: String,
}

/// Backend health check result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthStatus {
    pub llm_online: bool,
    pub hub_online: bool,
    pub rag_ready: bool,
    pub model_name: String,
    pub error: String,
}

/// Result of a web/folder/email scan.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScanResult {
    pub text: String,
    pub sources: Vec<HashMap<String, Box<dyn std::any::Any>>>,
    pub images: Vec<Box<dyn std::any::Any>>,
    pub chunks: i64,
    pub elapsed_s: f64,
}

/// Every operation the UI can request from the backend.
/// 
/// Both NiceGUI (zena.py) and Flet (app::py) import this and call
/// the same methods, guaranteeing feature parity.
#[derive(Debug, Clone)]
pub struct UIBackend {
}

impl UIBackend {
    /// Send a chat message and get a response (optionally RAG-augmented).
    pub async fn chat(&self, prompt: String) -> RAGResult {
        // Send a chat message and get a response (optionally RAG-augmented).
        Ellipsis;
    }
    /// Stream chat tokens one at a time.
    pub async fn chat_stream(&self, prompt: String) -> AsyncIterator<String> {
        // Stream chat tokens one at a time.
        Ellipsis;
    }
    /// Route prompt through multi-expert swarm/council.
    pub async fn council_chat(&self, prompt: String) -> HashMap<String, Box<dyn std::any::Any>> {
        // Route prompt through multi-expert swarm/council.
        Ellipsis;
    }
    /// Scrape a website and index into RAG.
    pub async fn scan_web(&self, url: String) -> ScanResult {
        // Scrape a website and index into RAG.
        Ellipsis;
    }
    /// Scan a local directory and index into RAG.
    pub async fn scan_folder(&self, path: String) -> ScanResult {
        // Scan a local directory and index into RAG.
        Ellipsis;
    }
    /// Ingest emails (.mbox/.pst or IMAP) into RAG.
    pub async fn scan_email(&self, path_or_config: String) -> ScanResult {
        // Ingest emails (.mbox/.pst or IMAP) into RAG.
        Ellipsis;
    }
    /// Build (or rebuild) the RAG vector index.
    pub async fn build_index(&self, documents: Vec<String>) -> () {
        // Build (or rebuild) the RAG vector index.
        Ellipsis;
    }
    /// Hybrid search the RAG index (no LLM generation).
    pub async fn rag_search(&self, query: String) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
        // Hybrid search the RAG index (no LLM generation).
        Ellipsis;
    }
    /// Return index stats: chunk count, sources, collection info.
    pub async fn rag_stats(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Return index stats: chunk count, sources, collection info.
        Ellipsis;
    }
    /// Detect and optionally remove conflicting/duplicate docs.
    pub async fn rag_cleanup(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Detect and optionally remove conflicting/duplicate docs.
        Ellipsis;
    }
    /// Find and report duplicate content in the index.
    pub async fn rag_dedup(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Find and report duplicate content in the index.
        Ellipsis;
    }
    /// List locally available LLM models.
    pub async fn list_models(&self) -> Vec<ModelInfo> {
        // List locally available LLM models.
        Ellipsis;
    }
    /// Load / switch to a specific model.
    pub async fn load_model(&self, filename: String) -> bool {
        // Load / switch to a specific model.
        Ellipsis;
    }
    /// Download a model from HuggingFace.
    pub async fn download_model(&self, repo_id: String, filename: String) -> HashMap<String, Box<dyn std::any::Any>> {
        // Download a model from HuggingFace.
        Ellipsis;
    }
    /// Text-to-speech: returns {audio_url, success, error}.
    pub async fn speak(&self, text: String) -> HashMap<String, Box<dyn std::any::Any>> {
        // Text-to-speech: returns {audio_url, success, error}.
        Ellipsis;
    }
    /// List available audio input devices.
    pub async fn voice_devices(&self) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
        // List available audio input devices.
        Ellipsis;
    }
    /// Check backend health (LLM, Hub, RAG).
    pub async fn health(&self) -> HealthStatus {
        // Check backend health (LLM, Hub, RAG).
        Ellipsis;
    }
    /// Run a quick LLM speed benchmark (tok/s).
    pub async fn benchmark(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Run a quick LLM speed benchmark (tok/s).
        Ellipsis;
    }
    /// Persist a message to conversation memory.
    pub async fn save_message(&self, role: String, content: String) -> () {
        // Persist a message to conversation memory.
        Ellipsis;
    }
    /// Build contextual prompt from conversation history.
    pub async fn build_context(&self, prompt: String) -> String {
        // Build contextual prompt from conversation history.
        Ellipsis;
    }
    /// Return semantic cache statistics.
    pub async fn cache_stats(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Return semantic cache statistics.
        Ellipsis;
    }
    /// Return evaluation metrics.
    pub async fn eval_stats(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Return evaluation metrics.
        Ellipsis;
    }
    /// Start Telegram/WhatsApp gateways if configured.
    pub async fn start_gateways(&self) -> HashMap<String, bool> {
        // Start Telegram/WhatsApp gateways if configured.
        Ellipsis;
    }
    /// Check for app/model updates.
    pub async fn check_updates(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Check for app/model updates.
        Ellipsis;
    }
    /// Extract text from an uploaded file (PDF, DOCX, image, etc.).
    pub async fn extract_text(&self, data: Vec<u8>, filename: String) -> String {
        // Extract text from an uploaded file (PDF, DOCX, image, etc.).
        Ellipsis;
    }
}
