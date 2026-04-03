use anyhow::{Result, Context};
use crate::config_system::{config};
use crate::utils::{safe_print};
use crate::voice_service::*;
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use tokio;

/// Handles WebSocket connections for real-time voice streaming.
/// Manages client sessions and audio processing.
#[derive(Debug, Clone)]
pub struct VoiceStreamHandler {
    pub clients: HashMap<object, object>,
}

impl VoiceStreamHandler {
    pub fn new() -> Self {
        Self {
            clients: HashMap::new(),
        }
    }
    /// Main WebSocket handler.
    pub async fn handle_client(&mut self, websocket: String) -> Result<()> {
        // Main WebSocket handler.
        file_log(("=".to_string() * 50));
        file_log(format!("⚡ VOICE CLIENT CONNECTED: {}", /* getattr */ "Unknown".to_string()));
        file_log(("=".to_string() * 50));
        let mut processor = None;
        let mut client_id = (&websocket as *const _ as usize);
        file_log(format!("[Voice] Client connected: {}", client_id));
        // try:
        {
            file_log("Initializing StreamProcessor...".to_string());
            let mut service = get_voice_service(config::MODEL_DIR);
            let mut processor = service.create_stream_processor();
            self.clients[websocket] = processor;
            file_log("StreamProcessor ready.".to_string());
            websocket.send(serde_json::to_string(&HashMap::from([("status".to_string(), "ready".to_string()), ("msg".to_string(), "Stream Processor Initialized".to_string())])).unwrap()).await;
            file_log("Entering message loop...".to_string());
            // async for
            while let Some(message) = websocket.next().await {
                if /* /* isinstance(message, str) */ */ true {
                    self._handle_text_message(websocket, processor, message).await;
                } else if /* /* isinstance(message, bytes) */ */ true {
                    file_log(format!("Received audio chunk: {} bytes", message.len()));
                    self._handle_audio_chunk(websocket, processor, message).await;
                }
            }
        }
        // except Exception as e:
        // finally:
            Ok(self._cleanup(websocket))
    }
    /// Handle control messages.
    pub async fn _handle_text_message(&self, websocket: String, processor: String, message: String) -> Result<()> {
        // Handle control messages.
        // try:
        {
            let mut data = serde_json::from_str(&message).unwrap();
        }
        // except json::JSONDecodeError as _e:
        let mut cmd = data.get(&"command".to_string()).cloned();
        if cmd == "client_info".to_string() {
            file_log(format!("CLIENT INFO: {}", data));
        }
        if cmd == "stop".to_string() {
            file_log("Stop command received.".to_string());
            let mut result = processor.finish();
            let mut final_text = if result { result["text".to_string()] } else { "".to_string() };
            file_log(format!("Final Result: {}", final_text));
            websocket.send(serde_json::to_string(&HashMap::from([("type".to_string(), "transcription".to_string()), ("text".to_string(), final_text), ("is_final".to_string(), true)])).unwrap()).await;
        } else if cmd == "clear".to_string() {
            processor.finish();
            websocket.send(serde_json::to_string(&HashMap::from([("status".to_string(), "cleared".to_string())])).unwrap()).await;
        }
    }
    /// Process binary audio chunk.
    pub async fn _handle_audio_chunk(&self, websocket: String, processor: String, chunk: Vec<u8>) -> () {
        // Process binary audio chunk.
        if !chunk {
            return;
        }
        processor.add_audio(chunk);
        let mut result = processor.process();
        if result {
            file_log(format!("Partial Result: {}", result));
            let mut payload = serde_json::to_string(&HashMap::from([("type".to_string(), "transcription".to_string()), ("text".to_string(), result["text".to_string()]), ("is_final".to_string(), result["is_final".to_string()])])).unwrap();
            file_log(format!(">>> SENDING PAYLOAD ({} bytes)...", payload.len()));
            websocket.send(payload).await;
            file_log("<<< PAYLOAD SENT.".to_string());
        }
    }
    pub fn _cleanup(&self, websocket: String) -> () {
        if self.clients.contains(&websocket) {
            drop(self.clients[websocket]);
        }
        file_log(format!("[Voice] Client disconnected: {}", (&websocket as *const _ as usize)));
    }
}

/// Guaranteed logging to file.
pub fn file_log(msg: String) -> Result<()> {
    // Guaranteed logging to file.
    // try:
    {
        let mut f = File::create("voice_trace.txt".to_string())?;
        {
            f.write(format!("{}\n", msg));
        }
    }
    // except Exception as _e:
    Ok(safe_print(msg))
}
