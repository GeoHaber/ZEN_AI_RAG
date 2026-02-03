# -*- coding: utf-8 -*-
"""
ui/styles.py - "ZenAI Flow" Theme (Glassmorphism Edition)
"""

class Styles:
    """
    Premium Modern UI Tokens (Tailwind + CSS Variables).
    Focus on Glassmorphism, Gradients, and Depth.
    """
    
    # Global CSS Injection (Font, Animations, Mesh Gradient)
    GLOBAL_CSS = """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    :root {
        --primary: #6366f1;
    }
    
    body {
        font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
        -webkit-font-smoothing: antialiased;
    }
    
    /* Mesh Gradients */
    body.body--dark {
        background-color: #0b0f19 !important;
        background-image: 
            radial-gradient(at 0% 0%, hsla(253,16%,7%,1) 0, transparent 50%), 
            radial-gradient(at 50% 0%, hsla(225,39%,30%,1) 0, transparent 50%), 
            radial-gradient(at 100% 0%, hsla(339,49%,30%,1) 0, transparent 50%);
        background-size: cover;
        background-attachment: fixed;
    }
    
    /* Input Capsule */
    .zen-capsule {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.6);
        box-shadow: 0 8px 32px rgba(0,0,0,0.08);
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }
    
    body.body--dark .zen-capsule {
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    
    /* Living Logo Animation */
    @keyframes logo-spin { 
        100% { transform: rotate(360deg); } 
    }
    .logo-thinking {
        animation: logo-spin 1s linear infinite;
        border-color: transparent !important;
        border-top-color: #6366f1 !important;
        border-left-color: #8b5cf6 !important;
    }
    """

    # ==========================================================================
    # LAYOUT
    # ==========================================================================
    PAGE_CHAT = "flex flex-col h-screen overflow-hidden transition-colors duration-500"
    
    # Message container with bottom padding for floating capsule
    CHAT_CONTAINER = "w-full max-w-3xl mx-auto flex-1 overflow-y-auto px-4 py-20 pb-40 scroll-smooth"
    
    # ==========================================================================
    # GLASS CAPSULE (Footer)
    # ==========================================================================
    # The invisible container at bottom
    FOOTER_WRAPPER = "fixed bottom-8 left-0 right-0 p-4 flex flex-col items-center gap-3 pointer-events-none z-50"
    
    # The actual input bar
    INPUT_CAPSULE = "zen-capsule pointer-events-auto w-full max-w-3xl flex items-center gap-2 p-2 rounded-[28px] focus-within:ring-2 focus-within:ring-blue-500/50"
    
    # ==========================================================================
    # HEADER
    # ==========================================================================
    HEADER = "fixed top-0 left-0 right-0 p-4 flex items-center justify-between z-50 pointer-events-none"
    HEADER_GLASS = "pointer-events-auto backdrop-blur-xl bg-white/70 dark:bg-[#0b0f19]/70 rounded-full px-6 py-2 shadow-sm border border-gray-200 dark:border-white/5 flex items-center gap-4 transition-all"
    
    # ==========================================================================
    # BUBBLES
    # ==========================================================================
    CHAT_BUBBLE_USER = "bg-gradient-to-br from-blue-600 to-violet-600 text-white shadow-lg shadow-blue-500/20"
    CHAT_BUBBLE_AI = "bg-white dark:bg-[#1a1f2e] border border-gray-100 dark:border-white/5 text-gray-800 dark:text-gray-100 shadow-sm"
    CHAT_BUBBLE_RAG = "bg-blue-50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-500/20 text-gray-800 dark:text-gray-100"
    CHAT_BUBBLE_BASE = "px-6 py-4 rounded-2xl max-w-3xl text-[15px] leading-7 shadow-sm"

    # ==========================================================================
    # UTILS
    # ==========================================================================
    TEXT_GRADIENT = "bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-violet-600 dark:from-blue-400 dark:to-violet-400 font-bold"
    TEXT_PRIMARY = "text-gray-900 dark:text-gray-100"
    TEXT_SECONDARY = "text-gray-600 dark:text-gray-400"
    TEXT_MUTED = "text-gray-500 dark:text-gray-500"
    TEXT_ACCENT = "text-blue-600 dark:text-blue-400"
    TEXT_SUCCESS = "text-green-600 dark:text-green-400"
    
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
    CARD_BASE = "rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-slate-800"
    
    DIALOG_CARD = "p-0 rounded-2xl overflow-hidden bg-white dark:bg-slate-900 shadow-2xl"
    DIALOG_TITLE = "text-lg font-bold p-4 border-b border-gray-100 dark:border-gray-800"
    
    GRID_2_COL = "grid grid-cols-1 md:grid-cols-2 gap-4"
    
    CHIP = "rounded-full px-4 py-1 text-sm font-medium transition-colors"
    PROGRESS = "h-2 rounded-full overflow-hidden bg-gray-100 dark:bg-gray-800"
    LOADING_PULSE = "animate-pulse"
    DRAWER = "bg-white dark:bg-slate-900 border-r border-gray-200 dark:border-gray-800"
    DRAWER_ITEM = "flex items-center gap-3 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors"
    AVATAR = "shadow-sm ring-2 ring-white dark:ring-slate-800"
    
    # Additional commonly needed styles
    BATCH_CARD = "p-3 rounded-lg border border-blue-100 dark:border-blue-800 bg-blue-50/30 dark:bg-blue-900/20"
    BATCH_PROGRESS_BAR = "h-1.5 rounded-full bg-blue-100 dark:bg-slate-700 overflow-hidden"
    TEXT_WARNING = "text-orange-600 dark:text-orange-400"
    TEXT_ERROR = "text-red-600 dark:text-red-400"
    FOOTER = "w-full border-t border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-2 md:p-4"
    INPUT_BAR = "w-full max-w-4xl mx-auto flex items-center gap-1 md:gap-2 p-2 bg-white dark:bg-slate-900 border border-gray-300 dark:border-slate-600 rounded-xl shadow-sm"
    CHAT_ROW_USER = "w-full flex justify-end mb-3 md:mb-4"
    CHAT_ROW_AI = "w-full flex justify-start mb-3 md:mb-4"
    CHAT_NAME = "text-xs font-bold text-slate-500 dark:text-slate-400 mb-1"
    LABEL_RAG = "bg-green-600 text-white text-[9px] px-1.5 py-0.5 rounded-sm font-bold uppercase mr-2"
    CHAT_CONTAINER_LIGHT = "bg-slate-50"
    CHAT_CONTAINER_DARK = "dark:bg-slate-900"

    @classmethod
    def combine(cls, *names):
        return " ".join(names)
