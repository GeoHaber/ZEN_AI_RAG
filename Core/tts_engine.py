"""
TTS Engine - Text-to-Speech for Jarvis Voice Mode
Uses edge-tts for high-quality, free speech synthesis
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)

# Try to import edge-tts
try:
    import edge_tts

    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logger.warning("edge-tts not installed. Install with: pip install edge-tts")

# Fallback: pyttsx3 (offline, but robotic)
try:
    import pyttsx3

    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False


class TTSEngine:
    """
    Text-to-Speech engine with multiple backend support.

    Backends (in priority order):
    1. edge-tts (best quality, requires internet)
    2. pyttsx3 (offline, robotic voice)
    """

    def __init__(self, voice: str = "en-US-AriaNeural", rate: str = "+0%"):
        """
        Initialize TTS engine.

        Args:
            voice: Voice ID (edge-tts format, e.g., "en-US-AriaNeural")
            rate: Speech rate (e.g., "+0%", "+20%", "-10%")
        """
        self.voice = voice
        self.rate = rate
        self.backend = self._detect_backend()

        # Initialize pyttsx3 engine if using it
        self.pyttsx3_engine = None
        if self.backend == "pyttsx3":
            self._init_pyttsx3()

    def _detect_backend(self) -> str:
        """Detect which TTS backend to use."""
        if EDGE_TTS_AVAILABLE:
            logger.info("Using edge-tts for TTS")
            return "edge-tts"
        elif PYTTSX3_AVAILABLE:
            logger.info("Using pyttsx3 for TTS (offline mode)")
            return "pyttsx3"
        else:
            logger.error("No TTS backend available")
            return "none"

    def _init_pyttsx3(self):
        """Initialize pyttsx3 engine."""
        try:
            self.pyttsx3_engine = pyttsx3.init()
            # Set properties
            self.pyttsx3_engine.setProperty("rate", 150)  # Speed
            self.pyttsx3_engine.setProperty("volume", 0.9)  # Volume
        except Exception as e:
            logger.error(f"Failed to initialize pyttsx3: {e}")
            self.pyttsx3_engine = None

    async def speak_async(self, text: str, play: bool = True) -> Optional[bytes]:
        """
        Convert text to speech (async version for Streamlit).

        Args:
            text: Text to speak
            play: If True, play the audio immediately

        Returns:
            Audio bytes (MP3 format) if successful, None otherwise
        """
        if self.backend == "edge-tts":
            return await self._speak_edge_tts(text, play)
        elif self.backend == "pyttsx3":
            return await self._speak_pyttsx3(text, play)
        else:
            logger.error("No TTS backend available")
            return None

    def speak(self, text: str, play: bool = True) -> Optional[bytes]:
        """
        Synchronous wrapper for speak_async.

        Args:
            text: Text to speak
            play: If True, play the audio immediately

        Returns:
            Audio bytes if successful, None otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a new task
                return asyncio.create_task(self.speak_async(text, play))
            else:
                return loop.run_until_complete(self.speak_async(text, play))
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None

    async def _speak_edge_tts(self, text: str, play: bool) -> Optional[bytes]:
        """Speak using edge-tts."""
        try:
            # Create communicate object
            communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)

            # Generate audio to temp file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name

            await communicate.save(tmp_path)

            # Read audio bytes
            audio_bytes = Path(tmp_path).read_bytes()

            # Play if requested
            if play:
                await self._play_audio(tmp_path)

            # Cleanup
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception as exc:
                logger.debug("%s", exc)

            return audio_bytes

        except Exception as e:
            logger.error(f"edge-tts error: {e}")
            return None

    async def _speak_pyttsx3(self, text: str, play: bool) -> Optional[bytes]:
        """Speak using pyttsx3 (offline)."""
        if not self.pyttsx3_engine:
            return None

        try:
            # pyttsx3 doesn't return audio bytes easily, so we just play
            if play:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._pyttsx3_say, text)
            return None  # pyttsx3 doesn't provide audio bytes
        except Exception as e:
            logger.error(f"pyttsx3 error: {e}")
            return None

    def _pyttsx3_say(self, text: str):
        """Helper to run pyttsx3 in thread."""
        self.pyttsx3_engine.say(text)
        self.pyttsx3_engine.runAndWait()

    async def _play_audio(self, audio_path: str):
        """Play audio file using system player."""
        try:
            import platform
            import subprocess

            system = platform.system()

            if system == "Windows":
                # Use PowerShell to play audio
                subprocess.Popen(
                    [
                        "powershell",
                        "-c",
                        f"(New-Object Media.SoundPlayer '{audio_path}').PlaySync()",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    shell=False,
                )
            elif system == "Darwin":  # macOS
                subprocess.Popen(["afplay", audio_path], shell=False)
            else:  # Linux
                # Try multiple players
                for player in ["aplay", "paplay", "ffplay"]:
                    try:
                        subprocess.Popen([player, audio_path], shell=False)
                        break
                    except FileNotFoundError:
                        continue
        except Exception as e:
            logger.error(f"Audio playback error: {e}")

    @staticmethod
    async def list_voices() -> List[dict]:
        """List available voices from edge-tts."""
        if not EDGE_TTS_AVAILABLE:
            return []

        try:
            voices = await edge_tts.list_voices()
            return [
                {
                    "name": v["ShortName"],
                    "gender": v.get("Gender", "Unknown"),
                    "locale": v.get("Locale", "Unknown"),
                }
                for v in voices
            ]
        except Exception as e:
            logger.error(f"Failed to list voices: {e}")
            return []


# Convenience function
async def speak(text: str, voice: str = "en-US-AriaNeural", rate: str = "+0%"):
    """
    Quick TTS function.

    Example:
        >>> await speak("Hello, I am Jarvis")
    """
    engine = TTSEngine(voice=voice, rate=rate)
    await engine.speak_async(text, play=True)
