#!/usr/bin/env python
"""
Injectable Voice Handler for ZEN_AI_RAG UI
Allows injecting synthetic audio for testing without microphone
"""

import numpy as np
import io
from scipy.io import wavfile
from typing import Optional, Dict, Any
from zena_mode.voice_manager import VoiceManager, RecordingResult


class InjectableVoiceManager(VoiceManager):
    """
    VoiceManager with audio injection capability for testing.
    Can synthesize audio or use pre-recorded audio for testing without microphone.
    """

    def __init__(self, *args, **kwargs):
        """Initialize instance."""
        super().__init__(*args, **kwargs)
        self.inject_audio: Optional[bytes] = None
        self.inject_enabled = False
        self.last_injection = None

    def generate_sine_wave(self, frequency: float = 1000, duration: float = 2.0, amplitude: float = 0.3) -> bytes:
        """
        Generate a sine wave for testing.

        Args:
            frequency: Frequency in Hz (default: 1000)
            duration: Duration in seconds (default: 2.0)
            amplitude: Amplitude 0-1 (default: 0.3)

        Returns:
            WAV bytes
        """
        sample_rate = 16000
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_data = amplitude * np.sin(2 * np.pi * frequency * t).astype(np.float32)

        # Convert to WAV bytes
        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, sample_rate, (audio_data * 32767).astype("int16"))
        return wav_buffer.getvalue()

    def generate_white_noise(self, duration: float = 2.0, amplitude: float = 0.1) -> bytes:
        """
        Generate white noise for testing.

        Args:
            duration: Duration in seconds
            amplitude: Amplitude 0-1

        Returns:
            WAV bytes
        """
        sample_rate = 16000
        samples = int(sample_rate * duration)
        audio_data = amplitude * np.random.normal(0, 1, samples).astype(np.float32)

        # Clip to prevent clipping
        audio_data = np.clip(audio_data, -1, 1)

        # Convert to WAV bytes
        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, sample_rate, (audio_data * 32767).astype("int16"))
        return wav_buffer.getvalue()

    def generate_voice_like_audio(self, duration: float = 2.0) -> bytes:
        """
        Generate audio that mimics voice (mix of frequencies).

        Args:
            duration: Duration in seconds

        Returns:
            WAV bytes
        """
        sample_rate = 16000
        t = np.linspace(0, duration, int(sample_rate * duration))

        # Mix of frequencies to sound voice-like
        # Fundamental around 150Hz, with harmonics
        audio_data = (
            0.3 * np.sin(2 * np.pi * 150 * t)  # Fundamental
            + 0.2 * np.sin(2 * np.pi * 300 * t)  # 2nd harmonic
            + 0.1 * np.sin(2 * np.pi * 600 * t)  # 4th harmonic
            + 0.05 * np.random.normal(0, 1, len(t))  # Some noise
        ).astype(np.float32)

        # Normalize
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            audio_data = audio_data / max_val * 0.3

        # Convert to WAV bytes
        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, sample_rate, (audio_data * 32767).astype("int16"))
        return wav_buffer.getvalue()

    def record_audio(
        self,
        duration: float = 3.0,
        device_id=None,
        sample_rate: int = 16000,
        channels: int = 1,
        auto_fallback: bool = True,
    ) -> RecordingResult:
        """
        Record audio, with injection support for testing.

        If inject_enabled=True and inject_audio is set, returns injected audio
        instead of recording from microphone.

        Args:
            duration: Recording duration in seconds
            device_id: Microphone device ID (ignored if injecting)
            sample_rate: Sample rate in Hz
            channels: Number of channels
            auto_fallback: Try alternate devices if primary fails

        Returns:
            RecordingResult with audio data
        """
        # Use injected audio if enabled
        if self.inject_enabled and self.inject_audio:
            self.last_injection = {
                "type": "custom",
                "size": len(self.inject_audio),
                "duration": duration,
                "sample_rate": sample_rate,
            }
            return RecordingResult(
                success=True, audio_data=self.inject_audio, duration=duration, sample_rate=sample_rate
            )

        # Otherwise use parent class implementation (real microphone)
        return super().record_audio(duration, device_id, sample_rate, channels, auto_fallback)

    def enable_injection(self, audio_type: str = "sine") -> None:
        """
        Enable audio injection with generated audio.

        Args:
            audio_type: 'sine' (1kHz), 'noise', or 'voice'
        """
        if audio_type == "sine":
            self.inject_audio = self.generate_sine_wave(frequency=1000, duration=2.0)
            label = "Sine Wave (1kHz)"
        elif audio_type == "noise":
            self.inject_audio = self.generate_white_noise(duration=2.0)
            label = "White Noise"
        elif audio_type == "voice":
            self.inject_audio = self.generate_voice_like_audio(duration=2.0)
            label = "Voice-like"
        else:
            raise ValueError(f"Unknown audio type: {audio_type}")

        self.inject_enabled = True
        self.last_injection = {"type": audio_type, "label": label}

    def disable_injection(self) -> None:
        """Disable audio injection and use real microphone."""
        self.inject_enabled = False
        self.inject_audio = None

    def get_injection_status(self) -> Dict[str, Any]:
        """Get current injection status."""
        return {
            "enabled": self.inject_enabled,
            "has_audio": self.inject_audio is not None,
            "last_injection": self.last_injection,
        }


# Example usage functions for UI integration
def create_audio_test_panel(ui, voice_manager: InjectableVoiceManager):
    """
    Create a test panel for audio injection in the UI.

    Args:
        ui: NiceGUI ui module
        voice_manager: InjectableVoiceManager instance
    """
    with ui.card().classes("gap-2"):
        ui.label("🔧 Audio Injection (Testing)").classes("font-bold")

        with ui.row().classes("gap-2"):

            async def use_sine():
                voice_manager.enable_injection("sine")
                ui.notify("Using synthetic sine wave (1kHz)", type="info")

            async def use_noise():
                voice_manager.enable_injection("noise")
                ui.notify("Using white noise", type="info")

            async def use_voice():
                voice_manager.enable_injection("voice")
                ui.notify("Using voice-like audio", type="info")

            async def disable():
                voice_manager.disable_injection()
                ui.notify("Injection disabled - using real microphone", type="info")

            ui.button("📡 Sine Wave", on_click=use_sine).classes("text-sm")
            ui.button("🌊 Noise", on_click=use_noise).classes("text-sm")
            ui.button("🗣️ Voice", on_click=use_voice).classes("text-sm")
            ui.button("❌ Real Mic", on_click=disable).classes("text-sm")

        # Status display
        status_label = ui.label("Status: Ready")

        async def update_status():
            """Update status."""
            status = voice_manager.get_injection_status()
            if status["enabled"]:
                mode = status["last_injection"].get("label", "Injected")
                status_label.text = f"✓ Injection ON ({mode})"
                status_label.classes("text-green-600", remove="text-gray-600")
            else:
                status_label.text = "⚪ Using real microphone"
                status_label.classes("text-gray-600", remove="text-green-600")

        ui.timer(0.5, update_status)


# Example: Minimal integration
"""
from nicegui import ui
from ui.injectable_voice import InjectableVoiceManager, create_audio_test_panel

@ui.page('/')
async def main():
    voice_manager = InjectableVoiceManager()
    
    # Add test panel (only in debug mode)
    if '--debug' in sys.argv:
        create_audio_test_panel(ui, voice_manager)
    
    # Rest of UI code...
    # When recording: audio = voice_manager.record_audio()
    # Will use injected audio if enabled, real mic otherwise!

ui.run()
"""
