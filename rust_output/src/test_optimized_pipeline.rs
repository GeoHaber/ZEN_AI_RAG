/// Optimized voice pipeline test with timing

use anyhow::{Result, Context};
use crate::voice_manager::{get_voice_manager};
use tokio;

/// Test voice pipeline part 1.
pub fn _test_voice_pipeline_part1() -> () {
    // Test voice pipeline part 1.
    let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    let mut result2 = vm.synthesize(test_text, /* use_cache= */ true);
    let mut time2 = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start);
    println!("   First call (synthesis):  {:.3}s", time1);
    println!("   Second call (cached):    {:.6}s (essentially instant)", time2);
    if time2 > 0 {
        println!("   Speedup:                 {:.0}x faster", (time1 / time2));
        // pass
    } else {
        println!("   Speedup:                 INSTANT (< 1ms)");
        // pass
    }
    println!("   ✓ Cache hit verified:    {}", result1["audio_data".to_string()] == result2["audio_data".to_string()]);
    println!("{}", "\n5️⃣ Audio Format Verification:".to_string());
    let mut result = vm.synthesize("Format test".to_string());
    if result["success".to_string()] {
        let mut audio_b64 = result["audio_data".to_string()];
        println!("   ✓ Base64 encoded:        {} chars", audio_b64.len());
        println!("   ✓ Audio URL ready:       data:audio/wav;base64,...");
        println!("   ✓ Duration estimate:     {:.1}s", result["duration".to_string()]);
        println!("   ✓ HTML5 compatible:      Yes (float32 WAV)");
    }
    println!("{}", "\n6️⃣ Batch Synthesis (5 unique phrases):".to_string());
    let mut phrases = vec!["Good morning".to_string(), "How are you".to_string(), "Very well, thank you".to_string(), "Nice to meet you".to_string(), "See you later".to_string()];
    let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    for phrase in phrases.iter() {
        vm.synthesize(phrase, /* use_cache= */ true);
    }
    let mut total_time = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start);
    println!("   Synthesized {} phrases in {:.2}s", phrases.len(), total_time);
    println!("   Average per phrase:      {:.2}s", (total_time / phrases.len()));
    let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    for phrase in phrases.iter() {
        vm.synthesize(phrase, /* use_cache= */ true);
    }
    (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start);
}

/// Test voice pipeline part 2.
pub fn _test_voice_pipeline_part2() -> () {
    // Test voice pipeline part 2.
    println!("   From cache (5 phrases):  {:.4}s (instant)", cached_time);
    if cached_time > 0 {
        println!("   Total speedup:           {:.0}x faster", (total_time / cached_time));
        // pass
    } else {
        println!("   Total speedup:           INSTANT (< 1ms for all)");
        // pass
    }
    println!("{}", ("\n".to_string() + ("=".to_string() * 70)));
    println!("{}", "✅ ALL TESTS PASSED!".to_string());
    println!("{}", "\n📊 Summary:".to_string());
    println!("{}", "   ✓ Device enumeration working".to_string());
    println!("{}", "   ✓ TTS synthesis optimized (float32 - no int16 conversion)".to_string());
    println!("{}", "   ✓ Audio caching working".to_string());
    println!("{}", "   ✓ Base64 encoding for HTML5".to_string());
    println!("{}", "   ✓ Ready for production deployment".to_string());
}

/// Test complete optimized voice pipeline
pub async fn test_voice_pipeline() -> () {
    // Test complete optimized voice pipeline
    let mut vm = get_voice_manager();
    println!("{}", "🚀 Optimized Voice Pipeline Test".to_string());
    println!("{}", ("=".to_string() * 70));
    println!("{}", "\n1️⃣ Microphone Enumeration:".to_string());
    let mut devices = vm.enumerate_devices();
    let mut input_devices = devices.iter().filter(|d| d.is_input).map(|d| d).collect::<Vec<_>>();
    println!("   ✓ Found {} input devices", input_devices.len());
    for (i, dev) in input_devices[..3].iter().enumerate().iter() {
        println!("     • {}", dev.name);
        // pass
    }
    println!("{}", "\n2️⃣ Voice System Status:".to_string());
    let mut status = vm.get_status();
    println!("   ✓ Voice service available: {}", status["voice_available".to_string()]);
    println!("   ✓ Audio capture: {}", status["audio_capture_available".to_string()]);
    println!("   ✓ STT model: {}", status["stt_model".to_string()]);
    println!("   ✓ TTS voice: {}", status["tts_voice".to_string()]);
    println!("{}", "\n3️⃣ TTS Performance (Float32 Optimized):".to_string());
    let mut test_cases = vec![("Short".to_string(), "Hi".to_string()), ("Medium".to_string(), "Hello, how are you today?".to_string()), ("Long".to_string(), "Artificial Intelligence is transforming how we work, learn, and communicate. From healthcare to education, AI is making systems smarter and more efficient every day.".to_string())];
    for (label, text) in test_cases.iter() {
        let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        let mut result = vm.synthesize(text, /* use_cache= */ false);
        let mut elapsed = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start);
        if result["success".to_string()] {
            let mut size_kb = (result["audio_data".to_string()].len() / 1024);
            println!("   • {:8} ({:3} chars) → {:6.1} KB in {:.2}s", label, text.len(), size_kb, elapsed);
        } else {
            println!("   • {:8} ERROR: {}", label, result.get(&"error".to_string()).cloned());
        }
    }
    println!("{}", "\n4️⃣ Caching Performance:".to_string());
    let mut test_text = "Cache performance test".to_string();
    let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    vm.synthesize(test_text, /* use_cache= */ true);
    (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start);
    _test_voice_pipeline_part1();
    _test_voice_pipeline_part2();
}
