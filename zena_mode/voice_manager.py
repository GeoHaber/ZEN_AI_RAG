#!/usr/bin/env python3
"""
ZenAI Voice Manager - Unified Voice System
Manages microphone enumeration, recording, and TTS with proper device handling.
"""

import logging
import io
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
import threading

logger = logging.getLogger("ZenAI.VoiceManager")

# Optional dependencies
try:
    import sounddevice as sd
    import scipy.io.wavfile as wav
    HAS_AUDIO_CAPTURE = True
except ImportError:
    HAS_AUDIO_CAPTURE = False
    logger.warning("sounddevice/scipy missing - audio capture disabled")

try:
    from voice_service import VoiceService
    HAS_VOICE_SERVICE = True
except ImportError:
    HAS_VOICE_SERVICE = False
    logger.warning("voice_service import failed - STT/TTS disabled")


@dataclass
class AudioDevice:
    """Microphone/speaker device info."""
    id: int
    name: str
    channels: int
    is_input: bool
    is_output: bool
    default_sample_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return asdict(self)


@dataclass
class RecordingResult:
    """Result from audio recording."""
    success: bool
    audio_data: Optional[bytes] = None
    duration: float = 0.0
    sample_rate: int = 16000
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict (excludes raw audio_data)."""
        return {
            'success': self.success,
            'duration': self.duration,
            'sample_rate': self.sample_rate,
            'error': self.error
        }


class VoiceManager:
    """
    Unified voice management system:
    - Enumerate audio devices
    - Record from selected microphone
    - Transcribe audio (STT)
    - Synthesize speech (TTS)
    """
    
    def __init__(self, model_dir: Optional[Path] = None, stt_model: str = "base.en", tts_voice: str = "en_US-lessac-medium"):
        """
        Initialize voice manager.
        
        Args:
            model_dir: Directory for downloaded models. Defaults to ~/.zena/models
            stt_model: Whisper model size ("tiny", "base", "small", "medium", "large")
            tts_voice: Piper voice name ("en_US-lessac-medium", etc.)
        """
        if model_dir is None:
            model_dir = Path.home() / ".zena" / "models"
        
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True, parents=True)
        
        # Configuration
        self.stt_model = stt_model
        self.tts_voice = tts_voice
        
        # Voice service (lazy load)
        self._voice_service: Optional[VoiceService] = None
        self._service_lock = threading.RLock()
        
        # Default device cache
        self._default_input_device: Optional[int] = None
        self._device_list_cache: Optional[List[AudioDevice]] = None
        self._cache_valid = False
        
        # TTS audio cache (text -> WAV bytes)
        self._tts_cache: Dict[str, bytes] = {}
        self._tts_cache_dir = self.model_dir / "tts_cache"
        self._tts_cache_dir.mkdir(exist_ok=True, parents=True)
        
        logger.info(f"[VoiceManager] Initialized (STT: {stt_model}, TTS: {tts_voice})")
    
    def get_voice_service(self) -> Optional[VoiceService]:
        """Get or create VoiceService instance (thread-safe)."""
        if not HAS_VOICE_SERVICE:
            return None
            
        with self._service_lock:
            if self._voice_service is None:
                try:
                    self._voice_service = VoiceService(
                        model_dir=self.model_dir,
                        stt_model=self.stt_model,
                        tts_voice=self.tts_voice
                    )
                except Exception as e:
                    logger.error(f"[VoiceManager] Failed to create VoiceService: {e}")
                    return None
            return self._voice_service
    
    def enumerate_devices(self) -> List[AudioDevice]:
        """
        Enumerate all audio input/output devices.
        
        Returns:
            List of AudioDevice objects with id, name, channels, etc.
        """
        if not HAS_AUDIO_CAPTURE:
            logger.warning("[VoiceManager] sounddevice not available")
            return []
        
        try:
            devices = []
            device_list = sd.query_devices()
            
            if isinstance(device_list, dict):
                # Single device (old sounddevice)
                device_list = [device_list]
            
            for i, dev in enumerate(device_list):
                device = AudioDevice(
                    id=i,
                    name=dev.get('name', f'Device {i}'),
                    channels=dev.get('max_input_channels', 0),
                    is_input=dev.get('max_input_channels', 0) > 0,
                    is_output=dev.get('max_output_channels', 0) > 0,
                    default_sample_rate=float(dev.get('default_samplerate', 48000))
                )
                devices.append(device)
            
            self._device_list_cache = devices
            self._cache_valid = True
            logger.info(f"[VoiceManager] Enumerated {len(devices)} devices")
            return devices
        
        except Exception as e:
            logger.error(f"[VoiceManager] Device enumeration failed: {e}")
            return []
    
    def get_default_input_device(self) -> Optional[int]:
        """Get default microphone device ID."""
        if not HAS_AUDIO_CAPTURE:
            return None
        
        try:
            default_info = sd.default.device
            if isinstance(default_info, tuple):
                return default_info[0]  # Input device ID
            return default_info
        except Exception as e:
            logger.error(f"[VoiceManager] Failed to get default device: {e}")
            return None
    
def _record_audio_part1_part2(self):
    """Record audio part1 part 2."""


    def transcribe(self, audio_data: bytes, language: str = "en") -> Dict[str, Any]:
        """
        Transcribe audio to text using Whisper.

        Args:
            audio_data: WAV audio bytes
            language: Language code (default: "en")

        Returns:
            Dict with 'text' (transcribed text) and 'success'
        """
        vs = self.get_voice_service()
        if not vs:
            return {'success': False, 'error': 'VoiceService not available'}

        try:
            logger.info(f"[VoiceManager] Transcribing {len(audio_data)} bytes")
            result = vs.transcribe_audio(io.BytesIO(audio_data), language=language)
            logger.info(f"[VoiceManager] Transcription: {result.get('text', '')[:50]}...")
            return result
        except Exception as e:
            logger.error(f"[VoiceManager] Transcription failed: {e}")
            return {'success': False, 'error': str(e)}

    def synthesize(self, text: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Synthesize text to speech with optional caching.

        Args:
            text: Text to speak
            use_cache: Use cached audio if available (default: True)

        Returns:
            Dict with:
            - 'success': bool
            - 'audio_data': base64-encoded WAV bytes
            - 'audio_url': data URL for HTML5 audio tag
            - 'text': original text
            - 'duration': estimated duration in seconds
            - 'error': error message if failed
        """
        vs = self.get_voice_service()
        if not vs:
            return {'success': False, 'error': 'VoiceService not available'}

        try:
            # Check cache first
            if use_cache and text in self._tts_cache:
                audio_data = self._tts_cache[text]
                logger.info(f"[VoiceManager] Using cached TTS: {text[:50]}...")
            else:
                logger.info(f"[VoiceManager] Synthesizing: {text[:50]}...")

                with self._service_lock:
                    # Use the synthesize_speech method which properly wraps audio in WAV
                    audio_data = vs.synthesize_speech(text)

                # Cache result
                if use_cache:
                    self._tts_cache[text] = audio_data

                logger.info(f"[VoiceManager] Generated {len(audio_data)} bytes")

            if not audio_data:
                return {'success': False, 'error': 'TTS generated empty audio'}

            # Convert to base64 for JSON/HTML5 compatibility
            import base64
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            audio_url = f"data:audio/wav;base64,{audio_b64}"

            # Estimate duration (rough: ~100 chars per second)
            estimated_duration = max(1.0, len(text) / 100.0)

            logger.info(f"[VoiceManager] Synthesis complete ({len(audio_data)} bytes)")
            return {
                'success': True,
                'audio_data': audio_b64,
                'audio_url': audio_url,
                'text': text,
                'duration': estimated_duration
            }
        except Exception as e:
            logger.error(f"[VoiceManager] Synthesis failed: {e}")
            return {'success': False, 'error': str(e)}


def _record_audio_part1_part3(self):
    """Record audio part1 part 3."""


    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive voice system status."""
        return {
            'voice_available': HAS_VOICE_SERVICE,
            'audio_capture_available': HAS_AUDIO_CAPTURE,
            'stt_model': self.stt_model,
            'tts_voice': self.tts_voice,
            'default_input_device': self.get_default_input_device(),
            'devices': [d.to_dict() for d in self.enumerate_devices()]
        }


def _record_audio_part1(self):
    """Record audio part 1."""

    # All devices failed
    return RecordingResult(
        success=False,
        error=f"Recording failed on all {len(devices_to_try)} devices. Last error: {last_error}"
    )


    def record_audio(
        self, 
        duration: float = 3.0, 
        device_id: Optional[int] = None,
        sample_rate: int = 16000,
        channels: int = 1,
        auto_fallback: bool = True
    ) -> RecordingResult:
        """
        Record audio from microphone with auto-fallback support.
        
        Args:
            duration: Recording duration in seconds (default: 3.0)
            device_id: Microphone device ID (default: system default)
            sample_rate: Sample rate in Hz (default: 16000)
            channels: Number of channels (default: 1 for mono)
            auto_fallback: Try alternate devices if primary fails (default: True)
        
        Returns:
            RecordingResult with audio_data as WAV bytes
        """
        if not HAS_AUDIO_CAPTURE:
            return RecordingResult(
                success=False,
                error="sounddevice not installed - run: pip install sounddevice scipy"
            )
        
        # Collect list of devices to try
        devices_to_try = []
        if device_id is not None:
            devices_to_try.append(device_id)
        
        # Add default device
        default_dev = self.get_default_input_device()
        if default_dev is not None and default_dev not in devices_to_try:
            devices_to_try.append(default_dev)
        
        # Add all input devices if auto_fallback
        if auto_fallback:
            all_devices = self.enumerate_devices()
            for dev in all_devices:
                if dev.is_input and dev.id not in devices_to_try:
                    devices_to_try.append(dev.id)
        
        # Try each device in order
        for attempt, dev_id in enumerate(devices_to_try, 1):
            try:
                logger.info(f"[VoiceManager] Recording {duration}s from device {dev_id} (attempt {attempt}/{len(devices_to_try)})")
                
                # Record audio
                num_samples = int(duration * sample_rate)
                recording = sd.rec(
                    num_samples,
                    samplerate=sample_rate,
                    channels=channels,
                    dtype='float32',
                    device=dev_id,
                    blocking=True
                )
                sd.wait()  # Wait for recording to complete
                
                # Convert to WAV bytes
                wav_buffer = io.BytesIO()
                wav.write(wav_buffer, sample_rate, (recording * 32767).astype('int16'))
                wav_buffer.seek(0)
                
                result = RecordingResult(
                    success=True,
                    audio_data=wav_buffer.getvalue(),
                    duration=duration,
                    sample_rate=sample_rate
                )
                logger.info(f"[VoiceManager] Recording complete from device {dev_id} ({len(result.audio_data)} bytes)")
                return result
            
            except Exception as e:
                str(e)
                logger.warning(f"[VoiceManager] Recording failed on device {dev_id}: {e}")
                if attempt == len(devices_to_try):
                    # Last device failed
                    logger.error(f"[VoiceManager] All {attempt} devices failed")
        
        _record_audio_part1(self)
    _record_audio_part1_part2(self)
    _record_audio_part1_part3(self)


# Global singleton instance
_voice_manager: Optional[VoiceManager] = None
_voice_manager_lock = threading.Lock()


def get_voice_manager(model_dir: Optional[Path] = None) -> VoiceManager:
    """Get or create global VoiceManager instance."""
    global _voice_manager
    
    if _voice_manager is None:
        with _voice_manager_lock:
            if _voice_manager is None:
                _voice_manager = VoiceManager(model_dir=model_dir)
    
    return _voice_manager
