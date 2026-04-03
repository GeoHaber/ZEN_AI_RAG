/// Research Agent — Autonomous Web Research with ReACT Loop
/// =========================================================
/// 3-phase pipeline: Search → Browse → Synthesize (LLM-powered).
/// Supports ReACT-style iterative reasoning when llm_fn is provided.
/// 
/// Usage:
/// from Core.research_agent import ResearchAgent, quick_research
/// 
/// agent = ResearchAgent()
/// result = agent.research("What is FLARE retrieval?", llm_fn=my_llm)
/// print(result["answer"])
/// print(result["sources"])

use anyhow::{Result, Context};
use crate::web_search::{search_with_fallback};
use regex::Regex;
use std::collections::HashMap;
use std::collections::HashSet;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Autonomous research agent with optional LLM synthesis.
/// 
/// Workflow:
/// 1. Search Phase   — Find relevant URLs via search_with_fallback()
/// 2. Browse Phase   — Extract content from top URLs
/// 3. Synthesize     — LLM-powered answer (or snippet fallback)
/// 
/// ReACT variant (research_react):
/// Adds a Thought→Action→Observation loop for deeper research.
#[derive(Debug, Clone)]
pub struct ResearchAgent {
    pub llm_fn: String,
    pub max_sources: String,
    pub max_chars_per_source: String,
    pub search_provider: String,
}

impl ResearchAgent {
    /// Args:
    /// llm_fn:              Callable(prompt) -> str  (None = snippet fallback)
    /// max_sources:         How many URLs to browse
    /// max_chars_per_source: Max characters to keep per source
    /// search_provider:     Default provider for search_web()
    pub fn new(llm_fn: Option<Box<dyn Fn(serde_json::Value)>>, max_sources: i64, max_chars_per_source: i64, search_provider: String) -> Self {
        Self {
            llm_fn,
            max_sources,
            max_chars_per_source,
            search_provider,
        }
    }
    /// Find relevant URLs using fallback search.
    pub fn _search_phase(&self, query: String, max_results: i64) -> Vec<HashMap> {
        // Find relevant URLs using fallback search.
        logger.info(format!("[Research] Searching: {}", query));
        let mut results = search_with_fallback(query, /* max_results= */ max_results);
        logger.info(format!("[Research] Found {} results", results.len()));
        results
    }
    /// Extract content from a single URL.
    pub fn _browse_url(&mut self, url: String) -> HashMap {
        // Extract content from a single URL.
        logger.info(format!("[Research] Browsing: {}", url));
        let mut content = extract_web_content(url, /* max_chars= */ self.max_chars_per_source);
        content
    }
    /// Browse top search results and return sources with content.
    pub fn _browse_phase(&mut self, search_results: Vec<HashMap>) -> Vec<HashMap> {
        // Browse top search results and return sources with content.
        let mut sources = vec![];
        for result in search_results[..self.max_sources].iter() {
            let mut content = self._browse_url(result["url".to_string()]);
            if content.get(&"text".to_string()).cloned() {
                sources.push(HashMap::from([("url".to_string(), result["url".to_string()]), ("title".to_string(), (content.get(&"title".to_string()).cloned() || result.get(&"title".to_string()).cloned().unwrap_or(result["url".to_string()]))), ("text".to_string(), content["text".to_string()]), ("snippet".to_string(), result.get(&"snippet".to_string()).cloned().unwrap_or("".to_string()))]));
            }
        }
        sources
    }
    /// Build a compact context string from sources.
    pub fn _build_context(&self, sources: Vec<HashMap>, max_total_chars: i64) -> String {
        // Build a compact context string from sources.
        let mut parts = vec![];
        let mut chars_used = 0;
        for (i, src) in sources.iter().enumerate().iter() {
            let mut chunk = format!("[Source {}: {}]\n{}\n", i, src["title".to_string()], src["text".to_string()]);
            if (chars_used + chunk.len()) > max_total_chars {
                let mut remaining = (max_total_chars - chars_used);
                if remaining > 200 {
                    let mut chunk = format!("[Source {}: {}]\n{}…\n", i, src["title".to_string()], src["text".to_string()][..(remaining - 50)]);
                    parts.push(chunk);
                }
                break;
            }
            parts.push(chunk);
            chars_used += chunk.len();
        }
        parts.join(&"\n\n".to_string())
    }
    /// Generate an answer from collected sources.
    /// 
    /// Uses LLM if available, otherwise returns structured snippet fallback.
    pub fn _synthesize(&mut self, query: String, sources: Vec<HashMap>, llm_fn: Option<Box<dyn Fn(serde_json::Value)>>) -> Result<String> {
        // Generate an answer from collected sources.
        // 
        // Uses LLM if available, otherwise returns structured snippet fallback.
        if !sources {
            "I couldn't find relevant information to answer your question.".to_string()
        }
        let mut effective_llm = (llm_fn || self.llm_fn);
        if effective_llm {
            let mut context = self._build_context(sources);
            let mut prompt = format!("You are a research assistant. Answer the question using ONLY the sources below.\n\nQuestion: {}\n\nSources:\n{}\n\nInstructions:\n- Answer directly and concisely (3-5 sentences)\n- Cite sources as [Source 1], [Source 2], etc.\n- If sources don't answer the question, say so\n- Answer in the same language as the question\n\nAnswer:", query, context);
            // try:
            {
                let mut answer = effective_llm(prompt);
                if (answer && answer.trim().to_string().len() > 20) {
                    answer.trim().to_string()
                }
            }
            // except Exception as e:
        }
        let mut lines = vec![format!("Based on {} sources:\n", sources.len())];
        for (i, src) in sources.iter().enumerate().iter() {
            let mut snippet = (src.get(&"snippet".to_string()).cloned() || src["text".to_string()][..300]);
            lines.push(format!("**[{}] {}**", i, src["title".to_string()]));
            lines.push(snippet.trim().to_string());
            lines.push(format!("🔗 {}\n", src["url".to_string()]));
        }
        Ok(lines.join(&"\n".to_string()))
    }
    /// Perform complete research cycle (synchronous).
    /// 
    /// Args:
    /// query:       The research question
    /// max_sources: Override default max_sources
    /// llm_fn:      Override instance llm_fn
    /// 
    /// Returns:
    /// Dict with:
    /// answer:      Synthesized answer string
    /// sources:     List of {url, title}
    /// raw_content: Full extracted content list
    pub fn research(&mut self, query: String, max_sources: Option<i64>, llm_fn: Option<Box<dyn Fn(serde_json::Value)>>) -> HashMap {
        // Perform complete research cycle (synchronous).
        // 
        // Args:
        // query:       The research question
        // max_sources: Override default max_sources
        // llm_fn:      Override instance llm_fn
        // 
        // Returns:
        // Dict with:
        // answer:      Synthesized answer string
        // sources:     List of {url, title}
        // raw_content: Full extracted content list
        let mut n = (max_sources || self.max_sources);
        let mut search_results = self._search_phase(query, /* max_results= */ (n * 2));
        if !search_results {
            HashMap::from([("answer".to_string(), "I couldn't find any relevant information online.".to_string()), ("sources".to_string(), vec![]), ("raw_content".to_string(), vec![])])
        }
        let mut sources = self._browse_phase(search_results);
        let mut answer = self._synthesize(query, sources, /* llm_fn= */ llm_fn);
        HashMap::from([("answer".to_string(), answer), ("sources".to_string(), sources.iter().map(|s| HashMap::from([("url".to_string(), s["url".to_string()]), ("title".to_string(), s["title".to_string()])])).collect::<Vec<_>>()), ("raw_content".to_string(), sources)])
    }
    /// ReACT-style research loop: Thought → Action → Observation × N → Answer.
    /// 
    /// Each iteration refines the search query based on what was found.
    /// Requires an LLM; falls back to plain research() if none available.
    pub fn research_react(&mut self, query: String, llm_fn: Option<Box<dyn Fn(serde_json::Value)>>, max_iterations: i64) -> Result<HashMap> {
        // ReACT-style research loop: Thought → Action → Observation × N → Answer.
        // 
        // Each iteration refines the search query based on what was found.
        // Requires an LLM; falls back to plain research() if none available.
        let mut effective_llm = (llm_fn || self.llm_fn);
        if !effective_llm {
            logger.info("ReACT: no LLM available, falling back to plain research".to_string());
            self.research(query, /* llm_fn= */ llm_fn)
        }
        let mut all_sources = vec![];
        let mut current_query = query;
        let mut observations = vec![];
        for iteration in 1..(max_iterations + 1).iter() {
            logger.info(format!("[ReACT] Iteration {}/{}: {}", iteration, max_iterations, current_query));
            if (iteration > 1 && observations) {
                let mut thought_prompt = ((format!("Original question: {}\n\nPrevious searches and findings:\n", query) + observations.iter().map(|obs| format!("- {}", obs)).collect::<Vec<_>>().join(&"\n".to_string())) + "\n\nWhat should I search next to better answer the original question?\nWrite ONLY the new search query (1 line, no explanation):".to_string());
                // try:
                {
                    let mut new_query = effective_llm(thought_prompt).trim().to_string();
                    let mut new_query = regex::Regex::new(&"^[\"\\']|[\"\\']$".to_string()).unwrap().replace_all(&"".to_string(), new_query).to_string();
                    if (new_query && new_query.len() > 5) {
                        let mut current_query = new_query;
                        logger.info(format!("[ReACT] Refined query: {}", current_query));
                    }
                }
                // except Exception as e:
            }
            let mut search_results = self._search_phase(current_query, /* max_results= */ 4);
            let mut new_sources = self._browse_phase(search_results);
            let mut known_urls = all_sources.iter().map(|s| s["url".to_string()]).collect::<HashSet<_>>();
            for src in new_sources.iter() {
                if !known_urls.contains(&src["url".to_string()]) {
                    all_sources.push(src);
                    known_urls.insert(src["url".to_string()]);
                }
            }
            let mut obs = (format!("Searched '{}': found {} sources", current_query, new_sources.len()) + if new_sources { format!(" — {}", new_sources[..2].iter().map(|s| s["title".to_string()][..40]).collect::<Vec<_>>().join(&", ".to_string())) } else { "".to_string() });
            observations.push(obs);
            if all_sources.len() >= (self.max_sources * 2) {
                logger.info("[ReACT] Enough sources collected — stopping early".to_string());
                break;
            }
        }
        let mut answer = self._synthesize(query, all_sources[..(self.max_sources * 2)], /* llm_fn= */ effective_llm);
        Ok(HashMap::from([("answer".to_string(), answer), ("sources".to_string(), all_sources.iter().map(|s| HashMap::from([("url".to_string(), s["url".to_string()]), ("title".to_string(), s["title".to_string()])])).collect::<Vec<_>>()), ("raw_content".to_string(), all_sources), ("react_trace".to_string(), observations), ("iterations_used".to_string(), observations.len())]))
    }
    /// Async wrapper for Streamlit compatibility.
    pub async fn research_async(&mut self, query: String, max_sources: Option<i64>, llm_fn: Option<Box<dyn Fn(serde_json::Value)>>, use_react: bool) -> HashMap {
        // Async wrapper for Streamlit compatibility.
        let mut r#loop = asyncio.get_event_loop();
        if use_react {
            let mut r#fn = || self.research_react(query, /* llm_fn= */ llm_fn);
        } else {
            let mut r#fn = || self.research(query, /* max_sources= */ max_sources, /* llm_fn= */ llm_fn);
        }
        r#loop.run_in_executor(None, r#fn).await
    }
}

/// Extract content from a URL using content_extractor.
/// 
/// Returns:
/// Dict with keys: text, title, url
pub fn extract_web_content(url: String, max_chars: i64) -> Result<HashMap> {
    // Extract content from a URL using content_extractor.
    // 
    // Returns:
    // Dict with keys: text, title, url
    if !_EXTRACTOR_AVAILABLE {
        HashMap::from([("text".to_string(), "".to_string()), ("title".to_string(), "".to_string()), ("url".to_string(), url)])
    }
    // try:
    {
        let mut result = scan_web(url);
        let mut text = result.get(&"content".to_string()).cloned().unwrap_or("".to_string());
        if text.len() > max_chars {
            let mut text = (text[..max_chars] + "…".to_string());
        }
        HashMap::from([("text".to_string(), text), ("title".to_string(), result.get(&"title".to_string()).cloned().unwrap_or(url)), ("url".to_string(), url)])
    }
    // except Exception as e:
}

/// Quick research — returns just the answer string.
/// 
/// Example:
/// >>> answer = quick_research("What is FLARE retrieval?")
pub fn quick_research(query: String, max_sources: i64, llm_fn: Option<Box<dyn Fn(serde_json::Value)>>, use_react: bool) -> String {
    // Quick research — returns just the answer string.
    // 
    // Example:
    // >>> answer = quick_research("What is FLARE retrieval?")
    let mut agent = ResearchAgent(/* llm_fn= */ llm_fn, /* max_sources= */ max_sources);
    if (use_react && llm_fn) {
        let mut result = agent.research_react(query, /* llm_fn= */ llm_fn);
    } else {
        let mut result = agent.research(query, /* llm_fn= */ llm_fn);
    }
    result["answer".to_string()]
}
