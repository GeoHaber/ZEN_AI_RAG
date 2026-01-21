#!/usr/bin/env python3
"""
Nebula Voice Service - Local Speech-to-Text and Text-to-Speech
Provides voice input/output capabilities using:
- faster-whisper for STT (speech recognition)
- Piper TTS for TTS (speech synthesis)
"""

import os
import io
import wave
import logging
from pathlib import Path
from typing import Optional, BinaryIO

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

try:
    from piper import PiperVoice
except ImportError:
    PiperVoice = None

logger = logging.getLogger("NebulaVoice")

class VoiceService:
    """
    Local voice processing service with STT and TTS capabilities.
    All processing happens offline on the user's machine.
    """
    
    def __init__(self, model_dir: Path, stt_model: str = "base.en", tts_voice: str = "en_US-lessac-medium"):
        self.model_dir = model_dir
        self.model_dir.mkdir(exist_ok=True, parents=True)
        
        # STT Model (faster-whisper)
        self.stt_model_name = stt_model
        self.stt_model: Optional[WhisperModel] = None
        
        # TTS Model (Piper)
        self.tts_voice_name = tts_voice
        self.tts_model: Optional[PiperVoice] = None
        
        # Concurrency Lock (Windows/File Safety)
        import threading
        self._lock = threading.Lock()
        
        logger.info("[Voice] Service initialized (lazy loading enabled)")
    
    def load_stt_model(self):
        """Load faster-whisper model for speech recognition."""
        if self.stt_model is not None:
            return  # Already loaded
        
        if WhisperModel is None:
            raise RuntimeError("faster-whisper not installed. Run: pip install faster-whisper")
        
        logger.info(f"[STT] Loading {self.stt_model_name} model...")
        
        # Use CPU with 8-bit quantization for efficiency
        self.stt_model = WhisperModel(
            self.stt_model_name,
            device="cpu",
            compute_type="int8",
            download_root=str(self.model_dir / "whisper")
        )
        
        logger.info("[STT] Model loaded successfully")
    
    # --- Helper: TTS Model Auto-Downloader ---
    def ensure_piper_model(self):
        """Ensures the Piper model exists, downloading it if necessary."""
        voice_dir = self.model_dir / "piper"
        voice_dir.mkdir(exist_ok=True, parents=True)
        
        onnx_file = voice_dir / f"{self.tts_voice_name}.onnx"
        json_file = voice_dir / f"{self.tts_voice_name}.onnx.json"
        
        if onnx_file.exists() and json_file.exists():
            return onnx_file, json_file
            
        logger.info(f"[TTS] Downloading missing voice model: {self.tts_voice_name}")
        
        # Hardcoded mirror URL for known voices (Safe fallback)
        # Mirrors: https://github.com/rhasspy/piper/releases/tag/v0.0.2
        # Using a reliable HF mirror
        base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium"
        if self.tts_voice_name != "en_US-lessac-medium":
             logger.warning(f"[TTS] Auto-download only supports 'en_US-lessac-medium'. Please check path manually for {self.tts_voice_name}")
             return onnx_file, json_file

        import urllib.request
        try:
            if not onnx_file.exists():
                logger.info("Downloading ONNX model...")
                urllib.request.urlretrieve(f"{base_url}/en_US-lessac-medium.onnx", onnx_file)
            
            if not json_file.exists():
                logger.info("Downloading Config JSON...")
                urllib.request.urlretrieve(f"{base_url}/en_US-lessac-medium.onnx.json", json_file)
                
            logger.info("[TTS] Download complete.")
        except Exception as e:
            logger.error(f"[TTS] Download failed: {e}")
            if onnx_file.exists(): onnx_file.unlink()
            if json_file.exists(): json_file.unlink()
            raise

        return onnx_file, json_file

    def load_tts_model(self):
        """Load Piper TTS model for speech synthesis."""
        if self.tts_model is not None:
            return  # Already loaded
        
        if PiperVoice is None:
            raise RuntimeError("piper-tts not installed. Run: pip install piper-tts")
        
        logger.info(f"[TTS] Loading {self.tts_voice_name} voice...")
        
        try:
            # Ensure model exists (Download if missing)
            voice_path, config_path = self.ensure_piper_model()
            
            self.tts_model = PiperVoice.load(str(voice_path), config_path=str(config_path))
            logger.info("[TTS] Voice loaded successfully")
        except Exception as e:
            logger.error(f"[TTS] Failed to load voice: {e}")
            self.tts_model = None
            raise

    def transcribe_audio(self, audio_file: BinaryIO, language: str = "en") -> dict:
        """
        Transcribe audio file to text using faster-whisper.
        Robustly handles generic audio inputs by converting to clean WAV first.
        """
        import subprocess

        # Ensure single-threaded access to model (Windows file locking fix)
        with self._lock:
            self.load_stt_model()
            
            # Paths
            raw_path = self.model_dir / "raw_audio_input.bin" # Unknown extension
            clean_path = self.model_dir / "clean_audio.wav"
            
            # Save raw input to disk
            with open(raw_path, "wb") as f:
                f.write(audio_file.read())
        
            try:
                # 1. Convert to standardized WAV using system FFmpeg
                # This fixes "Invalid Data" errors from WebM/Opus blobs or corrupt headers
                # We use raw_path input and force output to 16kHz mono PCM (ideal for Whisper)
                cmd = [
                    "ffmpeg", "-y",
                    "-i", str(raw_path),
                    "-ar", "16000",
                    "-ac", "1",
                    "-c:a", "pcm_s16le",
                    str(clean_path)
                ]
                
                # Run conversion, suppressing loud logging unless error
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"[Voice] FFmpeg conversion failed: {result.stderr}")
                    # Fallback: Try raw path if ffmpeg failed (maybe it's already a valid wav?)
                    transcribe_target = str(raw_path)
                else:
                    transcribe_target = str(clean_path)

                # 2. Transcribe
                segments, info = self.stt_model.transcribe(
                    transcribe_target,
                    language=language if language != "auto" else None,
                    beam_size=5,
                    vad_filter=True
                )
                
                # Collect results
                text_parts = []
                segment_list = []
                
                for segment in segments:
                    text_parts.append(segment.text)
                    segment_list.append({
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text
                    })
                
                full_text = " ".join(text_parts).strip()
                
                return {
                    "text": full_text,
                    "language": info.language,
                    "segments": segment_list,
                    "duration": info.duration
                }
            
            except Exception as e:
                logger.error(f"[Voice] Transcription critical failure: {e}")
                raise
            
            finally:
                # Cleanup
                try: raw_path.unlink(missing_ok=True) 
                except: pass
                try: clean_path.unlink(missing_ok=True) 
                except: pass
    
    def synthesize_speech(self, text: str, speed: float = 1.0) -> bytes:
        """
        Convert text to speech using Piper TTS.
        
        Args:
            text: Text to speak
            speed: Speech speed multiplier (1.0 = normal)
        
        Returns:
            WAV audio data as bytes
        """
        self.load_tts_model()
        
        if self.tts_model is None:
             raise RuntimeError("TTS model failed to load. Check logs.")

        # Generate audio
        audio_stream = io.BytesIO()
        
        try:
            # Piper generates raw PCM audio
            with wave.open(audio_stream, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(22050)  # Piper default sample rate
                
                # Synthesize (Piper outputs raw PCM)
                audio_bytes = self.tts_model.synthesize(text, length_scale=1.0/speed)
                wav_file.writeframes(audio_bytes)
            
            audio_stream.seek(0)
            return audio_stream.read()
        
        except Exception as e:
            logger.error(f"[TTS] Synthesis failed: {e}")
            raise

    # --- Streaming Support ---
    def create_stream_processor(self):
        """Create a new stream processor instance."""
        self.load_stt_model()
        return StreamProcessor(self.stt_model)

class StreamProcessor:
    """
    Handles streaming audio input with real-time incremental transcription.
    Uses sliding window with quick partial results.
    """
    def __init__(self, model: WhisperModel):
        self.model = model
        self.audio_buffer = bytearray()
        self.sample_rate = 16000
        self.sample_width = 2  # 16-bit
        
        # Process every 0.5 seconds for faster feedback
        self.process_interval = self.sample_rate * self.sample_width * 0.5
        
        # Keep last transcription to avoid duplication
        self.last_text = ""
        self.transcription_count = 0
        
    def add_audio(self, audio_chunk: bytes):
        """Add PCM audio chunk to buffer."""
        self.audio_buffer.extend(audio_chunk)
        
    def process(self) -> dict:
        """
        Process current buffer and return incremental text.
        Returns: { "text": "incremental text...", "is_final": False }
        """
        # Only process if we have enough audio (0.5s minimum)
        if len(self.audio_buffer) < self.process_interval:
            return None
        
        import numpy as np
        
        try:
            # Convert 16-bit PCM to float32 for Whisper
            audio_int16 = np.frombuffer(self.audio_buffer, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            
            # Quick transcription with low beam size for speed
            segments, _ = self.model.transcribe(
                audio_float32, 
                language="en", 
                beam_size=1,  # Faster than default 5
                word_timestamps=False,
                vad_filter=False  # Don't cut off speech aggressively
            )
            
            # Combine all segments
            text_parts = [segment.text for segment in segments]
            full_text = " ".join(text_parts).strip()
            
            # Only return if text changed
            if full_text != self.last_text:
                self.last_text = full_text
                self.transcription_count += 1
                
                return {
                    "text": full_text,
                    "is_final": False
                }
            
            return None
            
        except Exception as e:
            logger.error(f"[Stream] Processing failed: {e}")
            return None
            
    def finish(self) -> dict:
        """Finalize the stream and return final text."""
        if not self.audio_buffer:
            return {"text": self.last_text, "is_final": True}
        
        # Do one final transcription with higher quality
        import numpy as np
        
        try:
            audio_int16 = np.frombuffer(self.audio_buffer, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            
            # Final pass with better quality (beam_size=5)
            segments, _ = self.model.transcribe(
                audio_float32, 
                language="en", 
                beam_size=5,
                word_timestamps=False
            )
            
            text_parts = [segment.text for segment in segments]
            final_text = " ".join(text_parts).strip()
            
            # Clear state
            self.audio_buffer.clear()
            self.last_text = ""
            self.transcription_count = 0
            
            return {
                "text": final_text,
                "is_final": True
            }
            
        except Exception as e:
            logger.error(f"[Stream] Final processing failed: {e}")
            return {"text": self.last_text, "is_final": True}

# Global instance (lazy-loaded)
_voice_service: Optional[VoiceService] = None

def get_voice_service(model_dir: Path, stt_model: str = "base.en", tts_voice: str = "en_US-lessac-medium") -> VoiceService:
    """Get or create the global voice service instance."""
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceService(model_dir, stt_model, tts_voice)
    return _voice_service

if __name__ == "__main__":
    # Test the voice service
    import sys
    logging.basicConfig(level=logging.INFO)
    
    model_dir = Path(__file__).parent / "voice_models"
    service = VoiceService(model_dir)
    
    print("[Test] Loading STT model...")
    service.load_stt_model()
    print("[Test] STT model ready!")
    
    print("[Test] Loading TTS model...")
    service.load_tts_model()
    print("[Test] TTS model ready!")
    
    # Test TTS
    print("[Test] Generating speech...")
    test_text = "Hello! This is Nebula's local voice system. Everything runs on your computer, with complete privacy."
    audio_data = service.synthesize_speech(test_text)
    print(f"[Test] Generated {len(audio_data)} bytes of audio")
    
    # Save test audio
    test_file = model_dir / "test_output.wav"
    with open(test_file, "wb") as f:
        f.write(audio_data)
    print(f"[Test] Saved to: {test_file}")
    
    print("[Test] Voice service is working!")
