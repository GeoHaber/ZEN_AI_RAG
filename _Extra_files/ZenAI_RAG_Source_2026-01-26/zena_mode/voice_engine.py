# -*- coding: utf-8 -*-
"""
voice_engine.py - Emotional Audio Engine using Qwen Native Capabilities
"""
import logging
import asyncio
import os
from pathlib import Path

logger = logging.getLogger("VoiceEngine")

class VoiceEngine:
    """
    Handles emotional speech generation using Qwen Audio models.
    """
    def __init__(self, output_dir: str = "generated_audio"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.enabled = True
        logger.info("[VoiceEngine] Initialized Qwen Native Audio Strategy")

    async def speak(self, text: str, emotion: str = "Neutral") -> str:
        """
        Generate speech file for the given text and emotion.
        Returns the path to the generated file or None if failed.
        """
        logger.info(f"[VoiceEngine] Request: '{text[:30]}...' ({emotion})")
        
        # TODO: Connect to actual backend inference here
        # For now, we simulate the output file creation as we did in the prototype
        
        try:
            filename = f"speech_{emotion.lower()}_{int(asyncio.get_event_loop().time())}.wav"
            filepath = self.output_dir / filename
            
            # Simulate generation delay
            await asyncio.sleep(1.0)
            
            # Create dummy file for UI verification
            self._create_dummy_wav(filepath)
            
            logger.info(f"[VoiceEngine] Generated: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"[VoiceEngine] Generation failed: {e}")
            return None

    def _create_dummy_wav(self, filepath):
        """Create a valid WAV file for testing UI playback."""
        try:
            import scipy.io.wavfile as wav
            import numpy as np
            
            sample_rate = 24000
            duration = 1.0 
            t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
            audio_data = 0.5 * np.sin(2 * np.pi * 440 * t)
            
            wav.write(filepath, sample_rate, (audio_data * 32767).astype(np.int16))
        except ImportError:
            with open(filepath, 'wb') as f:
                f.write(b'RIFF....WAVEfmt ....data....') # minimal stub

def get_voice_engine():
    return VoiceEngine()
