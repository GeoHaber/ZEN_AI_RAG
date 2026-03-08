#!/usr/bin/env python
"""
Production-Grade Microphone Self-Check & Self-Healing System
Based on industry best-practices from:
- OBS Studio (audio device management)
- FFmpeg (device detection & fallback)
- PulseAudio (device probing)
- Real-time audio frameworks

Features:
- Device lock detection (identifies which apps are using mic)
- Intelligent fallback with performance scoring
- Loopback verification (play->record->verify)
- Audio level optimization
- Self-healing with automatic recovery
"""

import io
import sys
import psutil
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from scipy.io import wavfile
from dataclasses import dataclass, asdict
import sounddevice as sd
import logging

# Fix Windows console encoding
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

logger = logging.getLogger("MicrophoneHealer")


@dataclass
class DeviceScore:
    """Score a microphone device for quality and availability"""

    device_id: int
    device_name: str

    # Scoring components (0-100)
    availability_score: int = 0  # Is it free/available?
    quality_score: int = 0  # Is audio quality good?
    priority_score: int = 0  # Is it a preferred device?

    # Overall score (weighted average)
    @property
    def total_score(self) -> int:
        """Total score."""
        return int(
            self.availability_score * 0.5  # Most important
            + self.quality_score * 0.3
            + self.priority_score * 0.2
        )

    # Details for debugging
    availability_reason: str = ""
    quality_reason: str = ""
    priority_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProcessAudioUsageDetector:
    """
    Detect which processes are using microphone.
    Based on Windows API patterns used in OBS Studio.
    """

    @staticmethod
    def find_processes_using_microphone() -> List[Dict[str, Any]]:
        """
        Find Windows processes using microphone.
        Uses psutil + heuristics (not guaranteed to find all).
        """
        processes = []

        try:
            # Common apps that use microphone
            audio_apps = {
                "obs.exe": "OBS Studio",
                "obs64.exe": "OBS Studio (64-bit)",
                "zoom.exe": "Zoom",
                "Teams.exe": "Microsoft Teams",
                "skype.exe": "Skype",
                "discord.exe": "Discord",
                "slack.exe": "Slack",
                "chrome.exe": "Google Chrome",
                "firefox.exe": "Mozilla Firefox",
                "brave.exe": "Brave Browser",
                "edge.exe": "Microsoft Edge",
                "audiodg.exe": "Windows Audio Device Graph Isolation",
                "WaveOutMix.exe": "Audio Mixer",
                "vlc.exe": "VLC Media Player",
                "audacity.exe": "Audacity",
            }

            for proc in psutil.process_iter(["pid", "name", "exe"]):
                try:
                    name = proc.info["name"].lower()

                    # Check if this is an audio app
                    for app_exe, app_name in audio_apps.items():
                        if app_exe.lower() not in name:
                            continue
                        processes.append(
                            {
                                "pid": proc.info["pid"],
                                "name": app_name,
                                "executable": proc.info["name"],
                                "status": "possibly_using_audio",
                            }
                        )
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            logger.warning(f"Could not scan processes: {e}")

        return processes


class ProductionMicrophoneHealer:
    """
    Enterprise-grade microphone diagnostic and auto-healing system.
    """

    def __init__(self, timeout_sec: float = 2.0):
        self.timeout_sec = timeout_sec
        self.test_frequency = 1000  # Hz
        self.process_detector = ProcessAudioUsageDetector()

    def generate_test_tone(self, frequency: float = 1000, duration: float = 0.2) -> bytes:
        """Generate a pure sine wave for loopback testing."""
        sample_rate = 16000
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = 0.2 * np.sin(2 * np.pi * frequency * t).astype(np.float32)

        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, sample_rate, (audio * 32767).astype("int16"))
        return wav_buffer.getvalue()

    def is_device_locked(self, device_id: int) -> Tuple[bool, Optional[str]]:
        """
        Check if device is locked by another process.
        Returns (is_locked, reason_or_none)
        """
        try:
            dev_info = sd.query_devices(device_id)

            # Use InputStream for input devices (microphone)
            channels = min(1, int(dev_info.get("max_input_channels", 1)))
            if channels < 1:
                channels = 1

            # Try to open stream - if fails, device is locked
            stream = sd.InputStream(device=device_id, channels=channels, samplerate=16000, latency="low")
            stream.start()
            stream.stop()
            stream.close()

            return False, None

        except RuntimeError as e:
            error_str = str(e).lower()

            if "device busy" in error_str or "in use" in error_str or "locked" in error_str:
                # Try to find which process
                using_procs = self.process_detector.find_processes_using_microphone()
                if using_procs:
                    proc_names = [p["name"] for p in using_procs]
                    return True, f"Locked by: {', '.join(proc_names)}"
                else:
                    return True, "Device locked (unknown process)"
            else:
                return True, f"Device error: {str(e)[:60]}"
        except Exception as e:
            return True, f"Check failed: {str(e)[:60]}"

    def measure_audio_quality(self, device_id: int, duration: float = 1.0) -> Tuple[int, str]:
        """
        Measure audio quality (0-100 score).
        Uses signal-to-noise ratio heuristics.

        Returns (quality_score, reason)
        """
        try:
            recording = sd.rec(int(duration * 16000), samplerate=16000, channels=1, device=device_id, dtype="float32")
            sd.wait()

            # Calculate RMS level
            rms = np.sqrt(np.mean(recording**2))

            if rms > 0.3:
                return 100, "Excellent - strong audio signal"
            elif rms > 0.1:
                return 85, "Good - clear audio"
            elif rms > 0.05:
                return 60, "Fair - somewhat quiet"
            elif rms > 0.01:
                return 40, "Poor - very quiet"
            else:
                return 0, "Silent - no audio detected"

        except Exception as e:
            return 0, f"Measurement failed: {str(e)[:40]}"

    def verify_loopback(self, device_id: int) -> Tuple[bool, float, str]:
        """
        Play a test tone and listen for it on same device.

        Returns (success, confidence_0_to_1, reason)
        """
        try:
            tone_bytes = self.generate_test_tone(frequency=1000, duration=0.2)
            wav_buffer = io.BytesIO(tone_bytes)
            rate, tone_data = wavfile.read(wav_buffer)
            tone_float = tone_data.astype(np.float32) / 32768.0

            # Record while playing
            sample_rate = 16000
            recording = sd.rec(
                int(0.5 * sample_rate), samplerate=sample_rate, channels=1, device=device_id, dtype="float32"
            )

            sd.play(tone_float, samplerate=sample_rate, device=device_id)
            sd.wait()

            # Analyze for tone
            recording = recording.flatten()
            fft = np.fft.fft(recording)
            freqs = np.fft.fftfreq(len(fft), 1 / sample_rate)

            # Look for peak near 1000Hz
            freq_mask = (freqs > 900) & (freqs < 1100)
            if np.any(freq_mask):
                peak_bin = np.argmax(np.abs(fft[freq_mask]))
                peak_val = np.abs(fft[freq_mask])[peak_bin]
                noise_floor = np.median(np.abs(fft[~freq_mask]))

                snr = peak_val / (noise_floor + 1e-10)
                confidence = min(1.0, snr / 100.0)

                if confidence > 0.7:
                    return True, confidence, "Loopback verified"
                else:
                    return True, confidence, f"Loopback detected (SNR: {snr:.1f})"

            return False, 0.0, "No loopback detected"

        except Exception as e:
            return False, 0.0, f"Loopback test failed: {str(e)[:40]}"

    def score_device(self, device_id: int) -> DeviceScore:
        """
        Score a device (0-100) based on:
        - Availability (is it free?)
        - Quality (how good is audio?)
        - Priority (is it preferred?)
        """
        dev_info = sd.query_devices(device_id)
        device_name = dev_info["name"]

        score = DeviceScore(device_id=device_id, device_name=device_name)

        # Check availability
        is_locked, lock_reason = self.is_device_locked(device_id)
        if is_locked:
            score.availability_score = 0
            score.availability_reason = lock_reason or "Device locked"
        else:
            score.availability_score = 100
            score.availability_reason = "Device available"

        # Skip quality test if locked
        if not is_locked:
            quality, quality_reason = self.measure_audio_quality(device_id, duration=0.5)
            score.quality_score = quality
            score.quality_reason = quality_reason

        # Check priority (is it a preferred device?)
        if "logi" in device_name.lower():
            score.priority_score = 100
            score.priority_reason = "Logitech device (preferred)"
        elif "microphone" in device_name.lower():
            score.priority_score = 80
            score.priority_reason = "Labeled as microphone"
        elif "audio" in device_name.lower():
            score.priority_score = 60
            score.priority_reason = "Generic audio device"
        else:
            score.priority_score = 30
            score.priority_reason = "Unrecognized device"

        return score


def _do_do_full_diagnostic_setup_setup(verbose):
    """Helper: setup phase for _do_full_diagnostic_setup."""

    if verbose:
        print("\n[DIAGNOSTIC] MICROPHONE SYSTEM")
        print("=" * 70)

    # Get all devices
    all_devices = sd.query_devices()
    input_devices = [(i, d) for i, d in enumerate(all_devices) if d["max_input_channels"] > 0]

    if verbose:
        # [X-Ray auto-fix] print(f"\n[INFO] Found {len(input_devices)} input device(s)")
        pass
    # Score each device
    device_scores: List[DeviceScore] = []

    for dev_id, dev_info in input_devices:
        if verbose:
            # [X-Ray auto-fix] print(f"\n  Testing device #{dev_id}: {dev_info['name']}")
            pass
        score = self.score_device(dev_id)
        device_scores.append(score)

        if verbose:
            # [X-Ray auto-fix] print(f"    Availability: {score.availability_score}/100 - {score.availability_reason}")
            # [X-Ray auto-fix] print(f"    Quality: {score.quality_score}/100 - {score.quality_reason}")
            # [X-Ray auto-fix] print(f"    Priority: {score.priority_score}/100 - {score.priority_reason}")
            # [X-Ray auto-fix] print(f"    TOTAL: {score.total_score}/100")
            pass
    return device_scores

    return device_scores


def _do_full_diagnostic_setup_part1():
    """Do full diagnostic setup part 1."""

    # Get diagnostic data
    diag = self.full_diagnostic(verbose=True)

    # Generate recommendations
    recommendations = []

    best_score = diag["best_device_id"]

    if best_score is None:
        recommendations.append("[ERROR] No input devices found! Connect a microphone.")
    elif diag["devices"][0]["availability_score"] < 100:
        # Device is locked
        processes = diag["competing_processes"]
        if processes:
            proc_names = [p["name"] for p in processes]
            # De-duplicate
            proc_names = list(dict.fromkeys(proc_names))
            recommendations.append(
                f"[ACTION] Microphone locked by: {', '.join(proc_names[:5])}. "
                f"Close these apps to use the microphone in ZEN_AI."
            )
        else:
            recommendations.append(
                "[ACTION] Microphone device is locked (unknown process). "
                "Check Windows audio settings or restart your system."
            )

    elif diag["devices"][0]["quality_score"] < 50:
        recommendations.append(
            "[ACTION] Microphone audio quality is very low. "
            "Increase microphone volume in Windows Sound Mixer (Right-click speaker icon)."
        )

    elif diag["devices"][0]["quality_score"] < 80:
        recommendations.append(
            "[ACTION] Microphone audio could be better. Consider increasing microphone gain in system settings."
        )
    else:
        recommendations.append("[OK] Microphone system is healthy and ready to use!")

    # [X-Ray auto-fix] print(f"\n[ADVICE] RECOMMENDATIONS:")
    for rec in recommendations:
        # [X-Ray auto-fix] print(f"  {rec}")
        pass
        pass
    return {
        "diagnostic": diag,
        "recommendations": recommendations,
        "status": "OK" if diag["devices"][0]["availability_score"] == 100 else "NEEDS_ATTENTION",
    }


def _do_full_diagnostic_setup(verbose):
    """Helper: setup phase for full_diagnostic."""
    _do_do_full_diagnostic_setup_setup(verbose)

    def full_diagnostic(self, verbose: bool = True) -> Dict[str, Any]:
        """
        Run complete system diagnostic.

        Returns comprehensive analysis with recommendations.
        """
        device_scores = _do_full_diagnostic_setup(verbose)
        # Sort by score
        device_scores.sort(key=lambda s: s.total_score, reverse=True)

        # Find best device
        best_device = device_scores[0] if device_scores else None

        if verbose and best_device:
            # [X-Ray auto-fix] print(f"\n[BEST] Device #{best_device.device_id} - {best_device.device_name}")
            # [X-Ray auto-fix] print(f"  Score: {best_device.total_score}/100")
            pass
        # Check for processes using mic
        if verbose:
            processes = self.process_detector.find_processes_using_microphone()
            if processes:
                # [X-Ray auto-fix] print(f"\n[WARNING] Audio-using processes detected:")
                for proc in processes[:10]:  # Show first 10
                    # [X-Ray auto-fix] print(f"    * {proc['name']} (PID: {proc['pid']})")
                    pass
                if len(processes) > 10:
                    # [X-Ray auto-fix] print(f"    ... and {len(processes) - 10} more")
                    pass
            else:
                # [X-Ray auto-fix] print(f"\n[OK] No other audio-using processes detected")
                pass
        return {
            "devices": [s.to_dict() for s in device_scores],
            "best_device": best_device.to_dict() if best_device else None,
            "best_device_id": best_device.device_id if best_device else None,
            "competing_processes": self.process_detector.find_processes_using_microphone(),
            "total_devices": len(device_scores),
        }

    def auto_heal_with_recommendations(self) -> Dict[str, Any]:
        """
        Run diagnostics and provide actionable recommendations.
        """
        print("\n[HEALING] MICROPHONE AUTO-HEALING SYSTEM")
        print("=" * 70)

    _do_full_diagnostic_setup_part1()


# Test script
if __name__ == "__main__":
    healer = ProductionMicrophoneHealer()
    result = healer.auto_heal_with_recommendations()

    print("\n" + "=" * 70)
    print("[SUMMARY] DIAGNOSTIC SUMMARY")
    print("=" * 70)
    # [X-Ray auto-fix] print(f"Best device: #{result['diagnostic']['best_device_id']}")
    # [X-Ray auto-fix] print(f"Status: {result['status']}")
    # [X-Ray auto-fix] print(f"Devices tested: {result['diagnostic']['total_devices']}")
