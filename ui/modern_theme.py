# -*- coding: utf-8 -*-
"""
ui/modern_theme.py - Modern Claude-Inspired UI Theme
Beautiful, clean design with purple accents and smooth animations.

This theme provides:
- Claude-inspired color palette (purple primary, clean whites/grays)
- Modern typography (larger, better spacing)
- Smooth animations and transitions
- Improved chat bubbles with better visual hierarchy
- Dark mode with cohesive color scheme
"""


class ModernTheme:
    """
    Modern UI theme inspired by Claude desktop interface.

    Design Principles:
    1. Minimalism - Focus on content, reduce visual clutter
    2. Whitespace - Generous padding and margins
    3. Hierarchy - Clear visual distinction between elements
    4. Consistency - Unified color scheme and typography
    5. Smoothness - Subtle animations and transitions
    """

    # ==========================================================================
    # COLOR PALETTE - Claude-Inspired
    # ==========================================================================

    # Primary Colors (Purple)
    PURPLE_50 = "#F5F3FF"
    PURPLE_100 = "#EDE9FE"
    PURPLE_400 = "#A78BFA"
    PURPLE_500 = "#8B5CF6"   # Primary purple
    PURPLE_600 = "#7C3AED"
    PURPLE_700 = "#6D28D9"

    # Neutral Colors (Light Mode)
    WHITE = "#FFFFFF"
    GRAY_50 = "#F9FAFB"
    GRAY_100 = "#F3F4F6"
    GRAY_200 = "#E5E7EB"
    GRAY_300 = "#D1D5DB"
    GRAY_400 = "#9CA3AF"
    GRAY_500 = "#6B7280"
    GRAY_600 = "#4B5563"
    GRAY_700 = "#374151"
    GRAY_800 = "#1F2937"
    GRAY_900 = "#111827"
    BLACK = "#000000"

    # Neutral Colors (Dark Mode)
    SLATE_50 = "#F8FAFC"
    SLATE_800 = "#1E293B"
    SLATE_900 = "#0F172A"
    SLATE_950 = "#020617"

    # Accent Colors
    BLUE_500 = "#3B82F6"
    BLUE_600 = "#2563EB"
    GREEN_500 = "#10B981"
    GREEN_600 = "#059669"
    RED_500 = "#EF4444"
    RED_600 = "#DC2626"
    AMBER_500 = "#F59E0B"
    AMBER_600 = "#D97706"

    # ==========================================================================
    # TYPOGRAPHY
    # ==========================================================================

    # Font Families
    FONT_SANS = "'Inter', 'SF Pro Display', 'Segoe UI', system-ui, -apple-system, sans-serif"
    FONT_MONO = "'Fira Code', 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace"

    # Font Sizes (using rem for accessibility)
    TEXT_XS = "text-xs"      # 0.75rem - 12px
    TEXT_SM = "text-sm"      # 0.875rem - 14px
    TEXT_BASE = "text-base"  # 1rem - 16px
    TEXT_LG = "text-lg"      # 1.125rem - 18px
    TEXT_XL = "text-xl"      # 1.25rem - 20px
    TEXT_2XL = "text-2xl"    # 1.5rem - 24px
    TEXT_3XL = "text-3xl"    # 1.875rem - 30px

    # Font Weights
    FONT_LIGHT = "font-light"     # 300
    FONT_NORMAL = "font-normal"   # 400
    FONT_MEDIUM = "font-medium"   # 500
    FONT_SEMIBOLD = "font-semibold"  # 600
    FONT_BOLD = "font-bold"       # 700

    # Line Heights
    LEADING_TIGHT = "leading-tight"      # 1.25
    LEADING_NORMAL = "leading-normal"    # 1.5
    LEADING_RELAXED = "leading-relaxed"  # 1.625
    LEADING_LOOSE = "leading-loose"      # 2

    # ==========================================================================
    # SPACING (using Tailwind's 4px base unit)
    # ==========================================================================

    P_1 = "p-1"    # 4px
    P_2 = "p-2"    # 8px
    P_3 = "p-3"    # 12px
    P_4 = "p-4"    # 16px
    P_5 = "p-5"    # 20px
    P_6 = "p-6"    # 24px
    P_8 = "p-8"    # 32px

    M_1 = "m-1"
    M_2 = "m-2"
    M_3 = "m-3"
    M_4 = "m-4"
    M_6 = "m-6"
    M_8 = "m-8"

    # ==========================================================================
    # MODERN CHAT BUBBLES - Claude-Inspired
    # ==========================================================================

    class ChatBubbles:
        """
        Modern chat bubble styles with improved visual design.

        Features:
        - Larger padding for better readability
        - Rounded corners (3xl - very rounded)
        - Subtle shadows for depth
        - Color differentiation between user/AI
        - Smooth animations on appearance
        """

        # Base bubble style (shared)
        BASE = "px-6 py-4 rounded-3xl max-w-3xl shadow-md text-base leading-relaxed transition-all duration-200"

        # User message (Purple accent, right-aligned)
        USER = "bg-purple-600 text-white shadow-purple-200 dark:shadow-purple-900/50"
        USER_FULL = f"{BASE} {USER}"

        # AI message (Light gray, left-aligned)
        AI = "bg-gray-100 text-gray-900 dark:bg-slate-800 dark:text-gray-100 shadow-gray-200 dark:shadow-slate-900/50"
        AI_FULL = f"{BASE} {AI}"

        # RAG-enhanced message (Blue tint with border)
        RAG = "bg-blue-50 text-gray-900 dark:bg-slate-800 dark:text-gray-100 border-l-4 border-blue-500 shadow-blue-200 dark:shadow-blue-900/50"
        RAG_FULL = f"{BASE} {RAG}"

        # System message (Subtle, centered)
        SYSTEM = "bg-gray-50 text-gray-600 dark:bg-slate-900 dark:text-gray-400 text-center text-sm italic border border-gray-200 dark:border-slate-700"
        SYSTEM_FULL = f"{BASE} {SYSTEM}"

        # Message container rows
        ROW_USER = "w-full flex justify-end mb-4"
        ROW_AI = "w-full flex justify-start mb-4 gap-3"
        ROW_SYSTEM = "w-full flex justify-center mb-4"

    # ==========================================================================
    # BUTTONS - Modern Design
    # ==========================================================================

    class Buttons:
        """Modern button styles with smooth interactions."""

        # Base button
        BASE = "px-4 py-2 rounded-xl font-medium transition-all duration-200 cursor-pointer"

        # Primary (Purple)
        PRIMARY = "bg-purple-600 text-white hover:bg-purple-700 active:bg-purple-800 shadow-md hover:shadow-lg"
        PRIMARY_FULL = f"{BASE} {PRIMARY}"

        # Secondary (Gray)
        SECONDARY = "bg-gray-200 text-gray-800 hover:bg-gray-300 dark:bg-slate-700 dark:text-gray-100 dark:hover:bg-slate-600"
        SECONDARY_FULL = f"{BASE} {SECONDARY}"

        # Ghost (Transparent with hover)
        GHOST = "bg-transparent text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-slate-800"
        GHOST_FULL = f"{BASE} {GHOST}"

        # Outline (Border only)
        OUTLINE = "bg-transparent border-2 border-purple-600 text-purple-600 hover:bg-purple-50 dark:border-purple-500 dark:text-purple-400 dark:hover:bg-slate-800"
        OUTLINE_FULL = f"{BASE} {OUTLINE}"

        # Icon button (circular, compact)
        ICON = "p-2 rounded-full text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-slate-800 transition-colors"

        # Sizes
        SM = "px-3 py-1.5 text-sm"
        MD = "px-4 py-2 text-base"
        LG = "px-6 py-3 text-lg"

    # ==========================================================================
    # CARDS - Modern Container Design
    # ==========================================================================

    class Cards:
        """Modern card styles with depth and shadows."""

        # Base card
        BASE = "rounded-2xl border bg-white dark:bg-slate-800 border-gray-200 dark:border-slate-700"

        # With padding
        PADDED = "p-6 rounded-2xl border bg-white dark:bg-slate-800 border-gray-200 dark:border-slate-700"

        # With shadow
        SHADOWED = "rounded-2xl border bg-white dark:bg-slate-800 border-gray-200 dark:border-slate-700 shadow-lg"

        # Interactive (hover effect)
        INTERACTIVE = "rounded-2xl border bg-white dark:bg-slate-800 border-gray-200 dark:border-slate-700 hover:shadow-xl transition-shadow cursor-pointer"

        # Info card (blue tint)
        INFO = "rounded-2xl bg-blue-50 dark:bg-slate-800 border-l-4 border-blue-500 p-4"

        # Success card (green tint)
        SUCCESS = "rounded-2xl bg-green-50 dark:bg-slate-800 border-l-4 border-green-500 p-4"

        # Warning card (amber tint)
        WARNING = "rounded-2xl bg-amber-50 dark:bg-slate-800 border-l-4 border-amber-500 p-4"

        # Error card (red tint)
        ERROR = "rounded-2xl bg-red-50 dark:bg-slate-800 border-l-4 border-red-500 p-4"

    # ==========================================================================
    # LAYOUT - Two-Column Design
    # ==========================================================================

    class Layout:
        """Layout components for modern UI structure."""

        # Header (top bar)
        HEADER = "bg-white dark:bg-slate-900 border-b border-gray-200 dark:border-slate-800 px-6 py-3 shadow-sm flex items-center gap-4"

        # Sidebar (left drawer)
        SIDEBAR = "bg-white dark:bg-slate-900 border-r border-gray-200 dark:border-slate-700 p-6 shadow-lg"

        # Main content area
        MAIN = "flex-1 bg-gray-50 dark:bg-slate-950 overflow-auto"

        # Footer (bottom bar)
        FOOTER = "bg-white dark:bg-slate-900 border-t border-gray-200 dark:border-slate-800 px-6 py-4"

        # Chat container (centered, max-width)
        CHAT_CONTAINER = "w-full max-w-4xl mx-auto p-6 space-y-4"

    # ==========================================================================
    # INPUTS - Modern Form Elements
    # ==========================================================================

    class Inputs:
        """Modern input field styles."""

        # Base input
        BASE = "w-full px-4 py-2 rounded-xl border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all"

        # Chat input (larger, more prominent)
        CHAT = "flex-1 px-4 py-3 rounded-2xl border-0 bg-transparent text-gray-900 dark:text-gray-100 text-base focus:outline-none"

        # Input container (chat bar)
        CHAT_BAR = "w-full flex items-center gap-3 px-4 py-2 rounded-2xl bg-gray-100 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 shadow-sm focus-within:ring-2 focus-within:ring-purple-500 transition-all"

    # ==========================================================================
    # ANIMATIONS - Smooth Transitions
    # ==========================================================================

    class Animations:
        """Animation and transition classes."""

        # Loading pulse
        PULSE = "animate-pulse"

        # Fade in
        FADE_IN = "animate-fade-in opacity-0"

        # Slide up
        SLIDE_UP = "animate-slide-up transform translate-y-4"

        # Smooth transition (all properties)
        TRANSITION = "transition-all duration-200 ease-in-out"

        # Smooth transition (colors only)
        TRANSITION_COLORS = "transition-colors duration-200 ease-in-out"

        # Hover lift effect
        HOVER_LIFT = "hover:-translate-y-0.5 hover:shadow-lg transition-all duration-200"

    # ==========================================================================
    # BADGES & CHIPS
    # ==========================================================================

    class Badges:
        """Modern badge and chip styles."""

        # Base badge
        BASE = "px-3 py-1 rounded-full text-xs font-semibold"

        # Purple
        PURPLE = "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400"
        PURPLE_FULL = f"{BASE} {PURPLE}"

        # Blue
        BLUE = "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
        BLUE_FULL = f"{BASE} {BLUE}"

        # Green
        GREEN = "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
        GREEN_FULL = f"{BASE} {GREEN}"

        # Amber
        AMBER = "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
        AMBER_FULL = f"{BASE} {AMBER}"

        # Red
        RED = "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
        RED_FULL = f"{BASE} {RED}"

        # Chip (interactive, pill-shaped)
        CHIP = "px-4 py-2 rounded-full border-2 border-purple-500 text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-slate-800 cursor-pointer transition-colors"

    # ==========================================================================
    # TEXT COLORS - Semantic Colors
    # ==========================================================================

    class TextColors:
        """Semantic text color classes."""

        PRIMARY = "text-gray-900 dark:text-gray-100"
        SECONDARY = "text-gray-600 dark:text-gray-400"
        MUTED = "text-gray-500 dark:text-gray-500"

        ACCENT = "text-purple-600 dark:text-purple-400"
        LINK = "text-blue-600 dark:text-blue-400 hover:underline cursor-pointer"

        SUCCESS = "text-green-600 dark:text-green-400"
        WARNING = "text-amber-600 dark:text-amber-400"
        ERROR = "text-red-600 dark:text-red-400"
        INFO = "text-blue-600 dark:text-blue-400"

    # ==========================================================================
    # AVATARS
    # ==========================================================================

    class Avatars:
        """Avatar styles for chat interface."""

        BASE = "rounded-full flex items-center justify-center font-semibold"

        # Sizes
        SM = "w-8 h-8 text-sm"
        MD = "w-10 h-10 text-base"
        LG = "w-12 h-12 text-lg"

        # AI avatar (purple)
        AI = "bg-purple-600 text-white"
        AI_FULL = f"{BASE} {MD} {AI}"

        # User avatar (gray)
        USER = "bg-gray-400 text-white"
        USER_FULL = f"{BASE} {MD} {USER}"

    # ==========================================================================
    # HELPER METHODS
    # ==========================================================================

    @staticmethod
    def combine(*classes: str) -> str:
        """Combine multiple class strings into one."""
        return " ".join(filter(None, classes))

    @classmethod
    def get_chat_bubble(cls, role: str, rag_enhanced: bool = False) -> str:
        """Get appropriate chat bubble style based on role."""
        if role == "user":
            return cls.ChatBubbles.USER_FULL
        elif role == "system":
            return cls.ChatBubbles.SYSTEM_FULL
        elif rag_enhanced:
            return cls.ChatBubbles.RAG_FULL
        else:
            return cls.ChatBubbles.AI_FULL

    @classmethod
    def get_button(cls, variant: str = "primary", size: str = "md") -> str:
        """Get button style based on variant and size."""
        variant_map = {
            "primary": cls.Buttons.PRIMARY,
            "secondary": cls.Buttons.SECONDARY,
            "ghost": cls.Buttons.GHOST,
            "outline": cls.Buttons.OUTLINE,
        }
        size_map = {
            "sm": cls.Buttons.SM,
            "md": cls.Buttons.MD,
            "lg": cls.Buttons.LG,
        }

        base = cls.Buttons.BASE
        variant_class = variant_map.get(variant, cls.Buttons.PRIMARY)
        size_class = size_map.get(size, cls.Buttons.MD)

        return cls.combine(base, variant_class, size_class)


# ==========================================================================
# CUSTOM CSS FOR ADDITIONAL ANIMATIONS
# ==========================================================================

MODERN_CSS = r"""
<style>
/* Custom Font Import */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Apply Inter font globally */
body {
    font-family: 'Inter', 'SF Pro Display', 'Segoe UI', system-ui, -apple-system, sans-serif;
}

/* Smooth scroll behavior */
html {
    scroll-behavior: smooth;
}

/* Custom animations */
@keyframes fade-in {
    from {
        opacity: 0;
    }
    to {
        opacity: 1;
    }
}

@keyframes slide-up {
    from {
        opacity: 0;
        transform: translateY(16px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.animate-fade-in {
    animation: fade-in 0.3s ease-in-out forwards;
}

.animate-slide-up {
    animation: slide-up 0.4s ease-out forwards;
}

/* Message appearance animation */
.chat-message {
    animation: slide-up 0.3s ease-out;
}

/* Typing indicator */
.typing-indicator {
    display: inline-flex;
    gap: 4px;
}

.typing-indicator span {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: currentColor;
    opacity: 0.4;
    animation: typing-pulse 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
    animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
    animation-delay: 0.4s;
}

@keyframes typing-pulse {
    0%, 60%, 100% {
        opacity: 0.4;
        transform: scale(1);
    }
    30% {
        opacity: 1;
        transform: scale(1.2);
    }
}

/* Smooth focus ring */
*:focus-visible {
    outline: 2px solid #8B5CF6;
    outline-offset: 2px;
    border-radius: 8px;
}

/* Better code block styling */
code {
    background-color: rgba(139, 92, 246, 0.1);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
    font-size: 0.9em;
}

pre code {
    background-color: transparent;
    padding: 0;
}

/* Markdown content spacing */
.markdown-content p {
    margin-bottom: 1em;
}

.markdown-content ul, .markdown-content ol {
    margin-left: 1.5em;
    margin-bottom: 1em;
}

.markdown-content li {
    margin-bottom: 0.5em;
}

/* Smooth hover transitions on interactive elements */
button, a, .clickable {
    transition: all 0.2s ease-in-out;
}

/* Custom scrollbar (WebKit browsers) */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: transparent;
}

::-webkit-scrollbar-thumb {
    background: rgba(139, 92, 246, 0.3);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: rgba(139, 92, 246, 0.5);
}

/* Dark mode scrollbar */
.dark ::-webkit-scrollbar-thumb {
    background: rgba(139, 92, 246, 0.4);
}

.dark ::-webkit-scrollbar-thumb:hover {
    background: rgba(139, 92, 246, 0.6);
}
/* =================================================================== */
/* REFINED POLISH - Claude-like Chiseled Interface */
/* =================================================================== */

/* Smooth transitions for all interactive elements */
* {
    transition-property: background-color, border-color, color, fill, stroke, opacity, box-shadow, transform;
    transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
    transition-duration: 200ms;
}

/* Refined shadow system - subtle depth */
.shadow-refined {
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1),
                0 1px 2px 0 rgba(0, 0, 0, 0.06);
}

.shadow-refined-lg {
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1),
                0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.shadow-refined-xl {
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1),
                0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

/* Refined borders */
.border-refined {
    border: 1px solid rgba(0, 0, 0, 0.06);
}

.dark .border-refined {
    border: 1px solid rgba(255, 255, 255, 0.08);
}

/* Glass morphism effect */
.glass {
    background: rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
}

.dark .glass {
    background: rgba(15, 23, 42, 0.8);
}

/* Button press animation */
@keyframes button-press {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(0.98); }
}

.btn-press:active {
    animation: button-press 0.15s ease-in-out;
}

/* Micro-interactions */
@keyframes fade-in-up {
    from {
        opacity: 0;
        transform: translateY(8px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.animate-fade-in-up {
    animation: fade-in-up 0.3s ease-out;
}

/* Shimmer effect for loading states */
@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

.shimmer {
    background: linear-gradient(
        90deg,
        rgba(255, 255, 255, 0) 0%,
        rgba(255, 255, 255, 0.2) 50%,
        rgba(255, 255, 255, 0) 100%
    );
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
}

/* Enhanced switch/toggle visibility */
.q-toggle__track {
    opacity: 1 !important;
}

.q-toggle--dark .q-toggle__track {
    opacity: 0.8 !important;
}

/* Improved button hover states */
button:hover:not(:disabled) {
    transform: translateY(-1px);
}

button:active:not(:disabled) {
    transform: translateY(0);
}

/* Enhanced card interactions */
.q-card {
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.q-card:hover {
    transform: translateY(-2px);
}

/* Smooth icon rotations */
.transition-transform {
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.rotate-90 {
    transform: rotate(90deg);
}

.hover\:rotate-180:hover {
    transform: rotate(180deg);
}

/* Enhanced focus rings */
*:focus-visible {
    outline: 2px solid #8B5CF6;
    outline-offset: 2px;
    border-radius: 4px;
}

.dark *:focus-visible {
    outline-color: #A78BFA;
}

/* ========================================================================== */
/* WCAG CONTRAST FIXES - Ensure all elements meet accessibility standards */
/* ========================================================================== */

/* Fix 1: Purple text (Logo, RAG label) - darken for better contrast */
/* Original: #8B5CF6 (4.23:1) -> Need: 4.5:1+ */
.text-purple-600 {
    color: #7C3AED !important; /* purple-600, darker */
}

/* Fix 2: Inactive toggle track - increase visibility */
/* Original: too light gray (1.24:1) -> Need: 3:1+ */
.q-toggle__track:not(.q-toggle--truthy .q-toggle__track) {
    opacity: 1 !important;
    background: #6B7280 !important; /* gray-500 for 4.83:1 contrast */
}

.dark .q-toggle__track:not(.q-toggle--truthy .q-toggle__track) {
    opacity: 1 !important;
    background: #64748B !important; /* slate-500, lighter for 3.75:1 contrast */
}

/* Fix 3: Borders - increase contrast */
/* Original: #E5E7EB (1.24:1) -> Need: 3:1+ */
.border-gray-100,
.dark\:border-gray-700,
.border {
    border-color: #6B7280 !important; /* gray-500 for 4.83:1 contrast */
}

.dark .border-gray-100,
.dark .dark\:border-gray-700,
.dark .border {
    border-color: #64748B !important; /* slate-500 for 3.07:1 contrast */
}

/* Fix 4: Input placeholder - increase contrast */
/* Light mode: #9CA3AF (2.54:1) -> Need: 4.5:1+ */
/* Dark mode: #64748B (3.75:1) -> Need: 4.5:1+ */
input::placeholder,
textarea::placeholder,
.q-field__native::placeholder {
    color: #6B7280 !important; /* gray-500 for light mode */
    opacity: 1 !important;
}

.dark input::placeholder,
.dark textarea::placeholder,
.dark .q-field__native::placeholder {
    color: #94A3B8 !important; /* slate-400 for dark mode */
    opacity: 1 !important;
}

/* Fix 5: User message bubble - use darker purple background */
/* Original: #8B5CF6 with white text (4.23:1) -> Need: 4.5:1+ */
.bg-gradient-to-br.from-purple-600.to-purple-700,
.bg-purple-600 {
    background: linear-gradient(to bottom right, #7C3AED, #6D28D9) !important;
}

/* Fix 6: Secondary text and icons - ensure minimum 4.5:1 for text, 3:1 for icons */
.text-gray-500 {
    color: #6B7280 !important;
}

.dark .text-gray-500,
.dark .text-slate-400 {
    color: #94A3B8 !important; /* slate-400 */
}

/* Icon color adjustments for better visibility */
.q-icon {
    opacity: 1 !important;
}

/* Ensure RAG toggle label is visible in both modes */
.text-purple-600.dark\:text-purple-400 {
    color: #7C3AED !important; /* darker purple for light mode */
}

.dark .text-purple-600.dark\:text-purple-400 {
    color: #C4B5FD !important; /* purple-300, lighter for dark mode */
}

</style>
"""
