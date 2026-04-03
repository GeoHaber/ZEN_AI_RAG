/// Index medical scenario documents into the RAG vector database, verify success,
/// and expose one vector DB entry as an example (structure + sample content).
/// Run from project root: python -m medical_scenarios.index_and_verify

use anyhow::{Result, Context};
use std::collections::HashMap;

pub const PROJECT_ROOT: &str = "Path(file!()).resolve().parent.parent";

pub const SCRIPT_DIR: &str = "Path(file!()).resolve().parent";

pub const DATA_DIR: &str = "SCRIPT_DIR / 'data";

/// Load generated scenario files into document list for RAG.
pub fn load_scenario_documents() -> () {
    // Load generated scenario files into document list for RAG.
    let mut documents = vec![];
    if !DATA_DIR.exists() {
        println!("Error: {} not found. Run generate_scenarios::py first.", DATA_DIR);
        documents
    }
    for f in { let mut v = DATA_DIR.glob("*.txt".to_string()).clone(); v.sort(); v }.iter() {
        let mut text = f.read_to_string()).trim().to_string();
        if !text {
            continue;
        }
        let mut title = if text.contains(&"\n".to_string()) { text.split("\n".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[0][..80] } else { text[..80] };
        documents.push(HashMap::from([("content".to_string(), text), ("url".to_string(), format!("medical_scenarios/data/{}", f.name)), ("title".to_string(), title)]));
    }
    documents
}

/// Index documents with LocalRAG, verify count, print one entry structure.
pub fn index_and_verify() -> Result<()> {
    // Index documents with LocalRAG, verify count, print one entry structure.
    let mut documents = load_scenario_documents();
    if !documents {
        println!("{}", "No documents to index.".to_string());
        false
    }
    println!("Loaded {} scenario documents.", documents.len());
    let mut storage = (PROJECT_ROOT / "rag_storage".to_string());
    println!("Vector DB path: {}", storage);
    // try:
    {
        // TODO: from zena_mode.rag_pipeline import LocalRAG
    }
    // except ImportError as _e:
    let mut rag = LocalRAG(/* cache_dir= */ storage);
    rag.warmup();
    rag.build_index(documents, /* dedup_threshold= */ 0.9_f64, /* filter_junk= */ true);
    let mut n_chunks = rag.chunks.len();
    println!("\nIndexing result: {} chunks in vector DB.", n_chunks);
    if n_chunks == 0 {
        println!("{}", "WARNING: No chunks were added. Check chunker/filter or document content.".to_string());
        false
    }
    println!("{}", "Indexing verified: chunks added successfully.".to_string());
    println!("{}", ("\n".to_string() + ("=".to_string() * 60)));
    println!("{}", "  ONE VECTOR DB ENTRY (structure example)".to_string());
    println!("{}", "  (from LocalRAG in-memory chunk mirror; Qdrant payload is similar)".to_string());
    println!("{}", ("=".to_string() * 60));
    let mut example = rag.chunks[0];
    for key in { let mut v = example.keys().clone(); v.sort(); v }.iter() {
        let mut val = example[&key];
        if key == "text".to_string() {
            let mut preview = if val.len() > 200 { (val[..200] + "…".to_string()) } else { val };
            let mut preview = preview.replace(&*"\n".to_string(), &*" ".to_string());
            println!("  {}: {}", key, preview);
        } else {
            println!("  {}: {}", key, val);
            // pass
        }
    }
    println!("{}", ("=".to_string() * 60));
    // try:
    {
        rag.close();
    }
    // except Exception as exc:
    Ok(true)
}
