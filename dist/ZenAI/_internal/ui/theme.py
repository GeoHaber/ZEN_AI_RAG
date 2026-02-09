# -*- coding: utf-8 -*-
"""
ui/theme.py - Design Tokens & Theme Configuration
Centralized color palette, typography, and spacing values.

All CSS variables and design tokens should be defined here,
then referenced throughout the application.
"""

class Colors:
    """Color palette for the application."""
    
    # ==========================================================================
    # PRIMARY BRAND COLORS
    # ==========================================================================
    PRIMARY = "#3b82f6"        # Blue-500
    PRIMARY_HOVER = "#2563eb"  # Blue-600
    PRIMARY_LIGHT = "#60a5fa"  # Blue-400
    PRIMARY_DARK = "#1d4ed8"   # Blue-700
    
    SECONDARY = "#6c757d"      # Gray
    ACCENT = "#17a2b8"         # Cyan
    
    # ==========================================================================
    # SEMANTIC COLORS
    # ==========================================================================
    SUCCESS = "#22c55e"        # Green-500
    SUCCESS_LIGHT = "#86efac"  # Green-300
    WARNING = "#f59e0b"        # Amber-500
    ERROR = "#ef4444"          # Red-500
    INFO = "#3b82f6"           # Blue-500
    
    # ==========================================================================
    # LIGHT MODE PALETTE
    # ==========================================================================
    LIGHT_BG = "#f8fafc"           # Slate-50
    LIGHT_BG_SECONDARY = "#f1f5f9" # Slate-100
    LIGHT_CARD = "#ffffff"         # White
    LIGHT_CARD_HOVER = "#f8fafc"   # Slate-50
    LIGHT_BORDER = "#e2e8f0"       # Slate-200
    LIGHT_BORDER_STRONG = "#cbd5e1" # Slate-300
    
    LIGHT_TEXT = "#1e293b"         # Slate-800
    LIGHT_TEXT_SECONDARY = "#64748b" # Slate-500
    LIGHT_TEXT_MUTED = "#94a3b8"   # Slate-400
    
    # ==========================================================================
    # DARK MODE PALETTE
    # ==========================================================================
    DARK_BG = "#0f172a"            # Slate-950
    DARK_BG_SECONDARY = "#1e293b"  # Slate-800
    DARK_CARD = "#1e293b"          # Slate-800
    DARK_CARD_HOVER = "#334155"    # Slate-700
    DARK_BORDER = "#334155"        # Slate-700
    DARK_BORDER_STRONG = "#475569" # Slate-600
    
    DARK_TEXT = "#f1f5f9"          # Slate-100
    DARK_TEXT_SECONDARY = "#cbd5e1" # Slate-300
    DARK_TEXT_MUTED = "#94a3b8"    # Slate-400
    
    # ==========================================================================
    # CHAT COLORS
    # ==========================================================================
    CHAT_USER_BG = "#3b82f6"       # Blue-500
    CHAT_USER_TEXT = "#ffffff"     # White
    CHAT_AI_BG_LIGHT = "#f1f5f9"   # Slate-100
    CHAT_AI_BG_DARK = "#1e293b"    # Slate-800
    CHAT_AI_TEXT_LIGHT = "#1e293b" # Slate-800
    CHAT_AI_TEXT_DARK = "#f1f5f9"  # Slate-100
    
    # RAG highlight
    RAG_HIGHLIGHT_BG_LIGHT = "#eff6ff"  # Blue-50
    RAG_HIGHLIGHT_BG_DARK = "#1e293b"   # Slate-800
    RAG_HIGHLIGHT_BORDER = "#3b82f6"    # Blue-500


class Typography:
    """Typography settings."""
    
    # Font families
    FONT_FAMILY = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    FONT_MONO = "'JetBrains Mono', 'Fira Code', 'Consolas', monospace"
    
    # Font sizes (rem)
    SIZE_XS = "0.75rem"    # 12px
    SIZE_SM = "0.875rem"   # 14px
    SIZE_BASE = "1rem"     # 16px
    SIZE_LG = "1.125rem"   # 18px
    SIZE_XL = "1.25rem"    # 20px
    SIZE_2XL = "1.5rem"    # 24px
    SIZE_3XL = "1.875rem"  # 30px
    
    # Font weights
    WEIGHT_NORMAL = "400"
    WEIGHT_MEDIUM = "500"
    WEIGHT_SEMIBOLD = "600"
    WEIGHT_BOLD = "700"
    
    # Line heights
    LINE_TIGHT = "1.25"
    LINE_NORMAL = "1.5"
    LINE_RELAXED = "1.625"


class Spacing:
    """Spacing values for consistent layout."""
    
    # Base spacing unit (4px)
    UNIT = 4
    
    # Named spacing
    XS = "4px"      # 1 unit
    SM = "8px"      # 2 units
    MD = "12px"     # 3 units
    LG = "16px"     # 4 units
    XL = "24px"     # 6 units
    XXL = "32px"    # 8 units
    XXXL = "48px"   # 12 units
    
    # Padding presets
    PAD_CARD = "16px"
    PAD_BUTTON = "12px 18px"
    PAD_INPUT = "12px 16px"
    PAD_DIALOG = "24px"
    
    # Gap presets
    GAP_SM = "8px"
    GAP_MD = "12px"
    GAP_LG = "16px"
    GAP_XL = "24px"


class BorderRadius:
    """Border radius values."""
    
    NONE = "0"
    SM = "4px"
    MD = "8px"
    LG = "12px"
    XL = "16px"
    XXL = "24px"
    FULL = "9999px"  # Pill shape
    
    # Component-specific
    BUTTON = "8px"
    CARD = "16px"
    INPUT = "10px"
    CHAT_BUBBLE = "18px"
    AVATAR = "9999px"
    DIALOG = "16px"
    MENU = "12px"


class Shadows:
    """Box shadow values."""
    
    NONE = "none"
    SM = "0 1px 2px 0 rgba(0, 0, 0, 0.05)"
    MD = "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)"
    LG = "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)"
    XL = "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)"
    
    # Dark mode shadows (more pronounced)
    DARK_SM = "0 1px 2px 0 rgba(0, 0, 0, 0.3)"
    DARK_MD = "0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -1px rgba(0, 0, 0, 0.2)"
    DARK_LG = "0 10px 15px -3px rgba(0, 0, 0, 0.5)"


class Transitions:
    """CSS transition presets."""
    
    FAST = "all 0.15s ease"
    NORMAL = "all 0.2s ease"
    SLOW = "all 0.3s ease"
    
    # Specific transitions
    COLORS = "color 0.2s ease, background-color 0.2s ease, border-color 0.2s ease"
    TRANSFORM = "transform 0.2s ease"
    OPACITY = "opacity 0.2s ease"
    SHADOW = "box-shadow 0.2s ease"


class Theme:
    """
    Combined theme configuration.
    Central access point for all design tokens.
    """
    
    # Sub-modules
    colors = Colors
    typography = Typography
    spacing = Spacing
    radius = BorderRadius
    shadows = Shadows
    transitions = Transitions
    
    # Quick access to common values
    PRIMARY = Colors.PRIMARY
    FONT_FAMILY = Typography.FONT_FAMILY
    
    @classmethod
    def get_css_variables(cls) -> str:
        """Generate CSS custom properties from theme values."""
        return f"""
            :root {{
                /* Colors */
                --primary: {Colors.PRIMARY};
                --primary-hover: {Colors.PRIMARY_HOVER};
                --primary-light: {Colors.PRIMARY_LIGHT};
                --success: {Colors.SUCCESS};
                --warning: {Colors.WARNING};
                --error: {Colors.ERROR};
                
                /* Light mode */
                --light-bg: {Colors.LIGHT_BG};
                --light-card: {Colors.LIGHT_CARD};
                --light-border: {Colors.LIGHT_BORDER};
                --light-text: {Colors.LIGHT_TEXT};
                --light-text-secondary: {Colors.LIGHT_TEXT_SECONDARY};
                
                /* Dark mode */
                --dark-bg: {Colors.DARK_BG};
                --dark-card: {Colors.DARK_CARD};
                --dark-border: {Colors.DARK_BORDER};
                --dark-text: {Colors.DARK_TEXT};
                --dark-text-secondary: {Colors.DARK_TEXT_SECONDARY};
                
                /* Typography */
                --font-family: {Typography.FONT_FAMILY};
                --font-mono: {Typography.FONT_MONO};
                
                /* Spacing */
                --spacing-sm: {Spacing.SM};
                --spacing-md: {Spacing.MD};
                --spacing-lg: {Spacing.LG};
                --spacing-xl: {Spacing.XL};
                
                /* Border radius */
                --radius-sm: {BorderRadius.SM};
                --radius-md: {BorderRadius.MD};
                --radius-lg: {BorderRadius.LG};
                --radius-full: {BorderRadius.FULL};
                
                /* Shadows */
                --shadow-sm: {Shadows.SM};
                --shadow-md: {Shadows.MD};
                --shadow-lg: {Shadows.LG};
            }}
        """
