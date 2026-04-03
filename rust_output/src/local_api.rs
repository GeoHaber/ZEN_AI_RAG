/// Local API - Direct Python Access to the Application
/// 
/// This adapter provides direct Python access to the ApplicationInterface.
/// Used by:
/// - Tests (to verify functionality)
/// - Local scripts (to automate tasks)
/// - Development (to debug)
/// 
/// NOT used by:
/// - UIs (they import this but wrap it appropriately)
/// - External HTTP clients (use HTTP adapter)

use anyhow::{Result, Context};
use crate::application_interface::{ApplicationInterface};
use crate::models::{QueryRequest, QueryResponse, ChatRequest, ChatResponse, ChatMessage, SearchRequest, SearchResponse, SearchResult, StreamRequest, StreamChunk, StatusResponse};
use std::collections::HashMap;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// The ACTUAL application implementation.
/// 
/// Delegates to the real service layer in Core/services/:
/// - RAGService  – retrieval-augmented generation pipeline
/// - LLMService  – provider-agnostic LLM access
/// - DocumentService – knowledge-base management
/// - SessionService – conversation history
#[derive(Debug, Clone)]
pub struct ApplicationCore {
    pub config: String,
    pub _initialized: bool,
    pub _uptime_start: Option<datetime>,
    pub _rag_service: Option<serde_json::Value>,
    pub _llm_service: Option<serde_json::Value>,
    pub _doc_service: Option<serde_json::Value>,
    pub _session_service: Option<serde_json::Value>,
    pub _provider: String /* self.config::get */,
    pub _model: String /* self.config::get */,
    pub _api_key: String /* self.config::get */,
}

impl ApplicationCore {
    pub fn new(config: HashMap<String, serde_json::Value>) -> Self {
        Self {
            config: (config || HashMap::new()),
            _initialized: false,
            _uptime_start: None,
            _rag_service: None,
            _llm_service: None,
            _doc_service: None,
            _session_service: None,
            _provider: self.config::get(&"provider".to_string()).cloned().unwrap_or("local".to_string()),
            _model: self.config::get(&"model".to_string()).cloned().unwrap_or("default".to_string()),
            _api_key: self.config::get(&"api_key".to_string()).cloned(),
        }
    }
    /// Instantiate and wire real services from Core/services/.
    pub async fn initialize(&mut self) -> Result<bool> {
        // Instantiate and wire real services from Core/services/.
        // try:
        {
            logger.info("Initializing ApplicationCore…".to_string());
            // TODO: from Core.services.llm_service import LLMService
            // TODO: from Core.services.rag_service import RAGService
            // TODO: from Core.services.document_service import DocumentService
            // TODO: from Core.services.session_service import SessionService
            self._llm_service = LLMService();
            self._rag_service = RAGService();
            self._doc_service = DocumentService();
            self._session_service = SessionService();
            self._rag_service.llm_service = self._llm_service;
            self._uptime_start = datetime::now();
            self._initialized = true;
            logger.info("ApplicationCore initialized successfully".to_string());
            true
        }
        // except Exception as e:
    }
    /// Graceful shutdown - release resources.
    pub async fn shutdown(&mut self) -> Result<bool> {
        // Graceful shutdown - release resources.
        // try:
        {
            logger.info("Shutting down ApplicationCore…".to_string());
            self._initialized = false;
            self._rag_service = None;
            self._llm_service = None;
            self._doc_service = None;
            self._session_service = None;
            logger.info("ApplicationCore shutdown complete".to_string());
            true
        }
        // except Exception as e:
    }
    /// Full RAG query: retrieve context → augment prompt → call LLM.
    pub async fn query(&mut self, request: QueryRequest) -> Result<QueryResponse> {
        // Full RAG query: retrieve context → augment prompt → call LLM.
        request.validate();
        logger.info(format!("Processing query: {}…", request.query[..50]));
        let mut start = datetime::now();
        // try:
        {
            let mut answer = self._rag_service.full_rag_pipeline(/* query= */ request.query, /* provider= */ self._provider, /* model= */ self._model, /* api_key= */ self._api_key, /* temperature= */ request.temperature, /* max_tokens= */ request.max_tokens).await;
            let mut sources = vec![];
            if request.include_sources {
                let mut sources = self._rag_service.retrieve_documents(/* query= */ request.query, /* top_k= */ 5).await;
            }
            let mut elapsed = ((datetime::now() - start).total_seconds() * 1000);
            let mut response = QueryResponse(/* content= */ answer, /* sources= */ sources, /* processing_time_ms= */ elapsed);
            logger.info(format!("Query completed in {:.1}ms", elapsed));
            response
        }
        // except Exception as e:
    }
    /// Conversational RAG with session history.
    pub async fn chat(&mut self, request: ChatRequest) -> Result<ChatResponse> {
        // Conversational RAG with session history.
        request.validate();
        logger.info(format!("Processing chat: session={}", request.session_id));
        let mut start = datetime::now();
        // try:
        {
            let mut session = self._session_service.get_session(request.session_id);
            if session.is_none() {
                self._session_service.create_session(/* user_id= */ request.session_id);
            }
            self._session_service.add_message(request.session_id, /* role= */ "user".to_string(), /* content= */ request.message);
            let mut recent = self._session_service.get_recent_history(request.session_id, /* max_messages= */ request.max_history);
            let mut history_msgs = recent.iter().map(|m| HashMap::from([("role".to_string(), m["role".to_string()]), ("content".to_string(), m["content".to_string()])])).collect::<Vec<_>>();
            let mut docs = self._rag_service.retrieve_documents(/* query= */ request.message, /* top_k= */ 5).await;
            if docs {
                let mut ctx_text = docs.iter().map(|d| d.get(&"content".to_string()).cloned().unwrap_or("".to_string())[..1000]).collect::<Vec<_>>().join(&"\n\n".to_string());
                let mut system_prompt = format!("Use the following context to answer the user. If the context is not relevant, say so.\n\nContext:\n{}", ctx_text);
            } else {
                let mut system_prompt = "You are a helpful assistant.".to_string();
            }
            let mut messages = vec![HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), system_prompt)])];
            messages.extend(history_msgs);
            let mut answer = self._llm_service.call_llm(/* provider= */ self._provider, /* model= */ self._model, /* messages= */ messages, /* api_key= */ self._api_key, /* temperature= */ request.temperature, /* max_tokens= */ request.max_tokens).await;
            self._session_service.add_message(request.session_id, /* role= */ "assistant".to_string(), /* content= */ answer);
            let mut assistant_msg = ChatMessage(/* role= */ "assistant".to_string(), /* content= */ answer);
            let mut full_hist = self._session_service.get_history(request.session_id);
            let mut chat_msgs = full_hist.iter().map(|m| ChatMessage(/* role= */ m["role".to_string()], /* content= */ m["content".to_string()])).collect::<Vec<_>>();
            let mut elapsed = ((datetime::now() - start).total_seconds() * 1000);
            let mut response = ChatResponse(/* message= */ assistant_msg, /* history= */ chat_msgs, /* processing_time_ms= */ elapsed);
            logger.info(format!("Chat completed in {:.1}ms", elapsed));
            response
        }
        // except Exception as e:
    }
    /// Knowledge-base search (embeddings / hybrid).
    pub async fn search(&mut self, request: SearchRequest) -> Result<SearchResponse> {
        // Knowledge-base search (embeddings / hybrid).
        request.validate();
        logger.info(format!("Searching: {}…", request.query[..50]));
        let mut start = datetime::now();
        // try:
        {
            let mut raw = self._rag_service.retrieve_documents(/* query= */ request.query, /* top_k= */ request.limit).await;
            let mut results = raw.iter().filter(|d| d.get(&"score".to_string()).cloned().unwrap_or(0.0_f64) >= request.threshold).map(|d| SearchResult(/* content= */ d.get(&"content".to_string()).cloned().unwrap_or("".to_string()), /* score= */ d.get(&"score".to_string()).cloned().unwrap_or(0.0_f64), /* document_id= */ d.get(&"name".to_string()).cloned().unwrap_or("unknown".to_string()))).collect::<Vec<_>>();
            let mut elapsed = ((datetime::now() - start).total_seconds() * 1000);
            let mut response = SearchResponse(/* results= */ results, /* total_count= */ results.len(), /* processing_time_ms= */ elapsed);
            logger.info(format!("Search completed in {:.1}ms ({} hits)", elapsed, results.len()));
            response
        }
        // except Exception as e:
    }
    /// Streaming RAG response - yields chunks as they arrive.
    pub async fn stream(&mut self, request: StreamRequest) -> Result<AsyncIterator<StreamChunk>> {
        // Streaming RAG response - yields chunks as they arrive.
        logger.info(format!("Starting stream: {}…", request.query[..50]));
        // try:
        {
            let mut chunk_id = 0;
            // async for
            while let Some(text) = self._rag_service.stream_rag_pipeline(/* query= */ request.query, /* provider= */ self._provider, /* model= */ self._model, /* api_key= */ self._api_key, /* temperature= */ request.temperature, /* max_tokens= */ request.max_tokens).next().await {
                /* yield StreamChunk(/* content= */ text, /* chunk_id= */ chunk_id, /* is_final= */ false) */;
                chunk_id += 1;
            }
            /* yield StreamChunk(/* content= */ "".to_string(), /* chunk_id= */ chunk_id, /* is_final= */ true) */;
        }
        // except Exception as e:
    }
    /// Real status from actual service instances.
    pub async fn get_status(&mut self) -> StatusResponse {
        // Real status from actual service instances.
        let mut uptime = if self._uptime_start { (datetime::now() - self._uptime_start).total_seconds() } else { 0.0_f64 };
        StatusResponse(/* is_ready= */ self._initialized, /* rag_engine_ready= */ self._rag_service.is_some(), /* llm_service_ready= */ self._llm_service.is_some(), /* cache_service_ready= */ true, /* uptime_seconds= */ uptime)
    }
    /// Return recent chat history for *session_id*.
    pub async fn get_chat_history(&mut self, session_id: String, limit: i64) -> Vec {
        // Return recent chat history for *session_id*.
        self._session_service.get_recent_history(session_id, /* max_messages= */ limit)
    }
    /// Clear all messages in *session_id*.
    pub async fn clear_chat_session(&self, session_id: String) -> bool {
        // Clear all messages in *session_id*.
        self._session_service.clear_session(session_id)
    }
    /// Aggregate stats from DocumentService.
    pub async fn get_knowledge_base_stats(&mut self) -> HashMap {
        // Aggregate stats from DocumentService.
        let mut docs = self._doc_service.list_indexed_documents();
        HashMap::from([("total_documents".to_string(), docs.len()), ("documents".to_string(), docs)])
    }
}

/// Public API for direct Python access.
/// 
/// This is what tests and scripts use.
/// It wraps ApplicationCore and provides a clean interface.
/// 
/// Example:
/// api = LocalAPI()
/// await api.initialize()
/// response = await api.query("What is RAG?")
/// await api.shutdown()
#[derive(Debug, Clone)]
pub struct LocalAPI {
    pub _app: ApplicationCore,
    pub _initialized: bool,
}

impl LocalAPI {
    /// Initialize LocalAPI
    pub fn new(config: HashMap<String, serde_json::Value>) -> Self {
        Self {
            _app: ApplicationCore(config),
            _initialized: false,
        }
    }
    /// Initialize the application
    pub async fn initialize(&mut self) -> bool {
        // Initialize the application
        self._initialized = self._app.initialize().await;
        self._initialized
    }
    /// Shutdown the application
    pub async fn shutdown(&self) -> bool {
        // Shutdown the application
        self._app.shutdown().await
    }
    /// Simple query method for tests.
    /// 
    /// Example:
    /// response = await api.query("What is RAG?")
    pub async fn query(&mut self, query_text: String, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> QueryResponse {
        // Simple query method for tests.
        // 
        // Example:
        // response = await api.query("What is RAG?")
        let mut request = QueryRequest(/* query= */ query_text, /* ** */ kwargs);
        self._app.query(request).await
    }
    /// Simple chat method for tests.
    /// 
    /// Example:
    /// response = await api.chat("Follow up question", session_id="user123")
    pub async fn chat(&mut self, message: String, session_id: String, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> ChatResponse {
        // Simple chat method for tests.
        // 
        // Example:
        // response = await api.chat("Follow up question", session_id="user123")
        let mut request = ChatRequest(/* message= */ message, /* session_id= */ session_id, /* ** */ kwargs);
        self._app.chat(request).await
    }
    /// Simple search method.
    /// 
    /// Example:
    /// response = await api.search("Document about RAG")
    pub async fn search(&mut self, query_text: String, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> SearchResponse {
        // Simple search method.
        // 
        // Example:
        // response = await api.search("Document about RAG")
        let mut request = SearchRequest(/* query= */ query_text, /* ** */ kwargs);
        self._app.search(request).await
    }
    /// Simple stream method.
    /// 
    /// Example:
    /// async for chunk in api.stream("Long question"):
    /// print(chunk.content, end="")
    pub async fn stream(&mut self, query_text: String, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> AsyncIterator<StreamChunk> {
        // Simple stream method.
        // 
        // Example:
        // async for chunk in api.stream("Long question"):
        // print(chunk.content, end="")
        let mut request = StreamRequest(/* query= */ query_text, /* ** */ kwargs);
        // async for
        while let Some(chunk) = self._app.stream(request).next().await {
            /* yield chunk */;
        }
    }
    /// Get application status
    pub async fn get_status(&self) -> StatusResponse {
        // Get application status
        self._app.get_status().await
    }
}
