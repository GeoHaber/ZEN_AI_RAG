"""
rag_rat_launcher.py — RAG_RAT Windows Launcher

When frozen by PyInstaller this becomes rag_rat.exe.
It:
  1. Resolves the app root (works both frozen and from source)
  2. Starts streamlit run app_new.py in a subprocess
  3. Waits for the server to be ready (polls /healthz)
  4. Opens the browser to http://localhost:8501
  5. Shows a system-tray icon; right-click → Quit kills everything
"""

import os
import sys
import time
import subprocess
import threading
import webbrowser
import socket
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rag_rat_launcher")

# ── Port ──────────────────────────────────────────────────────────────────────
PORT = 8501
URL = f"http://localhost:{PORT}"

# ── Resolve app root ──────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    # Running inside PyInstaller bundle
    APP_ROOT = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    APP_ROOT = Path(__file__).parent

APP_SCRIPT = APP_ROOT / "app_new.py"

# ── Streamlit binary ──────────────────────────────────────────────────────────
# When frozen, streamlit is bundled as a module; we call it via python -m
if getattr(sys, "frozen", False):
    PYTHON_EXE = Path(sys.executable)
    STREAMLIT_CMD = [str(PYTHON_EXE), "-m", "streamlit"]
else:
    import shutil

    _st = shutil.which("streamlit")
    STREAMLIT_CMD = [_st] if _st else [sys.executable, "-m", "streamlit"]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _port_open(port: int) -> bool:
    """Return True if something is listening on localhost:port."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def _wait_for_server(port: int, timeout: float = 120.0) -> bool:
    """Poll until the server is up or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _port_open(port):
            return True
        time.sleep(0.5)
    return False


# ── System tray ───────────────────────────────────────────────────────────────


def _make_icon_image():
    """Create a simple 64×64 tray icon (blue circle with 🔬 text)."""
    try:
        from PIL import Image, ImageDraw

        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([4, 4, 60, 60], fill=(59, 130, 246, 255))  # blue
        draw.text((18, 18), "R", fill="white")
        return img
    except Exception:
        # Fallback: plain blue square
        try:
            from PIL import Image

            img = Image.new("RGB", (64, 64), (59, 130, 246))
            return img
        except Exception:
            return None


def _run_tray(proc: subprocess.Popen):
    """Run the system-tray icon (blocks until Quit is chosen)."""
    try:
        import pystray
        from PIL import Image  # noqa: F401

        icon_img = _make_icon_image()
        if icon_img is None:
            log.warning("Could not create tray icon image — skipping tray")
            return

        def on_open(_icon, _item):
            webbrowser.open(URL)

        def on_quit(_icon, _item):
            log.info("Quit requested — stopping RAG_RAT…")
            _icon.stop()
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
            os._exit(0)

        menu = pystray.Menu(
            pystray.MenuItem("Open RAG_RAT", on_open, default=True),
            pystray.MenuItem("Quit", on_quit),
        )
        icon = pystray.Icon("RAG_RAT", icon_img, "RAG_RAT Pro", menu)
        log.info("System tray icon running — right-click to quit")
        icon.run()

    except ImportError:
        log.warning("pystray/PIL not available — no tray icon; press Ctrl+C to stop")
        try:
            proc.wait()
        except KeyboardInterrupt:
            proc.terminate()


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    log.info("=" * 60)
    log.info("  RAG_RAT Pro — Starting…")
    log.info(f"  App root : {APP_ROOT}")
    log.info(f"  Script   : {APP_SCRIPT}")
    log.info(f"  URL      : {URL}")
    log.info("=" * 60)

    if not APP_SCRIPT.exists():
        log.error(f"app_new.py not found at {APP_SCRIPT}")
        input("Press Enter to exit…")
        sys.exit(1)

    # Build streamlit command
    cmd = STREAMLIT_CMD + [
        "run",
        str(APP_SCRIPT),
        "--server.port",
        str(PORT),
        "--server.headless",
        "true",
        "--server.enableCORS",
        "false",
        "--server.enableXsrfProtection",
        "false",
        "--browser.gatherUsageStats",
        "false",
    ]
    log.info(f"Launching: {' '.join(cmd)}")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(APP_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

    proc = subprocess.Popen(
        cmd,
        cwd=str(APP_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        shell=False,
    )

    # Stream streamlit logs to our log
    def _stream_logs():
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                log.info(f"[streamlit] {line}")

    threading.Thread(target=_stream_logs, daemon=True).start()

    # Wait for server
    log.info(f"Waiting for server on port {PORT}…")
    ready = _wait_for_server(PORT, timeout=120)
    if ready:
        log.info("Server ready — opening browser")
        webbrowser.open(URL)
    else:
        log.warning("Server did not start in 120s — opening browser anyway")
        webbrowser.open(URL)

    # System tray (blocks until Quit)
    _run_tray(proc)


if __name__ == "__main__":
    main()
