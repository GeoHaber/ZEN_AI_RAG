import json
import logging
import os
from zena_mode.handlers.base import BaseZenHandler
from config_system import config

logger = logging.getLogger("ZenAI.Handler.Voice")

# Optional dependencies for voice
try:
    import sounddevice as sd
    import scipy.io.wavfile as wav
except ImportError:
    sd = wav = None

class VoiceHandler:
    """Namespace for voice-related request handling."""
    
    @staticmethod
    def handle_get(handler: BaseZenHandler):
        """Routing for GET requests related to voice."""
        path = handler.path
        
        if path == '/voice/lab':
            # Serve voice lab HTML
            try:
                lab_path = config.BASE_DIR / "static" / "voice_lab.html"
                if lab_path.exists():
                    handler.send_response(200)
                    handler.send_header('Content-Type', 'text/html')
                    handler.end_headers()
                    with open(lab_path, 'rb') as f:
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
        
        if path == '/voice/transcribe':
            try:
                from voice_service import VoiceService
                content_length = int(handler.headers.get('Content-Length', 0))
                audio_data = handler.rfile.read(content_length)
                
                import io
                vs = VoiceService() # Simple instantiation for now, or use singleton
                result = vs.transcribe_audio(io.BytesIO(audio_data))
                handler.send_json_response(200, result)
            except Exception as e:
                handler.send_json_response(500, {"error": str(e)})
            return True

        elif path == '/api/record':
            try:
                params = handler.parse_json_body()
                device_id = params.get('device_id')
                if device_id is not None: device_id = int(device_id)
                
                if not sd:
                    handler.send_json_response(500, {"error": "sounddevice missing"})
                    return True

                # Record 3 seconds (Standard for brief test)
                duration = 3.0
                sr = 16000
                recording = sd.rec(int(duration * sr), samplerate=sr, channels=1, dtype='int16', device=device_id)
                sd.wait()
                
                import io
                buf = io.BytesIO()
                wav.write(buf, sr, recording)
                buf.seek(0)
                
                from voice_service import VoiceService
                vs = VoiceService()
                result = vs.transcribe_audio(buf)
                handler.send_json_response(200, result)
            except Exception as e:
                handler.send_json_response(500, {"error": str(e)})
            return True
            
        return False
