/// pdf_extractor::py - Extract text from PDF files for RAG indexing

use anyhow::{Result, Context};
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Extract text from PDF files.
#[derive(Debug, Clone)]
pub struct PDFExtractor {
}

impl PDFExtractor {
    /// Extract text from PDF file.
    /// 
    /// Args:
    /// pdf_path: Path to PDF file
    /// 
    /// Returns:
    /// Extracted text or None if failed
    pub fn extract_text(pdf_path: PathBuf) -> Result<Option<String>> {
        // Extract text from PDF file.
        // 
        // Args:
        // pdf_path: Path to PDF file
        // 
        // Returns:
        // Extracted text or None if failed
        // try:
        {
            let mut file = File::open(pdf_path)?;
            {
                let mut pdf_reader = PyPDF2.PdfReader(file);
                let mut text_parts = vec![];
                for (page_num, page) in pdf_reader.pages.iter().enumerate().iter() {
                    // try:
                    {
                        let mut text = page.extract_text();
                        if text {
                            text_parts.push(text);
                        }
                    }
                    // except Exception as e:
                }
                let mut full_text = text_parts.join(&"\n\n".to_string());
                if full_text {
                    logger.info(format!("[PDF] Extracted {} chars from {}", full_text.len(), pdf_path.file_name().unwrap_or_default().to_str().unwrap_or("")));
                    full_text
                } else {
                    logger.warning(format!("[PDF] No text extracted from {}", pdf_path.file_name().unwrap_or_default().to_str().unwrap_or("")));
                    None
                }
            }
        }
        // except Exception as e:
    }
    /// Check if file is a PDF.
    pub fn is_pdf(filename: String) -> bool {
        // Check if file is a PDF.
        filename.to_lowercase().ends_with(&*".pdf".to_string())
    }
}
