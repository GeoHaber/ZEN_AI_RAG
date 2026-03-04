import json
from typing import Dict
from config_system import config
import voice_service
from utils import safe_print

def file_log(msg):
    """Guaranteed logging to file."""
    try:
        with open("voice_trace.txt", "a", encoding="utf-8") as f:
            f.write(f"{msg}\n")
    except Exception: pass
    safe_print(msg)

class VoiceStreamHandler:

    """
    Handles WebSocket connections for real-time voice streaming.
    Manages client sessions and audio processing.
    """
    def __init__(self):
        self.clients: Dict[object, object] = {} # {websocket: StreamProcessor}
        file_log("[Voice] Stream Handler Initialized")

    async def handle_client(self, websocket):
        """Main WebSocket handler."""
        file_log("="*50)
        file_log(f"⚡ VOICE CLIENT CONNECTED: {getattr(websocket, 'remote_address', 'Unknown')}")
        file_log("="*50)

        processor = None
        client_id = id(websocket)
        file_log(f"[Voice] Client connected: {client_id}")
        
        try:
            # 1. Initialize Processor
            file_log("Initializing StreamProcessor...")
            # Lazy load the service model if haven't already
            service = voice_service.get_voice_service(config.MODEL_DIR)
            processor = service.create_stream_processor()
            self.clients[websocket] = processor
            file_log("StreamProcessor ready.")
            
            await websocket.send(json.dumps({"status": "ready", "msg": "Stream Processor Initialized"}))

            # 2. Loop
            file_log("Entering message loop...")
            async for message in websocket:
                if isinstance(message, str):
                    await self._handle_text_message(websocket, processor, message)
                elif isinstance(message, bytes):
                    file_log(f"Received audio chunk: {len(message)} bytes")
                    await self._handle_audio_chunk(websocket, processor, message)

        except Exception as e:
            file_log(f"[Voice] Connection error {client_id}: {e}")
            await websocket.close()
        finally:
            self._cleanup(websocket)

    async def _handle_text_message(self, websocket, processor, message: str):
        """Handle control messages."""
        try:
            data = json.loads(message)
            cmd = data.get("command")
            
            if cmd == "client_info":
                 file_log(f"CLIENT INFO: {data}")

            if cmd == "stop":
                file_log("Stop command received.")
                # Finalize transcription
                result = processor.finish()
                
                # ALWAYS send final response to close loop
                final_text = result["text"] if result else ""
                file_log(f"Final Result: {final_text}")
                
                await websocket.send(json.dumps({
                    "type": "transcription",
                    "text": final_text,
                    "is_final": True
                }))
            elif cmd == "clear":
                processor.finish() 
                await websocket.send(json.dumps({"status": "cleared"}))
                
        except json.JSONDecodeError:
            pass

    async def _handle_audio_chunk(self, websocket, processor, chunk: bytes):
        """Process binary audio chunk."""
        if not chunk: return
        
        processor.add_audio(chunk)
        
        # Try processing
        result = processor.process()
        if result:
            file_log(f"Partial Result: {result}")
            # We got a partial update or change
            payload = json.dumps({
                "type": "transcription",
                "text": result["text"],
                "is_final": result["is_final"]
            })
            file_log(f">>> SENDING PAYLOAD ({len(payload)} bytes)...")
            await websocket.send(payload)
            file_log("<<< PAYLOAD SENT.")

    def _cleanup(self, websocket):
        if websocket in self.clients:
            del self.clients[websocket]
        file_log(f"[Voice] Client disconnected: {id(websocket)}")
