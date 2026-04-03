use anyhow::{Result, Context};
use crate::email_ingestor::{EmailIngestor};
use crate::rag_pipeline::{LocalRAG};

/// TestEmailRAGE2E class.
#[derive(Debug, Clone)]
pub struct TestEmailRAGE2E {
}

impl TestEmailRAGE2E {
    /// Setup temporary RAG environment.
    pub fn rag_environment(&self, tmp_path: String) -> () {
        // Setup temporary RAG environment.
        let mut rag_dir = (tmp_path / "rag_db".to_string());
        rag_dir.create_dir_all();
        let mut rag = LocalRAG(/* cache_dir= */ rag_dir);
        /* yield (rag, tmp_path) */;
        rag.close();
    }
    /// Test email retrieval flow.
    pub fn test_email_retrieval_flow(&self, rag_environment: String) -> () {
        // Test email retrieval flow.
        let (mut rag, mut tmp_path) = rag_environment;
        let mut mbox_path = (tmp_path / "legacy_archive.mbox".to_string());
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
        let mut ingestor = EmailIngestor();
        let mut docs = ingestor.ingest(mbox_path.to_string());
        assert!(docs.len() == 2);
        rag.build_index(docs);
        let mut results = rag.search("When did Project Alpha start?".to_string(), /* k= */ 3);
        assert!(results.len() > 0);
        let mut top = results[0];
        assert!(top["text".to_string()].contains(&"1990".to_string()));
        assert!(top["metadata".to_string()]["date".to_string()].contains(&"1990".to_string()));
        let mut results = rag.search("Who warned about Y2K server melting?".to_string(), /* k= */ 3);
        assert!(results.len() > 0);
        let mut found = false;
        for res in results.iter() {
            if !res["metadata".to_string()]["sender".to_string()].contains(&"admin@zenacorp.com".to_string()) {
                continue;
            }
            let mut found = true;
            break;
        }
        assert!(found, "Did not find admin email in results: {}", results);
    }
}
