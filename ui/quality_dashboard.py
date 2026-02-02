import asyncio
import json
import time
from pathlib import Path
from nicegui import ui
from tests.run_quality_bench import run_benchmark as execute_bench

class QualityDashboard:
    """
    The 'Judge' View: Visualizes semantic quality scores and system drift.
    """
    def __init__(self):
        self.report_path = Path("tests/quality_report.json")
        self.history_path = Path("tests/quality_history.json")
        self.status_label = None
        self.results_container = None
        
    def _load_report(self):
        if self.report_path.exists():
            with open(self.report_path, "r") as f:
                return json.load(f)
        return None

    def _save_to_history(self, report):
        history = []
        if self.history_path.exists():
            with open(self.history_path, "r") as f:
                history = json.load(f)
        
        history.append({
            "timestamp": report["timestamp"],
            "score": report["avg_quality_score"],
            "latency": report["avg_latency"]
        })
        # Keep last 10 runs
        history = history[-10:]
        
        with open(self.history_path, "w") as f:
            json.dump(history, f, indent=4)

    async def run_judge(self):
        self.status_label.set_text("⚖️ The Judge is deliberating... (Benchmarking)")
        self.status_label.classes('text-blue-500 animate-pulse')
        
        try:
            # Run the benchmark logic
            await execute_bench()
            
            report = self._load_report()
            if report:
                self._save_to_history(report)
                self.update_view(report)
                self.status_label.set_text("✅ Judgement Complete.")
                self.status_label.classes(replace='text-green-500')
                self.status_label.classes(remove='animate-pulse')
        except Exception as e:
            self.status_label.set_text(f"❌ Error during bench: {e}")
            self.status_label.classes(replace='text-red-500')

    def update_view(self, report=None):
        if report is None:
            report = self._load_report()
            if not report: return

        self.results_container.clear()
        
        with self.results_container:
            # Summary Metrics
            with ui.row().classes('w-full justify-around mb-4'):
                with ui.column().classes('items-center'):
                    ui.label(f"{report['avg_quality_score']:.2f}").classes('text-4xl font-bold text-blue-600')
                    ui.label('Semantic Quality').classes('text-xs uppercase text-gray-500')
                
                with ui.column().classes('items-center'):
                    ui.label(f"{report['avg_latency']:.1f}s").classes('text-4xl font-bold text-orange-600')
                    ui.label('Avg Latency').classes('text-xs uppercase text-gray-500')

            # Semantic Drift Detection
            history = []
            if self.history_path.exists():
                with open(self.history_path, "r") as f:
                    history = json.load(f)
            
            if len(history) > 1:
                prev_score = history[-2]['score']
                diff = report['avg_quality_score'] - prev_score
                color = "text-green-500" if diff >= 0 else "text-red-500"
                sign = "+" if diff >= 0 else ""
                ui.label(f"Drift: {sign}{diff:.2f} compared to last run").classes(f'text-sm font-medium {color} text-center w-full')

            # Detailed results
            ui.label('Detailed Report').classes('text-lg font-bold mt-4 mb-2')
            for res in report['detailed_results']:
                with ui.card().classes('w-full mb-2 bg-gray-50'):
                    with ui.row().classes('w-full items-center justify-between'):
                        ui.label(res['question']).classes('font-medium text-sm')
                        ui.badge(f"{res['score']:.2f}", color='blue' if res['score'] > 0.8 else 'orange')
                    ui.markdown(f"*Response:* {res['response'][:200]}...").classes('text-xs italic text-gray-600')

    def build(self):
        with ui.column().classes('w-full p-4'):
            with ui.row().classes('w-full items-center justify-between'):
                ui.label('ZenAI Intelligence Judge').classes('text-2xl font-bold')
                ui.button('Run Benchmark', on_click=self.run_judge).props('unelevated rounded')
            
            self.status_label = ui.label('Ready to evaluate system quality.').classes('text-sm text-gray-400')
            
            ui.separator().classes('my-4')
            
            self.results_container = ui.column().classes('w-full')
            self.update_view()

def create_quality_tab():
    dashboard = QualityDashboard()
    dashboard.build()
