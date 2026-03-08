# -*- coding: utf-8 -*-
"""
zena_mode/tutorial.py - Interactive Guided Tour for ZenAI
Provides step-by-step UI guidance with robust dialog management.
"""

import asyncio
import logging
from nicegui import ui
from ui.registry import UI_IDS

logger = logging.getLogger("Tutorial")


class UITutorial:
    """Manages the interactive guided tour sequence."""

    def __init__(self, client):
        """Initialize instance."""
        self.client = client
        self.current_step = 0
        self.is_running = False
        self.dialog = None
        self.title_label = None
        self.message_label = None
        self.btn_next = None

        # Define the tour steps
        self.steps = [
            {
                "title": "Welcome to ZenAI! 🚀",
                "message": "Let's take a 1-minute tour of the key features.",
                "element_id": None,
            },
            {
                "title": "The Brain (Chat Hub) 🧠",
                "message": "Type your questions here. RAG searches your local docs first!",
                "element_id": UI_IDS.INPUT_CHAT,
            },
            {
                "title": "Attach & Analyze 📎",
                "message": "Upload PDFs or Images. I'll OCR them instantly.",
                "element_id": UI_IDS.BTN_ATTACH,
            },
            {
                "title": "Voice Intelligence 🎙️",
                "message": "Use the voice button for speech-to-text input.",
                "element_id": UI_IDS.BTN_VOICE,
            },
            {
                "title": "Knowledge Management 📚",
                "message": "Manage RAG sources, switch models, or toggle Swarm mode in the drawer.",
                "element_id": "ui-drawer-btn",
            },
            {
                "title": "Settings ⚙️",
                "message": "Configure language and AI behavior here.",
                "element_id": UI_IDS.BTN_SETTINGS,
            },
            {"title": "Tour Complete! ✨", "message": "You're all set. Ask me anything!", "element_id": None},
        ]

    async def start(self):
        """Begin the tour sequence."""
        if self.is_running:
            return
        self.is_running = True
        self.current_step = 0
        logger.info("[Tutorial] Starting guided tour...")

        try:
            with self.client:
                self._setup_dialog()
                await self._run_step()
        except Exception as e:
            logger.error(f"[Tutorial] Start failed: {e}")
            self.stop()

    def _setup_dialog(self):
        """Creates the persistent dialog structure within the client context."""
        with ui.dialog().props("persistent") as self.dialog, ui.card().classes("w-80 shadow-24 p-4 rounded-xl"):
            self.title_label = ui.label("Tour").classes("text-h6 font-bold text-primary")
            self.message_label = ui.label("Message").classes("text-body2 py-2 text-gray-600 dark:text-gray-300")

            with ui.row().classes("w-full justify-end mt-4 gap-2"):
                ui.button("Skip", on_click=self.stop).props("flat color=grey")
                self.btn_next = ui.button("Next", on_click=self.next_step).props("unelevated color=primary")

    async def next_step(self):
        """Advance to the next step."""
        self.current_step += 1
        if self.current_step < len(self.steps):
            try:
                with self.client:
                    await self._run_step()
            except Exception as e:
                logger.error(f"[Tutorial] Next step failed: {e}")
                self.stop()
        else:
            self.stop()

    def stop(self):
        """End the tour and cleanup."""
        self.is_running = False
        try:
            with self.client:
                self._remove_highlights()
                if self.dialog:
                    self.dialog.close()
                ui.notify("Tutorial completed!", color="positive", icon="check")
        except Exception:
            pass
        logger.info("[Tutorial] Tour ended.")

    async def _run_step(self):
        """Update the dialog and apply visual effects."""
        step = self.steps[self.current_step]

        # Update Labels safely
        if self.title_label:
            self.title_label.text = step["title"]
        if self.message_label:
            self.message_label.text = step["message"]

        # Update Button safely
        if self.btn_next:
            is_last = self.current_step == len(self.steps) - 1
            self.btn_next.text = "Finish" if is_last else "Next"
            self.btn_next.props(f"color={'positive' if is_last else 'primary'}")

        # Ensure dialog is open
        if self.dialog:
            self.dialog.open()

        # Remove previous highlights
        self._remove_highlights()

        # Apply new highlight
        target_id = step.get("element_id")
        if target_id:
            logger.debug(f"[Tutorial] Highlighting {target_id}")
            self._apply_highlight(target_id)

    def _apply_highlight(self, element_id: str):
        """Inject CSS/JS to highlight element."""
        js = f"""
        (function() {{
            const el = document.getElementById('{element_id}');
            if (el) {{
                el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                el.style.boxShadow = '0 0 20px 8px rgba(25, 118, 210, 0.6)';
                el.style.outline = '3px solid #1976d2';
                el.classList.add('zena-tutorial-highlight');
            }}
        }})();
        """
        self.client.run_javascript(js)

    def _remove_highlights(self):
        """Clear highlights."""
        js = """
        document.querySelectorAll('.zena-tutorial-highlight').forEach(el => {
            el.style.boxShadow = '';
            el.style.outline = '';
            el.classList.remove('zena-tutorial-highlight');
        });
        """
        self.client.run_javascript(js)


def start_tutorial(client):
    """Entry point."""
    if not client:
        return
    tut = UITutorial(client)
    asyncio.create_task(tut.start())
