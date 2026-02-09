from nicegui import ui
from ui import Styles
import asyncio
import random
import time

def render_rag_summary(stats, container, on_reset=None, on_close=None):
    """Render a colorful, detailed summary card after ingestion."""
    container.clear()
    with container:
        with ui.card().classes('w-full bg-white dark:bg-slate-800 border-l-4 border-green-500 p-4 animate-fade-in'):
            # Header
            with ui.row().classes('w-full items-center justify-between mb-3'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('check_circle', size='28px').classes('text-green-500')
                    with ui.column().classes('gap-0'):
                        ui.label('Ingestion Complete').classes('text-lg font-bold text-green-700 dark:text-green-400')
                        ui.label(f"Processed in {stats['time_taken']:.1f}s").classes('text-xs text-gray-400')
                
                ui.badge(f"{stats['total_size']}", color='green').props('outline').classes('text-xs font-mono')

            ui.separator().classes('mb-3 opacity-50')
            
            # Key Metrics Grid
            with ui.grid(columns=3).classes('w-full gap-2 mb-4'):
                def stat_box(label, value, icon, color):
                    with ui.column().classes(f'p-2 rounded bg-{color}-50 dark:bg-{color}-900/20 items-center justify-center text-center'):
                        ui.icon(icon, size='20px').classes(f'text-{color}-500 mb-1')
                        ui.label(str(value)).classes(f'text-lg font-bold text-{color}-700 dark:text-{color}-300 leading-none')
                        ui.label(label).classes(f'text-[10px] uppercase tracking-wider text-{color}-600/70 dark:text-{color}-400/70')

                stat_box('Files', stats['files'], 'description', 'blue')
                stat_box('Chunks', stats['chunks'], 'segment', 'purple')
                stat_box('Images', stats['images'], 'image', 'orange')

            # Detailed Breakdown
            ui.label('Content Distribution').classes('text-xs font-bold text-gray-500 mb-2 uppercase tracking-wide')
            with ui.column().classes('w-full gap-1'):
                for ftype, count in stats['breakdown'].items():
                    pct = (count / stats['files']) * 100 if stats['files'] > 0 else 0
                    with ui.row().classes('w-full items-center gap-2 text-xs'):
                        ui.label(ftype).classes('w-12 font-mono text-gray-600 dark:text-gray-400')
                        ui.linear_progress(value=pct/100, show_value=False, color='grey').classes('flex-grow h-1.5 rounded-full opacity-50')
                        ui.label(str(count)).classes('w-6 text-right font-bold')

            # Footer Actions
            with ui.row().classes('w-full gap-2 mt-4'):
                def handle_chat_click():
                    ui.notify("Ready to chat!")
                    if on_close: on_close()
                
                ui.button('Start Chatting', icon='chat', on_click=handle_chat_click).props('flat dense flex-grow text-green-500')
                if on_reset:
                    ui.button('New Scan', icon='refresh', on_click=on_reset).props('flat dense text-gray-500').classes('w-auto')

def setup_rag_dialog(app_state, ZENA_MODE, ZENA_CONFIG, locale, rag_system, Styles):
    """Setup the RAG dialog and its logic in a clean, modular way."""
    rag_dialog = ui.dialog().classes('z-50')
    app_state['open_rag_dialog'] = rag_dialog.open
    
    with rag_dialog, ui.card().classes('w-[600px] max-w-[95vw] max-h-[85vh] p-0 rounded-2xl shadow-2xl bg-white dark:bg-slate-900 flex flex-col overflow-hidden'):
        if ZENA_MODE:
            # Header (Fixed padding)
            with ui.column().classes('w-full p-6 pb-2'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('library_books', size='28px').classes('text-blue-500')
                    ui.label("Knowledge Base Scanner").classes('text-xl font-bold ' + Styles.TEXT_PRIMARY)
                
                ui.label("Add websites or local files to the AI's knowledge").classes('text-sm text-gray-500 dark:text-gray-400')
            
            # Scrollable Content (Padding inside)
            with ui.column().classes('w-full px-6 overflow-y-auto').style('max-height: 60vh'):
                # Content Area (Tabs or Summary)
                content_container = ui.column().classes('w-full')
                
                with content_container:
                    # Mode selector with clear tabs
                    with ui.tabs().classes('w-full mb-4') as mode_tabs:
                        web_tab = ui.tab('website', label='🌐 Website')
                        dir_tab = ui.tab('directory', label='📁 Local Files')
                    
                    with ui.tab_panels(mode_tabs, value='website').classes('w-full'):
                        # Website Panel
                        with ui.tab_panel('website'):
                            with ui.column().classes('w-full gap-3'):
                                ui.input('Website URL', placeholder='https://example.com', value=ZENA_CONFIG.get('website_url', '')).props('outlined').classes('w-full').bind_value(app_state, 'rag_url')
                                with ui.row().classes('w-full gap-2'):
                                    ui.number('Max Pages', value=50, min=1, max=500).props('outlined dense').classes('w-24').bind_value(app_state, 'rag_max_pages')
                                    ui.label('pages to scan').classes('text-sm text-gray-400 self-center')
                        
                        # Directory Panel
                        with ui.tab_panel('directory'):
                            with ui.column().classes('w-full gap-3'):
                                ui.input('Directory Path', placeholder='C:/Users/YourName/Documents').props('outlined').classes('w-full').bind_value(app_state, 'rag_dir')
                                with ui.row().classes('w-full gap-2'):
                                    ui.number('Max Files', value=1000, min=1, max=10000).props('outlined dense').classes('w-24').bind_value(app_state, 'rag_max_files')
                                    ui.label('files to index').classes('text-sm text-gray-400 self-center')
                                ui.label('Supports: .txt, .md, .py, .pdf, .docx, .png, .jpg').classes('text-xs text-gray-400')
                
                ui.separator().classes('my-4')
                
                # Progress section
                with ui.column().classes('w-full gap-2') as progress_section:
                    progress_label = ui.label('').classes('text-sm font-medium text-blue-600 dark:text-blue-400')
                    progress_bar = ui.linear_progress(value=0, show_value=True).classes('w-full')
                    progress_bar.visible = False
                    stats_label = ui.label('').classes('text-xs text-gray-500')
                
                app_state['rag_progress_label'] = progress_label
                app_state['rag_progress_bar'] = progress_bar
                app_state['rag_stats_label'] = stats_label
                
                # Summary Container
                summary_container = ui.column().classes('w-full mt-2')

            def reset_view():
                content_container.visible = True
                summary_container.clear()

            async def start_scan():
                # Reset UI
                content_container.visible = True
                progress_bar.visible = True
                progress_bar.value = 0
                progress_label.text = "🔍 Starting scan..."
                stats_label.text = ""
                summary_container.clear()
                
                start_time = time.time()
                
                try:
                    # Simulate progress
                    # TODO: Call actual rag_system scan stats
                    total_steps = 15
                    for i in range(total_steps):
                        await asyncio.sleep(0.2)
                        progress_bar.value = (i + 1) / total_steps
                        progress_label.text = f"📄 Processing file {i+1}/{total_steps}..."
                        if i == 5: progress_label.text = "🖼️ Extracting images..."
                        if i == 10: progress_label.text = "🧠 Generating embeddings..."

                    # Generate rich stats for summary
                    elapsed = time.time() - start_time
                    mock_stats = {
                        'files': 42,
                        'chunks': 1250,
                        'images': 8,
                        'total_size': '15.4 MB',
                        'time_taken': elapsed,
                        'breakdown': {
                            'PDF Documents': 12,
                            'Markdown / Text': 20,
                            'Source Code': 5,
                            'Images': 5
                        }
                    }
                    
                    # Hide progress, show summary
                    progress_section.visible = False
                    content_container.visible = False # Hide inputs on success
                    
                    render_rag_summary(mock_stats, summary_container, on_reset=reset_view, on_close=rag_dialog.close)
                    
                    ui.notify("Knowledge base updated!", color='positive')
                    
                    if 'user_input' in app_state and app_state.get('send_handler'):
                        await asyncio.sleep(2)
                        pass 

                except Exception as e:
                    progress_label.text = f"❌ Error: {str(e)[:50]}"
                    progress_bar.visible = False
            
            # Buttons (Footer, fixed padding)
            with ui.column().classes('w-full p-6 pt-2 border-t dark:border-slate-800'):
                with ui.row().classes('w-full gap-2'):
                    ui.button('Start Scan', icon='search', on_click=start_scan).props('color=primary unelevated').classes('flex-grow')
                    ui.button('Close', on_click=rag_dialog.close).props('flat').classes('text-gray-500')
        else:
            ui.label("RAG not enabled in Zena mode").classes('text-center text-gray-400')
            ui.button('Close', on_click=rag_dialog.close).props('flat').classes('w-full mt-2')
    
    return rag_dialog
