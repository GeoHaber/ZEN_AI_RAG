use anyhow::{Result, Context};
use crate::config_system::{config};
use std::collections::HashMap;
use tokio;

/// Simulates a browser client streaming audio to the backend.
pub async fn test_voice_streaming() -> Result<()> {
    // Simulates a browser client streaming audio to the backend.
    let mut uri = format!("ws://127.0.0.1:{}", config::voice_port);
    println!("Connecting to {}...", uri);
    // try:
    {
        let mut websocket = websockets.connect(uri);
        {
            let mut msg = websocket.recv().await;
            println!("< {}", msg);
            println!("{}", "> Streaming synthetic audio...".to_string());
            let mut sample_rate = 16000;
            let mut duration = 3;
            let mut frequency = 440;
            let mut t = numpy.linspace(0, duration, (sample_rate * duration).to_string().parse::<i64>().unwrap_or(0), false);
            let mut note = numpy.sin((((frequency * t) * 2) * numpy.pi));
            let mut audio = (note * 32767).astype(numpy.int16).tobytes();
            let mut chunk_size = ((sample_rate * 0.25_f64) * 2).to_string().parse::<i64>().unwrap_or(0);
            for i in (0..audio.len()).step_by(chunk_size as usize).iter() {
                let mut chunk = audio[i..(i + chunk_size)];
                websocket.send(chunk).await;
                asyncio.sleep(0.1_f64).await;
            }
            println!("{}", "> Audio finished. Sending Stop command...".to_string());
            websocket.send(serde_json::to_string(&HashMap::from([("command".to_string(), "stop".to_string())])).unwrap()).await;
            while true {
                let mut response = websocket.recv().await;
                let mut data = serde_json::from_str(&response).unwrap();
                println!("< {}", data);
                if (data.get(&"is_final".to_string()).cloned() || data.get(&"status".to_string()).cloned() == "cleared".to_string()) {
                    break;
                }
            }
            println!("{}", "✅ Test Passed: Stream completed.".to_string());
        }
    }
    // except Exception as _e:
}
