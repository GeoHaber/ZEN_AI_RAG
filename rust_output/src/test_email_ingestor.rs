use anyhow::{Result, Context};
use crate::email_ingestor::{EmailIngestor};

/// TestEmailIngestor class.
#[derive(Debug, Clone)]
pub struct TestEmailIngestor {
}

impl TestEmailIngestor {
    /// Create a dummy MBOX file
    pub fn mbox_file(&self, tmp_path: String) -> () {
        // Create a dummy MBOX file
        let mut mbox_path = (tmp_path / "test_archive.mbox".to_string());
        let mut mbox = mailbox.mbox(mbox_path.to_string());
        let mut msg1 = EmailMessage();
        msg1["Subject".to_string()] = "Meeting Update".to_string();
        msg1["From".to_string()] = "boss@company.com".to_string();
        msg1["To".to_string()] = "me@company.com".to_string();
        msg1["Date".to_string()] = "Fri, 21 Nov 1997 09:55:06 -0600".to_string();
        msg1.set_content("The meeting is moved to Monday.".to_string());
        mbox.insert(msg1);
        let mut msg2 = EmailMessage();
        msg2["Subject".to_string()] = "Project Launch".to_string();
        msg2["From".to_string()] = "marketing@company.com".to_string();
        msg2["Date".to_string()] = "Tue, 1 Jan 2000 12:00:00 +0000".to_string();
        msg2.set_content("Launch is successful!".to_string());
        mbox.insert(msg2);
        mbox.flush();
        mbox.close();
        mbox_path
    }
    /// Test mbox ingestion.
    pub fn test_mbox_ingestion(&self, mbox_file: String) -> () {
        // Test mbox ingestion.
        let mut ingestor = EmailIngestor();
        let mut docs = ingestor.ingest(mbox_file.to_string());
        assert!(docs.len() == 2);
        let mut doc1 = next(docs.iter().filter(|d| d["title".to_string()].contains(&"Meeting Update".to_string())).map(|d| d).collect::<Vec<_>>());
        assert!(doc1["metadata".to_string()]["date".to_string()].contains(&"1997".to_string()));
        assert!(doc1["metadata".to_string()]["sender".to_string()].contains(&"boss@company.com".to_string()));
        assert!(doc1["title".to_string()].contains(&"Meeting Update".to_string()));
        assert!(doc1["content".to_string()].contains(&"The meeting is moved to Monday".to_string()));
        let mut doc2 = next(docs.iter().filter(|d| d["title".to_string()].contains(&"Project Launch".to_string())).map(|d| d).collect::<Vec<_>>());
        assert!(doc2["metadata".to_string()]["date".to_string()].contains(&"2000".to_string()));
    }
    /// Test unsupported format.
    pub fn test_unsupported_format(&self, tmp_path: String) -> () {
        // Test unsupported format.
        let mut ingestor = EmailIngestor();
        let mut bad_file = (tmp_path / "archive.xyz".to_string());
        bad_file.touch();
        let mut docs = ingestor.ingest(bad_file.to_string());
        assert!(docs.len() == 0);
    }
}
