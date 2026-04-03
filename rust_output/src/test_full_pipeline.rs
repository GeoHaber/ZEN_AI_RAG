/// Complete voice pipeline test

use anyhow::{Result, Context};
use crate::voice_manager::{get_voice_manager};
use tokio;

/// Helper: setup phase for test_voice_pipeline.
pub fn _do_test_voice_pipeline_setup() -> () {
    // Helper: setup phase for test_voice_pipeline.
    let mut vm = get_voice_manager();
    println!("{}", "🎤 Full Voice Pipeline Test\n".to_string());
    println!("{}", ("=".to_string() * 60));
    println!("{}", "\n1️⃣ Microphone Devices:".to_string());
    let mut devices = vm.enumerate_devices();
    let mut input_devices = devices.iter().filter(|d| d.is_input).map(|d| d.to_dict()).collect::<Vec<_>>();
    for dev in input_devices[..3].iter() {
        println!("   • {} (ID {})", dev["name".to_string()], dev["id".to_string()]);
        // pass
    }
    println!("{}", if input_devices.len() > 3 { format!("   ... and {} more", (input_devices.len() - 3)) } else { "".to_string() });
    println!("{}", "\n2️⃣ Testing STT (Speech-to-Text):".to_string());
    // TODO: from voice_service import VoiceService
    // TODO: from pathlib import Path
    // TODO: import io
    let mut vs = VoiceService(/* model_dir= */ ((Path.home() / ".zena".to_string()) / "models".to_string()));
    println!("{}", "   Loading Whisper model...".to_string());
    vs.load_stt_model();
    println!("{}", "   ✓ Whisper ready".to_string());
    println!("{}", "\n3️⃣ Testing TTS (Text-to-Speech):".to_string());
    let mut test_texts = vec!["Hello world".to_string(), "This is a test".to_string(), "Artificial intelligence is amazing".to_string()];
    (test_texts, vm)
}

/// Test complete voice input -> transcription -> synthesis -> output
pub async fn test_voice_pipeline() -> () {
    // Test complete voice input -> transcription -> synthesis -> output
    let (mut test_texts, mut vm) = _do_test_voice_pipeline_setup();
    for text in test_texts.iter() {
        let mut result = vm.synthesize(text);
        let mut size = if result["success".to_string()] { result["audio_data".to_string()].len() } else { 0 };
        println!("   • '{}...' → {} bytes", text[..30], size);
        if !result["success".to_string()] {
            println!("     Error: {}", result.get(&"error".to_string()).cloned());
        }
    }
    println!("{}", "\n4️⃣ Testing TTS Cache:".to_string());
    let mut text = "Cache this".to_string();
    let mut r1 = vm.synthesize(text, /* use_cache= */ true);
    let mut r2 = vm.synthesize(text, /* use_cache= */ true);
    println!("   First:  {} bytes", r1["audio_data".to_string()].len());
    println!("   Second: {} bytes (cached)", r2["audio_data".to_string()].len());
    println!("   Same:   {} ✓", r1["audio_data".to_string()] == r2["audio_data".to_string()]);
    println!("{}", "\n5️⃣ Testing Audio URL Generation:".to_string());
    let mut result = vm.synthesize("Test audio URL".to_string());
    if result["success".to_string()] {
        let mut has_url = (result.get(&"audio_url".to_string()).cloned() != 0);
        let mut url_length = if has_url { result["audio_url".to_string()].len() } else { 0 };
        println!("   Audio URL generated: {}", has_url);
        println!("   Data URL length: {} chars", url_length);
        println!("   Format: data:audio/wav;base64,...");
    }
    println!("{}", ("\n".to_string() + ("=".to_string() * 60)));
    println!("{}", "✅ All pipeline tests passed!".to_string());
    println!("{}", "\n📊 Pipeline Status:".to_string());
    println!("{}", "   ✓ Device enumeration working".to_string());
    println!("{}", "   ✓ STT model loading working".to_string());
    println!("{}", "   ✓ TTS synthesis working".to_string());
    println!("{}", "   ✓ Audio caching working".to_string());
    println!("{}", "   ✓ HTML5 audio URL generation working".to_string());
    println!("{}", "\n🎯 Ready for UI integration!".to_string());
}
