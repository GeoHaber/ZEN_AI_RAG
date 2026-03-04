from nicegui import ui
import logging
from ui.registry import UI_IDS

logger = logging.getLogger("ZenAI.UI.Tour")

async def start_tutorial(client):
    """Run a spotlight tour of the interface."""
    ui.notify("🚀 Starting Guided Tour...", color='accent')
    
    # Inject CSS for spotlight
    ui.add_head_html('''
        <style>
            .spotlight {
                position: relative;
                z-index: 9999 !important;
                box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.75) !important;
                pointer-events: none;
                border-radius: 8px;
                transition: all 0.5s ease;
            }
        </style>
    ''')

    steps = [
        {"id": None, "msg": "👋 **Welcome to ZenAI!**<br>I'm your local AI powerhouse.<br>Let me show you around."},
        {"id": f"#{UI_IDS.INPUT_CHAT}", "msg": "💬 **Chat Input**<br>Type here to chat, or use **Drag & Drop** to analyze files."},
        {"id": f"#{UI_IDS.BTN_BATCH_START}", "msg": "🏗️ **Batch Mode**<br>Analyze entire folders of code at once."},
        {"id": "ui-drawer-btn", "msg": "📂 **Sidebar**<br>Access settings, models, and RAG configuration here."},
    ]

    with ui.dialog() as tour_dialog, ui.card().classes('w-96 items-center text-center'):
        lbl = ui.markdown().classes('text-lg mb-4')
        ui.button('Next', on_click=lambda: tour_dialog.submit(True))
        
    tour_dialog.open()
    
    for step in steps:
        lbl.content = step['msg']
        if step['id']:
             ui.run_javascript(f"document.querySelector('{step['id']}').classList.add('spotlight');")
        
        await tour_dialog
        tour_dialog.open()
        
        if step['id']:
             ui.run_javascript(f"document.querySelector('{step['id']}').classList.remove('spotlight');")
    
    tour_dialog.close()
    ui.notify("✨ Tour Complete! You're ready to go.", color='positive')
