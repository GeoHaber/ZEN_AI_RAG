# -*- coding: utf-8 -*-
"""
ui_test_stub.py - Professional UI Test Harness for ZenAI (v4)

Features:
- Proper NiceGUI dark mode API
- API response logging
- Stress Test popup with accelerating speed
- Complete action matrix coverage
"""

import sys
import os
import time
import random
import asyncio
from datetime import datetime
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Clear NiceGUI test env vars
os.environ.pop('NICEGUI_SCREEN_TEST_PORT', None)
os.environ.pop('NICEGUI_SCREEN_TEST', None)

from nicegui import ui, app

# ============= CONSTANTS =============
DARK_BG = '#0f172a'   # Slate 900
LIGHT_BG = '#ffffff'  # White

# ============= STATE =============
class TestState:
    is_dark = True
    tts_on = False
    rag_on = False
    drawer_open = True
    stress_running = False
    stress_phase = 0
    action_count = 0
    logs = []
    messages = []

state = TestState()

MODELS = [
    "SmolLM2-135M",
    "Qwen-0.5B", 
    "Llama-3.2-3B",
    "Phi-3.5-mini",
    "Mistral-7B"
]

# ============= API LOGGING =============
def log(action: str, api_call: str = "", response: str = ""):
    """Log action with API call and response."""
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    if api_call:
        entry = f"[{ts}] {action}: {api_call} → {response}"
    else:
        entry = f"[{ts}] {action}"
    
    print(entry)
    state.logs.append(entry)
    state.action_count += 1
    
    if len(state.logs) > 200:
        state.logs = state.logs[-200:]
    
    try:
        log_panel.refresh()
    except:
        pass

# ============= PROPER DARK MODE API =============
dark_mode_ctrl = None  # Will hold the dark_mode instance
header_panel = None
drawer_panel = None
footer_panel = None

def update_theme():
    """Update Quasar component props based on state."""
    if not (header_panel and drawer_panel and footer_panel):
        return
        
    # Python-side state propagation to Quasar props
    # This is the clean, framework-intended way
    mode = 'dark' if state.is_dark else 'bisque' # Dummy value to remove 'dark'
    
    if state.is_dark:
        header_panel.props('dark')
        drawer_panel.props('dark')
        footer_panel.props('dark')
    else:
        header_panel.props(remove='dark')
        drawer_panel.props(remove='dark')
        footer_panel.props(remove='dark')
        
    log("THEME_UPDATE", f"Props updated for dark={state.is_dark}", "OK")

def set_dark_mode(enable: bool):
    """Use proper NiceGUI dark mode API."""
    global dark_mode_ctrl
    if dark_mode_ctrl is None:
        return
    
    if enable:
        dark_mode_ctrl.enable()
        state.is_dark = True
        log("DARK_MODE", "dark_mode.enable()", "True")
    else:
        dark_mode_ctrl.disable()
        state.is_dark = False
        log("DARK_MODE", "dark_mode.disable()", "False")
        
    update_theme()
    # Refresh content
    try:
        drawer_content.refresh()
    except:
        pass

def toggle_dark_mode():
    set_dark_mode(not state.is_dark)

# ============= ACTION HANDLERS =============
def toggle_tts():
    state.tts_on = not state.tts_on
    log("TTS", f"state.tts_on = {state.tts_on}", "OK")

def toggle_rag():
    state.rag_on = not state.rag_on
    log("RAG", f"state.rag_on = {state.rag_on}", "OK")

def select_model(m: str):
    log("MODEL", f"select('{m}')", "OK")

def send_message(text: str):
    if not text.strip():
        return
    log("USER_MSG", f"send('{text[:30]}...')" if len(text) > 30 else f"send('{text}')", "Queued")
    state.messages.append({"role": "user", "text": text, "is_rag": False})
    
    # Mock bot response with RAG awareness
    is_rag_reply = state.rag_on
    if is_rag_reply:
         reply = f"Thinking with RAG...\nFound context in {random.randint(1,4)} files.\nHere is the answer based on your data: {text}"
    else:
        reply = random.choice([
            "Mock response OK",
            "Test reply ✓",
            "Bot says hello! 🤖"
        ])
    
    state.messages.append({"role": "bot", "text": reply, "is_rag": is_rag_reply})
    log("BOT_REPLY", f"mock_reply('{reply[:20]}...', rag={is_rag_reply})", "Sent")
    
    try:
        chat_panel.refresh()
    except:
        pass

def menu_click(item: str):
    log("MENU", f"click('{item}')", "OK")

def voice_click():
    log("VOICE", "button.click()", "Recording mock")

def clear_chat():
    state.messages = []
    log("CLEAR", "messages.clear()", "OK")
    try:
        chat_panel.refresh()
    except:
        pass

def toggle_drawer():
    state.drawer_open = not state.drawer_open
    log("DRAWER", f"toggle() → {'OPEN' if state.drawer_open else 'CLOSED'}", "OK")
    drawer_panel.toggle()

def scan_action():
    log("SCAN", "rag_scan.start()", "Mock started")

def notify_test():
    ui.notify("Test notification!", color="info", position="top")
    log("NOTIFY", "ui.notify('Test')", "Shown")

# Window resize test sizes
WINDOW_SIZES = [
    (800, 600, "Small"),
    (1024, 768, "Medium"),
    (1280, 1024, "Large"),
    (1920, 1080, "Full HD"),
    (480, 800, "Mobile Portrait"),
    (800, 480, "Mobile Landscape"),
]

async def resize_window(width: int, height: int, name: str):
    """Resize browser viewport simulation via CSS."""
    try:
        # Simulate window resize by constraining body width
        js = f'''
        document.body.style.maxWidth = "{width}px";
        document.body.style.margin = "0 auto";
        document.body.style.border = "4px solid #333";
        document.body.style.boxShadow = "0 0 20px rgba(0,0,0,0.5)";
        window.dispatchEvent(new Event('resize'));
        '''
        if width >= 1920:  # Reset for full screen
            js = '''
            document.body.style.maxWidth = "";
            document.body.style.margin = "";
            document.body.style.border = "";
            document.body.style.boxShadow = "";
            window.dispatchEvent(new Event('resize'));
            '''
        
        await ui.run_javascript(js)
        log("RESIZE", f"Viewport -> {width}x{height}", f"{name}")
    except Exception as e:
        log("RESIZE_ERROR", f"Failed: {width}x{height}", str(e)[:30])

def resize_random():
    """Trigger random resize."""
    w, h, name = random.choice(WINDOW_SIZES)
    asyncio.create_task(resize_window(w, h, name))

# ============= ACTION MATRIX (All testable actions) =============
ALL_ACTIONS = [
    ("Dark Mode ON", lambda: set_dark_mode(True)),
    ("Dark Mode OFF", lambda: set_dark_mode(False)),
    ("Dark Toggle", toggle_dark_mode),
    ("TTS Toggle", toggle_tts),
    ("RAG Toggle", toggle_rag),
    ("Model: Random", lambda: select_model(random.choice(MODELS))),
    ("Model: SmolLM2", lambda: select_model("SmolLM2-135M")),
    ("Model: Qwen", lambda: select_model("Qwen-0.5B")),
    ("Model: Llama", lambda: select_model("Llama-3.2-3B")),
    ("Model: Phi", lambda: select_model("Phi-3.5-mini")),
    ("Model: Mistral", lambda: select_model("Mistral-7B")),
    ("Send: Short", lambda: send_message("Hi")),
    ("Send: Medium", lambda: send_message("This is a test message for the UI")),
    ("Send: Long", lambda: send_message("Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.")),
    ("Send: Random", lambda: send_message(f"Random test #{random.randint(1,9999)}")),
    ("Clear Chat", clear_chat),
    ("Menu: Home", lambda: menu_click("Home")),
    ("Menu: Settings", lambda: menu_click("Settings")),
    ("Menu: Scan", lambda: menu_click("Scan Folder")),
    ("Menu: Download", lambda: menu_click("Download Model")),
    ("Menu: About", lambda: menu_click("About")),
    ("Voice Button", voice_click),
    ("Scan Action", scan_action),
    ("Notify Test", notify_test),
    ("Resize: Random", resize_random),
]

# ============= STRESS TEST ENGINE =============
STRESS_PHASES = [
    {"name": "Slow", "delay": 1.0, "duration": 8},
    {"name": "Medium", "delay": 0.5, "duration": 8},
    {"name": "Fast", "delay": 0.25, "duration": 8},
    {"name": "Very Fast", "delay": 0.1, "duration": 8},
    {"name": "STRESS", "delay": 0.05, "duration": 8},
]

async def run_stress_test():
    """Run accelerating stress test through all phases."""
    if state.stress_running:
        log("STRESS", "Already running!", "SKIP")
        return
    
    state.stress_running = True
    state.action_count = 0
    log("STRESS", "=== STRESS TEST STARTED ===", "")
    
    try:
        for phase_idx, phase in enumerate(STRESS_PHASES):
            state.stress_phase = phase_idx + 1
            log("STRESS", f"Phase {phase_idx+1}/5: {phase['name']}", f"Delay={phase['delay']}s")
            
            start_time = time.time()
            while (time.time() - start_time) < phase["duration"]:
                if not state.stress_running:
                    log("STRESS", "Stopped by user", "ABORT")
                    return
                
                # Pick random action
                action_name, action_fn = random.choice(ALL_ACTIONS)
                try:
                    action_fn()
                except Exception as e:
                    log("ERROR", f"{action_name}", str(e)[:50])
                
                await asyncio.sleep(phase["delay"])
        
        log("STRESS", f"=== COMPLETED: {state.action_count} actions ===", "SUCCESS")
    finally:
        state.stress_running = False
        state.stress_phase = 0

def stop_stress_test():
    state.stress_running = False
    log("STRESS", "Stop requested", "Stopping...")

# ============= REFRESHABLE UI COMPONENTS =============
@ui.refreshable
def log_panel():
    """Action log panel."""
    with ui.column().classes('w-full h-72 bg-gray-900 rounded p-2 overflow-y-auto font-mono text-xs'):
        for entry in state.logs[-20:]:
            # Color code by type
            if "ERROR" in entry:
                color = "text-red-400"
            elif "STRESS" in entry:
                color = "text-yellow-400"
            elif "API" in entry or "→" in entry:
                color = "text-cyan-400"
            else:
                color = "text-green-400"
            ui.label(entry).classes(f'{color} whitespace-nowrap')

@ui.refreshable
def chat_panel():
    """Chat messages panel."""
    with ui.column().classes('w-full gap-2'):
        if not state.messages:
            ui.label("Send a message...").classes('text-gray-400 italic text-sm')
        for msg in state.messages[-8:]:
            # RAG messages get special styling
            is_rag = msg.get("is_rag", False)
            bg_class = "bg-green-100 dark:bg-green-900 border-green-500" if is_rag else "bg-gray-100 dark:bg-slate-600"
                
            if msg["role"] == "user":
                 with ui.row().classes('w-full justify-end'):
                     ui.label(msg["text"]).classes('bg-blue-100 dark:bg-blue-900 text-blue-900 dark:text-blue-100 p-2 rounded-lg max-w-[80%]')
            else:
                 with ui.row().classes('w-full justify-start items-start gap-2'):
                     if is_rag:
                         ui.icon('auto_awesome').classes('text-green-500 mt-1')
                     ui.label(msg["text"]).classes(f'{bg_class} text-gray-800 dark:text-gray-100 p-2 rounded-lg max-w-[80%] whitespace-pre-wrap')

@ui.refreshable
def stress_status():
    """Stress test status display."""
    if state.stress_running:
        ui.label(f"🔥 STRESS TEST: Phase {state.stress_phase}/5 | Actions: {state.action_count}").classes('text-yellow-400 font-bold')
    else:
        ui.label("Ready for testing").classes('text-gray-400')

@ui.refreshable
def drawer_content():
    """Drawer content that refreshes on theme change."""
    text_class = "text-white" if state.is_dark else "text-gray-800"
    btn_text_class = "text-white" if state.is_dark else "text-gray-700"
    
    ui.label('Menu').classes(f'text-lg font-bold mb-4 {text_class}')
    
    for item in ['Home', 'Settings', 'Scan Folder', 'Download Model', 'About']:
        ui.button(item, icon='chevron_right', on_click=lambda i=item: menu_click(i)).props('flat align=left').classes(f'w-full justify-start mb-1 {btn_text_class}')
    
    ui.separator().classes('my-4')
    
    ui.label('Model').classes(f'font-bold mb-2 {text_class}')
    ui.select(MODELS, value=MODELS[2], on_change=lambda e: select_model(e.value)).classes('w-full')

# ============= STRESS TEST DIALOG =============
def create_stress_dialog():
    with ui.dialog() as dialog, ui.card().classes('p-6 w-[500px]'):
        ui.label('🧪 UI Stress Test').classes('text-2xl font-bold mb-4')
        
        ui.markdown('''
**This test will:**
1. Run ALL possible UI actions randomly
2. Start SLOW (1s delay) → Get FASTER (0.05s delay)
3. 5 phases, ~40 seconds total
4. Log every action and API response

**Purpose:** Find UI bugs, race conditions, and crashes.
        ''').classes('mb-4')
        
        # Phase breakdown
        with ui.card().classes('bg-gray-100 dark:bg-slate-800 p-3 mb-4'):
            ui.label('Phases:').classes('font-bold mb-2')
            for i, p in enumerate(STRESS_PHASES):
                ui.label(f"{i+1}. {p['name']}: {p['duration']}s @ {p['delay']}s delay").classes('text-sm font-mono')
        
        with ui.row().classes('gap-2 w-full'):
            ui.button('🚀 START', on_click=lambda: [dialog.close(), asyncio.create_task(run_stress_test())]).props('color=positive').classes('flex-grow')
            ui.button('Cancel', on_click=dialog.close).props('flat')
    
    return dialog

# ============= MAIN UI =============
# ============= MAIN UI =============
def build_ui():
    """Build the professional test UI."""
    global dark_mode_ctrl, header_panel, drawer_panel, footer_panel
    
    # Create dark mode controller FIRST
    dark_mode_ctrl = ui.dark_mode(True)  # Start in dark mode
    
    stress_dialog = create_stress_dialog()
    
    # --- HEADER (matches zena.py) ---
    header_panel = ui.header().classes('p-3 shadow-sm transition-all duration-300')
    header_panel.classes('bg-white dark:bg-slate-800 text-gray-800 dark:text-white border-b border-gray-200 dark:border-slate-700')
    
    with header_panel:
        with ui.row().classes('w-full items-center justify-between'):
            # Left: Menu toggle (actually toggles drawer)
            ui.button(icon='menu', on_click=lambda: drawer_panel.toggle()).props('flat').classes('text-gray-700 dark:text-white')
            
            # Dark mode toggle (single button)
            ui.button(icon='dark_mode', on_click=toggle_dark_mode).props('flat').classes('text-gray-700 dark:text-white').tooltip('Toggle Dark/Light')
            
            # Center title
            ui.label('ZenAI').classes('text-xl font-bold text-gray-800 dark:text-white')
            
            # Right: TTS + RAG + Scan Button + Stress Test
            with ui.row().classes('gap-2 items-center'):
                ui.button(icon='volume_up', on_click=toggle_tts).props('flat').classes('text-gray-700 dark:text-white').tooltip('TTS')
                
                # Scan Button (hidden by default, shown when RAG enabled)
                scan_button = ui.button('Start Scanning', icon='book', on_click=scan_action).props('flat').classes('text-blue-600 dark:text-blue-400')
                scan_button.visible = False
                
                # RAG Toggle (shows/hides scan button)
                def on_rag_toggle(e):
                    state.rag_on = e.value
                    scan_button.visible = e.value
                    status = "enabled" if e.value else "disabled"
                    ui.notify(f"RAG mode {status}", color="positive" if e.value else "info")
                    log("RAG", f"toggle({e.value})", f"scan_button.visible={e.value}")
                
                ui.switch('Scan & Learn', value=False, on_change=on_rag_toggle).props('color=cyan keep-color').classes('text-gray-700 dark:text-white')
                
                ui.button('🧪 STRESS', on_click=stress_dialog.open).props('color=warning dense')
    
    # --- LEFT DRAWER (with dark mode colors) ---
    drawer_panel = ui.left_drawer(value=True).classes('p-4 transition-all duration-300')
    drawer_panel.classes('bg-gray-100 dark:bg-slate-700 text-gray-800 dark:text-white')
    
    with drawer_panel:
        drawer_content()
    
    # --- MAIN CONTENT ---
    # Added 'main-content-row' class for JS targeting
    with ui.row().classes('w-full flex-grow p-4 gap-4 main-content-row'):
        # LEFT: Chat
        # Added 'content-col' class
        with ui.column().classes('w-full md:w-1/2 gap-4 content-col'): # Responsive: full width on mobile
            ui.label('💬 Chat').classes('text-lg font-bold')
            with ui.card().classes('w-full min-h-60'):
                chat_panel()
        
        # RIGHT: Log + Controls
        # Added 'content-col' class
        with ui.column().classes('w-full md:w-1/2 gap-2 content-col'): # Responsive: full width on mobile
            ui.label('📟 Action Log').classes('text-lg font-bold')
            stress_status()
            log_panel()
            
            with ui.row().classes('gap-2 mt-2'):
                ui.button('Run Random', icon='shuffle', on_click=lambda: asyncio.create_task(run_random_quick())).props('color=primary')
                ui.button('Stop', icon='stop', on_click=stop_stress_test).props('color=negative flat')
                ui.button('Clear Log', on_click=lambda: [state.logs.clear(), log_panel.refresh()]).props('flat')
    
    # --- FOOTER (with dark mode colors) ---
    footer_panel = ui.footer().classes('p-3 transition-all duration-300')
    footer_panel.classes('bg-white dark:bg-slate-800 text-gray-800 dark:text-white border-t border-gray-200 dark:border-slate-700')
    with footer_panel:
        with ui.row().classes('w-full items-center gap-2'):
            ui.button(icon='mic', on_click=voice_click).props('round color=primary')
            msg_input = ui.input(placeholder='Type a message...').classes('flex-grow bg-white dark:bg-slate-900 rounded').props('outlined dense')
            
            def do_send():
                if msg_input.value:
                    send_message(msg_input.value)
                    msg_input.value = ''
            
            msg_input.on('keydown.enter', do_send)
            ui.button(icon='send', on_click=do_send).props('round color=primary')
            ui.button('Clear', on_click=clear_chat).props('flat color=grey')
    
    # Apply initial dark mode
    set_dark_mode(True)
    update_theme() # Ensure props are set
    
    # Add JavaScript error handler to capture browser errors
    ui.add_head_html('''
    <script>
    window.addEventListener('error', function(e) {
        console.log('[JS_ERROR]', e.message, e.filename, e.lineno);
    });
    window.addEventListener('unhandledrejection', function(e) {
        console.log('[JS_PROMISE_ERROR]', e.reason);
    });
    </script>
    ''')
    log("SETUP", "JavaScript error handlers", "Installed")

async def resize_window(width: int, height: int, name: str):
    """Resize app simulation via CSS injection for fixed elements."""
    try:
        # Simulate window resize by constraining key elements
        # We need to target header, footer, drawer, and main content
        
        if width >= 1920: # Reset
            css = """
            document.body.style.maxWidth = '';
            document.body.style.margin = '';
            document.body.style.border = '';
            
            // Reset layout container
            var layout = document.querySelector('.q-layout');
            if(layout) layout.style.maxWidth = '';
            if(layout) layout.style.margin = '';

            // Fix header/footer width
            document.querySelectorAll('.q-header, .q-footer, .q-drawer').forEach(el => {
                el.style.maxWidth = '';
                el.style.left = '';
                el.style.right = '';
                el.style.width = '';
            });
            window.dispatchEvent(new Event('resize'));
            """
        else:
            # Constrain to width, center on screen
            css = f"""
            document.body.style.maxWidth = '{width}px';
            document.body.style.margin = '0 auto';
            document.body.style.border = '4px solid #F59E0B';
            
            // Constrain layout container
            var layout = document.querySelector('.q-layout');
            if(layout) layout.style.maxWidth = '{width}px';
            if(layout) layout.style.margin = '0 auto';
            
            // Force fixed elements to respect the new body width
            document.querySelectorAll('.q-header, .q-footer').forEach(el => {{
                el.style.maxWidth = '{width}px';
                el.style.left = '50%';
                el.style.transform = 'translateX(-50%)';
                el.style.width = '100%';
            }});
            
            window.dispatchEvent(new Event('resize'));
            """
        
        # SIMULATE RESPONSIVE LAYOUT (Since width change doesn't trigger media queries)
        # We must manually switch flex directions if width < 800
        is_mobile = width < 800
        
        js_layout = f'''
        const mainRow = document.querySelector('.main-content-row');
        const cols = document.querySelectorAll('.content-col');
        
        if ({str(is_mobile).lower()}) {{
            // Mobile: Stack vertically
            if(mainRow) {{
                mainRow.classList.remove('flex-row', 'gap-4');
                mainRow.classList.add('flex-col', 'gap-2');
            }}
            cols.forEach(c => {{
                c.classList.remove('w-1/2'); // Remove desktop width
                c.classList.add('w-full');   // Force full width
            }});
        }} else {{
            // Desktop: Side by side
            if(mainRow) {{
                mainRow.classList.remove('flex-col', 'gap-2');
                mainRow.classList.add('flex-row', 'gap-4');
            }}
            cols.forEach(c => {{
                c.classList.remove('w-full');
                c.classList.add('w-1/2');
            }});
        }}
        '''
        
        await ui.run_javascript(css)
        await ui.run_javascript(js_layout) # Apply layout shift
        
        log("RESIZE", f"App -> {width}px", f"{name} (Reflowed)")
    except Exception as e:
        log("RESIZE_ERROR", f"Failed: {width}x{height}", str(e)[:30])

async def run_random_quick():
    """Quick random test (10 actions)."""
    log("QUICK", "=== Quick Random Test ===", "")
    for i in range(10):
        name, fn = random.choice(ALL_ACTIONS)
        try:
            fn()
        except:
            pass
        await asyncio.sleep(0.3)
    log("QUICK", "=== Done ===", "")

# ============= MAIN =============
def main():
    @ui.page('/')
    async def index():
        build_ui()
        log("STARTUP", "UI Test Stub v4 ready!", "Professional Edition")
    
    print("[UI Test Stub v4] Starting on port 8090...")
    ui.run(title='ZenAI Test Stub v4', port=8090, reload=False)

if __name__ == '__main__':
    main()
