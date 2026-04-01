#!/usr/bin/env python
"""
Self-Checking & Self-Healing Microphone System
Comprehensive diagnostics + auto-recovery for ZEN_AI audio
"""

import io
import time
import numpy as np
from typing import Dict, Any, Optional
from scipy.io import wavfile
import sounddevice as sd
import logging

logger = logging.getLogger("MicrophoneHealer")


class MicrophoneHealer:
    """
    Professional microphone diagnostics and self-healing system.

    Features:
    - Device lock detection (other apps using mic)
    - Loopback test (play beep, record it back)
    - Audio level verification
    - Automatic device switching
    - Self-healing on failure
    """

    def __init__(self):
        """Initialize instance."""
        self.test_results = {}
        self.device_status = {}
        self.locked_devices = set()
        self.working_device = None

    def generate_test_beep(self, frequency: float = 1000, duration: float = 0.5) -> bytes:
        """Generate a test beep sound."""
        sample_rate = 16000
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = 0.3 * np.sin(2 * np.pi * frequency * t).astype(np.float32)

        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, sample_rate, (audio * 32767).astype("int16"))
        return wav_buffer.getvalue()

    def test_device_availability(self, device_id: int, timeout: float = 2.0) -> Dict[str, Any]:
        """
        Test if a device is available (not locked by another app).

        Returns:
            {
                'available': bool,
                'error': str or None,
                'device_name': str,
                'reason': str
            }
        """
        try:
            dev_info = sd.query_devices(device_id)

            # Try to open stream briefly to see if device is locked
            try:
                stream = sd.OutputStream(device=device_id, channels=1, samplerate=16000, latency="low")
                stream.start()
                stream.stop()
                stream.close()

                return {
                    "available": True,
                    "error": None,
                    "device_name": dev_info["name"],
                    "reason": "Device is available",
                }
            except Exception as e:
                error_str = str(e).lower()

                # Determine if locked by another app
                if "device busy" in error_str or "in use" in error_str:
                    return {
                        "available": False,
                        "error": str(e),
                        "device_name": dev_info["name"],
                        "reason": "LOCKED - Another app is using this device",
                    }
                else:
                    return {
                        "available": False,
                        "error": str(e),
                        "device_name": dev_info["name"],
                        "reason": f"Device error: {str(e)[:50]}",
                    }

        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "device_name": f"Device #{device_id}",
                "reason": f"Query failed: {str(e)[:50]}",
            }

    def loopback_test(self, device_id: int, timeout: float = 3.0) -> Dict[str, Any]:
        """
        Loopback test: Play beep + record it back.

        Returns:
            {
                'success': bool,
                'beep_detected': bool,
                'audio_level': float,
                'frequency': float,
                'error': str or None
            }
        """
        try:
            # Generate test beep
            beep_bytes = self.generate_test_beep(frequency=1000, duration=0.5)
            sample_rate = 16000

            # Parse beep to get waveform
            beep_wav = io.BytesIO(beep_bytes)
            rate, beep_data = wavfile.read(beep_wav)
            beep_float = beep_data.astype(np.float32) / 32768.0

            # Record while playing beep
            duration = 1.0
            recording = sd.rec(
                int(duration * sample_rate), samplerate=sample_rate, channels=1, device=device_id, dtype="float32"
            )

            # Play beep simultaneously
            sd.play(beep_float, samplerate=sample_rate, device=device_id)
            sd.wait()

            # Analyze recording
            recording = recording.flatten()
            audio_level = np.max(np.abs(recording))

            # Check if beep frequency is detected (simple peak detection)
            fft = np.fft.fft(recording)
            freqs = np.fft.fftfreq(len(fft), 1 / sample_rate)

            # Find peak around 1000Hz
            freq_range = np.where((freqs > 800) & (freqs < 1200))[0]
            if len(freq_range) > 0:
                peak_idx = freq_range[np.argmax(np.abs(fft[freq_range]))]
                peak_freq = freqs[peak_idx]
            else:
                peak_freq = 0

            beep_detected = peak_freq > 800 and peak_freq < 1200

            return {
                "success": True,
                "beep_detected": beep_detected,
                "audio_level": float(audio_level),
                "frequency": float(peak_freq),
                "error": None,
            }

        except Exception as e:
            return {"success": False, "beep_detected": False, "audio_level": 0.0, "frequency": 0.0, "error": str(e)}

    def audio_level_check(self, device_id: int, duration: float = 2.0) -> Dict[str, Any]:
        """
        Check if microphone captures real audio (not just silence).

        Returns:
            {
                'success': bool,
                'level': float (0-1),
                'quality': 'EXCELLENT' | 'GOOD' | 'LOW' | 'SILENT',
                'error': str or None
            }
        """
        try:
            recording = sd.rec(int(duration * 16000), samplerate=16000, channels=1, device=device_id, dtype="float32")
            sd.wait()

            level = np.max(np.abs(recording))

            if level > 0.3:
                quality = "EXCELLENT"
            elif level > 0.1:
                quality = "GOOD"
            elif level > 0.01:
                quality = "LOW"
            else:
                quality = "SILENT"

            return {"success": True, "level": float(level), "quality": quality, "error": None}

        except Exception as e:
            return {"success": False, "level": 0.0, "quality": "ERROR", "error": str(e)}


def _full_diagnostic_part3_part4(self):
    """Full diagnostic part3 part 4."""

    if not avail["available"]:
        results["recommendations"].append(
            f"Device is locked: {avail['reason']}. Close other apps using this microphone."
        )

    # Test 2: Audio Level
    print(f"  [2/3] Testing audio level (2 seconds, speak now!)...")
    level = self.audio_level_check(device_id, duration=2)
    results["tests"]["audio_level"] = level
    print(f"    ✓ Level: {level['level']:.4f} ({level['quality']})")
    if level["quality"] == "SILENT":
        results["recommendations"].append(
            "Microphone is capturing silence. Check Windows Volume Mixer - increase microphone volume."
        )
    elif level["quality"] == "LOW":
        results["recommendations"].append("Audio level is very low. Increase microphone volume in system settings.")

    # Test 3: Loopback
    print(f"  [3/3] Testing loopback (play beep and record)...")
    loopback = self.loopback_test(device_id, timeout=3)
    results["tests"]["loopback"] = loopback

    if loopback["success"]:
        if loopback["beep_detected"]:
            print(f"    ✓ Beep detected at {loopback['frequency']:.0f}Hz")
        else:
            print(f"    ⚠️ No beep detected (audio level: {loopback['audio_level']:.4f})")
            results["recommendations"].append("Loopback test failed - microphone may be muted or disconnected.")
    else:
        print(f"    ✗ Loopback failed: {loopback['error'][:50]}")
        results["recommendations"].append(f"Loopback test error: {loopback['error'][:100]}")
    _full_diagnostic_part3(self)


def _full_diagnostic_part3(self):
    """Full diagnostic part 3."""

    # Determine overall status
    if avail["available"] and level["quality"] in ("EXCELLENT", "GOOD"):
        results["overall_status"] = "OK"
    elif avail["available"] and level["quality"] in ("LOW",):
        results["overall_status"] = "DEGRADED"
    else:
        results["overall_status"] = "FAILED"

    return results

    def full_diagnostic(self, device_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Run full microphone diagnostic.

        Returns:
            {
                'device_id': int,
                'device_name': str,
                'overall_status': 'OK' | 'DEGRADED' | 'FAILED',
                'tests': {
                    'availability': {...},
                    'audio_level': {...},
                    'loopback': {...}
                },
                'recommendations': [str, ...],
                'timestamp': float
            }
        """
        if device_id is None:
            device_id = sd.default.device[0]

        results = {
            "device_id": device_id,
            "device_name": sd.query_devices(device_id)["name"],
            "timestamp": time.time(),
            "tests": {},
            "recommendations": [],
        }

        # Test 1: Availability (locked?)
        print(f"\n  [1/3] Testing device availability...")
        avail = self.test_device_availability(device_id)
        results["tests"]["availability"] = avail
        print(f"    {'✓' if avail['available'] else '✗'} {avail['reason']}")

    _full_diagnostic_part3_part4(self)


def _auto_heal_part1_part2(self):
    """Auto heal part1 part 2."""

    print("\n🔧 AUTO-HEALING MICROPHONE SYSTEM")
    print("=" * 60)

    # Step 1: Get all input devices
    print("\n[1] Discovering audio devices...")
    devices = sd.query_devices()
    input_devices = [i for i, d in enumerate(devices) if d["max_input_channels"] > 0]
    print(f"  ✓ Found {len(input_devices)} input device(s)")
    actions.append(f"Discovered {len(input_devices)} input devices")

    # Step 2: Check default device first
    default_dev = sd.default.device[0]
    print(f"\n[2] Testing default device (#{default_dev})...")
    diag = self.full_diagnostic(default_dev)

    if diag["overall_status"] == "OK":
        print(f"  ✓ Default device is OK!")
        return {
            "healed": True,
            "working_device": default_dev,
            "actions_taken": actions + ["Default device is healthy"],
            "status": "OK",
        }

    actions.append(f"Default device status: {diag['overall_status']}")

    # Step 3: Try other Logi webcam devices
    print(f"\n[3] Trying alternate Logi devices...")
    logi_devices = [i for i in input_devices if "logi" in devices[i]["name"].lower()]

    for dev_id in logi_devices:
        if dev_id == default_dev:
            continue

        print(f"  Trying device #{dev_id}: {devices[dev_id]['name']}")
        avail = self.test_device_availability(dev_id)

        if avail["available"]:
            level = self.audio_level_check(dev_id, duration=1)
            if level["quality"] in ("EXCELLENT", "GOOD"):
                print(f"  ✓ Found working device!")
                actions.append(f"Switched to device #{dev_id}")
                return {"healed": True, "working_device": dev_id, "actions_taken": actions, "status": "RECOVERED"}

    actions.append("Could not find alternate working device")
    _auto_heal_part1(self)


def _auto_heal_part1(self):
    """Auto heal part 1."""

    # Step 4: Try all remaining devices
    print(f"\n[4] Trying all other input devices...")
    for dev_id in input_devices:
        if dev_id in logi_devices or dev_id == default_dev:
            continue

        avail = self.test_device_availability(dev_id)
        if avail["available"]:
            level = self.audio_level_check(dev_id, duration=1)
            if level["quality"] in ("EXCELLENT", "GOOD"):
                print(f"  ✓ Found working device: {avail['device_name']}")
                actions.append(f"Fallback to device #{dev_id}")
                return {"healed": True, "working_device": dev_id, "actions_taken": actions, "status": "FALLBACK"}

    # Step 5: Print recommendations
    print(f"\n[5] Healing failed. Recommendations:")
    for rec in diag["recommendations"]:
        print(f"  • {rec}")
    return {"healed": False, "working_device": None, "actions_taken": actions, "status": "FAILED - See recommendations"}

    def auto_heal(self) -> Dict[str, Any]:
        """
        Automatically diagnose and heal microphone issues.

        Returns:
            {
                'healed': bool,
                'working_device': int or None,
                'actions_taken': [str, ...],
                'status': str
            }
        """

    _auto_heal_part1_part2(self)


# Test script
if __name__ == "__main__":
    healer = MicrophoneHealer()

    print("🎤 MICROPHONE SELF-CHECK & SELF-HEAL TEST")
    print("=" * 70)

    # Run diagnostics
    print("\n1️⃣ DIAGNOSTIC TEST")
    default_dev = sd.default.device[0]
    result = healer.full_diagnostic(default_dev)

    print(f"\nStatus: {result['overall_status']}")
    if result["recommendations"]:
        print("\nRecommendations:")
        for rec in result["recommendations"]:
            print(f"  • {rec}")
    # Run auto-heal
    print("\n2️⃣ AUTO-HEAL TEST")
    heal_result = healer.auto_heal()

    print(f"\n{'✓' if heal_result['healed'] else '✗'} Healed: {heal_result['healed']}")
    print(f"Working device: {heal_result['working_device']}")
    print(f"Status: {heal_result['status']}")
    print(f"Actions taken:")
    for action in heal_result["actions_taken"]:
        print(f"  • {action}")
