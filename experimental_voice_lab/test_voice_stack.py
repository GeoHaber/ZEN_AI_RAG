import os
import sys
import time
import subprocess
import requests
import unittest
from pathlib import Path

import json

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
BIN_DIR = PROJECT_ROOT / "bin"
SERVER_EXE = BIN_DIR / "llama-server.exe"
CONFIG_FILE = PROJECT_ROOT / "config.json"

try:
    with open(CONFIG_FILE) as f:
        config = json.load(f)
        MODEL_DIR = Path(config.get("model_dir", "models"))
        BIN_DIR = Path(config.get("bin_dir", "_bin"))
except:
    MODEL_DIR = PROJECT_ROOT / "models"
    BIN_DIR = PROJECT_ROOT / "_bin"

SERVER_EXE = BIN_DIR / "llama-server.exe"
SERVER_SCRIPT = Path(__file__).parent / "start_voice_server.py"

class TestVoiceStack(unittest.TestCase):
    def test_01_environment(self):
        """Verify binaries and models exist."""
        print(f"\n🔍 Checking Server Binary: {SERVER_EXE}")
        self.assertTrue(SERVER_EXE.exists(), "llama-server.exe not found!")
        
        print(f"🔍 Checking Models Registry in: {MODEL_DIR}")
        models = list(MODEL_DIR.glob("*.gguf"))
        if not models:
            print("⚠️ No models found, test will skip launch.")
        self.assertTrue(len(models) > 0, "No .gguf models found!")

    def test_02_server_launch(self):
        """Launch the lightweight server and check health."""
        if not SERVER_SCRIPT.exists():
            self.fail("start_voice_server.py does not exist yet!")

        print("\n🚀 Launching start_voice_server.py...")
        # Launch in background
        proc = subprocess.Popen(
            [sys.executable, str(SERVER_SCRIPT), "--test-mode"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # Wait for startup (max 10s)
            start_time = time.time()
            alive = False
            while time.time() - start_time < 10:
                try:
                    resp = requests.get("http://localhost:8005/health", timeout=1)
                    if resp.status_code == 200:
                        alive = True
                        break
                except:
                    time.sleep(1)
            
            if not alive:
                print("❌ Server failed to respond on port 8005")
                # Print stderr for debugging
                _, stderr = proc.communicate(timeout=1)
                print(f"STDERR: {stderr.decode()}")
                
            self.assertTrue(alive, "Server did not come online on port 8005")
            print("✅ Server is Online!")
            
        finally:
            print("🛑 Killing Server...")
            proc.kill()

if __name__ == '__main__':
    unittest.main()
