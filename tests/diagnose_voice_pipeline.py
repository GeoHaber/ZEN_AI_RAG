import asyncio
import websockets
import json
import logging
import math
import struct
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VoiceDiagnose")

async def generate_sine_wave(duration_sec=3, frequency=440, sample_rate=16000):
    """Generates a raw PCM 16-bit mono audio buffer (Sine Wave at 440Hz)."""
    num_samples = int(duration_sec * sample_rate)
    audio_data = bytearray()
    
    for i in range(num_samples):
        # Generate sine wave sample
        sample = 32767 * math.sin(2 * math.pi * frequency * i / sample_rate)
        # Pack as little-endian 16-bit signed integer
        audio_data.extend(struct.pack('<h', int(sample)))
        
    return bytes(audio_data)

async def test_backend_direct():
    """Test backend direct."""
    uri = "ws://127.0.0.1:8005"
    logger.info(f"Connecting to Voice Server at {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("✅ Connected to WebSocket.")
            
            # 1. Wait for Ready Signal (optional, based on my server code)
            try:
                msg = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                logger.info(f"Server Greeting: {msg}")
            except asyncio.TimeoutError:
                logger.warning("No greeting received (might be okay depending on protocol).")

            # 2. Generate Synthetic Audio
            logger.info("Generating 3 seconds of synthetic audio (440Hz Sine)...")
            # NOTE: Sine waves are not speech, so transcription might be garbage or empty,
            # BUT the server should at least acknowledge receiving it or log something.
            # Ideally, we'd use a real speech file, but let's test *throughput* first.
            chunk_size = 4096 
            audio_bytes = await generate_sine_wave()
            
            total_chunks = len(audio_bytes) // chunk_size
            logger.info(f"Streaming {len(audio_bytes)} bytes in {total_chunks} chunks...")

            # 3. Stream
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i:i+chunk_size]
                await websocket.send(chunk)
                await asyncio.sleep(0.01) # Simulate real-time streaming
                
                # Check for partial responses immediately?
                # Usually client sends all, server responds async.
            
            logger.info("Stream complete. Sending STOP command...")
            await websocket.send(json.dumps({"command": "stop"}))
            
            # 4. Wait for Final Response
            start_wait = time.time()
            while time.time() - start_wait < 10:
                try:
                    response = await websocket.recv()
                    data = json.loads(response)
                    logger.info(f"Received: {data}")
                    
                    if data.get("is_final") or data.get("type") == "transcription":
                        logger.info("✅ Backend responded with transcription packet!")
                        return True
                        
                except websockets.exceptions.ConnectionClosed:
                    logger.error("Connection closed unexpectedly.")
                    break
                except Exception as e:
                    logger.error(f"Error receiving: {e}")
                    break
            
            logger.error("❌ Timed out waiting for transcription response.")
            return False

    except Exception as e:
        logger.error(f"❌ Connection Failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_backend_direct())
