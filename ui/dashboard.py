from nicegui import ui
import logging
from zena_mode.profiler import monitor

logger = logging.getLogger("ZenAI.UI.Dashboard")

def build_performance_dashboard(ui_state):
    """Build the performance metrics dashboard row."""
    with ui.row().classes('w-full px-4 py-1 bg-gray-50/50 dark:bg-slate-800/50 backdrop-blur-sm border-b border-gray-100 dark:border-slate-800 gap-4 justify-center items-center'), ui.row().classes('items-center gap-1'):
        ui.label('⚡TPS:').classes('text-[10px] font-bold text-blue-500 uppercase')
        ui_state.tps_label = ui.label('0.0').classes('text-[10px] font-mono text-blue-600 dark:text-blue-400')
        with ui.row().classes('items-center gap-1'):
            ui.label('⏱️TTFT:').classes('text-[10px] font-bold text-orange-500 uppercase')
            ui_state.ttft_label = ui.label('0ms').classes('text-[10px] font-mono text-orange-600 dark:text-orange-400')
        with ui.row().classes('items-center gap-1'):
            ui.label('📚RAG:').classes('text-[10px] font-bold text-green-500 uppercase')
            ui_state.rag_latency_label = ui.label('0ms').classes('text-[10px] font-mono text-green-600 dark:text-green-400')

    def update_metrics():
        """Update metrics."""
        avgs = monitor.get_averages()
        ui_state.tps_label.text = f"{avgs['llm_tps']:.1f}"
        ui_state.ttft_label.text = f"{int(avgs['llm_ttft'])}ms"
        ui_state.rag_latency_label.text = f"{int(avgs['rag_retrieval'])}ms"
    
    ui.timer(1.0, update_metrics)
