use anyhow::{Result, Context};
use crate::utils::{parsedate_to_datetime};
use std::collections::HashMap;
use std::collections::HashSet;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Ingests email archives (MBOX, PST) and converts them to RAG-ready documents.
#[derive(Debug, Clone)]
pub struct EmailIngestor {
    pub supported_formats: HashSet<serde_json::Value>,
}

impl EmailIngestor {
    pub fn new() -> Self {
        Self {
            supported_formats: HashSet::from([".mbox".to_string(), ".pst".to_string(), ".ost".to_string()]),
        }
    }
    /// Auto-detect format and ingest email file.
    /// Returns list of documents compatible with RAG pipeline.
    pub fn ingest(&mut self, file_path: String) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
        // Auto-detect format and ingest email file.
        // Returns list of documents compatible with RAG pipeline.
        let mut path = PathBuf::from(file_path);
        if !path.exists() {
            logger.error(format!("[Email] File not found: {}", file_path));
            vec![]
        }
        let mut ext = path.extension().unwrap_or_default().to_str().unwrap_or("").to_lowercase();
        if ext == ".mbox".to_string() {
            self.scan_mbox(path)
        } else if vec![".pst".to_string(), ".ost".to_string()].contains(&ext) {
            self.scan_pst(path)
        } else {
            logger.error(format!("[Email] Unsupported format: {}", ext));
            vec![]
        }
    }
    /// Parse MBOX files (Thunderbird, etc)
    pub fn scan_mbox(&mut self, path: PathBuf) -> Result<Vec<HashMap<String, Box<dyn std::any::Any>>>> {
        // Parse MBOX files (Thunderbird, etc)
        logger.info(format!("[Email] Scanning MBOX: {}", path));
        let mut documents = vec![];
        // try:
        {
            let mut mbox = mailbox.mbox(path.to_string());
            for (i, message) in mbox.iter().enumerate().iter() {
                // try:
                {
                    let mut doc = self._process_message(message, /* source= */ format!("mbox::{}::{}", path.file_name().unwrap_or_default().to_str().unwrap_or(""), i));
                    if doc {
                        documents.push(doc);
                    }
                }
                // except Exception as e:
            }
            logger.info(format!("[Email] Extracted {} emails from MBOX", documents.len()));
        }
        // except Exception as e:
        Ok(documents)
    }
    /// Parse PST/OST files using best available method
    pub fn scan_pst(&self, path: PathBuf) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
        // Parse PST/OST files using best available method
        logger.info(format!("[Email] Scanning PST: {}", path));
        if LIBRATOM_AVAILABLE {
            self._scan_pst_libratom(path)
        }
        if WIN32_AVAILABLE {
            self._scan_pst_win32(path)
        }
        logger.warning("[Email] partial PST support: Install 'libratom' or use on Windows with Outlook.".to_string());
        vec![]
    }
    /// Use local Outlook to read PST (Windows only)
    pub fn _scan_pst_win32(&mut self, path: PathBuf) -> Result<Vec<HashMap<String, Box<dyn std::any::Any>>>> {
        // Use local Outlook to read PST (Windows only)
        let mut documents = vec![];
        // try:
        {
            let mut outlook = win32com.client.Dis/* mock::patch("Outlook.Application".to_string() */).GetNamespace("MAPI".to_string());
            // try:
            {
                outlook.AddStore(path.to_string());
            }
            // except Exception as e:
            let mut pst_store = None;
            for store in outlook.Stores.iter() {
                if !store.FilePath.to_string().contains(&path.to_string()) {
                    continue;
                }
                let mut pst_store = store;
                break;
            }
            if !pst_store {
                logger.error("[Email] Could not load PST in Outlook".to_string());
                vec![]
            }
            let mut root = pst_store.GetRootFolder();
            documents.extend(self._walk_outlook_folders(root, /* source_file= */ path.file_name().unwrap_or_default().to_str().unwrap_or("")));
        }
        // except Exception as e:
        Ok(documents)
    }
    /// Walk outlook folders.
    pub fn _walk_outlook_folders(&mut self, folder: String, source_file: String) -> Result<Vec<HashMap>> {
        // Walk outlook folders.
        let mut docs = vec![];
        // try:
        {
            for item in folder.Items.iter() {
                // try:
                {
                    if /* getattr */ 0 == 43 {
                        let mut sender = /* getattr */ "Unknown".to_string();
                        let mut subject = /* getattr */ "No Subject".to_string();
                        let mut body = /* getattr */ "".to_string();
                        let mut received_time = /* getattr */ datetime::now();
                        if /* hasattr(received_time, "strftime".to_string()) */ true {
                            let mut date_str = received_time.strftime("%Y-%m-%d %H:%M:%S".to_string());
                        } else {
                            let mut date_str = received_time.to_string();
                        }
                        let mut content = format!("Date: {}\nFrom: {}\nSubject: {}\n\n{}", date_str, sender, subject, body);
                        docs.push(HashMap::from([("content".to_string(), content), ("title".to_string(), format!("Email: {}", subject)), ("url".to_string(), format!("pst://{}/{}", source_file, /* getattr */ "unknown".to_string())), ("metadata".to_string(), HashMap::from([("date".to_string(), date_str), ("sender".to_string(), sender), ("type".to_string(), "email".to_string())]))]));
                    }
                }
                // except Exception as _e:
            }
            for sub in folder.Folders.iter() {
                docs.extend(self._walk_outlook_folders(sub, source_file));
            }
        }
        // except Exception as e:
        Ok(docs)
    }
    /// Use libratom for standalone PST parsing
    pub fn _scan_pst_libratom(&self, path: PathBuf) -> Result<Vec<HashMap<String, Box<dyn std::any::Any>>>> {
        // Use libratom for standalone PST parsing
        let mut documents = vec![];
        // try:
        {
            let mut archive = PffArchive(path.to_string());
            for folder in archive.folders().iter() {
                if folder.name == "Top of Personal Folders".to_string() {
                    continue;
                }
                for message in folder.sub_messages.iter() {
                    // try:
                    {
                        let mut sender = message.get_transport_headers().get(&"From".to_string()).cloned().unwrap_or("Unknown".to_string());
                        let mut subject = message.subject;
                        let mut body = message.get_plain_text_body();
                        let mut date = message.client_submit_time;
                        let mut content = format!("Date: {}\nFrom: {}\nSubject: {}\n\n{}", date, sender, subject, body);
                        documents.push(HashMap::from([("content".to_string(), content), ("title".to_string(), format!("Email: {}", subject)), ("url".to_string(), format!("pst://{}/{}", path.file_name().unwrap_or_default().to_str().unwrap_or(""), message.identifier)), ("metadata".to_string(), HashMap::from([("date".to_string(), date.to_string()), ("sender".to_string(), sender), ("type".to_string(), "email".to_string())]))]));
                    }
                    // except Exception as _e:
                }
            }
        }
        // except Exception as e:
        Ok(documents)
    }
    /// Normalize Python email.message.Message to RAG Doc
    pub fn _process_message(&self, message: String, source: String) -> Result<Option<HashMap<String, Box<dyn std::any::Any>>>> {
        // Normalize Python email.message.Message to RAG Doc
        // try:
        {
            let mut subject = (message["subject".to_string()] || "No Subject".to_string());
            let mut sender = (message["from".to_string()] || "Unknown Sender".to_string());
            let mut date_header = message["date".to_string()];
            let mut date_str = "Unknown Date".to_string();
            if date_header {
                // try:
                {
                    let mut dt = parsedate_to_datetime(date_header);
                    let mut date_str = dt.strftime("%Y-%m-%d %H:%M:%S".to_string());
                }
                // except Exception as _e:
            }
            let mut body = "".to_string();
            if message.is_multipart() {
                for part in message.walk().iter() {
                    let mut content_type = part.get_content_type();
                    let mut content_disposition = part.get(&"Content-Disposition".to_string()).cloned().to_string();
                    if (content_type == "text/plain".to_string() && !content_disposition.contains(&"attachment".to_string())) {
                        let mut payload = part.get_payload(/* decode= */ true);
                        if payload {
                            body += payload.decode(/* errors= */ "replace".to_string());
                        }
                    }
                }
            } else {
                let mut payload = message.get_payload(/* decode= */ true);
                if payload {
                    let mut body = payload.decode(/* errors= */ "replace".to_string());
                }
            }
            let mut full_text = format!("Date: {}\nFrom: {}\nSubject: {}\n\n{}", date_str, sender, subject, body);
            HashMap::from([("content".to_string(), full_text), ("title".to_string(), format!("Email: {}", subject)), ("url".to_string(), source), ("metadata".to_string(), HashMap::from([("date".to_string(), date_str), ("sender".to_string(), sender), ("year".to_string(), if date_str[..4].chars().all(|c| c.is_ascii_digit()) { date_str[..4].to_string().parse::<i64>().unwrap_or(0) } else { 0 }), ("type".to_string(), "email".to_string())]))])
        }
        // except Exception as e:
    }
}
