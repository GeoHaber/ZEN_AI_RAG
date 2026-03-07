from nicegui import ui
import asyncio
import random
from config_system import config, EMOJI
from ui.locales import get_locale
from ui import Styles, Icons, Formatters
from ui.registry import UI_IDS
from ui.examples import EXAMPLES
from ui.dashboard import build_performance_dashboard
from ui.tour import start_tutorial

from ui.model_gallery import create_model_gallery

def build_header(ui_state, drawer, locale, open_gallery=None):
    """Build the application header."""
    with ui.header().classes(Styles.HEADER) as header:
        ui.button(on_click=lambda: drawer.toggle(), icon=Icons.MENU).props('flat round id=ui-drawer-btn').classes(Styles.TEXT_PRIMARY)
        with ui.row().classes('items-center'):
            ui.label('ZenAI').classes('text-base md:text-lg font-bold ' + Styles.TEXT_ACCENT + ' ml-1 md:ml-2')
        ui.space()
        with ui.row().classes('items-center gap-2'):
             with ui.row().classes('items-center gap-1.5 px-3 py-1 rounded-full bg-gray-50/50 dark:bg-slate-800/50 border border-gray-100 dark:border-slate-700'):
                 ui_state.status_dot = ui.label('●').classes('text-green-500 animate-pulse text-[14px]').props('id=header-status-dot')
                 ui_state.status_indicator = ui.label('ONLINE').classes('text-[10px] font-black tracking-widest text-green-500').props('id=header-status-label')
             
             # Voice status indicator (hidden by default, shown when recording)
             ui_state.voice_status = ui.label('🎙️ REC').classes('text-[10px] font-black tracking-widest text-red-500 animate-pulse hidden').props('id=header-voice-label')
             
             # Model Gallery Button (The "Cards")
             if open_gallery:
                 with ui.button(icon='smart_toy', on_click=open_gallery).props('flat round dense').classes(Styles.TEXT_MUTED + ' hover:text-purple-500 transition-colors'):
                     ui.tooltip('The Council (Models)')

             ui.button(icon=Icons.PERSON).props('flat round dense').classes(Styles.TEXT_MUTED)
        ui_state.status_text = ui.label(locale.CHAT_READY).classes(Styles.TEXT_SECONDARY + ' text-xs md:text-sm ml-auto hidden xs:block')
    return header

def build_footer(ui_state, handlers, locale):
    """Build footer."""
    # ... (unchanged) ...
    # Floating capsule container - sits above the bottom edge
    with ui.footer().classes('bg-transparent border-0 p-3 md:p-4') as footer, ui.column().classes('w-full max-w-3xl mx-auto gap-2'):
        # Attachment preview (when file is attached) - start completely hidden
        ui_state.attachment_preview = ui.label('')
        ui_state.attachment_preview.set_visibility(False)
        ui_state.attachment_preview.classes(
            'text-sm px-4 py-2 rounded-full self-start '
            'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 '
            'border border-blue-200 dark:border-blue-700'
        )



        # === COMMAND CAPSULE ===
        # Floating pill-shaped input with shadow and modern styling
        with ui.card().classes(
            'w-full p-3 rounded-3xl shadow-xl '
            'bg-white dark:bg-slate-800 '
            'border-2 border-gray-100 dark:border-slate-600 '
        ).props('flat'):
            with ui.row().classes('items-center gap-2 w-full'):
                # Attach button
                uploader = ui.upload(on_upload=handlers.on_upload, auto_upload=True).classes('hidden')
                ui.button(
                    on_click=lambda: uploader.run_method('pickFiles'), 
                    icon=Icons.ATTACH
                ).props(f'flat round dense id={UI_IDS.BTN_ATTACH}').classes(
                    'text-gray-400 hover:text-blue-500 transition-colors'
                )

                # Input field - grows to fill space
                placeholder_text = getattr(locale, 'CHAT_PLACEHOLDER_ZENA', 'Ask anything...') if config.zena_mode_enabled else getattr(locale, 'CHAT_PLACEHOLDER', 'Type a message...')
                ui_state.user_input = ui.input(placeholder=placeholder_text).props(
                    f'borderless dense autogrow id={UI_IDS.INPUT_CHAT}'
                ).classes('flex-1 text-base bg-transparent')
                ui_state.user_input.on('keydown.enter.prevent', lambda: handlers.handle_send(ui_state.user_input.value))

                # Voice button with device selector
                async def setup_voice_devices():
                    """Initialize voice device selector."""
                    try:
                        import httpx
                        async with httpx.AsyncClient() as client:
                            response = await client.get('http://localhost:8001/voice/devices')
                            if response.status_code == 200:
                                data = response.json()
                                input_devices = [d for d in data.get('devices', []) if d['is_input']]
                                device_options = {d['name']: d['id'] for d in input_devices}
                                if device_options:
                                    ui_state.mic_device_select.set_options(device_options)
                                    default_id = data.get('default_device')
                                    if default_id is not None:
                                        ui_state.mic_device_select.value = list(device_options.values())[0]
                    except Exception as e:
                        logger.warning(f"[Voice] Failed to load devices: {e}")

                # Device selector (initially hidden, shown on click)
                ui_state.mic_device_select = ui.select(
                    {}, 
                    label='🎤'
                ).props('dense outlined').classes('text-sm').style('max-width: 200px; display: none;')
                ui_state.mic_device_select.tooltip = 'Select microphone'

                # Voice button
                ui.button(
                    icon=Icons.RECORD, 
                    on_click=handlers.on_voice_click
                ).props(f'flat round dense id={UI_IDS.BTN_VOICE}').classes(
                    'text-gray-400 hover:text-purple-500 transition-colors'
                ).tooltip('Click to toggle voice recording')

                # Send button - prominent
                ui.button(
                    icon=Icons.SEND, 
                    on_click=lambda: handlers.handle_send(ui_state.user_input.value)
                ).props(f'round dense unelevated id={UI_IDS.BTN_SEND}').classes(
                    'bg-gradient-to-r from-blue-500 to-violet-500 text-white w-10 h-10 shadow-md hover:shadow-lg transition-shadow'
                )
    return footer

def build_chat_area(ui_state):
    """Build the scrollable chat area."""
    ui_state.scroll_container = ui.scroll_area().classes('w-full').style('height: calc(100vh - 160px); min-height: 250px;')
    with ui_state.scroll_container:
        ui_state.chat_log = ui.column().classes('w-full max-w-4xl mx-auto p-2 md:p-4 space-y-3 md:space-y-4 ' + Styles.CHAT_CONTAINER_LIGHT + ' ' + Styles.CHAT_CONTAINER_DARK).props('id=chat-log-container')
    return ui_state.scroll_container

def build_page(ui_state, handlers, drawer_factory, rag_dialog_factory):
    """Assemble the complete page layout."""
    locale = get_locale()
    
    # 1. Dialogs & Components
    rag_dialog_factory()
    gallery_dialog = create_model_gallery(ui_state, None) # app_state not needed strictly yet
    drawer = drawer_factory()
    
    # 2. Layout Elements
    header = build_header(ui_state, drawer, locale, open_gallery=gallery_dialog.open)
    build_performance_dashboard(ui_state)
    build_chat_area(ui_state)
    build_footer(ui_state, handlers, locale)
    
    # 3. Initial State
    if config.zena_mode_enabled:
        handlers.add_message("system", locale.format('WELCOME_ZENAI', source_msg=locale.WELCOME_SOURCE_KB))
    else:
        handlers.add_message("system", locale.WELCOME_DEFAULT)
    
    # 4. Action Chips - Click to auto-send
    with ui_state.chat_log, ui.row().classes('w-full justify-center gap-2 mt-4 flex-wrap'):
        for item in EXAMPLES:
            async def make_handler(p=item['prompt']):
                # Set the input value and immediately send
                ui_state.user_input.value = p
                await handlers.handle_send(p)
            ui.button(item['title'], on_click=lambda p=item['prompt']: make_handler(p)).props('outline rounded-full dense').classes('text-[11px] px-3 py-1 normal-case hover:bg-blue-50 dark:hover:bg-slate-800 transition-colors')

    return {"header": header, "drawer": drawer}
