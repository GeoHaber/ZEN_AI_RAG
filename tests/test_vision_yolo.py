import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from zena_mode.vision_engine import get_vision_engine
import numpy as np
import cv2

def test_vision_engine_init():
    print("Testing VisionEngine initialization...")
    engine = get_vision_engine()
    assert engine is not None
    print(f"✅ VisionEngine initialized (Enabled: {engine.enabled})")

def test_object_detection_dummy():
    print("Testing object detection on a black image...")
    engine = get_vision_engine()
    if not engine.enabled:
        print("⚠️ Vision engine disabled, skipping detection test")
        return
        
    # Create a dummy image
    img = np.zeros((640, 640, 3), dtype=np.uint8)
    detections = engine.detect_objects(img)
    print(f"✅ Detection run completed. Found {len(detections)} objects.")
    
    summary = engine.get_vision_summary(detections)
    print(f"Summary: {summary or 'None'}")

if __name__ == "__main__":
    test_vision_engine_init()
    test_object_detection_dummy()
    print("\nVISION SMOKE TEST COMPLETE! 🤵")
