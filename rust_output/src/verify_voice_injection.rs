use anyhow::{Result, Context};
use std::collections::HashMap;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Generates synthetic Raw PCM 16-bit Mono Audio (Sine Wave).
pub async fn generate_sine_wave_pcm(duration_sec: String, frequency: String, sample_rate: String) -> () {
    // Generates synthetic Raw PCM 16-bit Mono Audio (Sine Wave).
    let mut num_samples = (duration_sec * sample_rate).to_string().parse::<i64>().unwrap_or(0);
    let mut audio_data = bytearray();
    for i in 0..num_samples.iter() {
        let mut sample = (32767 * math::sin(((((2 * math::pi) * frequency) * i) / sample_rate)));
        audio_data.extend(r#struct::pack("<h".to_string(), sample.to_string().parse::<i64>().unwrap_or(0)));
    }
    bytes(audio_data)
}

/// Inject voice.
pub async fn inject_voice() -> Result<()> {
    // Inject voice.
    let mut uri = "ws://127.0.0.1:8005".to_string();
    logger.info(format!("💉 Voice Injection Test Target: {}", uri));
    // try:
    {
        let mut websocket = websockets.connect(uri);
        {
            logger.info("✅ Connection Established (Port 8005 OPEN)".to_string());
            websocket.send(serde_json::to_string(&HashMap::from([("command".to_string(), "client_info".to_string()), ("device".to_string(), "SYNTHETIC_INJECTOR".to_string()), ("input_rate".to_string(), 16000)])).unwrap()).await;
            logger.info("🔊 Generating 3s Synthetic Audio (Sine Wave)...".to_string());
            let mut pcm_data = generate_sine_wave_pcm().await;
            let mut chunk_size = 4096;
            logger.info("🌊 Streaming Audio...".to_string());
            let mut start_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            for i in (0..pcm_data.len()).step_by(chunk_size as usize).iter() {
                let mut chunk = pcm_data[i..(i + chunk_size)];
                websocket.send(chunk).await;
                asyncio.sleep(0.01_f64).await;
            }
            logger.info("🛑 Audio Sent. Sending STOP command...".to_string());
            websocket.send(serde_json::to_string(&HashMap::from([("command".to_string(), "stop".to_string())])).unwrap()).await;
            logger.info("👂 Listening for Transcription...".to_string());
            while (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_time) < 10 {
                // try:
                {
                    let mut response = asyncio.wait_for(websocket.recv(), /* timeout= */ 5.0_f64).await;
                    let mut data = serde_json::from_str(&response).unwrap();
                    logger.info(format!("📩 RX: {}", data));
                    if data.get(&"text".to_string()).cloned() {
                        logger.info(format!("✅ SUCCESS: Received text '{}'", data["text".to_string()]));
                        true
                    }
                    if data.get(&"is_final".to_string()).cloned() {
                        logger.info("✅ SUCCESS: Received Final Signal (Even if text is empty)".to_string());
                        true
                    }
                }
                // except asyncio.TimeoutError as _e:
                // except websockets.exceptions::ConnectionClosed as _e:
            }
        }
    }
    // except Exception as e:
}
