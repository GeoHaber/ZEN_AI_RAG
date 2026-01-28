# -*- coding: utf-8 -*-
"""
ui/settings_dialog.py - Settings Dialog Component
Provides a full settings interface for ZenAI.
"""

from nicegui import ui
from typing import Callable, Optional
from settings import get_settings, SettingsManager
from locales import get_locale, set_locale, get_available_locales
from ui.styles import Styles
from ui.icons import Icons
from ui.theme import Colors
from ui.registry import UI_IDS


def create_settings_dialog(on_save: Optional[Callable] = None, on_language_change: Optional[Callable] = None, on_dark_mode_change: Optional[Callable[[bool], None]] = None):
    """
    Create the settings dialog with all configuration options.
    
    Args:
        on_save: Callback when settings are saved
        on_language_change: Callback when language is changed (for UI refresh)
        on_dark_mode_change: Callback when dark mode is toggled (receives bool)
    
    Returns:
        The dialog element
    """
    locale = get_locale()
    settings = get_settings()
    
    def _handle_dark_mode_change(e):
        """Handle dark mode switch change."""
        settings.appearance.dark_mode = e.value
        if on_dark_mode_change:
            on_dark_mode_change(e.value)
    
    with ui.dialog() as dialog, ui.card().classes('w-full max-w-3xl max-h-[90vh]'):
        # Header
        with ui.row().classes('w-full items-center justify-between p-4 border-b border-gray-200 dark:border-slate-700'):
            ui.label(locale.SETTINGS_TITLE).classes('text-xl font-bold ' + Styles.TEXT_PRIMARY)
            ui.button(icon=Icons.CLOSE, on_click=dialog.close).props(f'flat round dense id={UI_IDS.BTN_CLOSE_DIALOG}')
        
        # Scrollable Content
        with ui.scroll_area().classes('w-full flex-1 p-4'):
            with ui.column().classes('w-full gap-6'):
                
                # ==================== LANGUAGE ====================
                with ui.expansion(locale.SETTINGS_CAT_LANGUAGE, icon='language').classes('w-full ' + Styles.CARD_BASE):
                    with ui.column().classes('w-full gap-4 p-4'):
                        ui.label(locale.SETTINGS_UI_LANGUAGE).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                        ui.label(locale.SETTINGS_UI_LANGUAGE_DESC).classes(Styles.LABEL_XS)
                        
                        available_locales = get_available_locales()
                        language_options = {code: f"{info['native']} ({info['name']})" 
                                          for code, info in available_locales.items()}
                        
                        language_select = ui.select(
                            options=language_options,
                            value=settings.language.ui_language,
                            on_change=lambda e: _on_language_select(e.value, on_language_change)
                        ).classes('w-full max-w-xs').props(f'id={UI_IDS.SET_LANGUAGE}')
                
                # ==================== APPEARANCE ====================
                with ui.expansion(locale.SETTINGS_CAT_APPEARANCE, icon='palette').classes('w-full ' + Styles.CARD_BASE):
                    with ui.column().classes('w-full gap-4 p-4'):
                        # Dark Mode
                        with ui.row().classes('w-full items-center justify-between'):
                            with ui.column().classes('gap-0'):
                                ui.label(locale.SETTINGS_DARK_MODE).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_DARK_MODE_DESC).classes(Styles.LABEL_XS)
                            ui.switch(value=settings.appearance.dark_mode, on_change=_handle_dark_mode_change).props(f'id={UI_IDS.SET_DARK_MODE}')
                        
                        ui.separator()
                        
                        # Font Size
                        ui.label(locale.SETTINGS_FONT_SIZE).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                        ui.toggle(
                            {
                                'small': locale.SETTINGS_FONT_SIZE_SMALL,
                                'medium': locale.SETTINGS_FONT_SIZE_MEDIUM,
                                'large': locale.SETTINGS_FONT_SIZE_LARGE
                            },
                            value=settings.appearance.font_size
                        ).bind_value(settings.appearance, 'font_size')
                        
                        ui.separator()
                        
                        # Chat Density
                        ui.label(locale.SETTINGS_CHAT_DENSITY).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                        ui.toggle(
                            {
                                'compact': locale.SETTINGS_CHAT_DENSITY_COMPACT,
                                'comfortable': locale.SETTINGS_CHAT_DENSITY_COMFORTABLE,
                                'spacious': locale.SETTINGS_CHAT_DENSITY_SPACIOUS
                            },
                            value=settings.appearance.chat_density
                        ).bind_value(settings.appearance, 'chat_density')
                        
                        ui.separator()
                        
                        # Show Avatars & Animations
                        with ui.row().classes('w-full gap-8'):
                            ui.checkbox(locale.SETTINGS_SHOW_AVATARS, value=settings.appearance.show_avatars).bind_value(settings.appearance, 'show_avatars')
                            ui.checkbox(locale.SETTINGS_ANIMATE_MESSAGES, value=settings.appearance.animate_messages).bind_value(settings.appearance, 'animate_messages')
                
                # ==================== AI MODEL ====================
                with ui.expansion(locale.SETTINGS_CAT_AI_MODEL, icon='smart_toy').classes('w-full ' + Styles.CARD_BASE):
                    with ui.column().classes('w-full gap-4 p-4'):
                        # Default Model
                        ui.label(locale.SETTINGS_DEFAULT_MODEL).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                        ui.label(locale.SETTINGS_DEFAULT_MODEL_DESC).classes(Styles.LABEL_XS)
                        ui.input(value=settings.ai_model.default_model, placeholder='e.g., qwen2.5-7b-q4_k_m.gguf').bind_value(settings.ai_model, 'default_model').classes('w-full max-w-md')
                        
                        ui.separator()
                        
                        # Temperature
                        with ui.row().classes('w-full items-center gap-4'):
                            with ui.column().classes('flex-1'):
                                ui.label(locale.SETTINGS_TEMPERATURE).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_TEMPERATURE_DESC).classes(Styles.LABEL_XS)
                            ui.number(value=settings.ai_model.temperature, min=0, max=2, step=0.1, format='%.1f').bind_value(settings.ai_model, 'temperature').classes('w-24')
                        
                        # Max Tokens
                        with ui.row().classes('w-full items-center gap-4'):
                            with ui.column().classes('flex-1'):
                                ui.label(locale.SETTINGS_MAX_TOKENS).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_MAX_TOKENS_DESC).classes(Styles.LABEL_XS)
                            ui.number(value=settings.ai_model.max_tokens, min=128, max=32768, step=256).bind_value(settings.ai_model, 'max_tokens').classes('w-32')
                        
                        # Context Window
                        with ui.row().classes('w-full items-center gap-4'):
                            with ui.column().classes('flex-1'):
                                ui.label(locale.SETTINGS_CONTEXT_WINDOW).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_CONTEXT_WINDOW_DESC).classes(Styles.LABEL_XS)
                            ui.number(value=settings.ai_model.context_window, min=512, max=131072, step=512).bind_value(settings.ai_model, 'context_window').classes('w-32')
                        
                        ui.separator()
                        
                        # CoT Swarm
                        with ui.row().classes('w-full items-center justify-between'):
                            with ui.column().classes('gap-0'):
                                ui.label(locale.SETTINGS_USE_COT_SWARM).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_USE_COT_SWARM_DESC).classes(Styles.LABEL_XS)
                            ui.switch(value=settings.ai_model.use_cot_swarm).bind_value(settings.ai_model, 'use_cot_swarm').props(f'id={UI_IDS.SET_SWARM_COT}')
                        
                        with ui.row().classes('w-full items-center justify-between'):
                            with ui.column().classes('gap-0'):
                                ui.label(locale.SETTINGS_QUIET_COT).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_QUIET_COT_DESC).classes(Styles.LABEL_XS)
                            ui.switch(value=settings.ai_model.quiet_cot).bind_value(settings.ai_model, 'quiet_cot')
                
                # ==================== VOICE ====================
                with ui.expansion(locale.SETTINGS_CAT_VOICE, icon='mic').classes('w-full ' + Styles.CARD_BASE):
                    with ui.column().classes('w-full gap-4 p-4'):
                        # TTS Enabled
                        with ui.row().classes('w-full items-center justify-between'):
                            with ui.column().classes('gap-0'):
                                ui.label(locale.SETTINGS_TTS_ENABLED).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_TTS_ENABLED_DESC).classes(Styles.LABEL_XS)
                            ui.switch(value=settings.voice.tts_enabled).bind_value(settings.voice, 'tts_enabled').props(f'id={UI_IDS.SET_TTS_ENABLE}')
                        
                        ui.separator()
                        
                        # Voice Speed
                        with ui.row().classes('w-full items-center gap-4'):
                            with ui.column().classes('flex-1'):
                                ui.label(locale.SETTINGS_VOICE_SPEED).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_VOICE_SPEED_DESC).classes(Styles.LABEL_XS)
                            ui.slider(min=0.5, max=2.0, step=0.1, value=settings.voice.voice_speed).bind_value(settings.voice, 'voice_speed').classes('w-48')
                        
                        # Auto-Speak
                        with ui.row().classes('w-full items-center justify-between'):
                            with ui.column().classes('gap-0'):
                                ui.label(locale.SETTINGS_AUTO_SPEAK).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_AUTO_SPEAK_DESC).classes(Styles.LABEL_XS)
                            ui.switch(value=settings.voice.auto_speak_responses).bind_value(settings.voice, 'auto_speak_responses')
                        
                        # Recording Duration
                        with ui.row().classes('w-full items-center gap-4'):
                            with ui.column().classes('flex-1'):
                                ui.label(locale.SETTINGS_RECORDING_DURATION).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_RECORDING_DURATION_DESC).classes(Styles.LABEL_XS)
                            ui.number(value=settings.voice.recording_duration, min=1, max=30, step=1).bind_value(settings.voice, 'recording_duration').classes('w-24').props('suffix="s"')
                
                # ==================== RAG ====================
                with ui.expansion(locale.SETTINGS_CAT_RAG, icon='library_books').classes('w-full ' + Styles.CARD_BASE):
                    with ui.column().classes('w-full gap-4 p-4'):
                        # RAG Enabled
                        with ui.row().classes('w-full items-center justify-between'):
                            with ui.column().classes('gap-0'):
                                ui.label(locale.SETTINGS_RAG_ENABLED).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_RAG_ENABLED_DESC).classes(Styles.LABEL_XS)
                            ui.switch(value=settings.rag.enabled).bind_value(settings.rag, 'enabled').props(f'id={UI_IDS.SET_RAG_ENABLE}')
                        
                        ui.separator()
                        
                        # Chunk Size
                        with ui.row().classes('w-full items-center gap-4'):
                            with ui.column().classes('flex-1'):
                                ui.label(locale.SETTINGS_CHUNK_SIZE).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_CHUNK_SIZE_DESC).classes(Styles.LABEL_XS)
                            ui.number(value=settings.rag.chunk_size, min=100, max=2000, step=50).bind_value(settings.rag, 'chunk_size').classes('w-32')
                        
                        # Similarity Threshold
                        with ui.row().classes('w-full items-center gap-4'):
                            with ui.column().classes('flex-1'):
                                ui.label(locale.SETTINGS_SIMILARITY_THRESHOLD).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_SIMILARITY_THRESHOLD_DESC).classes(Styles.LABEL_XS)
                            ui.number(value=settings.rag.similarity_threshold, min=0, max=1, step=0.05, format='%.2f').bind_value(settings.rag, 'similarity_threshold').classes('w-24')
                        
                        # Max Results
                        with ui.row().classes('w-full items-center gap-4'):
                            with ui.column().classes('flex-1'):
                                ui.label(locale.SETTINGS_MAX_RESULTS).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_MAX_RESULTS_DESC).classes(Styles.LABEL_XS)
                            ui.number(value=settings.rag.max_results, min=1, max=20, step=1).bind_value(settings.rag, 'max_results').classes('w-24')
                        
                        # Auto-Index
                        with ui.row().classes('w-full items-center justify-between'):
                            with ui.column().classes('gap-0'):
                                ui.label(locale.SETTINGS_AUTO_INDEX).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_AUTO_INDEX_DESC).classes(Styles.LABEL_XS)
                            ui.switch(value=settings.rag.auto_index_on_startup).bind_value(settings.rag, 'auto_index_on_startup')
                
                # ==================== CHAT ====================
                with ui.expansion(locale.SETTINGS_CAT_CHAT, icon='chat').classes('w-full ' + Styles.CARD_BASE):
                    with ui.column().classes('w-full gap-4 p-4'):
                        # Row of switches
                        with ui.row().classes('w-full items-center justify-between'):
                            with ui.column().classes('gap-0'):
                                ui.label(locale.SETTINGS_SHOW_TIMESTAMPS).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_SHOW_TIMESTAMPS_DESC).classes(Styles.LABEL_XS)
                            ui.switch(value=settings.chat.show_timestamps).bind_value(settings.chat, 'show_timestamps')
                        
                        with ui.row().classes('w-full items-center justify-between'):
                            with ui.column().classes('gap-0'):
                                ui.label(locale.SETTINGS_AUTO_SCROLL).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_AUTO_SCROLL_DESC).classes(Styles.LABEL_XS)
                            ui.switch(value=settings.chat.auto_scroll).bind_value(settings.chat, 'auto_scroll')
                        
                        with ui.row().classes('w-full items-center justify-between'):
                            with ui.column().classes('gap-0'):
                                ui.label(locale.SETTINGS_STREAM_RESPONSES).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_STREAM_RESPONSES_DESC).classes(Styles.LABEL_XS)
                            ui.switch(value=settings.chat.stream_responses).bind_value(settings.chat, 'stream_responses')
                        
                        with ui.row().classes('w-full items-center justify-between'):
                            with ui.column().classes('gap-0'):
                                ui.label(locale.SETTINGS_SHOW_TOKEN_COUNT).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_SHOW_TOKEN_COUNT_DESC).classes(Styles.LABEL_XS)
                            ui.switch(value=settings.chat.show_token_count).bind_value(settings.chat, 'show_token_count')
                        
                        with ui.row().classes('w-full items-center justify-between'):
                            with ui.column().classes('gap-0'):
                                ui.label(locale.SETTINGS_SAVE_CONVERSATIONS).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_SAVE_CONVERSATIONS_DESC).classes(Styles.LABEL_XS)
                            ui.switch(value=settings.chat.save_conversations).bind_value(settings.chat, 'save_conversations')
                        
                        ui.separator()
                        
                        # History Days
                        with ui.row().classes('w-full items-center gap-4'):
                            with ui.column().classes('flex-1'):
                                ui.label(locale.SETTINGS_HISTORY_DAYS).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_HISTORY_DAYS_DESC).classes(Styles.LABEL_XS)
                            ui.number(value=settings.chat.history_days, min=1, max=365, step=1).bind_value(settings.chat, 'history_days').classes('w-24').props('suffix=" days"')
                
                # ==================== SYSTEM ====================
                with ui.expansion(locale.SETTINGS_CAT_SYSTEM, icon='settings').classes('w-full ' + Styles.CARD_BASE):
                    with ui.column().classes('w-full gap-4 p-4'):
                        # API Port
                        with ui.row().classes('w-full items-center gap-4'):
                            with ui.column().classes('flex-1'):
                                ui.label(locale.SETTINGS_API_PORT).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_API_PORT_DESC).classes(Styles.LABEL_XS)
                            ui.number(value=settings.system.api_port, min=1024, max=65535, step=1).bind_value(settings.system, 'api_port').classes('w-32')
                        
                        # Models Directory
                        ui.label(locale.SETTINGS_MODELS_DIRECTORY).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                        ui.label(locale.SETTINGS_MODELS_DIRECTORY_DESC).classes(Styles.LABEL_XS)
                        ui.input(value=settings.system.models_directory).bind_value(settings.system, 'models_directory').classes('w-full max-w-md')
                        
                        ui.separator()
                        
                        # Switches
                        with ui.row().classes('w-full items-center justify-between'):
                            with ui.column().classes('gap-0'):
                                ui.label(locale.SETTINGS_CHECK_UPDATES).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_CHECK_UPDATES_DESC).classes(Styles.LABEL_XS)
                            ui.switch(value=settings.system.check_updates_on_startup).bind_value(settings.system, 'check_updates_on_startup')
                        
                        with ui.row().classes('w-full items-center justify-between'):
                            with ui.column().classes('gap-0'):
                                ui.label(locale.SETTINGS_AUTO_START_BACKEND).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                                ui.label(locale.SETTINGS_AUTO_START_BACKEND_DESC).classes(Styles.LABEL_XS)
                            ui.switch(value=settings.system.auto_start_backend).bind_value(settings.system, 'auto_start_backend')
                        
                        ui.separator()
                        
                        # Log Level
                        ui.label(locale.SETTINGS_LOG_LEVEL).classes('font-semibold ' + Styles.TEXT_PRIMARY)
                        ui.label(locale.SETTINGS_LOG_LEVEL_DESC).classes(Styles.LABEL_XS)
                        ui.select(
                            options=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                            value=settings.system.log_level
                        ).bind_value(settings.system, 'log_level').classes('w-32')
        
        # Footer with Save/Reset buttons
        with ui.row().classes('w-full items-center justify-between p-4 border-t border-gray-200 dark:border-slate-700'):
            ui.button(locale.SETTINGS_RESET, icon=Icons.REFRESH, on_click=lambda: _reset_settings(dialog, on_save)).props(f'flat id={UI_IDS.BTN_SET_RESET}').classes(Styles.TEXT_ERROR)
            
            with ui.row().classes('gap-2'):
                ui.button(locale.BTN_CANCEL, on_click=dialog.close).props(f'flat id={UI_IDS.BTN_CLOSE_DIALOG}')
                ui.button(locale.SETTINGS_SAVE, icon=Icons.SAVE, on_click=lambda: _save_settings(dialog, on_save)).classes(Styles.BTN_PRIMARY).props(f'id={UI_IDS.BTN_SET_SAVE}')
    
    return dialog


def _on_language_select(code: str, callback: Optional[Callable]):
    """Handle language selection change."""
    settings = get_settings()
    settings.language.ui_language = code
    set_locale(code)
    
    if callback:
        callback(code)


def _save_settings(dialog, callback: Optional[Callable]):
    """Save settings and close dialog."""
    locale = get_locale()
    settings = get_settings()
    
    if settings.save():
        ui.notify(locale.SETTINGS_SAVED, color='positive')
        if callback:
            callback()
    else:
        ui.notify(locale.NOTIFY_ERROR.format(error="Failed to save"), color='negative')
    
    dialog.close()


def _reset_settings(dialog, callback: Optional[Callable]):
    """Reset settings to defaults after confirmation."""
    locale = get_locale()
    
    with ui.dialog() as confirm_dialog, ui.card():
        ui.label(locale.SETTINGS_RESET_CONFIRM).classes(Styles.TEXT_PRIMARY)
        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button(locale.BTN_NO, on_click=confirm_dialog.close).props('flat')
            ui.button(locale.BTN_YES, on_click=lambda: _do_reset(dialog, confirm_dialog, callback)).classes(Styles.BTN_PRIMARY)
    
    confirm_dialog.open()


def _do_reset(main_dialog, confirm_dialog, callback: Optional[Callable]):
    """Perform the actual reset."""
    locale = get_locale()
    settings = get_settings()
    settings.reset()
    
    ui.notify(locale.SETTINGS_SAVED, color='positive')
    confirm_dialog.close()
    main_dialog.close()
    
    if callback:
        callback()
