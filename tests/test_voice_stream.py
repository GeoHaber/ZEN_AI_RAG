import asyncio
import websockets
import json
import wave
import sys
import os
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_system import config


async def test_voice_streaming():
    """
    Simulates a browser client streaming audio to the backend.
    """
    uri = f"ws://127.0.0.1:{config.voice_port}"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            # 1. Wait for Ready
            msg = await websocket.recv()
            print(f"< {msg}")
            # 2. Generate Synthetic Audio (Sine Wave "Beep")
            # We use a simple 440Hz tone. Whisper won't transcribe it as English text usually,
            # but it validates the pipeline processes audio without crashing.
            # Ideally we'd use a real wav file, but generating one is self-contained.
            print("> Streaming synthetic audio...")
            sample_rate = 16000
            duration = 3  # seconds
            frequency = 440
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            note = np.sin(frequency * t * 2 * np.pi)
            audio = (note * 32767).astype(np.int16).tobytes()

            # Chunk it (0.25s chunks)
            chunk_size = int(sample_rate * 0.25 * 2)  # 2 bytes per sample

            for i in range(0, len(audio), chunk_size):
                chunk = audio[i : i + chunk_size]
                await websocket.send(chunk)
                await asyncio.sleep(0.1)  # Simulate real-time

                # Check for partials (non-blocking recv is tricky in simple loop, so we just send)

            print("> Audio finished. Sending Stop command...")
            await websocket.send(json.dumps({"command": "stop"}))

            # 3. Read Final Result
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                print(f"< {data}")
                if data.get("is_final") or data.get("status") == "cleared":
                    break

            print("✅ Test Passed: Stream completed.")

    except Exception:
        print(f"❌ Test Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(test_voice_streaming())
    except KeyboardInterrupt:
        pass
