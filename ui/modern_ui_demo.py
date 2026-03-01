#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui/modern_ui_demo.py - Modern UI Component Demo
Standalone demo showcasing the new modern UI components.

Run this file to see the modern UI in action:
    python ui/modern_ui_demo.py

This demonstrates:
- Modern chat bubbles (user, AI, RAG-enhanced)
- Smooth animations
- Beautiful typography
- Purple accent colors (Claude-inspired)
- Dark mode support
- Modern input bar
- Action chips
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from nicegui import ui
from ui.modern_theme import ModernTheme as MT, MODERN_CSS
from ui.modern_chat import (
    ModernChatMessage,
    ModernTypingIndicator,
    ModernInputBar,
    ModernActionChips,
    ModernWelcomeMessage,
    add_modern_css
)


# ==========================================================================
# DEMO PAGE
# ==========================================================================



def _demo_page_continued(avatar_text, chat_container, content, features, icon, indicator, on_click, rag_enhanced, role, scroll_area, sources):
    """Continue demo_page logic."""
    msg2 = ModernChatMessage(
        role='assistant',
        content='''The new UI features a **Claude-inspired design** with:

**Visual Improvements:**
- Purple primary color (#8B5CF6)
- Clean, rounded chat bubbles
- Smooth animations and transitions
- Better typography with Inter font

**User Experience:**
- Larger padding for better readability
- Clear visual hierarchy
- Subtle shadows for depth
- Responsive design

**Dark Mode:**
- Cohesive dark color scheme
- Proper contrast ratios
- Smooth theme transitions

Try clicking the dark mode button to see it in action!''',
        avatar_text='Z'
    )
    msg2.render(chat_container)

    # System message
    msg3 = ModernChatMessage(
        role='system',
        content='UI components loaded successfully'
    )
    msg3.render(chat_container)

    # RAG-enhanced message
    msg4 = ModernChatMessage(
        role='assistant',
        content='''Based on the documentation, here's how to use the modern theme:

```python
from ui.modern_theme import ModernTheme as MT

# Use predefined styles
button = ui.button('Click me').classes(MT.Buttons.PRIMARY_FULL)

# Combine multiple classes
label = ui.label('Hello').classes(
    MT.combine(MT.TEXT_LG, MT.FONT_BOLD, MT.TextColors.ACCENT)
)
```

The theme provides organized classes for all UI elements!''',
        avatar_text='Z',
        rag_enhanced=True,
        sources=[
            {
                'title': 'ModernTheme Documentation',
                'url': 'ui/modern_theme.py',
                'text': 'The ModernTheme class provides Claude-inspired color palette, modern typography, and organized style classes for all UI components...'
            }
        ]
    )
    msg4.render(chat_container)

    # Footer with input bar
    with ui.footer().classes(MT.Layout.FOOTER):
        async def handle_send(message):
            """Handle message send"""
            # Add user message
            user_msg = ModernChatMessage(
                role='user',
                content=message,
                avatar_text='U'
            )
            user_msg.render(chat_container)

            # Show typing indicator
            indicator = ModernTypingIndicator()
            indicator.render(chat_container)
            scroll_area.scroll_to(percent=1.0)

            # Simulate AI response after 1.5 seconds
            import asyncio
            await asyncio.sleep(1.5)
            indicator.remove()

            # Add AI response
            ai_msg = ModernChatMessage(
                role='assistant',
                content=f'You said: "{message}"\n\nThis is a demo response showing the modern UI in action!',
                avatar_text='Z'
            )
            ai_msg.render(chat_container)
            scroll_area.scroll_to(percent=1.0)

        async def handle_upload(e):
            """Handle file upload"""
            ui.notify(f'File uploaded: {e.name}', color='positive')

        async def handle_voice():
            """Handle voice recording"""
            ui.notify('Voice recording not implemented in demo', color='info')

        input_bar = ModernInputBar(
            on_send=handle_send,
            on_upload=handle_upload,
            on_voice=handle_voice,
            placeholder='Type a message to see it in the modern UI...'
        )
        input_bar.render()

    # Info panel
    with ui.dialog() as info_dialog:
        with ui.card().classes(MT.Cards.PADDED + ' w-96'):
            ui.label('About This Demo').classes(
                MT.combine(MT.TEXT_XL, MT.FONT_BOLD, 'mb-4')
            )

            ui.markdown('''This demo showcases the new **Modern UI components** for ZenAI.

**Key Features:**
- Claude-inspired purple theme
- Beautiful chat bubbles
- Smooth animations
- Dark mode support
- Modern typography

**Components Used:**
- `ModernChatMessage`
- `ModernTypingIndicator`
- `ModernInputBar`
- `ModernActionChips`
- `ModernWelcomeMessage`

All components are **separate from the backend**, making them easy to integrate and test!''').classes('mb-4')

            ui.button('Close', on_click=info_dialog.close).classes(
                MT.Buttons.PRIMARY_FULL + ' w-full'
            )

    # Info button in header (add retroactively)
    with ui.header().classes(MT.Layout.HEADER):
        ui.button(
            icon='info',
            on_click=info_dialog.open
        ).props('flat').classes(MT.Buttons.ICON)


@ui.page('/')
def demo_page():
    """Modern UI Demo Page"""

    # Add custom CSS
    add_modern_css(None)

    # Dark mode toggle
    dark_mode = ui.dark_mode(value=False)

    # Header
    with ui.header().classes(MT.Layout.HEADER):
        ui.button(icon='menu').props('flat').classes(MT.Buttons.ICON)

        ui.label('Modern UI Demo').classes(
            MT.combine(MT.TEXT_XL, MT.FONT_SEMIBOLD, MT.TextColors.PRIMARY)
        )

        ui.space()

        # Dark mode toggle
        def toggle_dark():
            """Toggle dark."""
            if dark_mode.value:
                dark_mode.disable()
            else:
                dark_mode.enable()

        ui.button(
            icon='dark_mode' if not dark_mode.value else 'light_mode',
            on_click=toggle_dark
        ).props('flat').classes(MT.Buttons.ICON)

    # Main content area
    scroll_area = ui.scroll_area().classes('w-full').style(
        'height: calc(100vh - 200px); min-height: 300px;'
    )

    with scroll_area:
        chat_container = ui.column().classes(MT.Layout.CHAT_CONTAINER)

    # Welcome Message
    welcome = ModernWelcomeMessage(
        app_name='ZenAI',
        features=[
            'Beautiful Claude-inspired UI',
            'Smooth animations & transitions',
            'Purple accent colors',
            'Modern typography'
        ],
        custom_message='Experience the new modern interface'
    )
    welcome.render(chat_container)

    # Quick Action Chips
    actions = [
        {'label': 'Show User Message', 'value': 'user'},
        {'label': 'Show AI Response', 'value': 'ai'},
        {'label': 'Show RAG Message', 'value': 'rag'},
        {'label': 'Show Typing', 'value': 'typing'},
    ]

    async def handle_chip_click(value):
        """Handle quick action clicks"""
        if value == 'user':
            msg = ModernChatMessage(
                role='user',
                content='Hello! This is a user message with **markdown** support.',
                avatar_text='U'
            )
            msg.render(chat_container)
        elif value == 'ai':
            msg = ModernChatMessage(
                role='assistant',
                content='''This is an AI response! I can help you with:

1. Answering questions
2. Generating code
3. Explaining concepts
4. And much more!

**Note:** I support *Markdown* formatting!''',
                avatar_text='Z'
            )
            msg.render(chat_container)
        elif value == 'rag':
            msg = ModernChatMessage(
                role='assistant',
                content='This response is enhanced with RAG! I found relevant information from your knowledge base.',
                avatar_text='Z',
                rag_enhanced=True,
                sources=[
                    {
                        'title': 'ZenAI Documentation',
                        'url': 'https://example.com/docs',
                        'text': 'ZenAI is a powerful local AI assistant with multi-LLM consensus capabilities...'
                    },
                    {
                        'title': 'User Guide',
                        'url': 'docs/USER_GUIDE.md',
                        'text': 'To get started with ZenAI, first install the dependencies and download a model...'
                    }
                ]
            )
            msg.render(chat_container)
        elif value == 'typing':
            indicator = ModernTypingIndicator()
            indicator.render(chat_container)

            # Remove after 2 seconds
            import asyncio
            await asyncio.sleep(2)
            indicator.remove()

            # Show AI response
            msg = ModernChatMessage(
                role='assistant',
                content='Typing indicator disappeared! This is the response.',
                avatar_text='Z'
            )
            msg.render(chat_container)

        # Scroll to bottom
        scroll_area.scroll_to(percent=1.0)

    chips = ModernActionChips(actions=actions, on_click=handle_chip_click)
    chips.render(chat_container)

    # Sample Messages
    ui.label('Sample Messages').classes(
        MT.combine(
            MT.TEXT_LG,
            MT.FONT_SEMIBOLD,
            MT.TextColors.PRIMARY,
            'mt-8 mb-4'
        )
    ).move(chat_container)

    # User message
    msg1 = ModernChatMessage(
        role='user',
        content='What can you tell me about the new UI?',
        avatar_text='U'
    )
    msg1.render(chat_container)

    # AI response
    _demo_page_continued(avatar_text, chat_container, content, features, icon, indicator, on_click, rag_enhanced, role, scroll_area, sources)


# ==========================================================================
# RUN DEMO
# ==========================================================================

if __name__ in {'__main__', '__mp_main__'}:
    print('=' * 60)
    print('MODERN UI DEMO')
    print('=' * 60)
    print()
    print('Starting demo server...')
    print('Open browser at: http://localhost:8090')
    print()
    print('Features:')
    print('  - Modern chat bubbles')
    print('  - Smooth animations')
    print('  - Purple theme (Claude-inspired)')
    print('  - Dark mode toggle')
    print('  - Interactive components')
    print()
    print('Press Ctrl+C to stop')
    print('=' * 60)

    ui.run(
        title='Modern UI Demo - ZenAI',
        port=8090,
        reload=False,
        dark=False
    )
