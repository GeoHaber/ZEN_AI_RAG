use anyhow::{Result, Context};
use crate::rag_pipeline::{LocalRAG};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static DOCS_TO_INDEX: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub static _HELP_RAG: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

/// Lazy singleton for Help System RAG.
pub fn get_help_rag() -> Result<()> {
    // Lazy singleton for Help System RAG.
    // global/nonlocal _help_rag
    if _help_rag.is_none() {
        // try:
        {
            // TODO: from config_system import config
            let mut rag_cache = (config::BASE_DIR / "rag_cache".to_string());
            let mut _help_rag = LocalRAG(/* cache_dir= */ rag_cache);
        }
        // except Exception as e:
    }
    Ok(_help_rag)
}

/// Helper: setup phase for index_internal_docs.
pub fn _do_index_internal_docs_setup(rag: String, root_dir: String) -> Result<()> {
    // Helper: setup phase for index_internal_docs.
    let mut rag = (rag || get_help_rag());
    if !rag {
        logger.warning("[HelpSystem] RAG unavailable, skipping indexing.".to_string());
        return;
    }
    logger.info("📚 Indexing internal documentation for Interactive Help...".to_string());
    let mut docs_payload = vec![];
    let mut search_paths = vec![root_dir, (root_dir / "_docs".to_string()), (root_dir / "_Extra_files".to_string())];
    for doc_name in DOCS_TO_INDEX.iter() {
        let mut content = None;
        let mut found_path = None;
        for p in search_paths.iter() {
            let mut candidate = (p / doc_name);
            if candidate.exists() {
                let mut found_path = candidate;
                break;
            }
        }
        if found_path {
            // try:
            {
                let mut f = File::open(found_path)?;
                {
                    let mut content = f.read();
                }
                docs_payload.push(HashMap::from([("title".to_string(), format!("System Doc: {}", doc_name)), ("url".to_string(), found_path.to_string()), ("content".to_string(), content)]));
                logger.info(format!("  [+] Found: {}", doc_name));
            }
            // except Exception as e:
        }
    }
    Ok((docs_payload, f, rag))
}

/// Scans and indexes project documentation into the RAG system.
pub fn index_internal_docs(root_dir: PathBuf, rag: Option<LocalRAG>) -> Result<()> {
    // Scans and indexes project documentation into the RAG system.
    let (mut docs_payload, mut f, mut rag) = _do_index_internal_docs_setup(rag, root_dir);
    let mut zena_mode_dir = (root_dir / "zena_mode".to_string());
    if zena_mode_dir.exists() {
        logger.info("🔍 Indexing code docstrings in 'zena_mode'...".to_string());
        for py_file in zena_mode_dir.glob("*.py".to_string()).iter() {
            // try:
            {
                if py_file.name == "help_system::py".to_string() {
                    continue;
                }
                let mut f = File::open(py_file)?;
                {
                    let mut node = ast.parse(f.read());
                }
                let mut file_doc = ast.get_docstring(node);
                if file_doc {
                    docs_payload.push(HashMap::from([("title".to_string(), format!("Code Logic: {} (Overview)", py_file.name)), ("url".to_string(), py_file.to_string()), ("content".to_string(), file_doc)]));
                }
                for item in node.body.iter() {
                    if !/* /* isinstance(item, (ast.ClassDef, ast.FunctionDef) */) */ true {
                        continue;
                    }
                    let mut item_doc = ast.get_docstring(item);
                    if item_doc {
                        docs_payload.push(HashMap::from([("title".to_string(), format!("Logic: {} -> {}", py_file.name, item.name)), ("url".to_string(), py_file.to_string()), ("content".to_string(), item_doc)]));
                    }
                }
            }
            // except Exception as e:
        }
    }
    if docs_payload {
        rag.build_index(docs_payload);
        logger.info(format!("✅ Indexed {} documentation/code sources.", docs_payload.len()));
    } else {
        logger.warning("⚠️ No documentation files found to index.".to_string());
    }
}
