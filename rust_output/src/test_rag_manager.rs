use anyhow::{Result, Context};
use crate::rag_manager::{RAGManager};

/// Test update and read consistency.
pub fn test_update_and_read_consistency() -> () {
    // Test update and read consistency.
    let mut mgr = RAGManager();
    let writer = |i| {
        let mut docs = 0..5.iter().map(|j| format!("doc-{}-{}", i, j)).collect::<Vec<_>>();
        let mut paths = 0..5.iter().map(|j| format!("path-{}-{}", i, j)).collect::<Vec<_>>();
        mgr.update_documents(docs, paths);
    };
    let reader = || {
        // Reader.
        let mut d = mgr.documents;
        let mut p = mgr.file_paths;
        assert!(d.len() == p.len());
    };
    let mut ex = concurrent.futures.ThreadPoolExecutor(/* max_workers= */ 8);
    {
        let mut writers = 0..20.iter().map(|i| ex.submit(writer, i)).collect::<Vec<_>>();
        let mut readers = 0..50.iter().map(|_| ex.submit(reader)).collect::<Vec<_>>();
        for f in (writers + readers).iter() {
            f.result();
        }
    }
}

/// Test clear documents.
pub fn test_clear_documents() -> () {
    // Test clear documents.
    let mut mgr = RAGManager();
    mgr.update_documents(vec!["a".to_string(), "b".to_string()], vec!["p1".to_string(), "p2".to_string()]);
    mgr.clear_documents();
    assert!(mgr.documents == vec![]);
    assert!(mgr.file_paths == vec![]);
}
