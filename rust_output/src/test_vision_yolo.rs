use anyhow::{Result, Context};
use crate::vision_engine::{get_vision_engine};

/// Test vision engine init.
pub fn test_vision_engine_init() -> () {
    // Test vision engine init.
    println!("{}", "Testing VisionEngine initialization...".to_string());
    let mut engine = get_vision_engine();
    assert!(engine::is_some());
    println!("✅ VisionEngine initialized (Enabled: {})", engine::enabled);
}

/// Test object detection dummy.
pub fn test_object_detection_dummy() -> () {
    // Test object detection dummy.
    println!("{}", "Testing object detection on a black image...".to_string());
    let mut engine = get_vision_engine();
    if !engine::enabled {
        println!("{}", "⚠️ Vision engine disabled, skipping detection test".to_string());
        return;
    }
    let mut img = numpy.zeros((640, 640, 3), /* dtype= */ numpy.uint8);
    let mut detections = engine::detect_objects(img);
    println!("✅ Detection run completed. Found {} objects.", detections.len());
    let mut summary = engine::get_vision_summary(detections);
    println!("Summary: {}", (summary || "None".to_string()));
}
