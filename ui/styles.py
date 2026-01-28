# -*- coding: utf-8 -*-
"""
ui/styles.py - "ZenAI Flow" Theme (Glassmorphism Edition)
"""

class Styles:
    """
    Premium Modern UI Tokens (Tailwind + CSS Variables).
    Focus on Glassmorphism, Gradients, and Depth.
    """
    
    # Global CSS Injection (Slate Theme - Simple & Clean + Mobile Optimizations)
    GLOBAL_CSS = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    :root {
        --primary: #3b82f6;
        --slate-50: #f8fafc;
        --slate-100: #f1f5f9;
        --slate-200: #e2e8f0;
        --slate-800: #1e293b;
        --slate-900: #0f172a;
        --slate-950: #020617;
    }
    
    body {
        font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
        -webkit-font-smoothing: antialiased;
        background-color: var(--slate-50) !important;
    }
    
    body.body--dark {
        background-color: var(--slate-950) !important;
        background-image: none !important;
    }
    
    /* Simple Card / Box Shadow */
    .slate-card {
        background: white;
        border: 1px solid var(--slate-200);
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    body.body--dark .slate-card {
        background: var(--slate-900);
        border: 1px solid var(--slate-800);
    }

    /* Mobile Specific Layout Tweaks */
    @media (max-width: 600px) {
        .q-header { min-height: 50px !important; }
        .q-footer { padding: 8px !important; }
        .q-message-text { font-size: 13px !important; }
        .q-drawer { width: 300px !important; max-width: 85vw !important; }
        /* High density for mobile chat */
        .chat-mobile-row { margin-bottom: 8px !important; }
        .chat-mobile-bubble { padding: 8px 12px !important; border-radius: 14px !important; }
    }
    </style>
    """

    # ==========================================================================
    # LAYOUT
    # ==========================================================================
    PAGE_CHAT = "flex flex-col h-screen overflow-hidden bg-slate-50 dark:bg-slate-950"
    
    # Message container
    CHAT_CONTAINER = "w-full max-w-4xl mx-auto flex-1 overflow-y-auto px-2 md:px-4 py-4 md:py-6 scroll-smooth"
    CHAT_CONTAINER_LIGHT = "bg-slate-50"
    CHAT_CONTAINER_DARK = "dark:bg-slate-950"
    
    # ==========================================================================
    # FOOTER (Minimalist)
    # ==========================================================================
    FOOTER = "w-full border-t border-gray-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-2 md:p-4"
    FOOTER_WRAPPER = "w-full border-t border-gray-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-2 md:p-4"
    INPUT_BAR = "w-full max-w-4xl mx-auto flex items-center gap-1 md:gap-2 p-1.5 md:p-2 bg-white dark:bg-slate-900 border border-gray-300 dark:border-slate-700 rounded-lg md:rounded-xl shadow-sm focus-within:ring-2 ring-blue-500/20"
    
    # ==========================================================================
    # HEADER (Minimalist)
    # ==========================================================================
    HEADER = "w-full h-12 md:h-14 border-b border-gray-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex items-center px-2 md:px-4 justify-between z-50"
    
    # ==========================================================================
    # BUBBLES (High Contrast)
    # ==========================================================================
    CHAT_BUBBLE_USER = "bg-blue-600 text-white"
    CHAT_BUBBLE_AI = "bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 text-slate-800 dark:text-slate-100"
    CHAT_BUBBLE_RAG = "bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 text-slate-800 dark:text-slate-100"
    CHAT_BUBBLE_BASE = "px-3 md:px-4 py-2 md:py-3 rounded-2xl max-w-[92%] md:max-w-[85%] text-[13px] md:text-[14px] leading-relaxed shadow-sm"
    
    CHAT_ROW_USER = "w-full flex justify-end mb-3 md:mb-4"
    CHAT_ROW_AI = "w-full flex justify-start mb-3 md:mb-4"
    CHAT_NAME = "text-[10px] md:text-xs font-bold text-slate-400 dark:text-slate-500 mb-0.5 md:mb-1"

    # ==========================================================================
    # UTILS
    # ==========================================================================
    TEXT_GRADIENT = "bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-violet-600 dark:from-blue-400 dark:to-violet-400 font-bold"
    TEXT_PRIMARY = "text-gray-900 dark:text-gray-100"
    TEXT_SECONDARY = "text-gray-600 dark:text-gray-400"
    TEXT_MUTED = "text-gray-500 dark:text-gray-500"
    TEXT_ACCENT = "text-blue-600 dark:text-blue-400"
    TEXT_SUCCESS = "text-green-600 dark:text-green-400"
    TEXT_WARNING = "text-orange-600 dark:text-orange-400"
    TEXT_ERROR = "text-red-600 dark:text-red-400"
    
    LABEL_XS = "text-[10px] font-bold uppercase tracking-wider opacity-70"
    LABEL_SM = "text-xs font-semibold uppercase tracking-wide opacity-80"
    LABEL_MUTED = "text-gray-400 dark:text-gray-500"

    # ==========================================================================
    # COMPONENTS
    # ==========================================================================
    BTN_PRIMARY = "bg-blue-600 hover:bg-blue-700 text-white shadow-md transition-transform active:scale-95"
    BTN_SECONDARY = "bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-white"
    BTN_GHOST = "text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-white/5"
    
    CARD_INFO = "bg-blue-50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-500/20 rounded-lg p-3"
    CARD_MODEL = "p-4 rounded-xl border border-gray-200 dark:border-gray-700 hover:shadow-md transition-all bg-white dark:bg-slate-800"
    CARD_BASE = "p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-slate-800"

    DIALOG_CARD = "p-0 rounded-2xl overflow-hidden bg-white dark:bg-slate-900 shadow-2xl"
    DIALOG_TITLE = "text-lg font-bold p-4 border-b border-gray-100 dark:border-gray-800"
    
    GRID_2_COL = "grid grid-cols-1 md:grid-cols-2 gap-4"
    
    CHIP = "rounded-full px-4 py-1 text-sm font-medium transition-colors"
    PROGRESS = "h-2 rounded-full overflow-hidden bg-gray-100 dark:bg-gray-800"
    LOADING_PULSE = "animate-pulse"
    DRAWER = "bg-white dark:bg-slate-900 border-r border-gray-200 dark:border-gray-800"
    DRAWER_ITEM = "flex items-center gap-3 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors"
    AVATAR = "shadow-sm ring-2 ring-white dark:ring-slate-800"
    
    # Batch Analysis
    BATCH_CARD = "p-3 rounded-lg border border-blue-100 dark:border-blue-500/20 bg-blue-50/30 dark:bg-blue-900/10"
    BATCH_PROGRESS_BAR = "h-1.5 rounded-full bg-blue-100 dark:bg-blue-900 overflow-hidden"

    @classmethod
    def combine(cls, *names):
        return " ".join(names)
