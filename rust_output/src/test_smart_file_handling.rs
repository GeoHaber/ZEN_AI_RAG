use anyhow::{Result, Context};
use crate::utils::{format_message_with_attachment};
use std::fs::File;
use std::io::{self, Read, Write};

/// TestSmartFileHandling class.
#[derive(Debug, Clone)]
pub struct TestSmartFileHandling {
}

impl TestSmartFileHandling {
    /// Python files should trigger a code review/analysis prompt.
    pub fn test_python_file_trigger(&mut self) -> () {
        // Python files should trigger a code review/analysis prompt.
        let mut query = "What does this do?".to_string();
        let mut filename = "script.py".to_string();
        let mut content = "print('hello')".to_string();
        let mut result = format_message_with_attachment(query, filename, content);
        assert!(result.contains("Please analyze and review".to_string()));
        assert!(result.contains("```python".to_string()));
        assert!(result.contains(content));
    }
    /// Text files should be treated as context.
    pub fn test_text_file_trigger(&mut self) -> () {
        // Text files should be treated as context.
        let mut query = "Summarize this.".to_string();
        let mut filename = "notes.txt".to_string();
        let mut content = "Meeting notes...".to_string();
        let mut result = format_message_with_attachment(query, filename, content);
        assert!(result.contains("for context".to_string()));
        self.assertNotIn("analyze and review".to_string(), result);
        assert!(result.contains(content));
    }
}
