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

        return False

    @staticmethod
    def handle_post(handler: BaseZenHandler):
        """Routing for POST requests related to voice."""
        path = handler.path

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
