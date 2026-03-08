# -*- coding: utf-8 -*-
"""
ui/modern_chat.py - Modern Chat Interface Components
Beautiful, Claude-inspired chat UI with smooth animations.

This module provides reusable chat components that can be integrated
into the main zena.py application without modifying the backend.
"""

from nicegui import ui
from .modern_theme import ModernTheme as MT


class ModernChatMessage:
    """
    Modern chat message component with beautiful styling.

    Features:
    - Smooth appearance animations
    - Role-based styling (user, AI, system, RAG)
    - Avatar support
    - Markdown rendering
    - Source citations (for RAG)
    """

    def __init__(
        self, role: str, content: str, avatar_text: str = None, rag_enhanced: bool = False, sources: list = None
    ):
        """
        Create a modern chat message.

        Args:
            role: Message role ('user', 'assistant', 'system')
            content: Message content (supports Markdown)
            avatar_text: Text for avatar (e.g., 'Z' for Zena, 'U' for User)
            rag_enhanced: Whether message uses RAG context
            sources: List of sources for RAG messages (optional)
        """
        self.role = role
        self.content = content
        self.avatar_text = avatar_text or ("U" if role == "user" else "Z")
        self.rag_enhanced = rag_enhanced
        self.sources = sources or []

    def render(self, container=None):
        """Render the message in the chat interface."""
        # Choose the appropriate container row style
        if self.role == "system":
            row_class = MT.ChatBubbles.ROW_SYSTEM
        elif self.role == "user":
            row_class = MT.ChatBubbles.ROW_USER
        else:
            row_class = MT.ChatBubbles.ROW_AI

        # Create message row with animation
        msg_row = ui.row().classes(row_class + " chat-message")
        if container:
            msg_row.move(container)

        with msg_row:
            # Add avatar for AI messages
            if self.role != "user" and self.role != "system":
                ui.avatar(
                    self.avatar_text, color="purple" if not self.rag_enhanced else "blue", text_color="white"
                ).classes(MT.Avatars.AI_FULL)

            # Message content column
            with ui.column().classes("gap-1 max-w-3xl"):
                # Sender name (small, subtle)
                if self.role != "system":
                    sender = "You" if self.role == "user" else "Zena"
                    ui.label(sender).classes(MT.combine(MT.TEXT_XS, MT.TextColors.SECONDARY, "ml-1"))

                # Message bubble with appropriate styling
                bubble_class = MT.get_chat_bubble(self.role, self.rag_enhanced)
                ui.markdown(self.content).classes(bubble_class + " markdown-content")

                # Add sources if RAG-enhanced
                if self.rag_enhanced and self.sources:
                    self._render_sources()

            # Add avatar for user messages
            if self.role == "user":
                ui.avatar(self.avatar_text, color="gray", text_color="white").classes(MT.Avatars.USER_FULL)

    def _render_sources(self):
        """Render sources expansion panel for RAG messages."""
        with ui.expansion("View Sources", icon="source").classes(MT.Cards.INFO + " mt-2"):
            with ui.column().classes("gap-2 p-2"):
                for i, source in enumerate(self.sources, 1):
                    title = source.get("title", "Untitled")
                    url = source.get("url", "N/A")
                    text_preview = source.get("text", "")[:200] + "..."

                    # Source item
                    with ui.card().classes(MT.Cards.BASE + " p-3"):
                        # Properties
                        is_cached = source.get("_is_cached", False)
                        score = source.get("rerank_score") or source.get("fusion_score") or source.get("score", 0)
                        score_label = f"{score:.2f}" if isinstance(score, float) else str(score)

                        # Header Row
                        with ui.row().classes("w-full items-center justify-between"):
                            # Title Link
                            if url.startswith("http"):
                                ui.link(f"[{i}] {title}", url, new_tab=True).classes(
                                    MT.TextColors.LINK + " font-semibold text-sm"
                                )
                            else:
                                ui.label(f"[{i}] {title}").classes(MT.TextColors.PRIMARY + " font-semibold text-sm")

                            # Badges
                            with ui.row().classes("gap-1"):
                                if is_cached:
                                    ui.badge("⚡ MEMORY", color="purple").props("outline rounded").classes(
                                        "text-[10px]"
                                    )
                                elif source.get("rerank_score"):
                                    ui.badge(f"🎯 {score_label}", color="green").props("outline rounded").classes(
                                        "text-[10px]"
                                    )
                                else:
                                    ui.badge(f"🔍 {score_label}", color="grey").props("outline rounded").classes(
                                        "text-[10px]"
                                    )

                        # URL/Path
                        ui.label(f"Location: {url}").classes(MT.combine(MT.TEXT_XS, MT.TextColors.MUTED))

                        # Preview
                        ui.label(f'"{text_preview}"').classes(
                            MT.combine(
                                MT.TEXT_SM, MT.TextColors.SECONDARY, "italic border-l-2 border-gray-300 pl-2 mt-1"
                            )
                        )


class ModernTypingIndicator:
    """
    Animated typing indicator for AI responses.

    Shows three pulsing dots to indicate the AI is "thinking".
    """

    def __init__(self):
        self.container = None

    def render(self, chat_container):
        """Show typing indicator."""
        row = ui.row().classes(MT.ChatBubbles.ROW_AI + " chat-message")
        if chat_container:
            row.move(chat_container)
        self.container = row

        with row:
            # AI avatar
            ui.avatar("Z", color="purple", text_color="white").classes(MT.Avatars.AI_FULL)

            # Typing indicator bubble
            with ui.column().classes("gap-1"):
                ui.label("Zena").classes(MT.combine(MT.TEXT_XS, MT.TextColors.SECONDARY, "ml-1"))

                # Bubble with typing animation
                with ui.card().classes(MT.ChatBubbles.AI_FULL + " flex items-center justify-center min-h-12"):
                    ui.html("""
                        <div class="typing-indicator">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                    """)

    def remove(self):
        """Remove typing indicator from chat."""
        if self.container:
            self.container.delete()
            self.container = None


class ModernInputBar:
    """
    Modern input bar component with file upload and voice support.

    Features:
    - Large, rounded input field
    - Attach file button
    - Voice record button
    - Send button
    - Smooth focus ring
    """

    def __init__(self, on_send=None, on_upload=None, on_voice=None, placeholder="Type your message..."):
        """
        Create modern input bar.

        Args:
            on_send: Callback for send button click (async function)
            on_upload: Callback for file upload (async function)
            on_voice: Callback for voice recording (async function)
            placeholder: Input placeholder text
        """
        self.on_send = on_send
        self.on_upload = on_upload
        self.on_voice = on_voice
        self.placeholder = placeholder
        self.input_field = None
        self.attachment_preview = None

    def render(self, container=None):
        """Render the input bar."""
        input_col = ui.column().classes("w-full max-w-4xl mx-auto gap-2")
        if container:
            input_col.move(container)

        with input_col:
            # Attachment preview (hidden by default)
            self.attachment_preview = ui.label("").classes(MT.Cards.INFO + " text-sm self-start").props("visible=false")

            # Input bar
            with ui.row().classes(MT.Inputs.CHAT_BAR):
                # File upload button
                if self.on_upload:
                    uploader = ui.upload(on_upload=self.on_upload, auto_upload=True).classes("hidden")

                    ui.button(icon="attach_file", on_click=lambda: uploader.run_method("pickFiles")).props(
                        "flat round dense"
                    ).classes(MT.Buttons.ICON + " text-gray-500 hover:text-purple-600")

                # Input field
                self.input_field = ui.input(placeholder=self.placeholder).classes(MT.Inputs.CHAT).props("borderless")

                # Bind Enter key to send
                if self.on_send:
                    self.input_field.on("keydown.enter.prevent", self._handle_send)

                # Voice record button
                if self.on_voice:
                    ui.button(icon="mic", on_click=self.on_voice).props("flat round dense").classes(
                        MT.Buttons.ICON + " text-gray-500 hover:text-purple-600"
                    )

                # Send button
                if self.on_send:
                    ui.button(icon="send", on_click=self._handle_send).props("round unelevated").classes(
                        MT.Buttons.PRIMARY_FULL + " w-10 h-10"
                    )

    async def _handle_send(self, e=None):
        """Handle send button click."""
        if not (self.on_send and self.input_field):
            return

        message = self.input_field.value.strip()
        if message:
            await self.on_send(message)
            self.input_field.value = ""

    def show_attachment(self, filename: str, size: int):
        """Show attachment preview."""
        if self.attachment_preview:
            self.attachment_preview.text = f"Attached: {filename} ({size:,} bytes)"
            self.attachment_preview.props("visible=true")

    def hide_attachment(self):
        """Hide attachment preview."""
        if self.attachment_preview:
            self.attachment_preview.props("visible=false")
            self.attachment_preview.text = ""


class ModernActionChips:
    """
    Quick action chips for guided interactions.

    Shows pill-shaped buttons for common queries.
    """

    def __init__(self, actions: list, on_click=None):
        """
        Create action chips.

        Args:
            actions: List of action dictionaries with 'label' and 'value'
            on_click: Callback when chip is clicked (async function)
        """
        self.actions = actions
        self.on_click = on_click

    def render(self, container=None):
        """Render action chips."""
        chips_col = ui.column().classes("w-full gap-2")
        if container:
            chips_col.move(container)

        with chips_col:
            ui.label("Quick Actions").classes(MT.combine(MT.TEXT_SM, MT.TextColors.MUTED, "ml-1"))

            with ui.row().classes("gap-2 flex-wrap"):
                for action in self.actions:
                    label = action.get("label", "")
                    value = action.get("value", label)

                    async def chip_click(val=value):
                        if self.on_click:
                            await self.on_click(val)

                    ui.button(label, on_click=chip_click).classes(MT.Badges.CHIP).props("outline size=sm no-caps")


class ModernWelcomeMessage:
    """
    Beautiful welcome message for new sessions.

    Features:
    - Large, centered greeting
    - Feature highlights
    - Smooth fade-in animation
    """

    def __init__(self, app_name: str = "Zena", features: list = None, custom_message: str = None):
        """
        Create welcome message.

        Args:
            app_name: Application name
            features: List of feature strings
            custom_message: Custom welcome message (optional)
        """
        self.app_name = app_name
        self.features = features or [
            "Fast local AI responses",
            "RAG-enhanced knowledge retrieval",
            "Multi-LLM consensus",
            "Voice interaction support",
        ]
        self.custom_message = custom_message

    def render(self, container=None):
        """Render welcome message."""
        welcome_col = ui.column().classes("w-full max-w-2xl mx-auto text-center gap-4 p-8 animate-fade-in")
        if container:
            welcome_col.move(container)

        with welcome_col:
            # App name (large, bold)
            ui.label(f"Welcome to {self.app_name}").classes(
                MT.combine(MT.TEXT_3XL, MT.FONT_BOLD, MT.TextColors.PRIMARY)
            )

            # Custom message or default
            message = self.custom_message or f"Your intelligent AI assistant powered by local LLMs"
            ui.label(message).classes(MT.combine(MT.TEXT_LG, MT.TextColors.SECONDARY, "mb-4"))

            # Feature cards
            with ui.row().classes("gap-4 justify-center flex-wrap"):
                for feature in self.features:
                    with ui.card().classes(MT.Cards.PADDED + " min-w-48"):
                        ui.label(feature).classes(MT.combine(MT.TEXT_SM, MT.TextColors.SECONDARY, "text-center"))

            # Getting started hint
            ui.label("Try asking a question or use the quick actions below").classes(
                MT.combine(MT.TEXT_SM, MT.TextColors.MUTED, "italic mt-4")
            )


# ==========================================================================
# HELPER FUNCTIONS
# ==========================================================================


def add_modern_css(page_container):
    """
    Add modern CSS styles to the page.

    This should be called once during page initialization.
    """
    from .modern_theme import MODERN_CSS

    ui.add_head_html(MODERN_CSS)


def create_modern_chat_container(scroll_container):
    """
    Create a modern chat container with proper styling.

    Args:
        scroll_container: The scroll area containing chat messages

    Returns:
        Column element for chat messages
    """
    with scroll_container:
        chat_log = ui.column().classes(MT.Layout.CHAT_CONTAINER)
    return chat_log
