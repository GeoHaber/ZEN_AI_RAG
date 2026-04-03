/// Core/parent_document_retrieval::py — Hierarchical Parent Document Retrieval.
/// 
/// Industry best practice: Index smaller child chunks for precise matching
/// but return their larger parent chunks to give the LLM more context.
/// This solves the chunk-size tradeoff: small chunks for retrieval precision,
/// large chunks for generation context.
/// 
/// Pipeline:
/// 1. Split documents into large "parent" chunks (e.g., 2000 chars)
/// 2. Split parents into smaller "child" chunks (e.g., 500 chars)
/// 3. Index child chunks with parent_id reference
/// 4. On retrieval: match child chunks, then return parent chunks
/// 5. Deduplicate parents to avoid redundant context
/// 
/// References:
/// - LangChain ParentDocumentRetriever
/// - "Small-to-Big" retrieval pattern (LlamaIndex)

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::collections::HashSet;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// A parent chunk containing child chunks.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParentChunk {
    pub text: String,
    pub chunk_id: String,
    pub metadata: HashMap<String, Box<dyn std::any::Any>>,
    pub children: Vec<HashMap<String, Box<dyn std::any::Any>>>,
}

impl ParentChunk {
    pub fn __post_init__(&mut self) -> () {
        if !self.chunk_id {
            self.chunk_id = hashlib::sha256(self.text[..200].as_bytes().to_vec()).hexdigest()[..16];
        }
    }
}

/// Result of parent document retrieval.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParentRetrievalResult {
    pub parent_chunks: Vec<ParentChunk>,
    pub matched_children: Vec<HashMap<String, Box<dyn std::any::Any>>>,
    pub child_to_parent_map: HashMap<String, String>,
    pub total_parent_chars: i64,
}

/// Hierarchical retrieval: match children, return parents.
/// 
/// Indexes small chunks for precision but expands to full parent
/// context for generation, giving the LLM the surrounding context
/// it needs to produce coherent answers.
/// 
/// Usage:
/// pdr = ParentDocumentRetriever(parent_size=2000, child_size=500)
/// parents, children = pdr.create_hierarchy(document_text, metadata)
/// # Index children in vector store with parent_id
/// 
/// # At retrieval time:
/// results = pdr.expand_to_parents(matched_children, parent_store)
#[derive(Debug, Clone)]
pub struct ParentDocumentRetriever {
    pub parent_size: String,
    pub child_size: String,
    pub child_overlap: String,
    pub max_parents_returned: String,
    pub _parent_store: HashMap<String, ParentChunk>,
}

impl ParentDocumentRetriever {
    /// Args:
    /// parent_size: char size for parent chunks
    /// child_size: char size for child chunks
    /// child_overlap: overlap between child chunks
    /// max_parents_returned: max parent chunks in output
    pub fn new(parent_size: i64, child_size: i64, child_overlap: i64, max_parents_returned: i64) -> Self {
        Self {
            parent_size,
            child_size,
            child_overlap,
            max_parents_returned,
            _parent_store: HashMap::new(),
        }
    }
    /// Split a document into parent and child chunks.
    /// 
    /// Returns:
    /// (parent_chunks, child_chunks) where each child has 'parent_id'
    pub fn create_hierarchy(&mut self, text: String, metadata: Option<HashMap<String, Box<dyn std::any::Any>>>) -> (Vec<ParentChunk>, Vec<HashMap<String, Box<dyn std::any::Any>>>) {
        // Split a document into parent and child chunks.
        // 
        // Returns:
        // (parent_chunks, child_chunks) where each child has 'parent_id'
        let mut metadata = (metadata || HashMap::new());
        let mut parents = self._split_text(text, self.parent_size, /* overlap= */ 0);
        let mut all_children = vec![];
        let mut parent_chunks = vec![];
        for (i, parent_text) in parents.iter().enumerate().iter() {
            let mut parent = ParentChunk(/* text= */ parent_text, /* metadata= */ HashMap::from([("parent_index".to_string(), i)]));
            let mut child_texts = self._split_text(parent_text, self.child_size, self.child_overlap);
            for (j, child_text) in child_texts.iter().enumerate().iter() {
                let mut child = HashMap::from([("text".to_string(), child_text), ("parent_id".to_string(), parent.chunk_id), ("chunk_index".to_string(), all_children.len()), ("child_index".to_string(), j), ("parent_index".to_string(), i)]);
                parent.children.push(child);
                all_children.push(child);
            }
            parent_chunks.push(parent);
            self._parent_store[parent.chunk_id] = parent;
        }
        logger.info(format!("[ParentDoc] Created {} parents, {} children", parent_chunks.len(), all_children.len()));
        (parent_chunks, all_children)
    }
    /// Given matched child chunks, expand to their parent chunks.
    /// 
    /// Deduplicates parents and orders by number of matched children
    /// (more child matches = more relevant parent).
    pub fn expand_to_parents(&mut self, matched_children: Vec<HashMap<String, Box<dyn std::any::Any>>>, parent_store: Option<HashMap<String, ParentChunk>>) -> ParentRetrievalResult {
        // Given matched child chunks, expand to their parent chunks.
        // 
        // Deduplicates parents and orders by number of matched children
        // (more child matches = more relevant parent).
        let mut store = (parent_store || self._parent_store);
        let mut result = ParentRetrievalResult(/* matched_children= */ matched_children);
        let mut parent_hits = HashMap::new();
        let mut child_map = HashMap::new();
        for child in matched_children.iter() {
            let mut pid = child.get(&"parent_id".to_string()).cloned();
            if pid {
                parent_hits[pid] = (parent_hits.get(&pid).cloned().unwrap_or(0) + 1);
                let mut child_key = child.get(&"text".to_string()).cloned().unwrap_or("".to_string())[..50];
                child_map[child_key] = pid;
            }
        }
        result.child_to_parent_map = child_map;
        let mut ranked_parents = { let mut v = parent_hits.iter().clone(); v.sort(); v };
        for (pid, hit_count) in ranked_parents[..self.max_parents_returned].iter() {
            let mut parent = store.get(&pid).cloned();
            if parent {
                result.parent_chunks.push(parent);
                result.total_parent_chars += parent.text.len();
            }
        }
        logger.info(format!("[ParentDoc] Expanded {} children → {} parents ({} chars)", matched_children.len(), result.parent_chunks.len(), result.total_parent_chars));
        result
    }
    /// Replace child search results with their parent chunks.
    /// 
    /// Maintains result ordering while expanding context.
    /// Returns results suitable for the standard RAG pipeline.
    pub fn get_parent_context(&mut self, search_results: Vec<HashMap<String, Box<dyn std::any::Any>>>, parent_store: Option<HashMap<String, ParentChunk>>) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
        // Replace child search results with their parent chunks.
        // 
        // Maintains result ordering while expanding context.
        // Returns results suitable for the standard RAG pipeline.
        let mut store = (parent_store || self._parent_store);
        let mut seen_parents = HashSet::new();
        let mut expanded = vec![];
        for result in search_results.iter() {
            let mut pid = result.get(&"parent_id".to_string()).cloned();
            if (pid && !seen_parents.contains(&pid)) {
                let mut parent = store.get(&pid).cloned();
                if parent {
                    seen_parents.insert(pid);
                    expanded.push(HashMap::from([("text".to_string(), parent.text), ("parent_text".to_string(), parent.text), ("_expanded_from_child".to_string(), true), ("_child_score".to_string(), result.get(&"score".to_string()).cloned().unwrap_or(0))]));
                    continue;
                }
            }
            if (!pid || seen_parents.contains(&pid)) {
                if !expanded.iter().map(|e| e.get(&"text".to_string()).cloned().unwrap_or("".to_string())[..50]).collect::<HashSet<_>>().contains(&result.get(&"text".to_string()).cloned().unwrap_or("".to_string())[..50]) {
                    expanded.push(result);
                }
            }
        }
        expanded[..(self.max_parents_returned * 2)]
    }
    /// Register parent chunks for later retrieval expansion.
    pub fn register_parents(&mut self, parents: Vec<ParentChunk>) -> () {
        // Register parent chunks for later retrieval expansion.
        for parent in parents.iter() {
            self._parent_store[parent.chunk_id] = parent;
        }
    }
    /// Clear the parent store.
    pub fn clear(&self) -> () {
        // Clear the parent store.
        self._parent_store.clear();
    }
    /// Simple character-level text splitter with overlap.
    pub fn _split_text(text: String, chunk_size: i64, overlap: i64) -> Vec<String> {
        // Simple character-level text splitter with overlap.
        if (!text || chunk_size <= 0) {
            vec![]
        }
        let mut overlap = overlap.min((chunk_size - 1));
        let mut chunks = vec![];
        let mut start = 0;
        while start < text.len() {
            let mut end = (start + chunk_size);
            if end < text.len() {
                let mut para_break = text.rfind("\n\n".to_string(), start, end);
                if para_break > (start + (chunk_size / 2)) {
                    let mut end = (para_break + 2);
                } else {
                    let mut sent_break = max(text.rfind(". ".to_string(), start, end), text.rfind("! ".to_string(), start, end), text.rfind("? ".to_string(), start, end));
                    if sent_break > (start + (chunk_size / 2)) {
                        let mut end = (sent_break + 2);
                    }
                }
            }
            let mut chunk = text[start..end].trim().to_string();
            if chunk {
                chunks.push(chunk);
            }
            let mut new_start = if overlap > 0 { (end - overlap) } else { end };
            let mut start = new_start.max((start + 1));
        }
        chunks
    }
}
