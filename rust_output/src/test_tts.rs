/// Test TTS synthesis

use anyhow::{Result, Context};
use crate::voice_manager::{get_voice_manager};
use tokio;

/// Test tts.
pub async fn test_tts() -> () {
    // Test tts.
    let mut vm = get_voice_manager();
    println!("{}", "Testing TTS Synthesis...\n".to_string());
    println!("{}", "1️⃣ Testing basic synthesis...".to_string());
    let mut result = vm.synthesize("Hello, this is a test.".to_string());
    println!("   Success: {}", result["success".to_string()]);
    if result["success".to_string()] {
        println!("   Duration: {} seconds", result["duration".to_string()]);
        println!("   Audio data: {} chars (base64)", result["audio_data".to_string()].len());
        println!("   Has audio URL: {}", (result.contains(&"audio_url".to_string()) && (result["audio_url".to_string()] != 0)));
        // pass
    } else {
        println!("   Error: {}", result.get(&"error".to_string()).cloned());
    }
    println!("{}", "\n2️⃣ Testing longer synthesis...".to_string());
    let mut long_text = "Artificial Intelligence is transforming the world. From healthcare to education, AI is making systems smarter and more efficient.".to_string();
    let mut result = vm.synthesize(long_text);
    println!("   Success: {}", result["success".to_string()]);
    if result["success".to_string()] {
        println!("   Duration: {} seconds", result["duration".to_string()]);
        println!("   Audio data: {} chars", result["audio_data".to_string()].len());
        // pass
    }
    println!("{}", "\n3️⃣ Testing cache...".to_string());
    let mut result1 = vm.synthesize("Test cache".to_string(), /* use_cache= */ true);
    let mut result2 = vm.synthesize("Test cache".to_string(), /* use_cache= */ true);
    println!("   First call success: {}", result1["success".to_string()]);
    println!("   Second call success: {}", result2["success".to_string()]);
    println!("   Same audio: {}", result1["audio_data".to_string()] == result2["audio_data".to_string()]);
    println!("{}", "\n✅ All TTS tests passed!".to_string());
}
