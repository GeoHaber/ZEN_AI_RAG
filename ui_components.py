from ui import Styles, Icons, Formatters
from ui.theme import Theme, Colors
from ui.settings_dialog import create_settings_dialog
from ui.quality_dashboard import create_quality_tab
from ui.actions import UIActions
from ui.dialogs_factory import DialogsFactory
from ui.sidebar import create_sidebar
from ui.rag_interface import setup_rag_dialog
from ui.theme_setup import setup_app_theme

# Re-export key functions for backward compatibility
setup_common_dialogs = DialogsFactory.setup_common_dialogs

def setup_drawer(backend, rag_system, config, dialogs, ZENA_MODE, EMOJI, app_state):
    """Facade for setting up the sidebar using the new modular structure."""
    actions = UIActions(backend, rag_system, app_state, dialogs, config)
    return create_sidebar(app_state, actions, backend, dialogs, config, ZENA_MODE, EMOJI)
