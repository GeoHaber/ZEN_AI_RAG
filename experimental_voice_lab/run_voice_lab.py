
import subprocess
import time
import sys
import webbrowser
from pathlib import Path

import shutil

# Paths
current_dir = Path(__file__).parent
server_script = current_dir / "start_voice_server.py"
ui_script = current_dir / "quen_emotional_chat_complete.py"
generated_dir = current_dir / "generated"
debug_wav = current_dir / "debug_input.wav"

def cleanup_temp_files():
    print("🧹 Cleaning up temporary audio files...")
    count = 0
    # Clean generated MP3s
    if generated_dir.exists():
        for file in generated_dir.glob("*.mp3"):
            try:
                file.unlink()
                count += 1
            except: pass
            
    # Clean debug WAV
    if debug_wav.exists():
        try:
            debug_wav.unlink()
            print(f"   - Removed {debug_wav.name}")
        except: pass
        
    print(f"   - Removed {count} cached speech files.")

def main():
    cleanup_temp_files()
    print("🚀 ONE-CLICK VOICE LAB LAUNCHER")
    print("================================")
    
    # 1. Start Backend (Restored)
    print("Starting Backend (The Ant)...")
    backend = subprocess.Popen([sys.executable, str(server_script)])
    
    # Wait for backend to warm up slightly
    time.sleep(2)

    # 2. Start Frontend
    print("Starting Frontend (Simple UI)...")
    frontend = subprocess.Popen([sys.executable, str(ui_script)])
    
    print("\n✅ System Running!")
    print("Backend: http://localhost:8005")
    print("Frontend: http://localhost:8081")
    print("\nPress Ctrl+C to stop everything.")
    
    # 3. Auto-Open Browser (Best Effort)
    try:
        time.sleep(2)
        webbrowser.open("http://localhost:8081")
    except:
        pass

    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
        backend.terminate()
        frontend.terminate()

if __name__ == "__main__":
    main()
