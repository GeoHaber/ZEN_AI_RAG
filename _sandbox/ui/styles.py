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
    
    @classmethod
    def combine(cls, *names):
        return " ".join(names)
