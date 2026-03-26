import asyncio
import logging
from zena_mode.handlers.base import BaseZenHandler
from zena_mode.voice_manager import get_voice_manager
from config_system import config

logger = logging.getLogger("ZenAI.Handler.Voice")


class VoiceHandler:
    """Namespace for voice-related request handling."""

    @staticmethod
    def handle_get(handler: BaseZenHandler):
        """Routing for GET requests related to voice."""
        path = handler.path

        # GET /voice/devices - Enumerate microphones
        if path == "/voice/devices":
            try:
                vm = get_voice_manager()
                devices = vm.enumerate_devices()
                result = {
                    "success": True,
                    "devices": [d.to_dict() for d in devices],
                    "default_device": vm.get_default_input_device(),
                }
                handler.send_json_response(200, result)
            except Exception as e:
                logger.error(f"Device enumeration failed: {e}")
                handler.send_json_response(500, {"success": False, "error": str(e)})
            return True

        # GET /voice/status - Get voice system status
        elif path == "/voice/status":
            try:
                vm = get_voice_manager()
                status = vm.get_status()
                handler.send_json_response(200, status)
            except Exception as e:
                logger.error(f"Status check failed: {e}")
                handler.send_json_response(500, {"success": False, "error": str(e)})
            return True

        # GET /voice/lab - Serve voice lab HTML (legacy)
        elif path == "/voice/lab":
            try:
                lab_path = config.BASE_DIR / "static" / "voice_lab.html"
                if lab_path.exists():
                    handler.send_response(200)
                    handler.send_header("Content-Type", "text/html")
                    handler.end_headers()
                    with open(lab_path, "rb") as f:
                        handler.wfile.write(f.read())
                else:
                    handler.send_json_response(404, {"error": "Voice Lab UI missing"})
            except Exception as e:
                handler.send_json_response(500, {"error": str(e)})
            return True

        # GET /api/tts-voices - List available TTS voices (edge-tts neural)
        elif path == "/api/tts-voices":
            try:
                from Core.tts_engine import TTSEngine
                loop = asyncio.new_event_loop()
                try:
                    voices = loop.run_until_complete(TTSEngine.list_voices())
                finally:
                    loop.close()
                result = {
                    "voices": [
                        {"id": v.get("name", ""), "name": v.get("name", ""), "gender": v.get("gender", "Unknown")}
                        for v in voices
                    ]
                }
                handler.send_json_response(200, result)
            except Exception as e:
                logger.error(f"TTS voices listing failed: {e}")
                handler.send_json_response(500, {"error": str(e), "voices": []})
            return True

        return False

    @staticmethod
    def handle_post(handler: BaseZenHandler):
        """Routing for POST requests related to voice."""
        path = handler.path

        # POST /api/test-audio - Play a test tone on the selected speaker
        if path == "/api/test-audio":
            try:
                import sounddevice as sd
                from zena_mode.production_microphone_healer import MicrophoneHealer

                params = handler.parse_json_body()
                device_id = params.get("device_id")
                if device_id is not None:
                    device_id = int(device_id)

                healer = MicrophoneHealer()
                tone_bytes = healer.generate_test_tone(frequency=1000, duration=0.3)

                import io
                from scipy.io import wavfile

                wav_buf = io.BytesIO(tone_bytes)
                rate, audio = wavfile.read(wav_buf)
                audio_float = audio.astype("float32") / 32768.0

                sd.play(audio_float, samplerate=rate, device=device_id)
                sd.wait()
                handler.send_json_response(200, {"status": "ok", "msg": "Test tone played"})
            except Exception as e:
                logger.error(f"test-audio failed: {e}")
                handler.send_json_response(500, {"status": "error", "msg": str(e)})
            return True

        # POST /api/test-loopback - Play tone and listen for it
        elif path == "/api/test-loopback":
            try:
                from zena_mode.production_microphone_healer import MicrophoneHealer

                params = handler.parse_json_body()
                input_id = params.get("input_id")
                output_id = params.get("output_id")
                if input_id is not None:
                    input_id = int(input_id)
                if output_id is not None:
                    output_id = int(output_id)

                device_id = input_id if input_id is not None else (output_id or 0)
                healer = MicrophoneHealer()
                success, confidence, reason = healer.verify_loopback(device_id)
                handler.send_json_response(200, {
                    "status": "ok",
                    "success": success,
                    "magnitude": confidence * 100,
                    "msg": reason,
                })
            except Exception as e:
                logger.error(f"test-loopback failed: {e}")
                handler.send_json_response(500, {"status": "error", "msg": str(e)})
            return True

        # POST /api/record - Record audio and transcribe
        if path == "/api/record":
            try:
                params = handler.parse_json_body()
                device_id = params.get("device_id")
                duration = params.get("duration", 3.0)

                if device_id is not None:
                    device_id = int(device_id)

                # Record audio
                vm = get_voice_manager()
                recording_result = vm.record_audio(duration=duration, device_id=device_id)

                if not recording_result.success:
                    handler.send_json_response(500, {"success": False, "error": recording_result.error})
                    return True

                # Transcribe
                transcribe_result = vm.transcribe(recording_result.audio_data)
                result = {
                    "success": transcribe_result.get("success", False),
                    "text": transcribe_result.get("text", ""),
                    "duration": recording_result.duration,
                    "error": transcribe_result.get("error"),
                }
                handler.send_json_response(200, result)
            except Exception as e:
                logger.error(f"Record endpoint failed: {e}")
                handler.send_json_response(500, {"success": False, "error": str(e)})
            return True

        # POST /voice/transcribe - Transcribe uploaded audio
        elif path == "/voice/transcribe":
            try:
                content_length = int(handler.headers.get("Content-Length", 0))
                audio_data = handler.rfile.read(content_length)

                vm = get_voice_manager()
                result = vm.transcribe(audio_data)
                handler.send_json_response(200, result)
            except Exception as e:
                logger.error(f"Transcribe endpoint failed: {e}")
                handler.send_json_response(500, {"success": False, "error": str(e)})
            return True

        # POST /voice/synthesize - Generate speech from text
        elif path == "/voice/synthesize":
            try:
                params = handler.parse_json_body()
                text = params.get("text", "")

                if not text:
                    handler.send_json_response(400, {"success": False, "error": "Missing 'text' parameter"})
                    return True

                vm = get_voice_manager()
                result = vm.synthesize(text)
                handler.send_json_response(200, result)
            except Exception as e:
                logger.error(f"Synthesize endpoint failed: {e}")
                handler.send_json_response(500, {"success": False, "error": str(e)})
            return True

        # POST /voice/speak - Alias for synthesize (more intuitive name)
        elif path == "/voice/speak":
            try:
                params = handler.parse_json_body()
                text = params.get("text", "")

                if not text:
                    handler.send_json_response(400, {"success": False, "error": "Missing 'text' parameter"})
                    return True

                vm = get_voice_manager()
                result = vm.synthesize(text, use_cache=True)

                # Return just the audio URL for easy HTML5 integration
                handler.send_json_response(
                    200,
                    {
                        "success": result["success"],
                        "audio_url": result.get("audio_url"),
                        "duration": result.get("duration"),
                        "text": text,
                        "error": result.get("error"),
                    },
                )
            except Exception as e:
                logger.error(f"Speak endpoint failed: {e}")
                handler.send_json_response(500, {"success": False, "error": str(e)})
            return True

        return False
