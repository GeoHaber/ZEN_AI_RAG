#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
demo_modern_ui.py - Simple Modern UI Demo
Quick demo showcasing the new modern UI components.

Run this file:
    python demo_modern_ui.py

Access at: http://localhost:8090
"""

from nicegui import ui
from ui.modern_theme import ModernTheme as MT, MODERN_CSS


# ==========================================================================
# DEMO PAGE
# ==========================================================================

@ui.page('/')
def demo_page():
    """Modern UI Demo Page - Simplified"""

    # Add custom CSS
    ui.add_head_html(MODERN_CSS)

    # Dark mode toggle
    dark_mode = ui.dark_mode(value=False)

    # Store debug label reference (will be created later in footer)
    debug_label_ref = {'label': None}

    # Header
    with ui.header().classes(MT.Layout.HEADER):
        menu_btn = ui.button(icon='menu').props('flat').classes(MT.Buttons.ICON + ' transition-transform')

        ui.label('ZenAI Modern UI Demo').classes(
            MT.combine(MT.TEXT_XL, MT.FONT_SEMIBOLD, MT.TextColors.PRIMARY)
        )

        ui.space()

        # Dark mode toggle
        dark_button = ui.button(
            icon='light_mode',
            on_click=lambda: toggle_dark(dark_mode, dark_button)
        ).props('flat').classes(MT.Buttons.ICON + ' transition-all')

        # Menu button click handler
        def on_menu_click():
            if debug_label_ref['label']:
                debug_label_ref['label'].text = '☰ Menu button clicked!'
                debug_label_ref['label'].classes('text-blue-600 font-semibold')
                ui.timer(2.0, lambda: reset_debug_ref(), once=True)
            menu_btn.classes('rotate-90')
            ui.notify('☰ Menu clicked', color='info')
            ui.timer(0.3, lambda: menu_btn.classes(remove='rotate-90'), once=True)

        menu_btn.on('click', on_menu_click)

    def toggle_dark(dm, btn):
        mode_name = 'Dark' if not dm.value else 'Light'
        if debug_label_ref['label']:
            debug_label_ref['label'].text = f'🌙 {mode_name} Mode activated!'
            debug_label_ref['label'].classes('text-purple-600 font-semibold')
            ui.timer(2.0, lambda: reset_debug_ref(), once=True)

        if dm.value:
            dm.disable()
            btn._props['icon'] = 'light_mode'
            ui.notify('☀️ Light mode activated', color='warning')
        else:
            dm.enable()
            btn._props['icon'] = 'dark_mode'
            ui.notify('🌙 Dark mode activated', color='info')
        btn.update()

    def reset_debug_ref():
        if debug_label_ref['label']:
            debug_label_ref['label'].text = 'Test me - Click any UI element to see it react!'
            debug_label_ref['label'].classes(MT.combine(MT.TEXT_XS, MT.TextColors.MUTED), remove='text-purple-600 text-blue-600 text-red-600 text-green-600 text-orange-600 font-semibold')

    # Main content area
    scroll_area = ui.scroll_area().classes('w-full').style(
        'height: calc(100vh - 200px); min-height: 300px;'
    )

    with scroll_area:
        with ui.column().classes(MT.Layout.CHAT_CONTAINER):
            # Welcome section
            with ui.column().classes('w-full text-center gap-4 p-8 animate-fade-in'):
                ui.label('Welcome to ZenAI Modern UI').classes(
                    MT.combine(MT.TEXT_3XL, MT.FONT_BOLD, MT.TextColors.PRIMARY)
                )

                ui.label('Experience the new Claude-inspired interface').classes(
                    MT.combine(MT.TEXT_LG, MT.TextColors.SECONDARY, 'mb-4')
                )

                # Feature cards (clickable)
                feature_cards_row = ui.row().classes('gap-4 justify-center flex-wrap')
                feature_cards_placeholder = []
                with feature_cards_row:
                    for feature in [
                        'Beautiful Purple Theme',
                        'Smooth Animations',
                        'Modern Typography',
                        'Dark Mode Support'
                    ]:
                        feature_card = ui.card().classes(MT.Cards.PADDED + ' min-w-48 cursor-pointer hover:shadow-xl transition-shadow')
                        with feature_card:
                            ui.label(feature).classes(
                                MT.combine(MT.TEXT_SM, MT.TextColors.SECONDARY, 'text-center')
                            )
                        feature_cards_placeholder.append((feature, feature_card))

            # Demo section header
            ui.label('Sample Chat Messages').classes(
                MT.combine(MT.TEXT_LG, MT.FONT_SEMIBOLD, MT.TextColors.PRIMARY, 'mt-8 mb-4')
            )

            # User message example (clickable)
            user_msg_row = ui.row().classes(MT.ChatBubbles.ROW_USER + ' chat-message cursor-pointer hover:opacity-90 transition-opacity')
            with user_msg_row:
                with ui.column().classes('gap-1 max-w-3xl'):
                    ui.label('You').classes(
                        MT.combine(MT.TEXT_XS, MT.TextColors.SECONDARY, 'ml-1')
                    )
                    user_bubble = ui.markdown('What can you tell me about the **new UI**?').classes(
                        MT.ChatBubbles.USER_FULL + ' markdown-content'
                    )

                user_avatar = ui.avatar('U', color='gray', text_color='white').classes(MT.Avatars.USER_FULL)

            # Store reference for click handler (will be added in footer)
            user_msg_placeholder = user_msg_row

            # AI response example (clickable)
            ai_msg_row = ui.row().classes(MT.ChatBubbles.ROW_AI + ' chat-message cursor-pointer hover:opacity-90 transition-opacity')
            with ai_msg_row:
                ai_avatar = ui.avatar('Z', color='purple', text_color='white').classes(MT.Avatars.AI_FULL)

                with ui.column().classes('gap-1 max-w-3xl'):
                    ui.label('Zena').classes(
                        MT.combine(MT.TEXT_XS, MT.TextColors.SECONDARY, 'ml-1')
                    )
                    ai_bubble = ui.markdown('''The new UI features a **Claude-inspired design** with:

**Visual Improvements:**
- Purple primary color (#8B5CF6)
- Clean, rounded chat bubbles
- Smooth animations and transitions
- Better typography with Inter font

**User Experience:**
- Larger padding for better readability
- Clear visual hierarchy
- Subtle shadows for depth

Try clicking the dark mode button above!''').classes(
                        MT.ChatBubbles.AI_FULL + ' markdown-content'
                    )

            # Store reference for click handler
            ai_msg_placeholder = ai_msg_row

            # RAG-enhanced message example (clickable)
            rag_msg_row = ui.row().classes(MT.ChatBubbles.ROW_AI + ' chat-message cursor-pointer hover:opacity-90 transition-opacity')
            with rag_msg_row:
                rag_avatar = ui.avatar('Z', color='blue', text_color='white').classes(MT.Avatars.AI_FULL)

                with ui.column().classes('gap-1 max-w-3xl'):
                    ui.label('Zena (RAG-Enhanced)').classes(
                        MT.combine(MT.TEXT_XS, MT.TextColors.INFO, 'ml-1 font-semibold')
                    )
                    rag_bubble = ui.markdown('''Based on the documentation, the modern theme includes:

```python
from ui.modern_theme import ModernTheme as MT

# Use predefined styles
button = ui.button('Click').classes(MT.Buttons.PRIMARY_FULL)
```

This response uses **RAG context** from the knowledge base!''').classes(
                        MT.ChatBubbles.RAG_FULL + ' markdown-content'
                    )

                    # Sources panel (clickable expansion)
                    sources_expansion = ui.expansion('View Sources', icon='source').classes(MT.Cards.INFO + ' mt-2 cursor-pointer')
                    with sources_expansion:
                        with ui.column().classes('gap-2 p-2'):
                            source_card = ui.card().classes(MT.Cards.BASE + ' p-3 cursor-pointer hover:shadow-lg transition-shadow')
                            with source_card:
                                source_link = ui.link('[1] ModernTheme Documentation', '#').classes(
                                    MT.TextColors.LINK + ' font-semibold'
                                )
                                ui.label('Location: ui/modern_theme.py').classes(
                                    MT.combine(MT.TEXT_XS, MT.TextColors.MUTED)
                                )
                                ui.label('"The ModernTheme class provides organized style classes..."').classes(
                                    MT.combine(
                                        MT.TEXT_SM,
                                        MT.TextColors.SECONDARY,
                                        'italic border-l-2 border-gray-300 pl-2 mt-1'
                                    )
                                )

                            # Store references
                            sources_placeholder = {'expansion': sources_expansion, 'card': source_card, 'link': source_link}

            # Store reference for click handler
            rag_msg_placeholder = rag_msg_row

            # System message example (clickable)
            system_msg_row = ui.row().classes(MT.ChatBubbles.ROW_SYSTEM + ' chat-message cursor-pointer hover:opacity-90 transition-opacity')
            with system_msg_row:
                system_bubble = ui.markdown('UI components loaded successfully').classes(
                    MT.ChatBubbles.SYSTEM_FULL
                )

            # Store reference for click handler
            system_msg_placeholder = system_msg_row

            # Interactive section
            ui.label('Interactive Demo').classes(
                MT.combine(MT.TEXT_LG, MT.FONT_SEMIBOLD, MT.TextColors.PRIMARY, 'mt-8 mb-4')
            )

            # Buttons showcase (will be updated with debug_label reference)
            ui.label('Button Variants:').classes(MT.combine(MT.TEXT_SM, MT.TextColors.MUTED, 'mb-2'))

            button_row = ui.row().classes('gap-3 flex-wrap mb-6')

            # Store button row for later population
            buttons_placeholder = button_row

            # Cards showcase
            ui.label('Card Variants:').classes(MT.combine(MT.TEXT_SM, MT.TextColors.MUTED, 'mb-2'))

            cards_row = ui.row().classes('gap-4 flex-wrap')
            cards_placeholder = cards_row

    # Footer with input bar
    with ui.footer().classes(MT.Layout.FOOTER):
        with ui.column().classes('w-full max-w-4xl mx-auto gap-2'):
            # Debug info label (above input bar)
            debug_label = ui.label('Test me - Click any UI element to see it react!').classes(
                MT.combine(MT.TEXT_XS, MT.TextColors.MUTED, 'text-center italic mb-1')
            )
            debug_label_ref['label'] = debug_label  # Store reference for header buttons

            # Input bar
            with ui.row().classes(MT.Inputs.CHAT_BAR):
                attach_btn = ui.button(icon='attach_file').props('flat round dense').classes(
                    MT.Buttons.ICON + ' text-gray-500 hover:text-purple-600 transition-all'
                )

                chat_input = ui.input(placeholder='Type a message to see it in the modern UI...').classes(
                    MT.Inputs.CHAT
                ).props('borderless')
                chat_input.value = 'Test me'  # Default message

                mic_btn = ui.button(icon='mic').props('flat round dense').classes(
                    MT.Buttons.ICON + ' text-gray-500 hover:text-purple-600 transition-all'
                )

                def send_message():
                    msg = chat_input.value.strip()
                    if msg:
                        debug_label.text = f'💬 Message sent: "{msg}"'
                        debug_label.classes('text-purple-600 font-semibold')
                        ui.notify(f'✅ Sent: {msg}', color='positive', position='top')
                        chat_input.value = ''
                        # Reset debug label after 2 seconds
                        ui.timer(2.0, lambda: reset_debug(), once=True)

                send_btn = ui.button(
                    icon='send',
                    on_click=send_message
                ).props('round unelevated').classes(
                    MT.Buttons.PRIMARY_FULL + ' w-10 h-10 transition-transform hover:scale-110'
                )

                # Click handlers for input bar buttons
                def on_attach_click():
                    debug_label.text = '📎 Attach File button clicked!'
                    debug_label.classes('text-blue-600 font-semibold')
                    attach_btn.classes('scale-125 text-purple-600', remove='text-gray-500')
                    ui.notify('📎 File attachment clicked', color='info')
                    ui.timer(0.3, lambda: attach_btn.classes('text-gray-500', remove='scale-125 text-purple-600'), once=True)
                    ui.timer(2.0, lambda: reset_debug(), once=True)

                def on_mic_click():
                    debug_label.text = '🎤 Voice Recording button clicked!'
                    debug_label.classes('text-red-600 font-semibold')
                    mic_btn.classes('scale-125 text-red-600', remove='text-gray-500')
                    ui.notify('🎤 Voice recording clicked', color='warning')
                    ui.timer(0.3, lambda: mic_btn.classes('text-gray-500', remove='scale-125 text-red-600'), once=True)
                    ui.timer(2.0, lambda: reset_debug(), once=True)

                def reset_debug():
                    debug_label.text = 'Test me - Click any UI element to see it react!'
                    debug_label.classes(MT.combine(MT.TEXT_XS, MT.TextColors.MUTED), remove='text-purple-600 text-blue-600 text-red-600 text-green-600 text-orange-600 font-semibold')

                attach_btn.on('click', on_attach_click)
                mic_btn.on('click', on_mic_click)

            # Now populate buttons with click handlers
            with buttons_placeholder:
                def make_button_handler(name, color):
                    def handler(btn):
                        debug_label.text = f'🔘 {name} Button clicked!'
                        debug_label.classes(f'text-{color}-600 font-semibold')
                        btn.classes('scale-110')
                        ui.notify(f'✨ {name} button clicked!', color=color if color != 'purple' else 'positive')
                        ui.timer(0.2, lambda: btn.classes(remove='scale-110'), once=True)
                        ui.timer(2.0, lambda: reset_debug(), once=True)
                    return handler

                primary_btn = ui.button('Primary').classes(
                    MT.Buttons.PRIMARY_FULL + ' transition-transform'
                )
                primary_btn.on('click', lambda: make_button_handler('Primary', 'purple')(primary_btn))

                secondary_btn = ui.button('Secondary').classes(
                    MT.Buttons.SECONDARY_FULL + ' transition-transform'
                )
                secondary_btn.on('click', lambda: make_button_handler('Secondary', 'gray')(secondary_btn))

                ghost_btn = ui.button('Ghost').classes(
                    MT.Buttons.GHOST_FULL + ' transition-transform'
                )
                ghost_btn.on('click', lambda: make_button_handler('Ghost', 'blue')(ghost_btn))

                outline_btn = ui.button('Outline').classes(
                    MT.Buttons.OUTLINE_FULL + ' transition-transform'
                )
                outline_btn.on('click', lambda: make_button_handler('Outline', 'purple')(outline_btn))

            # Now populate cards with click handlers
            with cards_placeholder:
                def make_card_click(name, color, emoji):
                    def handler():
                        debug_label.text = f'{emoji} {name} Card clicked!'
                        debug_label.classes(f'text-{color}-600 font-semibold')
                        ui.notify(f'{emoji} {name} card clicked!', color=color)
                        ui.timer(2.0, lambda: reset_debug(), once=True)
                    return handler

                info_card = ui.card().classes(MT.Cards.INFO + ' cursor-pointer hover:shadow-lg transition-shadow')
                with info_card:
                    ui.label('Info Card').classes(MT.FONT_SEMIBOLD)
                    ui.label('Blue tint for informational content').classes(MT.TEXT_SM)
                info_card.on('click', make_card_click('Info', 'blue', 'ℹ️'))

                success_card = ui.card().classes(MT.Cards.SUCCESS + ' cursor-pointer hover:shadow-lg transition-shadow')
                with success_card:
                    ui.label('Success Card').classes(MT.FONT_SEMIBOLD)
                    ui.label('Green tint for success messages').classes(MT.TEXT_SM)
                success_card.on('click', make_card_click('Success', 'green', '✅'))

                warning_card = ui.card().classes(MT.Cards.WARNING + ' cursor-pointer hover:shadow-lg transition-shadow')
                with warning_card:
                    ui.label('Warning Card').classes(MT.FONT_SEMIBOLD)
                    ui.label('Amber tint for warnings').classes(MT.TEXT_SM)
                warning_card.on('click', make_card_click('Warning', 'orange', '⚠️'))

            # Add click handlers for chat messages
            def on_user_msg_click():
                debug_label.text = '💬 User Message clicked!'
                debug_label.classes('text-purple-600 font-semibold')
                ui.notify('💬 User message bubble clicked', color='positive')
                ui.timer(2.0, lambda: reset_debug(), once=True)

            def on_ai_msg_click():
                debug_label.text = '🤖 AI Response clicked!'
                debug_label.classes('text-blue-600 font-semibold')
                ui.notify('🤖 AI response bubble clicked', color='info')
                ui.timer(2.0, lambda: reset_debug(), once=True)

            def on_rag_msg_click():
                debug_label.text = '📚 RAG-Enhanced Message clicked!'
                debug_label.classes('text-blue-600 font-semibold')
                ui.notify('📚 RAG message bubble clicked', color='info')
                ui.timer(2.0, lambda: reset_debug(), once=True)

            def on_system_msg_click():
                debug_label.text = '⚙️ System Message clicked!'
                debug_label.classes('text-gray-600 font-semibold')
                ui.notify('⚙️ System message clicked', color='info')
                ui.timer(2.0, lambda: reset_debug(), once=True)

            def on_sources_click():
                debug_label.text = '📖 Sources Panel clicked!'
                debug_label.classes('text-blue-600 font-semibold')
                ui.notify('📖 Sources panel expanded', color='info')
                ui.timer(2.0, lambda: reset_debug(), once=True)

            def on_source_card_click():
                debug_label.text = '📄 Source Document clicked!'
                debug_label.classes('text-green-600 font-semibold')
                ui.notify('📄 Source document clicked', color='positive')
                ui.timer(2.0, lambda: reset_debug(), once=True)

            def on_source_link_click():
                debug_label.text = '🔗 Documentation Link clicked!'
                debug_label.classes('text-purple-600 font-semibold')
                ui.notify('🔗 Documentation link clicked', color='positive')
                ui.timer(2.0, lambda: reset_debug(), once=True)

            # Attach handlers to chat messages
            user_msg_placeholder.on('click', on_user_msg_click)
            ai_msg_placeholder.on('click', on_ai_msg_click)
            rag_msg_placeholder.on('click', on_rag_msg_click)
            system_msg_placeholder.on('click', on_system_msg_click)

            # Attach handlers to RAG sources
            sources_placeholder['expansion'].on('click', on_sources_click)
            sources_placeholder['card'].on('click', on_source_card_click)
            sources_placeholder['link'].on('click', on_source_link_click)

            # Add handlers for feature cards
            def make_feature_click(name):
                def handler():
                    emoji_map = {
                        'Beautiful Purple Theme': '🎨',
                        'Smooth Animations': '✨',
                        'Modern Typography': '✍️',
                        'Dark Mode Support': '🌙'
                    }
                    emoji = emoji_map.get(name, '⭐')
                    debug_label.text = f'{emoji} {name} feature clicked!'
                    debug_label.classes('text-purple-600 font-semibold')
                    ui.notify(f'{emoji} {name} clicked', color='positive')
                    ui.timer(2.0, lambda: reset_debug(), once=True)
                return handler

            # Attach handlers to feature cards
            for feature_name, feature_card in feature_cards_placeholder:
                feature_card.on('click', make_feature_click(feature_name))


# ==========================================================================
# RUN DEMO
# ==========================================================================

if __name__ in {'__main__', '__mp_main__'}:
    print('=' * 70)
    print('ZENAI MODERN UI DEMO')
    print('=' * 70)
    print()
    print('Starting demo server...')
    print('Open browser at: http://localhost:8092')
    print()
    print('Features:')
    print('  - Claude-inspired purple theme')
    print('  - Modern chat bubbles')
    print('  - Smooth animations')
    print('  - Dark mode toggle')
    print('  - Interactive buttons and cards')
    print()
    print('Try:')
    print('  - Toggle dark mode (top right)')
    print('  - Click different button variants')
    print('  - Type a message in the input bar')
    print('  - Expand the RAG sources panel')
    print()
    print('Press Ctrl+C to stop')
    print('=' * 70)
    print()

    ui.run(
        title='ZenAI Modern UI Demo',
        port=8092,  # Interactive demo with click feedback
        reload=False,
        dark=False
    )
