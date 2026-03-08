import asyncio
import websockets
import json
import math
import struct
import time
import logging

# Configure logging to console
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("VoiceInjector")


async def generate_sine_wave_pcm(duration_sec=3, frequency=440, sample_rate=16000):
    """Generates synthetic Raw PCM 16-bit Mono Audio (Sine Wave)."""
    num_samples = int(duration_sec * sample_rate)
    audio_data = bytearray()
    for i in range(num_samples):
        sample = 32767 * math.sin(2 * math.pi * frequency * i / sample_rate)
        audio_data.extend(struct.pack("<h", int(sample)))
    return bytes(audio_data)


async def inject_voice():
    """Inject voice."""
    uri = "ws://127.0.0.1:8005"
    logger.info(f"💉 Voice Injection Test Target: {uri}")

    try:
        async with websockets.connect(uri) as websocket:
            logger.info("✅ Connection Established (Port 8005 OPEN)")

            # Handshake (Protocol 2.0)
            await websocket.send(
                json.dumps({"command": "client_info", "device": "SYNTHETIC_INJECTOR", "input_rate": 16000})
            )

            # Generate Audio
            logger.info("🔊 Generating 3s Synthetic Audio (Sine Wave)...")
            pcm_data = await generate_sine_wave_pcm()
            chunk_size = 4096

            # Stream
            logger.info("🌊 Streaming Audio...")
            start_time = time.time()
            for i in range(0, len(pcm_data), chunk_size):
                chunk = pcm_data[i : i + chunk_size]
                await websocket.send(chunk)
                await asyncio.sleep(0.01)  # Simulate real-time

            # Stop
            logger.info("🛑 Audio Sent. Sending STOP command...")
            await websocket.send(json.dumps({"command": "stop"}))

            # Listen for Response
            logger.info("👂 Listening for Transcription...")
            while time.time() - start_time < 10:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    logger.info(f"📩 RX: {data}")

                    if data.get("text"):
                        logger.info(f"✅ SUCCESS: Received text '{data['text']}'")
                        return True
                    if data.get("is_final"):
                        logger.info("✅ SUCCESS: Received Final Signal (Even if text is empty)")
                        return True

                except asyncio.TimeoutError:
                    logger.error("❌ TIMEOUT: waiting for response")
                    break
                except websockets.exceptions.ConnectionClosed:
                    logger.error("❌ DISCONNECTED")
                    break

    except Exception as e:
        logger.error(f"❌ CONNECTION FAILED: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(inject_voice())
