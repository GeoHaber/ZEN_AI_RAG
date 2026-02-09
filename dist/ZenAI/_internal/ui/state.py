import asyncio
import logging
from nicegui import ui

logger = logging.getLogger("ZenAI.UI.State")

class UIState:
    """Container for per-client UI element references."""
    def __init__(self):
        self.chat_log = None
        self.scroll_container = None
        self.status_text = None
        self.attachment_preview = None
        self.user_input = None
        self.is_valid = True  # Track if client is still connected
        self.session_id = None  # Unique session ID for conversation memory
        self.cancellation_event = asyncio.Event()  # For cancelling streaming
    
    def safe_update(self, element):
        """Safely update a UI element, handling disconnected clients."""
        if not self.is_valid:
            return
        try:
            if element is not None:
                element.update()
        except RuntimeError as e:
            if 'client' in str(e).lower() and 'deleted' in str(e).lower():
                logger.debug("[UI] Client disconnected, marking invalid and cancelling streams")
                self.is_valid = False
                self.cancellation_event.set()  # Cancel any ongoing streams
            else:
                raise
    
    def safe_scroll(self):
        """Safely scroll to bottom, handling disconnected clients."""
        if not self.is_valid:
            return
        try:
            if self.scroll_container is not None:
                self.scroll_container.scroll_to(percent=1.0)
        except RuntimeError as e:
            if 'client' in str(e).lower() and 'deleted' in str(e).lower():
                logger.debug("[UI] Client disconnected, marking invalid and cancelling streams")
                self.is_valid = False
                self.cancellation_event.set()  # Cancel any ongoing streams
            else:
                raise
