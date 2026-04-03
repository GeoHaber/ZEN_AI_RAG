/// Run predefined medical prompts: RAG retrieval + optional Llama server (or Ollama)
/// for answers; write a simple report to medical_scenarios/report.txt.
/// Run from project root: python -m medical_scenarios.run_queries_report

use anyhow::{Result, Context};
use tokio;

pub const PROJECT_ROOT: &str = "Path(file!()).resolve().parent.parent";

pub const SCRIPT_DIR: &str = "Path(file!()).resolve().parent";

pub const REPORT_PATH: &str = "SCRIPT_DIR / 'report.txt";

pub static LLM_ENDPOINT: std::sync::LazyLock<String /* os::environ.get */> = std::sync::LazyLock::new(|| Default::default());

pub static LLM_PROVIDER: std::sync::LazyLock<String /* os::environ.get */> = std::sync::LazyLock::new(|| Default::default());

pub static LLM_MODEL: std::sync::LazyLock<String /* os::environ.get */> = std::sync::LazyLock::new(|| Default::default());

/// Return LocalRAG instance using project rag_storage.
pub fn get_rag() -> () {
    // Return LocalRAG instance using project rag_storage.
    // TODO: from zena_mode.rag_pipeline import LocalRAG
    let mut storage = (PROJECT_ROOT / "rag_storage".to_string());
    let mut rag = LocalRAG(/* cache_dir= */ storage);
    if !rag.chunks {
        rag._load_metadata();
    }
    rag
}

/// Call LLM with system context and user prompt. Returns answer or error message.
pub async fn call_llm(prompt: String, context: String, provider: String, model: String, endpoint: String) -> Result<String> {
    // Call LLM with system context and user prompt. Returns answer or error message.
    // try:
    {
        // TODO: from adapter_factory import create_adapter
        // TODO: from llm_adapters import LLMRequest
    }
    // except ImportError as e:
    // try:
    {
        let mut adapter = create_adapter(provider, /* endpoint= */ endpoint);
    }
    // except Exception as e:
    let mut system = format!("Answer based only on the following context.\n\nContext:\n{}", context[..4000]);
    let mut request = LLMRequest(/* provider= */ provider, /* model= */ model, /* prompt= */ prompt, /* system_prompt= */ system, /* temperature= */ 0.3_f64, /* max_tokens= */ 512, /* stream= */ true, /* endpoint= */ endpoint);
    // try:
    {
        let mut chunks = vec![];
        let mut gen = adapter.query(request);
        // async for
        while let Some(token) = gen.next().await {
            chunks.push(token);
        }
        (chunks.join(&"".to_string()).trim().to_string() || "(no output)".to_string())
    }
    // except Exception as e:
}

/// Run predefined prompts, optional LLM, build report_lines and write file.
pub fn run_queries_and_report() -> Result<()> {
    // Run predefined prompts, optional LLM, build report_lines and write file.
    // TODO: from medical_scenarios.prompts import MEDICAL_PROMPTS, PROMPT_IDS
    let mut report_lines = vec![];
    report_lines.push(("=".to_string() * 70));
    report_lines.push("  MEDICAL SCENARIOS — QUERY REPORT".to_string());
    report_lines.push(("=".to_string() * 70));
    report_lines.push("".to_string());
    // try:
    {
        let mut rag = get_rag();
    }
    // except Exception as e:
    let mut n_chunks = /* getattr */ vec![].len();
    report_lines.push(format!("Vector DB: {} chunks loaded.", n_chunks));
    report_lines.push(format!("LLM: {} @ {} (model: {})", LLM_PROVIDER, LLM_ENDPOINT, LLM_MODEL));
    report_lines.push("".to_string());
    let mut use_llm = ("1".to_string(), "true".to_string(), "yes".to_string()).contains(&std::env::var(&"MEDICAL_USE_LLM".to_string()).unwrap_or_default().cloned().unwrap_or("1".to_string()).trim().to_string().to_lowercase());
    for (i, (prompt_id, prompt)) in PROMPT_IDS.iter().zip(MEDICAL_PROMPTS.iter()).iter().enumerate().iter() {
        report_lines.push(("-".to_string() * 70));
        report_lines.push(format!("  [{}]", prompt_id));
        report_lines.push(format!("  Q: {}", prompt));
        // try:
        {
            let mut results = rag.hybrid_search(prompt, /* k= */ 3, /* alpha= */ 0.5_f64, /* rerank= */ true);
        }
        // except Exception as e:
        if !results {
            report_lines.push("  RAG: no results.".to_string());
            report_lines.push("".to_string());
            continue;
        }
        let mut context = results.iter().map(|r| r.get(&"text".to_string()).cloned().unwrap_or("".to_string())[..800]).collect::<Vec<_>>().join(&"\n\n".to_string());
        report_lines.push(format!("  RAG: {} chunk(s) retrieved.", results.len()));
        report_lines.push(format!("  Top source: {}", results[0].get(&"url".to_string()).cloned().unwrap_or(results[0].get(&"title".to_string()).cloned().unwrap_or("N/A".to_string()))));
        report_lines.push("".to_string());
        if use_llm {
            let mut answer = asyncio.run(call_llm(prompt, context, LLM_PROVIDER, LLM_MODEL, LLM_ENDPOINT));
            report_lines.push(format!("  A: {}{}", answer[..500], if answer.len() > 500 { "…".to_string() } else { "".to_string() }));
        } else {
            report_lines.push("  A: (LLM disabled; top chunk preview below)".to_string());
            report_lines.push(format!("  {}…", results[0].get(&"text".to_string()).cloned().unwrap_or("".to_string())[..400]));
        }
        report_lines.push("".to_string());
    }
    report_lines.push(("=".to_string() * 70));
    report_lines.push("  END REPORT".to_string());
    report_lines.push(("=".to_string() * 70));
    REPORT_PATHstd::fs::write(&report_lines.join(&"\n".to_string()), /* encoding= */ "utf-8".to_string());
    Ok(println!("Report written: {}", REPORT_PATH))
}
