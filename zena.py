# -*- coding: utf-8 -*-
"""
zena.py - Zena AI Chat Interface
Elegant, professional chatbot with RAG capabilities
"""


# Local_LLM core modules
from Local_LLM.llama_cpp_manager import LlamaCppManager
from Local_LLM.local_llm_manager import LocalLLMManager
from Local_LLM.metrics import FIFO_Memory, start_metrics_server, set_fifo_depth, observe_inference
from Local_LLM.verification_oracle import Evidence, EvidenceType
from Local_LLM.trust_verify_supervisor import TrustScore, ConfidenceLevel
from Local_LLM.model_card import ModelRegistry, ModelCard, ModelCategory
from Local_LLM.enhanced_model_card import ModelMetadata
from Local_LLM.install_checks import verify_python_native_compatibility
from Local_LLM.cli_nonblocking import input_nonblocking, dedupe_preserve_order

# Initialize Local_LLM managers
llama_manager = LlamaCppManager()
local_llm_manager = LocalLLMManager()
fifo_memory = FIFO_Memory()
model_registry = ModelRegistry()
start_metrics_server(port=8000)

# Install-time check
verify_python_native_compatibility(["llama_cpp"])

# Example: Model metadata and trust/verification
def verify_and_score_response(response, worker_id="default", task_type="chat"):
    # Evidence and trust scoring
    evidence = Evidence(type=EvidenceType.DIRECT)
    trust = TrustScore(worker_id=worker_id, task_type=task_type, confidence=ConfidenceLevel.CERTAIN.value, basis="LocalLLM")
    return evidence, trust


# --- Modular Setup ---
def setup_app():
    setup_crash_handler()
    logger = setup_logging()
    start_background_gateways()
    services = initialize_services()
    return {
        'logger': logger,
        'services': services,
        'rag_system': services["rag_system"],
        'universal_extractor': services["universal_extractor"],
        'conversation_memory': services["conversation_memory"],
        'upload_cleanup': services["upload_cleanup"],
        'ZENA_CONFIG': services["ZENA_CONFIG"],
        'ZENA_MODE': services["ZENA_MODE"]
    }

def mount_static():
    import os
    os.makedirs("_static/rag_images", exist_ok=True)
    app.add_static_files('/rag_images', '_static/rag_images')

def get_backend():
    from async_backend import AsyncZenAIBackend
    from mock_backend import MockAsyncBackend
    return MockAsyncBackend() if "--mock" in sys.argv else AsyncZenAIBackend()

app_state = setup_app()
mount_static()
backend = get_backend()
logger = app_state['logger']
services = app_state['services']
rag_system = app_state['rag_system']
universal_extractor = app_state['universal_extractor']
conversation_memory = app_state['conversation_memory']
upload_cleanup = app_state['upload_cleanup']
ZENA_CONFIG = app_state['ZENA_CONFIG']
ZENA_MODE = app_state['ZENA_MODE']

@ui.page('/')
async def nebula_page():
    # --- Modern UI Layout ---
    ui_state = UIState()
    ui_state.session_id = str(uuid.uuid4())[:8]
    logger.info(f"[Session] New client session: {ui_state.session_id}")

    # Theme & App State
    setup_app_theme()
    app_state = {
        'rag_enabled': ZENA_CONFIG.get('rag_enabled', True) if ZENA_MODE else False,
        'open_rag_dialog': lambda: rag_dialog.open() if 'rag_dialog' in locals() else None
    }

    # Shared Services
    handlers = UIHandlers(
        ui_state=ui_state,
        app_state=app_state,
        rag_system=rag_system,
        universal_extractor=universal_extractor,
        conversation_memory=conversation_memory,
        async_backend=backend
    )

    # --- Layout ---
    with ui.column().classes('w-full h-screen bg-gradient-to-br from-blue-50 to-gray-100 p-6 gap-4'):  # Modern background
        with ui.row().classes('w-full items-center justify-between mb-4'):
            ui.label('ZEN_AI_RAG Chat').classes('text-2xl font-bold text-blue-700')
            ui.button('Settings', on_click=lambda: handlers.open_settings()).classes('bg-blue-500 text-white rounded px-4 py-2')

        with ui.row().classes('w-full gap-4'):
            ui.input('Ask anything...', on_change=handlers.handle_input).classes('w-2/3 bg-white rounded shadow')
            ui.button('Send', on_click=handlers.handle_send).classes('bg-green-500 text-white rounded px-4 py-2')

        with ui.column().classes('w-full bg-white rounded shadow p-4 mt-4'):
            ui.label('Conversation').classes('text-lg font-semibold mb-2')
            ui.list(handlers.get_conversation()).classes('w-full')

        with ui.row().classes('w-full justify-end mt-4'):
            ui.button('RAG Dialog', on_click=lambda: app_state['open_rag_dialog']()).classes('bg-purple-500 text-white rounded px-4 py-2')

    # --- Async Error Handling ---
    try:
        await handlers.async_backend.check_health()
    except Exception as e:
        ui.notify(f"Backend error: {str(e)}", color='negative')
    
    def rag_dialog_factory():
        return setup_rag_dialog(app_state, ZENA_MODE, ZENA_CONFIG, get_locale(), rag_system, Styles)
    
    def drawer_factory():
        # Note: config is imported from config_system
        return setup_drawer(backend, rag_system, config, dialogs, ZENA_MODE, EMOJI, app_state)

    # 6. Assemble Layout
    dialogs = dialog_factory()
    layout = build_page(ui_state, handlers, drawer_factory, rag_dialog_factory)
    header = layout['header']
    drawer = layout['drawer']
    
    # 7. Initialize Dark Mode
    from settings import is_dark_mode
    saved_dark_mode = is_dark_mode()
    dark_mode = ui.dark_mode(value=saved_dark_mode)

    def update_theme(is_dark: bool):
        if is_dark:
            header.props('dark'); drawer.props('dark')
            ui.query('body').classes(remove='bg-gray-50 text-gray-900', add='bg-slate-900 text-white')
        else:
            header.props(remove='dark'); drawer.props(remove='dark')
            ui.query('body').classes(remove='bg-slate-900 text-white', add='bg-gray-50 text-gray-900')
        ui.run_javascript('if(typeof syncDarkMode === "function") syncDarkMode();')

    update_theme(saved_dark_mode)

    # 8. Background Tasks (Per-Client)
    # Check backend health periodically
    import asyncio
    asyncio.create_task(handlers.check_backend_health())

    # Periodic cleanup
    ui.timer(10.0, lambda: upload_cleanup.cleanup(), once=True)
    ui.timer(6 * 3600, lambda: upload_cleanup.cleanup())

# 4. Register Global Events
register_test_endpoints()
register_test_endpoints()
# start_background_gateways() moved to top

@app.on_startup
async def on_startup():
    import asyncio
    asyncio.create_task(run_system_checks())
    if ZENA_MODE and rag_system:
        # Re-index if needed? bootstrap handled indexing.
        pass

def start_app():
    """Entry point for NiceGUI application."""
    import os
    from config_system import is_dark_mode
    from utils import ProcessManager
    
    # --- Zombie & Conflict Protection ---
    ui_port = getattr(config, 'ui_port', 8080)
    
    # Skip port checks if launched from server (ZENA_SKIP_PRUNE is set)
    if not os.environ.get("ZENA_SKIP_PRUNE"):
        from utils import is_port_active
        if is_port_active(ui_port):
            logger.warning(f"[!] Port {ui_port} is already active. Pruning existing UI...")
            if not ProcessManager.prune(ports=[ui_port], auto_confirm=True):
                 logger.error(f"[!] Could not clear port {ui_port}. Startup may fail.")
        
        # Check for port conflicts and handle "Zombie junk"
        if not ProcessManager.prune(auto_confirm=True):
            print("[!] Startup cancelled due to port conflict.")
            sys.exit(0)
    
    if 'NICEGUI_SCREEN_TEST_PORT' not in os.environ:
        os.environ['NICEGUI_SCREEN_TEST_PORT'] = '8081'

    # Local Device Mode (Native window)
    ui.run(title='ZenAI', dark=is_dark_mode(), port=8080, reload=False, native=False)

if __name__ == "__main__":
    try:
        start_app()
    except Exception as e:
        import traceback
        import time
        # Use safe characters for terminal to avoid UnicodeEncodeError on Windows
        error_msg = f"\n[!] FATAL ZENA UI ERROR: {e}\n"
        try:
            print(error_msg)
        except UnicodeEncodeError:
            print(f"\n[!] FATAL ZENA UI ERROR: {str(e).encode('ascii', 'ignore').decode()}\n")
        
        # Log to file for silent crashes (force utf-8)
        with open("ui_fatal_crash.txt", "w", encoding='utf-8') as f:
            f.write(error_msg)
            traceback.print_exc(file=f)
            
        traceback.print_exc()
        time.sleep(5)
        sys.exit(1)
