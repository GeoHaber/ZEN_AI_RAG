"""
Enhanced Voice Manager with Microphone Self-Healing

This module extends the standard VoiceManager with automatic microphone
diagnostics and recovery capabilities.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from zena_mode.voice_manager import VoiceManager

try:
    from zena_mode.production_microphone_healer import ProductionMicrophoneHealer
    HAS_HEALER = True
except ImportError:
    HAS_HEALER = False
    logging.warning("ProductionMicrophoneHealer not available")

logger = logging.getLogger("VoiceManager.WithHealing")


class VoiceManagerWithHealing(VoiceManager):
    """
    Voice Manager with automatic microphone diagnostics and self-healing.
    
    Features:
    - Automatic device health checks before recording
    - Fallback to alternative devices on failure
    - Process monitoring (finds which apps block microphone)
    - Audio quality scoring
    - Actionable recommendations for users
    """
    
    def __init__(
        self,
        model_dir: Optional[Path] = None,
        stt_model: str = "base.en",
        tts_voice: str = "en_US-lessac-medium",
        auto_heal: bool = True,
        preferred_device: Optional[int] = None
    ):
        """
        Initialize with optional auto-healing.
        
        Args:
            model_dir: Directory for downloaded models
            stt_model: Whisper model size
            tts_voice: Piper voice name
            auto_heal: Enable automatic microphone healing
            preferred_device: Preferred microphone device ID
        """
        super().__init__(model_dir=model_dir, stt_model=stt_model, tts_voice=tts_voice)
        
        self.preferred_device = preferred_device
        self.auto_heal_enabled = auto_heal and HAS_HEALER
        
        if self.auto_heal_enabled:
            self.healer = ProductionMicrophoneHealer()
        else:
            self.healer = None
"""
Enhanced Voice Manager with Microphone Self-Healing

This module extends the standard VoiceManager with automatic microphone
diagnostics and recovery capabilities.
"""

import logging
from pathlib import Path
# from typing import Optional, Dict, Any
from zena_mode.voice_manager import VoiceManager

try:
    from zena_mode.production_microphone_healer import ProductionMicrophoneHealer
    HAS_HEALER = True
except ImportError:
    HAS_HEALER = False
    logging.warning("ProductionMicrophoneHealer not available")

logger = logging.getLogger("VoiceManager.WithHealing")


class VoiceManagerWithHealing(VoiceManager):
    """
    Voice Manager with automatic microphone diagnostics and self-healing.
    
    Features:
    - Automatic device health checks before recording
    - Fallback to alternative devices on failure
    - Process monitoring (finds which apps block microphone)
    - Audio quality scoring
    - Actionable recommendations for users
    """
    
    def __init__(
        self,
        model_dir: Optional[Path] = None,
        stt_model: str = "base.en",
        tts_voice: str = "en_US-lessac-medium",
        auto_heal: bool = True
    ):
        """
        Initialize with optional auto-healing.
        
        Args:
            model_dir: Directory for downloaded models
            stt_model: Whisper model size
            tts_voice: Piper voice name
            auto_heal: Enable automatic microphone healing
        """
        super().__init__(model_dir=model_dir, stt_model=stt_model, tts_voice=tts_voice)
        
        self.auto_heal_enabled = auto_heal and HAS_HEALER
        
        if self.auto_heal_enabled:
            self.healer = ProductionMicrophoneHealer()
        else:
            self.healer = None
    
    def diagnose_microphone(self, verbose: bool = False) -> Dict[str, Any]:
        """
        Run complete microphone diagnostic.
        
        Args:
            verbose: Print detailed diagnostics
            
        Returns:
            Diagnostic results with recommendations
        """
        if not self.healer:
            logger.warning("Healer not available")
            return {'status': 'ERROR', 'message': 'Healer not initialized'}
        
        return self.healer.auto_heal_with_recommendations() if verbose \
               else self.healer.full_diagnostic(verbose=False)
    
    def get_best_device(self) -> Optional[int]:
        """
        Get the best available microphone device.
        
        Uses ProductionMicrophoneHealer to score all devices and return
        the best one based on availability, quality, and priority.
        
        Returns:
            Device ID or None if no devices available
        """
        if not self.healer:
            logger.warning("Healer not available")
            return None
        
        diag = self.healer.full_diagnostic(verbose=False)
        return diag.get('best_device_id')
    
    def record_audio_with_healing(
        self,
        duration: float = 5.0,
        device_id: Optional[int] = None,
        auto_fallback: bool = True,
        verbose: bool = False
    ) -> Optional[bytes]:
        """
        Record audio with automatic microphone healing.
        
        If recording fails:
        1. Run diagnostic to find best device
        2. Try alternative devices automatically
        3. Return audio or None on failure
        
        Args:
            duration: Recording duration in seconds
            device_id: Specific device to try first
            auto_fallback: Try alternative devices on failure
            verbose: Print healing messages
            
        Returns:
            WAV audio bytes or None on failure
        """
        if verbose:
            logger.info("Recording audio...")
        
        # Try recording with specified or default device
        result = self.record_audio(
            duration=duration,
            device_id=device_id,
            auto_fallback=auto_fallback
        )
        
        if result.success and result.audio_data:
            if verbose:
                logger.info(f"✓ Recording successful ({len(result.audio_data)} bytes)")
            return result.audio_data
        
        # If failed, try to heal
        if auto_fallback and self.healer and verbose:
            logger.warning(f"Recording failed: {result.error}")
            logger.info("Running microphone diagnostic...")
            
            diag = self.full_diagnostic(verbose=False)
            best = diag.get('best_device_id')
            
            if best is not None and best != device_id:
                logger.info(f"Trying best device: #{best}")
                result2 = self.record_audio(
                    duration=duration,
                    device_id=best,
                    auto_fallback=False
                )
                
                if result2.success:
                    logger.info(f"✓ Success with device {best}")
                    return result2.audio_data
        
        logger.error(f"Could not record audio: {result.error}")
        return None
    
    def full_diagnostic(self, verbose: bool = False) -> Dict[str, Any]:
        """Alias for diagnose_microphone for consistency."""
        return self.diagnose_microphone(verbose=verbose)
    
    def get_health_report(self) -> str:
        """
        Get human-readable microphone health report.
        
        Returns:
            Multi-line health report
        """
        if not self.healer:
            return "Healer not available"
        
        result = self.healer.auto_heal_with_recommendations()
        
        lines = []
        lines.append("=" * 70)
        lines.append("MICROPHONE HEALTH REPORT")
        lines.append("=" * 70)
        
        best = result['diagnostic']['best_device']
        if best:
            lines.append(f"\nBest Device: #{best['device_id']} - {best['device_name']}")
            lines.append(f"Overall Score: {best['total_score']}/100")
            lines.append(f"  - Availability: {best['availability_score']}/100")
            lines.append(f"  - Quality: {best['quality_score']}/100")
            lines.append(f"  - Priority: {best['priority_score']}/100")
        
        procs = result['diagnostic']['competing_processes']
        if procs:
            proc_names = list(set([p['name'] for p in procs]))
            lines.append(f"\nAudio-using Processes ({len(proc_names)}):")
            for name in proc_names[:5]:
                lines.append(f"  - {name}")
            if len(proc_names) > 5:
                lines.append(f"  ... and {len(proc_names) - 5} more")
        else:
            lines.append(f"\nNo competing audio processes detected")
        
        lines.append("\nRecommendations:")
        for rec in result['recommendations']:
            lines.append(f"  {rec}")
        
        return "\n".join(lines)


# Quick usage example
if __name__ == "__main__":
    # Create voice manager with healing
    voice = VoiceManagerWithHealing(auto_heal=True)
    
    # Get health report
    print(voice.get_health_report())
    
    # Find best device
    best = voice.get_best_device()
    print(f"\nUsing device: {best}")
    
    # Record with healing
    print("\nRecording 3 seconds...")
    audio = voice.record_audio_with_healing(
        duration=3.0,
        auto_fallback=True,
        verbose=True
    )
    
    if audio:
        print(f"✓ Recorded {len(audio)} bytes")
    else:
        print("✗ Recording failed")
    
def _record_audio_with_healing_part1(self, auto_fallback, duration, verbose):
    """Record audio with healing part 1."""

    # If failed and healing enabled, try to fix
    if auto_fallback:
        if verbose:
            logger.info("Running microphone healing...")

        result = self.diagnose_microphone(verbose=False)
        best_device = result['diagnostic']['best_device_id']

        if best_device is not None and best_device != self.device:
            if verbose:
                proc_count = len(result['diagnostic']['competing_processes'])
                if proc_count > 0:
                    logger.warning(
                        f"  {proc_count} audio-using processes detected"
                    )

                device_name = result['diagnostic']['best_device'][
                    'device_name'
                ]
                logger.info(f"  Switching to device: {device_name}")

            # Try alternative device
            old_device = self.device
            self.device = best_device

            try:
                audio = self.record_audio(
                    duration=duration,
                    auto_fallback=False
                )
                if audio:
                    if verbose:
                        logger.info("✓ Recording successful with alternative device")
                    return audio
            except Exception as e:
                if verbose:
                    logger.error(f"Alternative device also failed: {e}")
                self.device = old_device

    logger.error("Could not record audio after healing attempts")
    return None


    def record_audio_with_healing(
        self,
        duration: float = 5.0,
        auto_fallback: bool = True,
        verbose: bool = False
    ) -> Optional[bytes]:
        """
        Record audio with automatic microphone healing.
        
        If initial device fails:
        1. Check what's using microphone (process blocking?)
        2. Find alternative working device
        3. Use best available device automatically
        
        Args:
            duration: Recording duration in seconds
            auto_fallback: Try alternative devices on failure
            verbose: Print healing messages
            
        Returns:
            WAV audio bytes or None on failure
        """
        if not self.healer:
            # Fallback to normal recording without healing
            return self.record_audio(
                duration=duration,
                auto_fallback=auto_fallback
            )
        
        if verbose:
            logger.info("Recording audio with healing...")
        
        # Try current device first
        try:
            audio = self.record_audio(
                duration=duration,
                auto_fallback=False
            )
            if audio:
                if verbose:
                    logger.info("✓ Recording successful with current device")
                return audio
        except Exception as e:
            if verbose:
                logger.warning(f"Recording failed: {e}")
        
        _record_audio_with_healing_part1(self, auto_fallback, duration, verbose)
    
    def get_health_report(self) -> str:
        """
        Get human-readable microphone health report.
        
        Returns:
            Multi-line health report
        """
        if not self.healer:
            return "Healer not available"
        
        result = self.healer.auto_heal_with_recommendations()
        
        lines = []
        lines.append("=" * 70)
        lines.append("MICROPHONE HEALTH REPORT")
        lines.append("=" * 70)
        
        best = result['diagnostic']['best_device']
        if best:
            lines.append(f"\nBest Device: {best['device_name']}")
            lines.append(f"Score: {best['total_score']}/100")
            lines.append(f"  - Availability: {best['availability_score']}/100")
            lines.append(f"  - Quality: {best['quality_score']}/100")
            lines.append(f"  - Priority: {best['priority_score']}/100")
        
        procs = result['diagnostic']['competing_processes']
        if procs:
            proc_names = list(set([p['name'] for p in procs]))
            lines.append(f"\nBlocking Processes ({len(proc_names)}):")
            for name in proc_names[:5]:
                lines.append(f"  - {name}")
            if len(proc_names) > 5:
                lines.append(f"  ... and {len(proc_names) - 5} more")
        
        lines.append("\nRecommendations:")
        for rec in result['recommendations']:
            lines.append(f"  {rec}")
        
        return "\n".join(lines)


# Quick usage example
if __name__ == "__main__":
    # Create voice manager with healing
    voice = VoiceManagerWithHealing(auto_heal=True)
    
    # Get health report
    print(voice.get_health_report())
    
    # Find best device
    best = voice.get_best_device()
    print(f"\nUsing device: {best}")
    
    # Record with healing
    print("\nRecording 3 seconds with healing...")
    audio = voice.record_audio_with_healing(
        duration=3.0,
        auto_fallback=True,
        verbose=True
    )
    
    if audio:
        print(f"✓ Recorded {len(audio)} bytes")
    else:
        print("✗ Recording failed")
