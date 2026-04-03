use anyhow::{Result, Context};
use std::collections::HashMap;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Generates a raw PCM 16-bit mono audio buffer (Sine Wave at 440Hz).
pub async fn generate_sine_wave(duration_sec: String, frequency: String, sample_rate: String) -> () {
    // Generates a raw PCM 16-bit mono audio buffer (Sine Wave at 440Hz).
    let mut num_samples = (duration_sec * sample_rate).to_string().parse::<i64>().unwrap_or(0);
    let mut audio_data = bytearray();
    for i in 0..num_samples.iter() {
        let mut sample = (32767 * math::sin(((((2 * math::pi) * frequency) * i) / sample_rate)));
        audio_data.extend(r#struct::pack("<h".to_string(), sample.to_string().parse::<i64>().unwrap_or(0)));
    }
    bytes(audio_data)
}

/// Test backend direct.
pub async fn test_backend_direct() -> Result<()> {
    // Test backend direct.
    let mut uri = "ws://127.0.0.1:8005".to_string();
    logger.info(format!("Connecting to Voice Server at {}...", uri));
    // try:
    {
        let mut websocket = websockets.connect(uri);
        {
            logger.info("✅ Connected to WebSocket.".to_string());
            // try:
            {
                let mut msg = asyncio.wait_for(websocket.recv(), /* timeout= */ 2.0_f64).await;
                logger.info(format!("Server Greeting: {}", msg));
            }
            // except asyncio.TimeoutError as _e:
            logger.info("Generating 3 seconds of synthetic audio (440Hz Sine)...".to_string());
            let mut chunk_size = 4096;
            let mut audio_bytes = generate_sine_wave().await;
            let mut total_chunks = (audio_bytes.len() / chunk_size);
            logger.info(format!("Streaming {} bytes in {} chunks...", audio_bytes.len(), total_chunks));
            for i in (0..audio_bytes.len()).step_by(chunk_size as usize).iter() {
                let mut chunk = audio_bytes[i..(i + chunk_size)];
                websocket.send(chunk).await;
                asyncio.sleep(0.01_f64).await;
            }
            logger.info("Stream complete. Sending STOP command...".to_string());
            websocket.send(serde_json::to_string(&HashMap::from([("command".to_string(), "stop".to_string())])).unwrap()).await;
            let mut start_wait = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            while (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_wait) < 10 {
                // try:
                {
                    let mut response = websocket.recv().await;
                    let mut data = serde_json::from_str(&response).unwrap();
                    logger.info(format!("Received: {}", data));
                    if (data.get(&"is_final".to_string()).cloned() || data.get(&"type".to_string()).cloned() == "transcription".to_string()) {
                        logger.info("✅ Backend responded with transcription packet!".to_string());
                        true
                    }
                }
                // except websockets.exceptions::ConnectionClosed as _e:
                // except Exception as e:
            }
            logger.error("❌ Timed out waiting for transcription response.".to_string());
            false
        }
    }
    // except Exception as e:
}
