# Modern UI Theme Guide - ZenAI

**Date:** 2026-01-24
**Version:** 1.0
**Status:** Phase 1 Complete - Beautiful UI Polish

---

## Overview

The **Modern UI Theme** transforms ZenAI's interface with a beautiful, Claude-inspired design featuring:

- **Purple primary color** (#8B5CF6) - Professional, modern accent
- **Clean chat bubbles** - Rounded, spacious, easy to read
- **Smooth animations** - Fade-in, slide-up, typing indicators
- **Modern typography** - Inter font family, better spacing
- **Dark mode** - Cohesive color scheme with proper contrast
- **Separation from backend** - UI components are standalone and testable

---

## What's New

### Phase 1 Deliverables (Complete)

✅ **Modern Theme System** (`ui/modern_theme.py`)
- Claude-inspired color palette
- Typography system (Inter font)
- Spacing guidelines (4px base unit)
- Organized style classes

✅ **Modern Chat Components** (`ui/modern_chat.py`)
- `ModernChatMessage` - Beautiful chat bubbles
- `ModernTypingIndicator` - Animated thinking dots
- `ModernInputBar` - Modern input with file/voice support
- `ModernActionChips` - Quick action pills
- `ModernWelcomeMessage` - Elegant welcome screen

✅ **Custom CSS & Animations** (`ui/modern_theme.py`)
- Smooth fade-in/slide-up animations
- Typing indicator pulse
- Custom scrollbar styling
- Focus ring improvements
- Code block styling

✅ **Live Demo** (`ui/modern_ui_demo.py`)
- Standalone demo showcasing all components
- Run: `python ui/modern_ui_demo.py`
- Access: http://localhost:8090

---

## File Structure

```
ui/
├── modern_theme.py         # Theme system (colors, typography, styles)
├── modern_chat.py          # Chat UI components
├── modern_ui_demo.py       # Live demo (standalone)
├── __init__.py             # Updated to export modern theme
├── styles.py               # Original styles (still valid)
├── theme.py                # Original theme (still valid)
└── ...
```

---

## Quick Start

### 1. Import the Modern Theme

```python
from ui.modern_theme import ModernTheme as MT, MODERN_CSS
from ui.modern_chat import ModernChatMessage, ModernInputBar
```

### 2. Add Custom CSS (Once per Page)

```python
from nicegui import ui

@ui.page('/')
def my_page():
    # Add modern CSS animations
    ui.add_head_html(MODERN_CSS)

    # Your UI code here...
```

### 3. Use Modern Components

```python
# Create a chat message
msg = ModernChatMessage(
    role='assistant',
    content='Hello! I am using the modern UI!',
    avatar_text='Z',
    rag_enhanced=False
)
msg.render(chat_container)

# Create modern input bar
input_bar = ModernInputBar(
    on_send=handle_send_message,
    placeholder='Type your message...'
)
input_bar.render()
```

---

## Color Palette

### Primary Colors (Purple - Claude-Inspired)

```python
MT.PURPLE_500 = "#8B5CF6"   # Primary purple
MT.PURPLE_600 = "#7C3AED"   # Darker purple (hover)
MT.PURPLE_400 = "#A78BFA"   # Lighter purple
```

### Neutral Colors (Light Mode)

```python
MT.WHITE = "#FFFFFF"
MT.GRAY_50 = "#F9FAFB"      # Background
MT.GRAY_100 = "#F3F4F6"     # Chat bubbles
MT.GRAY_900 = "#111827"     # Text
```

### Neutral Colors (Dark Mode)

```python
MT.SLATE_950 = "#020617"    # Background
MT.SLATE_900 = "#0F172A"    # Header/Footer
MT.SLATE_800 = "#1E293B"    # Chat bubbles
```

### Accent Colors

```python
MT.BLUE_500 = "#3B82F6"     # Info, RAG
MT.GREEN_500 = "#10B981"    # Success
MT.RED_500 = "#EF4444"      # Error
MT.AMBER_500 = "#F59E0B"    # Warning
```

---

## Typography

### Font Families

```python
# Sans-serif (UI text)
MT.FONT_SANS = "'Inter', 'SF Pro Display', 'Segoe UI', system-ui, sans-serif"

# Monospace (code blocks)
MT.FONT_MONO = "'Fira Code', 'Cascadia Code', 'Consolas', monospace"
```

### Font Sizes

```python
MT.TEXT_XS = "text-xs"      # 12px - Labels, metadata
MT.TEXT_SM = "text-sm"      # 14px - Secondary text
MT.TEXT_BASE = "text-base"  # 16px - Body text (default)
MT.TEXT_LG = "text-lg"      # 18px - Emphasized text
MT.TEXT_XL = "text-xl"      # 20px - Headings
MT.TEXT_2XL = "text-2xl"    # 24px - Page titles
MT.TEXT_3XL = "text-3xl"    # 30px - Hero text
```

### Font Weights

```python
MT.FONT_NORMAL = "font-normal"      # 400 (default)
MT.FONT_MEDIUM = "font-medium"      # 500
MT.FONT_SEMIBOLD = "font-semibold"  # 600
MT.FONT_BOLD = "font-bold"          # 700
```

---

## Chat Bubbles

### User Message

```python
msg = ModernChatMessage(
    role='user',
    content='Hello, this is a user message!',
    avatar_text='U'
)
msg.render(chat_container)
```

**Styling:**
- Purple background (#8B5CF6)
- White text
- Right-aligned
- Avatar on the right

### AI Response

```python
msg = ModernChatMessage(
    role='assistant',
    content='I am Zena, your AI assistant!',
    avatar_text='Z'
)
msg.render(chat_container)
```

**Styling:**
- Light gray background (light mode)
- Dark gray background (dark mode)
- Left-aligned
- Avatar on the left (purple)

### RAG-Enhanced Response

```python
msg = ModernChatMessage(
    role='assistant',
    content='Answer based on knowledge base...',
    avatar_text='Z',
    rag_enhanced=True,
    sources=[
        {
            'title': 'Source Document',
            'url': 'https://example.com',
            'text': 'Preview text...'
        }
    ]
)
msg.render(chat_container)
```

**Styling:**
- Blue tint background
- Blue left border
- Sources expansion panel
- Clickable source links

### System Message

```python
msg = ModernChatMessage(
    role='system',
    content='Connection established'
)
msg.render(chat_container)
```

**Styling:**
- Subtle gray background
- Centered
- Italic text
- Smaller font size

---

## Buttons

### Primary Button (Purple)

```python
ui.button('Submit').classes(MT.Buttons.PRIMARY_FULL)
```

**Styling:**
- Purple background
- White text
- Hover: darker purple
- Shadow on hover

### Secondary Button (Gray)

```python
ui.button('Cancel').classes(MT.Buttons.SECONDARY_FULL)
```

### Ghost Button (Transparent)

```python
ui.button('Learn More').classes(MT.Buttons.GHOST_FULL)
```

### Outline Button (Border Only)

```python
ui.button('Options').classes(MT.Buttons.OUTLINE_FULL)
```

### Icon Button (Circular)

```python
ui.button(icon='settings').classes(MT.Buttons.ICON)
```

---

## Cards

### Basic Card

```python
with ui.card().classes(MT.Cards.PADDED):
    ui.label('Card content')
```

### Interactive Card (Hover Effect)

```python
with ui.card().classes(MT.Cards.INTERACTIVE):
    ui.label('Click me!')
```

### Info Card (Blue Tint)

```python
with ui.card().classes(MT.Cards.INFO):
    ui.label('This is informational')
```

### Success/Warning/Error Cards

```python
# Success (green tint)
with ui.card().classes(MT.Cards.SUCCESS):
    ui.label('Success!')

# Warning (amber tint)
with ui.card().classes(MT.Cards.WARNING):
    ui.label('Warning!')

# Error (red tint)
with ui.card().classes(MT.Cards.ERROR):
    ui.label('Error!')
```

---

## Layout Components

### Header

```python
with ui.header().classes(MT.Layout.HEADER):
    ui.button(icon='menu').classes(MT.Buttons.ICON)
    ui.label('ZenAI').classes(MT.TEXT_XL)
    ui.space()
    ui.button(icon='settings').classes(MT.Buttons.ICON)
```

### Chat Container

```python
scroll_area = ui.scroll_area().classes('w-full').style(
    'height: calc(100vh - 200px);'
)

with scroll_area:
    chat_container = ui.column().classes(MT.Layout.CHAT_CONTAINER)
```

### Footer

```python
with ui.footer().classes(MT.Layout.FOOTER):
    input_bar = ModernInputBar(on_send=handle_send)
    input_bar.render()
```

---

## Animations

### Fade In

```python
ui.label('Fading in...').classes(MT.Animations.FADE_IN)
```

### Slide Up

```python
ui.label('Sliding up...').classes(MT.Animations.SLIDE_UP)
```

### Typing Indicator

```python
indicator = ModernTypingIndicator()
indicator.render(chat_container)

# Remove after response
indicator.remove()
```

---

## Input Components

### Modern Input Bar

```python
async def handle_send(message):
    print(f'User sent: {message}')

async def handle_upload(e):
    print(f'File uploaded: {e.name}')

async def handle_voice():
    print('Voice recording started')

input_bar = ModernInputBar(
    on_send=handle_send,
    on_upload=handle_upload,
    on_voice=handle_voice,
    placeholder='Type your message...'
)
input_bar.render()
```

**Features:**
- Large, rounded input field
- File attachment button
- Voice recording button
- Send button (purple)
- Attachment preview

---

## Quick Action Chips

```python
actions = [
    {'label': 'Help', 'value': 'help'},
    {'label': 'Examples', 'value': 'examples'},
    {'label': 'Settings', 'value': 'settings'},
]

async def handle_chip(value):
    print(f'Chip clicked: {value}')

chips = ModernActionChips(actions=actions, on_click=handle_chip)
chips.render(chat_container)
```

**Styling:**
- Pill-shaped (fully rounded)
- Purple border
- Purple text
- Hover: light purple background

---

## Welcome Message

```python
welcome = ModernWelcomeMessage(
    app_name='ZenAI',
    features=[
        'Fast local AI responses',
        'Beautiful modern UI',
        'Dark mode support'
    ],
    custom_message='Welcome to the future of AI assistance'
)
welcome.render(chat_container)
```

**Features:**
- Large, centered title
- Feature cards
- Smooth fade-in animation
- Getting started hint

---

## Helper Methods

### Combine Classes

```python
# Combine multiple class strings
combined = MT.combine(
    MT.TEXT_LG,
    MT.FONT_BOLD,
    MT.TextColors.ACCENT,
    'mb-4'
)

ui.label('Hello').classes(combined)
```

### Get Chat Bubble Style

```python
# Get appropriate bubble style based on role
bubble_class = MT.get_chat_bubble('user')
bubble_class = MT.get_chat_bubble('assistant', rag_enhanced=True)
```

### Get Button Style

```python
# Get button style with variant and size
btn_class = MT.get_button('primary', 'lg')
btn_class = MT.get_button('outline', 'sm')
```

---

## Dark Mode Support

All components automatically support dark mode via Tailwind's `dark:` variants:

```python
# This automatically handles both light and dark modes
ui.label('Text').classes(MT.TextColors.PRIMARY)
# Light mode: text-gray-900
# Dark mode: text-gray-100

ui.card().classes(MT.Cards.PADDED)
# Light mode: bg-white
# Dark mode: bg-slate-800
```

---

## Running the Demo

### Start the Demo Server

```bash
cd ui
python modern_ui_demo.py
```

### Access in Browser

```
http://localhost:8090
```

### Demo Features

- ✅ Modern chat bubbles (user, AI, RAG, system)
- ✅ Typing indicator animation
- ✅ Quick action chips
- ✅ Welcome message
- ✅ Modern input bar
- ✅ Dark mode toggle
- ✅ Interactive examples

---

## Integration with Main App

### Step 1: Import Components

```python
# In zena.py
from ui.modern_theme import ModernTheme as MT, MODERN_CSS
from ui.modern_chat import ModernChatMessage, ModernInputBar, add_modern_css
```

### Step 2: Add CSS (Once)

```python
@ui.page('/')
async def main_page():
    # Add modern CSS
    add_modern_css(None)

    # Rest of page setup...
```

### Step 3: Replace Chat Bubbles

```python
# OLD: Manual chat bubble creation
def add_message(role, content):
    with ui.row():
        ui.markdown(content).classes('bg-gray-100 p-4 rounded-3xl')

# NEW: Modern chat message
def add_message(role, content, rag_enhanced=False):
    msg = ModernChatMessage(
        role=role,
        content=content,
        avatar_text='Z' if role == 'assistant' else 'U',
        rag_enhanced=rag_enhanced
    )
    msg.render(chat_container)
```

### Step 4: Replace Input Bar

```python
# OLD: Basic input
ui.input(placeholder='Type...').classes('flex-1')
ui.button(icon='send', on_click=send)

# NEW: Modern input bar
input_bar = ModernInputBar(
    on_send=handle_send,
    on_upload=handle_upload,
    on_voice=handle_voice,
    placeholder='Type your message...'
)
input_bar.render()
```

---

## Customization

### Changing Primary Color

To change from purple to another color, edit `ui/modern_theme.py`:

```python
# Change these values
PURPLE_500 = "#8B5CF6"  # Replace with your color
PURPLE_600 = "#7C3AED"  # Darker shade
PURPLE_400 = "#A78BFA"  # Lighter shade
```

### Adding New Components

```python
class MyCustomComponent:
    def render(self, container):
        with ui.card().classes(MT.Cards.PADDED).move(container):
            ui.label('Custom Component').classes(
                MT.combine(MT.TEXT_LG, MT.FONT_BOLD)
            )
```

---

## Design Principles

1. **Minimalism** - Focus on content, reduce visual clutter
2. **Whitespace** - Generous padding and margins
3. **Hierarchy** - Clear visual distinction between elements
4. **Consistency** - Unified color scheme and typography
5. **Smoothness** - Subtle animations and transitions

---

## Browser Compatibility

✅ Chrome/Edge (recommended)
✅ Firefox
✅ Safari
⚠️ IE11 (limited support)

---

## Performance

- **Custom CSS:** ~5 KB (minified)
- **Google Fonts (Inter):** ~15 KB (cached)
- **Animations:** GPU-accelerated (60fps)
- **Rendering:** Minimal re-renders via NiceGUI reactivity

---

## Next Steps

### Phase 2: Desktop App (Planned)

- Package with PyInstaller
- Create installers (Windows .exe, macOS .dmg)
- Add system tray integration
- Auto-updater

### Phase 3: Mobile Strategy (Future)

- Evaluate BeeWare (pure Python) or Flutter (Dart)
- Responsive design improvements
- Touch-friendly interactions

---

## Troubleshooting

### Issue: Fonts not loading

**Solution:** Check internet connection (Google Fonts requires CDN access)

```python
# Fallback if Google Fonts fails
font-family: 'Segoe UI', system-ui, sans-serif;
```

### Issue: Animations not working

**Solution:** Ensure `MODERN_CSS` is added to page head

```python
ui.add_head_html(MODERN_CSS)
```

### Issue: Dark mode colors incorrect

**Solution:** Verify Tailwind dark mode is enabled

```python
dark_mode = ui.dark_mode(value=True)
```

---

## Support

- **Documentation:** `UI_MODERN_THEME_GUIDE.md` (this file)
- **Demo:** `python ui/modern_ui_demo.py`
- **Source:** `ui/modern_theme.py`, `ui/modern_chat.py`

---

**Status:** ✅ Phase 1 Complete (2026-01-24)
**Next:** Integration with main zena.py application
