/// Core/streaming::py — Streaming answer generation utilities for ZEN_RAG.
/// 
/// Phase 2.3: Real-time streaming answers via Streamlit's st.write_stream().
/// 
/// Supports:
/// - Token-by-token streaming (for LLMs with streaming API)
/// - Chunk-by-chunk simulation (for LLMs without native streaming)
/// - Background hallucination checking after full answer is generated
/// 
/// Usage (in Streamlit):
/// from Core.streaming import stream_answer_to_streamlit
/// 
/// stream_answer_to_streamlit(
/// query="What is X?",
/// context_chunks=retrieved_chunks,
/// llm=my_llm,
/// rag=my_rag,
/// )

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::collections::HashSet;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub const RAG_ANSWER_PROMPT: &str = "You are a helpful assistant. Answer the question using ONLY the provided context.\\nBe concise and factual. If the answer is not in the context, say \"I don\\'t have enough information.\"\\n\\nContext:\\n{context}\\n\\nQuestion: {question}\\n\\nAnswer:";

/// Build numbered context string from retrieved chunks.
pub fn build_context_string(chunks: Vec<HashMap>, max_chars: i64) -> String {
    // Build numbered context string from retrieved chunks.
    let mut parts = vec![];
    let mut total = 0;
    for (i, chunk) in chunks.iter().enumerate().iter() {
        let mut text = chunk.get(&"text".to_string()).cloned().unwrap_or("".to_string());
        let mut source = (chunk.get(&"title".to_string()).cloned() || chunk.get(&"url".to_string()).cloned() || "".to_string());
        if source {
            let mut block = format!("[{}] ({})\n{}", i, source, text);
        } else {
            let mut block = format!("[{}] {}", i, text);
        }
        if (total + block.len()) > max_chars {
            break;
        }
        parts.push(block);
        total += block.len();
    }
    (parts.join(&"\n\n".to_string()) || "No context available.".to_string())
}

/// Simulate streaming by yielding characters with delay.
pub fn _char_stream(text: String, delay: f64) -> Generator</* unknown */> {
    // Simulate streaming by yielding characters with delay.
    for char in text.iter() {
        /* yield char */;
        if delay > 0 {
            std::thread::sleep(std::time::Duration::from_secs_f64(delay));
        }
    }
}

/// Simulate streaming by yielding words with delay.
pub fn _word_stream(text: String, delay: f64) -> Generator</* unknown */> {
    // Simulate streaming by yielding words with delay.
    let mut words = text.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>();
    for (i, word) in words.iter().enumerate().iter() {
        /* yield (word + if i < (words.len() - 1) { " ".to_string() } else { "".to_string() }) */;
        if delay > 0 {
            std::thread::sleep(std::time::Duration::from_secs_f64(delay));
        }
    }
}

/// Stream from Ollama adapter if available.
pub fn _ollama_stream(llm: Box<dyn std::any::Any>, prompt: String) -> Result<Generator</* unknown */>> {
    // Stream from Ollama adapter if available.
    // try:
    {
        // TODO: import ollama
        let mut model = (/* getattr */ None || /* getattr */ "llama3".to_string());
        let mut stream = ollama.chat(/* model= */ model, /* messages= */ vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), prompt)])], /* stream= */ true);
        for chunk in stream.iter() {
            let mut content = chunk.get(&"message".to_string()).cloned().unwrap_or(HashMap::new()).get(&"content".to_string()).cloned().unwrap_or("".to_string());
            if content {
                /* yield content */;
            }
        }
    }
    // except Exception as e:
}

/// Stream from llama-cpp-python if available.
pub fn _llama_cpp_stream(llm: Box<dyn std::any::Any>, prompt: String, max_tokens: i64) -> Result<Generator</* unknown */>> {
    // Stream from llama-cpp-python if available.
    // try:
    {
        let mut model = (/* getattr */ None || /* getattr */ None);
        if model.is_none() {
            return Err(anyhow::anyhow!("ValueError('No llama_cpp model found')"));
        }
        let mut output = model(prompt, /* max_tokens= */ max_tokens, /* stream= */ true, /* temperature= */ 0.1_f64);
        for token in output.iter() {
            let mut text = token.get(&"choices".to_string()).cloned().unwrap_or(vec![HashMap::new()])[0].get(&"text".to_string()).cloned().unwrap_or("".to_string());
            if text {
                /* yield text */;
            }
        }
    }
    // except Exception as e:
}

/// Get a streaming generator for an LLM response.
/// 
/// Tries native streaming adapters first, falls back to simulated word streaming.
pub fn get_answer_stream(llm: Box<dyn std::any::Any>, prompt: String, max_tokens: i64, fallback_delay: f64) -> Result<Generator</* unknown */>> {
    // Get a streaming generator for an LLM response.
    // 
    // Tries native streaming adapters first, falls back to simulated word streaming.
    // try:
    {
        let mut llm_type = r#type(llm).module_path!().to_lowercase();
        if llm_type.contains(&"ollama".to_string()) {
            /* yield from */ _ollama_stream(llm, prompt);
            return;
        }
    }
    // except Exception as exc:
    // try:
    {
        if (/* hasattr(llm, "_model".to_string()) */ true || /* hasattr(llm, "llm".to_string()) */ true) {
            /* yield from */ _llama_cpp_stream(llm, prompt, max_tokens);
            return;
        }
    }
    // except Exception as exc:
    // try:
    {
        if /* hasattr(llm, "query_sync".to_string()) */ true {
            let mut full_text = llm.query_sync(prompt, /* max_tokens= */ max_tokens);
        } else if /* hasattr(llm, "generate".to_string()) */ true {
            let mut full_text = llm.generate(prompt);
        } else if callable(llm) {
            let mut full_text = llm(prompt);
        } else {
            let mut full_text = "".to_string();
        }
        /* yield from */ _word_stream(full_text, /* delay= */ fallback_delay);
    }
    // except Exception as e:
}

/// Stream an LLM answer to the current Streamlit chat message container.
/// 
/// Args:
/// query: User query.
/// context_chunks: Retrieved chunks from RAG.
/// llm: LLM adapter.
/// rag: LocalRAG instance (used for hallucination check if available).
/// show_sources: Show source attribution after the answer.
/// check_hallucination_after: Run hallucination check in background after streaming.
/// 
/// Returns:
/// The complete generated answer text.
pub fn stream_answer_to_streamlit(query: String, context_chunks: Vec<HashMap>, llm: Box<dyn std::any::Any>, rag: Box<dyn std::any::Any>, show_sources: bool, check_hallucination_after: bool) -> Result<String> {
    // Stream an LLM answer to the current Streamlit chat message container.
    // 
    // Args:
    // query: User query.
    // context_chunks: Retrieved chunks from RAG.
    // llm: LLM adapter.
    // rag: LocalRAG instance (used for hallucination check if available).
    // show_sources: Show source attribution after the answer.
    // check_hallucination_after: Run hallucination check in background after streaming.
    // 
    // Returns:
    // The complete generated answer text.
    // try:
    {
        // TODO: import streamlit as st
    }
    // except ImportError as _e:
    let mut context_str = build_context_string(context_chunks);
    let mut prompt = format!(RAG_ANSWER_PROMPT, /* context= */ context_str, /* question= */ query);
    let mut full_answer = "".to_string();
    let _ctx = st.chat_message("assistant".to_string());
    {
        let mut placeholder = st.empty();
        let mut accumulated = "".to_string();
        // try:
        {
            for token in get_answer_stream(llm, prompt).iter() {
                accumulated += token;
                placeholder.markdown((accumulated + "▌".to_string()));
            }
            placeholder.markdown(accumulated);
            let mut full_answer = accumulated;
        }
        // except Exception as e:
        if (show_sources && context_chunks) {
            let _ctx = st.expander("Sources".to_string(), /* expanded= */ false);
            {
                let mut seen_sources = HashSet::new();
                for chunk in context_chunks.iter() {
                    let mut src = (chunk.get(&"title".to_string()).cloned() || chunk.get(&"url".to_string()).cloned() || "Unknown".to_string());
                    if !seen_sources.contains(&src) {
                        seen_sources.insert(src);
                        st.caption(format!("- {}", src));
                    }
                }
            }
        }
        if (check_hallucination_after && rag.is_some()) {
            // try:
            {
                // TODO: from Core.hallucination_detector_v2 import HallucinationDetector
                let mut detector = HallucinationDetector();
                let mut context_texts = context_chunks.iter().map(|c| c.get(&"text".to_string()).cloned().unwrap_or("".to_string())).collect::<Vec<_>>();
                let mut result = detector.check(full_answer, context_texts);
                if result.get(&"hallucination_detected".to_string()).cloned() {
                    st.warning("Potential hallucination detected. Please verify this answer.".to_string(), /* icon= */ "warning".to_string());
                    // try:
                    {
                        // TODO: from Core.metrics_tracker import MetricsTracker
                        MetricsTracker.get_instance().record_query(/* query= */ query, /* latency_s= */ 0.0_f64, /* hallucination_detected= */ true);
                    }
                    // except Exception as exc:
                }
            }
            // except Exception as e:
        }
    }
    Ok(full_answer)
}
