# -*- coding: utf-8 -*-
"""
ui/styles.py - Tailwind CSS Class Presets
Reusable class combinations for consistent styling.

Usage:
    from ui import Styles
    
    ui.button('Click me').classes(Styles.BTN_PRIMARY)
    ui.card().classes(Styles.CARD)
"""


class Styles:
    """
    Predefined Tailwind CSS class combinations.
    Use these instead of hardcoding classes throughout the app.
    """
    
    # ==========================================================================
    # CARDS
    # ==========================================================================
    CARD = "p-4 rounded-xl shadow-sm border"
    CARD_BASE = "rounded-lg border border-gray-200 dark:border-slate-700"  # Base for expansions
    CARD_LIGHT = "bg-white border-gray-200"
    CARD_DARK = "dark:bg-slate-800 dark:border-slate-700"
    CARD_FULL = "p-4 rounded-xl shadow-sm border bg-white border-gray-200 dark:bg-slate-800 dark:border-slate-700"
    
    CARD_HOVER = "hover:shadow-lg transition-shadow"
    CARD_INTERACTIVE = "p-4 rounded-xl shadow-sm border bg-white border-gray-200 dark:bg-slate-800 dark:border-slate-700 hover:shadow-lg transition-all cursor-pointer"
    
    # Specialized cards
    CARD_MODEL = "p-4 hover:shadow-lg transition-shadow border model-card"
    CARD_INFO = "bg-blue-50 dark:bg-slate-800 rounded-lg p-3 text-sm"
    CARD_WARNING = "bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3 text-sm border-l-4 border-amber-500"
    CARD_SUCCESS = "bg-green-50 dark:bg-green-900/20 rounded-lg p-3 text-sm border-l-4 border-green-500"
    
    # ==========================================================================
    # BUTTONS
    # ==========================================================================
    BTN_PRIMARY = "bg-blue-600 text-white hover:bg-blue-700"
    BTN_SECONDARY = "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-slate-700 dark:text-gray-200 dark:hover:bg-slate-600"
    BTN_DANGER = "bg-red-600 text-white hover:bg-red-700"
    BTN_SUCCESS = "bg-green-600 text-white hover:bg-green-700"
    
    BTN_OUTLINE = "border-2 border-blue-500 text-blue-600 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-slate-800"
    BTN_GHOST = "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-slate-800"
    
    BTN_ICON = "text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
    BTN_ICON_ROUND = "rounded-full p-2"
    
    # Size variants
    BTN_SM = "text-sm px-3 py-1.5"
    BTN_MD = "text-base px-4 py-2"
    BTN_LG = "text-lg px-6 py-3"
    
    # Full width
    BTN_FULL = "w-full"
    
    # Sidebar buttons
    BTN_SIDEBAR = "w-full text-left"
    BTN_SIDEBAR_LIGHT = "bg-slate-50 text-slate-800 hover:bg-slate-100"
    BTN_SIDEBAR_DARK = "dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700"
    
    # ==========================================================================
    # INPUTS
    # ==========================================================================
    INPUT = "w-full"
    INPUT_OUTLINED = "outlined"
    INPUT_DENSE = "dense"
    INPUT_BORDERLESS = "borderless"
    
    INPUT_CHAT = "flex-1 text-gray-900 dark:text-white text-base"
    
    # ==========================================================================
    # CHAT BUBBLES (Large chat area like LM Studio / Ollama)
    # ==========================================================================
    CHAT_CONTAINER = "w-full max-w-4xl mx-auto flex-1 overflow-y-auto p-4 space-y-4 pb-4"
    CHAT_CONTAINER_LIGHT = "bg-gray-50"
    CHAT_CONTAINER_DARK = "dark:bg-slate-950"
    
    # Full-height page container for chat
    PAGE_CHAT = "flex flex-col h-screen"
    
    CHAT_ROW_USER = "w-full justify-end"
    CHAT_ROW_AI = "w-full justify-start"
    
    CHAT_BUBBLE_BASE = "px-5 py-3 rounded-3xl max-w-3xl shadow-sm text-md leading-relaxed"
    CHAT_BUBBLE_USER = "bg-blue-500 text-white"
    CHAT_BUBBLE_AI = "bg-gray-100 dark:bg-slate-800 text-gray-900 dark:text-gray-100"
    CHAT_BUBBLE_RAG = "bg-blue-50 dark:bg-slate-800 border-l-4 border-blue-500 shadow-md"
    
    CHAT_NAME = "text-xs text-gray-500 dark:text-gray-400 mb-1 ml-1 mr-1"
    
    # ==========================================================================
    # AVATAR
    # ==========================================================================
    AVATAR = "w-10 h-10"
    AVATAR_SM = "w-8 h-8"
    AVATAR_LG = "w-12 h-12"
    
    # ==========================================================================
    # HEADERS & FOOTERS (Compact like LM Studio / Ollama)
    # ==========================================================================
    HEADER = "bg-white dark:bg-slate-900 border-b border-gray-200 dark:border-slate-800 px-4 py-2 shadow-sm text-gray-800 dark:text-gray-100"
    FOOTER = "bg-white dark:bg-slate-900 border-t border-gray-200 dark:border-slate-800 px-4 py-3 w-full flex justify-center"
    
    # ==========================================================================
    # DRAWER / SIDEBAR
    # ==========================================================================
    DRAWER = "bg-white dark:bg-slate-900 border-r border-gray-200 dark:border-slate-700 p-5 shadow-lg text-gray-900 dark:text-gray-100"
    
    # ==========================================================================
    # SECTIONS & LABELS
    # ==========================================================================
    SECTION_TITLE = "text-sm font-bold mb-3 text-primary"
    SECTION_TITLE_BLUE = "text-sm font-bold text-blue-600"
    
    LABEL_XS = "text-xs text-gray-500 dark:text-gray-400"
    LABEL_SM = "text-sm text-gray-600 dark:text-gray-300"
    LABEL_MUTED = "text-xs text-gray-500 italic"
    
    # ==========================================================================
    # BADGES & CHIPS
    # ==========================================================================
    BADGE = "px-2 py-1 rounded-full text-xs font-medium"
    BADGE_PRIMARY = "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
    BADGE_SUCCESS = "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
    BADGE_WARNING = "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
    BADGE_ERROR = "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
    
    CHIP = "rounded-full border-2 border-blue-500 text-blue-600 dark:text-blue-400 px-4 py-2 hover:bg-blue-50 dark:hover:bg-gray-800 transition-colors"
    
    # ==========================================================================
    # TEXT COLORS
    # ==========================================================================
    TEXT_PRIMARY = "text-gray-900 dark:text-gray-100"
    TEXT_SECONDARY = "text-gray-600 dark:text-gray-400"
    TEXT_MUTED = "text-gray-500 dark:text-gray-500"
    TEXT_ACCENT = "text-blue-600 dark:text-blue-400"
    TEXT_SUCCESS = "text-green-600 dark:text-green-400"
    TEXT_WARNING = "text-amber-600 dark:text-amber-400"
    TEXT_ERROR = "text-red-600 dark:text-red-400"
    
    # ==========================================================================
    # EXPANSION PANELS
    # ==========================================================================
    EXPANSION = "w-full"
    EXPANSION_LIGHT = "bg-blue-50 text-gray-900"
    EXPANSION_DARK = "dark:bg-slate-800 dark:text-gray-100"
    
    # ==========================================================================
    # PROGRESS & LOADING
    # ==========================================================================
    PROGRESS = "mb-4 h-4 rounded"
    LOADING_PULSE = "animate-pulse"
    
    # ==========================================================================
    # ATTACHMENTS & UPLOADS
    # ==========================================================================
    ATTACHMENT_PREVIEW = "text-blue-600 dark:text-blue-400 text-sm mb-2 bg-blue-50 dark:bg-gray-800 px-3 py-1 rounded-full shadow-sm self-start"
    
    # ==========================================================================
    # INPUT BAR (Chat footer - compact like LM Studio)
    # ==========================================================================
    INPUT_BAR = "w-full gap-2 items-center py-1.5 px-3 rounded-2xl bg-gray-100 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 shadow-sm focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 transition-all"
    
    # ==========================================================================
    # DIALOGS
    # ==========================================================================
    DIALOG_CARD = "p-6 shadow-2xl"
    DIALOG_TITLE = "text-xl font-bold mb-4"
    DIALOG_CONTENT = "mb-4"
    
    # ==========================================================================
    # GRIDS
    # ==========================================================================
    GRID_2_COL = "grid grid-cols-1 lg:grid-cols-2 gap-4"
    GRID_3_COL = "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
    GRID_4_COL = "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
    
    # ==========================================================================
    # UTILITY COMBINATIONS
    # ==========================================================================
    FLEX_CENTER = "flex items-center justify-center"
    FLEX_BETWEEN = "flex items-center justify-between"
    FLEX_START = "flex items-start"
    FLEX_COL_GAP = "flex flex-col gap-2"
    
    # Spacing
    MB_SM = "mb-2"
    MB_MD = "mb-4"
    MB_LG = "mb-6"
    MT_SM = "mt-2"
    MT_MD = "mt-4"
    MT_LG = "mt-6"
    GAP_SM = "gap-2"
    GAP_MD = "gap-4"
    GAP_LG = "gap-6"
    
    # ==========================================================================
    # HELPER METHODS
    # ==========================================================================
    
    @classmethod
    def combine(cls, *class_names: str) -> str:
        """Combine multiple class strings into one."""
        return " ".join(class_names)
    
    @classmethod
    def card(cls, hover: bool = False, dark: bool = True) -> str:
        """Get card classes with options."""
        classes = [cls.CARD, cls.CARD_LIGHT]
        if dark:
            classes.append(cls.CARD_DARK)
        if hover:
            classes.append(cls.CARD_HOVER)
        return cls.combine(*classes)
    
    @classmethod
    def button(cls, variant: str = "primary", size: str = "md", full: bool = False) -> str:
        """Get button classes with options."""
        variant_map = {
            "primary": cls.BTN_PRIMARY,
            "secondary": cls.BTN_SECONDARY,
            "danger": cls.BTN_DANGER,
            "success": cls.BTN_SUCCESS,
            "outline": cls.BTN_OUTLINE,
            "ghost": cls.BTN_GHOST,
        }
        size_map = {
            "sm": cls.BTN_SM,
            "md": cls.BTN_MD,
            "lg": cls.BTN_LG,
        }
        
        classes = [variant_map.get(variant, cls.BTN_PRIMARY), size_map.get(size, cls.BTN_MD)]
        if full:
            classes.append(cls.BTN_FULL)
        return cls.combine(*classes)
