import threading
import logging
import asyncio
import sys
import subprocess
import os
import time
from nicegui import ui
from config_system import config
from utils import is_port_active
from zena_mode.gateway_telegram import run_gateway as run_telegram_gateway
from zena_mode.gateway_whatsapp import run_whatsapp_gateway
from zena_mode.auto_updater import check_for_updates, get_local_version, ModelScout

logger = logging.getLogger("ZenAI.Background")


def start_backend_server():
    """Start the backend orchestrator if it's not already running."""
    # Prevent infinite recursion: If this Zena instance was launched BY the backend (via ZENA_SKIP_PRUNE),
    # we shouldn't try to launch it again unless checking strictly by port.

    mgmt_port = config.mgmt_port
    if is_port_active(mgmt_port):
        logger.info(f"[Background] Backend Hub already active on port {mgmt_port}")
        return

    logger.info(f"[Background] Starting Backend Orchestrator on port {mgmt_port}...")

    # Run server.py as a separate process
    # We pass --no-ui to prevent the server from trying to launch a *second* UI
    cmd = [sys.executable, "-m", "zena_mode.server", "--no-ui", "--guard-bypass"]

    # If we are in mock mode, we might want to signal that to the server (if it supports it)
    # For now, we just run the standard server.

    try:
        subprocess.Popen(
            cmd,
            cwd=str(config.BASE_DIR),
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
            shell=False,
        )
        logger.info("[Background] Backend launch command issued.")

        # Give it a second to bind
        time.sleep(2)
        if not is_port_active(mgmt_port):
            logger.warning("[Background] Backend port still closed after simple launch.")

    except Exception as e:
        logger.error(f"[Background] Failed to launch backend: {e}")


def start_background_gateways():
    """Launch backend services and messaging gateways."""

    # 1. Ensure Backend API (Orchestrator) is running
    # This is critical for Council, Voice, and System features that use the API
    if config.system.auto_start_backend:
        threading.Thread(target=start_backend_server, daemon=True, name="BackendLauncher").start()

    # 2. Gateways
    zena_config = config.get("zena_mode", {})
    if zena_config.get("telegram_token"):
        threading.Thread(target=run_telegram_gateway, daemon=True, name="TelegramBot").start()

    if zena_config.get("whatsapp_whitelist"):
        threading.Thread(target=run_whatsapp_gateway, daemon=True, name="WhatsAppBot").start()


async def run_system_checks():
    """Perform background auto-update and model scout checks."""
    zena_config = config.get("zena_mode", {})
    if zena_config.get("auto_update_enabled", True):
        local_tag = await get_local_version()
        update_info = check_for_updates(current_tag=local_tag)
        if update_info:
            ui.notify(f"💎 Shiny new update available: {update_info['tag']}!", color="info", position="bottom-right")

        # Scouting for "Best in Class" models
        scout = ModelScout()
        coding_models = scout.find_shiny_models("coding")
        if coding_models:
            logger.info(f"[ModelScout] Found {len(coding_models)} shiny models on HF.")
