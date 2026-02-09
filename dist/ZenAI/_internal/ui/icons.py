# -*- coding: utf-8 -*-
"""
ui/icons.py - Icon Constants
Centralized icon names for consistent use throughout the app.

Uses Material Icons (available in NiceGUI/Quasar).
"""


class Icons:
    """
    Material icon names used throughout the application.
    Centralizing these makes it easy to change icons app-wide.
    """
    
    # ==========================================================================
    # NAVIGATION
    # ==========================================================================
    MENU = "menu"
    CLOSE = "close"
    BACK = "arrow_back"
    FORWARD = "arrow_forward"
    HOME = "home"
    SETTINGS = "settings"
    HELP = "help"
    
    # ==========================================================================
    # ACTIONS
    # ==========================================================================
    DOWNLOAD = "download"
    UPLOAD = "upload"
    CLOUD_DOWNLOAD = "cloud_download"
    CLOUD_UPLOAD = "cloud_upload"
    DELETE = "delete"
    EDIT = "edit"
    SAVE = "save"
    COPY = "content_copy"
    REFRESH = "refresh"
    SEARCH = "search"
    SEND = "arrow_upward"
    CLEAR = "clear"
    ADD = "add"
    REMOVE = "remove"
    
    # ==========================================================================
    # MEDIA
    # ==========================================================================
    PLAY = "play_arrow"
    PAUSE = "pause"
    STOP = "stop"
    RECORD = "mic"
    VOLUME = "volume_up"
    VOLUME_OFF = "volume_off"
    
    # ==========================================================================
    # FILES & FOLDERS
    # ==========================================================================
    FILE = "description"
    FOLDER = "folder"
    FOLDER_OPEN = "folder_open"
    ATTACH = "attach_file"
    PDF = "picture_as_pdf"
    IMAGE = "image"
    CODE = "code"
    
    # ==========================================================================
    # STATUS & INFO
    # ==========================================================================
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "check_circle"
    LOADING = "hourglass_empty"
    PENDING = "pending"
    
    # ==========================================================================
    # THEME
    # ==========================================================================
    DARK_MODE = "dark_mode"
    LIGHT_MODE = "light_mode"
    BRIGHTNESS = "brightness_6"
    
    # ==========================================================================
    # AI & MODELS
    # ==========================================================================
    MODEL = "psychology"
    AI = "smart_toy"
    ROBOT = "smart_toy"
    BRAIN = "psychology"
    CHAT = "chat"
    MESSAGE = "message"
    
    # ==========================================================================
    # SYSTEM
    # ==========================================================================
    BENCHMARK = "speed"
    DIAGNOSTICS = "bug_report"
    VERSION = "info"
    TERMINAL = "terminal"
    
    # ==========================================================================
    # RAG & KNOWLEDGE
    # ==========================================================================
    SCAN = "radar"
    BOOK = "book"
    KNOWLEDGE = "menu_book"
    DATABASE = "storage"
    WEB = "language"
    SOURCE = "source"
    
    # ==========================================================================
    # SWARM / NETWORK
    # ==========================================================================
    HUB = "hub"
    NETWORK = "device_hub"
    CLOUD = "cloud"
    
    # ==========================================================================
    # USER INTERFACE
    # ==========================================================================
    EXPAND = "expand_more"
    COLLAPSE = "expand_less"
    MORE_VERT = "more_vert"
    MORE_HORIZ = "more_horiz"
    VISIBILITY = "visibility"
    VISIBILITY_OFF = "visibility_off"
    PERSON = "person"
    
    # ==========================================================================
    # EMOJI ALTERNATIVES (for text contexts)
    # ==========================================================================
    @classmethod
    def emoji(cls, name: str) -> str:
        """Get emoji for a given icon concept."""
        emoji_map = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
            "search": "🔍",
            "file": "📄",
            "folder": "📁",
            "database": "💾",
            "web": "🌐",
            "robot": "🤖",
            "sparkles": "✨",
            "loading": "💡",
            "thinking": "💭",
            "timer": "⏱️",
            "download": "📥",
            "upload": "📤",
            "check": "✓",
            "star": "⭐",
            "fire": "🔥",
            "lightning": "⚡",
            "rocket": "🚀",
            "gear": "⚙️",
            "mic": "🎤",
            "speaker": "🔊",
        }
        return emoji_map.get(name, "")
