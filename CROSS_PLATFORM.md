
# 🍎 Cross-Platform & Mobile Guide

## 📱 Mobile Access (iPhone/Android)
To access ZenAI from your phone:

1.  Open `config.json` and set `"network_access": true`.
2.  Restart ZenAI (`python zena.py`).
3.  Look for the message:
    > 📱 Mobile Access Enabled! Connect via: http://192.168.1.X:8080
4.  Type that address into your phone's browser.
    *   **Note**: Your phone and PC must be on the **same Wi-Fi**.

## 🍏 macOS Installation (Apple Silicon)

ZenAI runs great on M1/M2/M3 chips, but needs a specific install command for GPU acceleration (Metal).

1.  **Install Python 3.10+** (if not installed).
2.  **Clone/Unzip** ZenAI.
3.  **Install Dependencies with Metal Support**:
    ```bash
    # Uninstall generic version first
    pip uninstall llama-cpp-python -y
    
    # Reinstall with Metal acceleration
    CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python --no-cache-dir --force-reinstall --upgrade
    
    # Install other deps
    pip install -r requirements.txt
    ```
4.  **Run**:
    ```bash
    python zena.py
    ```

### Troubleshooting macOS
- **Microphone**: If voice fails, install `portaudio`:
  `brew install portaudio`
- **TTS**: If voice output is silent, ensure your system volume is up (`pyttsx3` uses the native customized system voice).
