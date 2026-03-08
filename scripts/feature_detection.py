# -*- coding: utf-8 -*-
"""
feature_detection.py - Detect and report availability of optional features
"""

import logging
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FeatureStatus:
    """Status of an optional feature."""

    available: bool
    module_name: str
    error_message: Optional[str] = None
    installation_hint: Optional[str] = None


class FeatureDetector:
    """Detect availability of optional dependencies and features."""

    def __init__(self):
        self._cache: Dict[str, FeatureStatus] = {}
        self._detect_all()

    def _detect_all(self):
        """Detect all optional features at initialization."""
        # Voice features (STT/TTS)
        self._cache["voice_stt"] = self._detect_voice_stt()
        self._cache["voice_tts"] = self._detect_voice_tts()

        # PDF support
        self._cache["pdf"] = self._detect_pdf()

        # RAG features
        self._cache["rag"] = self._detect_rag()

        # Audio processing
        self._cache["audio"] = self._detect_audio()

        # Report availability
        available_features = [k for k, v in self._cache.items() if v.available]
        unavailable_features = [k for k, v in self._cache.items() if not v.available]

        logger.info(
            f"[FeatureDetector] Available features: {', '.join(available_features) if available_features else 'None'}"
        )
        if unavailable_features:
            logger.info(f"[FeatureDetector] Unavailable features: {', '.join(unavailable_features)}")

    def _detect_voice_stt(self) -> FeatureStatus:
        """Detect Speech-to-Text (Whisper) availability."""
        try:
            import torch
            import whisper

            return FeatureStatus(
                available=True,
                module_name="whisper",
            )
        except ImportError as e:
            missing_module = "torch" if "torch" in str(e) else "whisper"
            return FeatureStatus(
                available=False,
                module_name="whisper",
                error_message=f"Missing dependency: {missing_module}",
                installation_hint="Install with: pip install openai-whisper torch",
            )

    def _detect_voice_tts(self) -> FeatureStatus:
        """Detect Text-to-Speech availability."""
        try:
            import pyttsx3

            # Try to initialize TTS engine
            engine = pyttsx3.init()
            engine.stop()  # Clean up
            return FeatureStatus(
                available=True,
                module_name="pyttsx3",
            )
        except ImportError:
            return FeatureStatus(
                available=False,
                module_name="pyttsx3",
                error_message="Missing dependency: pyttsx3",
                installation_hint="Install with: pip install pyttsx3",
            )
        except Exception as e:
            return FeatureStatus(
                available=False,
                module_name="pyttsx3",
                error_message=f"TTS engine initialization failed: {e}",
                installation_hint="TTS engine may not be available on this system",
            )

    def _detect_pdf(self) -> FeatureStatus:
        """Detect PDF reading support."""
        try:
            import pypdf

            return FeatureStatus(
                available=True,
                module_name="pypdf",
            )
        except ImportError:
            return FeatureStatus(
                available=False,
                module_name="pypdf",
                error_message="Missing dependency: pypdf",
                installation_hint="Install with: pip install pypdf",
            )

    def _detect_rag(self) -> FeatureStatus:
        """Detect RAG dependencies (sentence-transformers, FAISS)."""
        try:
            import sentence_transformers
            import faiss

            return FeatureStatus(
                available=True,
                module_name="sentence_transformers, faiss",
            )
        except ImportError as e:
            missing_module = "sentence-transformers" if "sentence" in str(e) else "faiss"
            return FeatureStatus(
                available=False,
                module_name="sentence_transformers, faiss",
                error_message=f"Missing dependency: {missing_module}",
                installation_hint="Install with: pip install sentence-transformers faiss-cpu",
            )

    def _detect_audio(self) -> FeatureStatus:
        """Detect audio recording support."""
        try:
            import sounddevice as sd
            import scipy.io.wavfile

            return FeatureStatus(
                available=True,
                module_name="sounddevice, scipy",
            )
        except ImportError as e:
            missing_module = "sounddevice" if "sounddevice" in str(e) else "scipy"
            return FeatureStatus(
                available=False,
                module_name="sounddevice, scipy",
                error_message=f"Missing dependency: {missing_module}",
                installation_hint="Install with: pip install sounddevice scipy",
            )

    def is_available(self, feature: str) -> bool:
        """Check if a feature is available."""
        status = self._cache.get(feature)
        return status.available if status else False

    def get_status(self, feature: str) -> Optional[FeatureStatus]:
        """Get detailed status of a feature."""
        return self._cache.get(feature)

    def get_unavailable_reason(self, feature: str) -> str:
        """Get user-friendly message for why a feature is unavailable."""
        status = self._cache.get(feature)
        if not status:
            return f"Unknown feature: {feature}"

        if status.available:
            return f"{feature} is available"

        message = f"{feature.replace('_', ' ').title()} is not available"
        if status.error_message:
            message += f": {status.error_message}"
        if status.installation_hint:
            message += f"\n{status.installation_hint}"

        return message

    def get_all_unavailable(self) -> Dict[str, FeatureStatus]:
        """Get all unavailable features."""
        return {k: v for k, v in self._cache.items() if not v.available}


# Global instance
_detector = None


def get_feature_detector() -> FeatureDetector:
    """Get the global feature detector instance."""
    global _detector
    if _detector is None:
        _detector = FeatureDetector()
    return _detector


def is_feature_available(feature: str) -> bool:
    """Quick check if a feature is available."""
    return get_feature_detector().is_available(feature)
