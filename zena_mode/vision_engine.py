# -*- coding: utf-8 -*-
"""
zena_mode/vision_engine.py - SOTA Vision Analysis with YOLOv26
Provides object detection and video scene analysis.
"""
import logging
import cv2
import numpy as np
from typing import List, Dict, Any
from collections import Counter

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False

logger = logging.getLogger("VisionEngine")

class VisionEngine:
    """
    High-performance Computer Vision engine using YOLOv26.
    Handles object detection, classification, and video frame analysis.
    """
    
    def __init__(self, model_name: str = "yolo26n.pt"):
        """Initialize instance."""
        self.enabled = ULTRALYTICS_AVAILABLE
        self.model = None
        self.model_name = model_name
        
        if self.enabled:
            try:
                # YOLO will auto-download the model if not found
                self.model = YOLO(model_name)
                logger.info(f"[Vision] YOLOv26 model '{model_name}' loaded successfully")
            except Exception as e:
                logger.error(f"[Vision] Failed to load YOLO model: {e}")
                self.enabled = False
        else:
            logger.warning("[Vision] 'ultralytics' not installed. Vision features disabled.")

    def detect_objects(self, img: np.ndarray, confidence: float = 0.25) -> List[Dict[str, Any]]:
        """
        Detect objects in an image and return structured results.
        """
        if not self.enabled or self.model is None:
            return []
            
        try:
            results = self.model.predict(img, conf=confidence, verbose=False)
            detections = []
            
            for result in results:
                # Extrat class names and counts
                for box in result.boxes:
                    cls_id = int(box.cls[0].item())
                    label = self.model.names[cls_id]
                    prob = float(box.conf[0].item())
                    
                    detections.append({
                        "label": label,
                        "confidence": prob,
                        "box": box.xyxy[0].tolist() # [xmin, ymin, xmax, ymax]
                    })
            
            return detections
        except Exception as e:
            logger.error(f"[Vision] Detection error: {e}")
            return []

    def get_vision_summary(self, detections: List[Dict[str, Any]]) -> str:
        """
        Generate a human-readable summary of detected objects.
        """
        if not detections:
            return ""
            
        counts = Counter([d['label'] for d in detections])
        summary_parts = []
        for label, count in counts.items():
            plural = "s" if count > 1 else ""
            summary_parts.append(f"{count} {label}{plural}")
            
        return "Objects detected: " + ", ".join(summary_parts)

    def analyze_video(self, video_path: str, fps_interval: float = 1.0) -> Dict[str, Any]:
        """
        Analyze a video file by extracting keyframes and aggregating detections.
        """
        if not self.enabled:
            return {"error": "Vision engine disabled"}
            
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"error": f"Could not open video: {video_path}"}
            
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(video_fps * fps_interval) if video_fps > 0 else 30
        
        frame_count = 0
        analyzed_frames = 0
        all_detections = []
        timeline = []
        
        logger.info(f"[Vision] Starting video analysis: {video_path} (Interval: {fps_interval}s)")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_count % frame_interval == 0:
                # Analyze this frame
                detections = self.detect_objects(frame)
                if detections:
                    timestamp = frame_count / video_fps if video_fps > 0 else 0
                    summary = self.get_vision_summary(detections)
                    
                    timeline.append({
                        "timestamp": round(timestamp, 2),
                        "summary": summary,
                        "detections": detections
                    })
                    all_detections.extend([d['label'] for d in detections])
                
                analyzed_frames += 1
                # Limit analysis to prevent timeout
                if analyzed_frames > 60: # Max 1 minute of processed content at 1fps
                    break
                    
            frame_count += 1
            
        cap.release()
        
        # Aggregate final report
        global_counts = Counter(all_detections)
        return {
            "duration_frames": frame_count,
            "processed_frames": analyzed_frames,
            "timeline": timeline,
            "summary": self.get_vision_summary([{"label": l} for l in all_detections]),
            "unique_objects": list(global_counts.keys())
        }

# Singleton instance
_vision_engine = None

def get_vision_engine():
    """Get vision engine."""
    global _vision_engine
    if _vision_engine is None:
        _vision_engine = VisionEngine()
    return _vision_engine
