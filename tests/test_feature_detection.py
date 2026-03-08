# -*- coding: utf-8 -*-
"""
Tests for feature_detection.py
"""

import pytest
from feature_detection import FeatureDetector, get_feature_detector, is_feature_available


class TestFeatureDetector:
    """Test feature detection system."""

    def test_initialization(self):
        """Test detector initializes without error."""
        detector = FeatureDetector()
        assert detector is not None
        assert detector._cache is not None

    def test_get_global_instance(self):
        """Test global instance is singleton."""
        detector1 = get_feature_detector()
        detector2 = get_feature_detector()
        assert detector1 is detector2

    def test_is_feature_available(self):
        """Test feature availability checks."""
        detector = get_feature_detector()

        # Check known features exist in cache
        assert "voice_stt" in detector._cache
        assert "voice_tts" in detector._cache
        assert "pdf" in detector._cache
        assert "rag" in detector._cache
        assert "audio" in detector._cache

    def test_get_status(self):
        """Test detailed status retrieval."""
        detector = get_feature_detector()
        status = detector.get_status("pdf")

        assert status is not None
        assert hasattr(status, "available")
        assert hasattr(status, "module_name")
        assert isinstance(status.available, bool)

    def test_get_unavailable_reason(self):
        """Test getting reason for unavailable features."""
        detector = get_feature_detector()

        # Get all unavailable features
        unavailable = detector.get_all_unavailable()

        for feature_name, status in unavailable.items():
            reason = detector.get_unavailable_reason(feature_name)
            assert isinstance(reason, str)
            assert len(reason) > 0

    def test_get_all_unavailable(self):
        """Test getting all unavailable features."""
        detector = get_feature_detector()
        unavailable = detector.get_all_unavailable()

        assert isinstance(unavailable, dict)
        # All values should have available=False
        for status in unavailable.values():
            assert status.available is False

    def test_unknown_feature(self):
        """Test handling of unknown feature."""
        detector = get_feature_detector()

        assert not is_feature_available("nonexistent_feature")
        assert detector.get_status("nonexistent_feature") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
