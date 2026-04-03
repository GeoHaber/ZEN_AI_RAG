use anyhow::{Result, Context};
use crate::config_system::{config};
use crate::email_ingestor::{EmailIngestor};
use crate::rag_pipeline::{LocalRAG};
use std::collections::HashMap;
use std::path::PathBuf;
use tokio;

/// Helper: setup phase for test_email_rag_flow.
pub fn _do_test_email_rag_flow_setup() -> () {
    // Helper: setup phase for test_email_rag_flow.
    println!("{}", "📧 Starting Email RAG Verification...".to_string());
    let mut tmp_dir = PathBuf::from("temp_email_test".to_string());
    if tmp_dir.exists() {
        std::fs::remove_dir_all(tmp_dir).ok();
    }
    tmp_dir.create_dir_all();
    let mut mbox_path = (tmp_dir / "legacy_archive.mbox".to_string());
    let mut rag_storage = (tmp_dir / "rag_db".to_string());
    (mbox_path, rag_storage, tmp_dir)
}

/// Test email rag flow.
pub async fn test_email_rag_flow() -> Result<()> {
    // Test email rag flow.
    let (mut mbox_path, mut rag_storage, mut tmp_dir) = _do_test_email_rag_flow_setup();
    // try:
    {
        println!("📦 Creating MBOX at {}...", mbox_path);
        let mut mbox = mailbox.mbox(mbox_path.to_string());
        let mut msg1 = EmailMessage();
        msg1["Subject".to_string()] = "Project Alpha Kickoff".to_string();
        msg1["From".to_string()] = "ceo@zenacorp.com".to_string();
        msg1["Date".to_string()] = "Mon, 1 Jan 1990 09:00:00 -0500".to_string();
        msg1.set_content("Welcome to Project Alpha. We start today, 1990.".to_string());
        mbox.insert(msg1);
        let mut msg2 = EmailMessage();
        msg2["Subject".to_string()] = "Urgent: Server Down".to_string();
        msg2["From".to_string()] = "admin@zenacorp.com".to_string();
        msg2["Date".to_string()] = "Fri, 31 Dec 1999 23:59:00 -0500".to_string();
        msg2.set_content("The server is melting! Y2K is coming!".to_string());
        mbox.insert(msg2);
        mbox.flush();
        mbox.close();
        println!("{}", "📥 Ingesting emails...".to_string());
        let mut ingestor = EmailIngestor();
        let mut docs = ingestor.ingest(mbox_path.to_string());
        println!("   found {} emails.", docs.len());
        println!("{}", "🧠 Indexing to RAG...".to_string());
        let mut rag = LocalRAG(/* cache_dir= */ rag_storage);
        rag.build_index(docs);
        println!("{}", "\n🔍 Query 1: 'When did Project Alpha start?'".to_string());
        let mut results = rag.search("When did Project Alpha start?".to_string());
        if results {
            let mut top = results[0];
            println!("   Answer Source: {}...", top["text".to_string()][..50]);
            println!("   Metadata Date: {}", top.get(&"metadata".to_string()).cloned().unwrap_or(HashMap::new()).get(&"date".to_string()).cloned());
            if (top["text".to_string()].contains(&"1990".to_string()) || top.get(&"metadata".to_string()).cloned().unwrap_or(HashMap::new()).get(&"date".to_string()).cloned().unwrap_or("".to_string()).contains(&"1990".to_string())) {
                println!("{}", "   ✅ SUCCESS: Retrieved 1990 date.".to_string());
            } else {
                println!("{}", "   ❌ FAILURE: Did not find 1990 context.".to_string());
            }
        } else {
            println!("{}", "   ❌ FAILURE: No results found.".to_string());
        }
        println!("{}", "\n🔍 Query 2: 'Who warned about Y2K?'".to_string());
        let mut results = rag.search("Who warned about Y2K server melting?".to_string());
        if results {
            let mut top = results[0];
            println!("   Answer Source: {}...", top["text".to_string()][..50]);
            println!("   Metadata Sender: {}", top.get(&"metadata".to_string()).cloned().unwrap_or(HashMap::new()).get(&"sender".to_string()).cloned());
            if top.to_string().contains(&"admin@zenacorp.com".to_string()) {
                println!("{}", "   ✅ SUCCESS: Retrieved correct sender.".to_string());
            } else {
                println!("{}", "   ❌ FAILURE: Wrong sender.".to_string());
            }
        } else {
            println!("{}", "   ❌ FAILURE: No results found.".to_string());
        }
    }
    // finally:
        if tmp_dir.exists() {
            // try:
            {
                if locals().contains(&"rag".to_string()) {
                    rag.close();
                }
                std::fs::remove_dir_all(tmp_dir).ok();
                println!("{}", "\n🧹 Cleanup complete.".to_string());
            }
            // except Exception as e:
        }
}
