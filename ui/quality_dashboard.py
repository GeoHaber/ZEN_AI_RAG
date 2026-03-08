import asyncio
import json
import time
from pathlib import Path
from nicegui import ui
from tests.run_quality_bench import run_benchmark as execute_bench
from ui import Styles, Icons


class QualityDashboard:
    """
    The 'Judge' View: Visualizes semantic quality scores and system drift.
    """

    def __init__(self, model_info=None):
        """Initialize instance."""
        self.report_path = Path("tests/quality_report.json")
        self.history_path = Path("tests/quality_history.json")
        self.status_label = None
        self.results_container = None
        self.model_info = model_info or {"id": "Unknown", "name": "Unknown Code Name"}

    def _load_report(self):
        if self.report_path.exists():
            with open(self.report_path, "r") as f:
                return json.load(f)
        return None

    def _save_to_history(self, report):
        """Save to history."""
        history = []
        if self.history_path.exists():
            with open(self.history_path, "r") as f:
                history = json.load(f)

        history.append(
            {"timestamp": report["timestamp"], "score": report["avg_quality_score"], "latency": report["avg_latency"]}
        )
        # Keep last 10 runs
        history = history[-10:]

        with open(self.history_path, "w") as f:
            json.dump(history, f, indent=4)

    async def run_judge(self):
        """Run judge."""
        self.status_label.set_text("⚖️ The Judge is deliberating... (Benchmarking)")
        self.status_label.classes("text-blue-500 animate-pulse")

        try:
            # Run the benchmark logic
            await execute_bench()

            report = self._load_report()
            if report:
                self._save_to_history(report)
                self.update_view(report)
                self.status_label.set_text("✅ Judgement Complete.")
                self.status_label.classes(replace="text-green-500")
                self.status_label.classes(remove="animate-pulse")
        except Exception as e:
            self.status_label.set_text(f"❌ Error during bench: {e}")
            self.status_label.classes(replace="text-red-500")

    def update_view(self, report=None):
        """Update view."""
        if report is None:
            report = self._load_report()
            if not report:
                return

        self.results_container.clear()

        with self.results_container:
            # Courtroom Context Card
            with (
                ui.card().classes("w-full mb-4 bg-slate-50 dark:bg-slate-800 border-l-4 border-indigo-500"),
                ui.row().classes("w-full items-center justify-between"),
                ui.row().classes("items-center gap-4"),
            ):
                ui.icon("gavel", size="32px").classes("text-indigo-500")
                with ui.column().classes("gap-0"):
                    ui.label("Courtroom Context").classes("text-xs font-bold text-gray-500 uppercase")
                    ui.label(f"Defendant: {self.model_info.get('id', 'Unknown')}").classes(
                        "text-lg font-bold text-indigo-700 dark:text-indigo-300"
                    )
                    ui.label("Judge: ZenAI Automated Evaluation Protocol (Self-Correction)").classes(
                        "text-xs italic text-gray-400"
                    )

                with ui.column().classes("items-end gap-0"):
                    ui.badge("Evaluation Protocol v2.1", color="indigo").props("outline")

            # Summary Metrics
            with ui.grid(columns=4).classes("w-full gap-4 mb-4"):

                def metric_box(label, value, color, icon):
                    """Metric box."""
                    with ui.card().classes(
                        f"p-3 items-center justify-center bg-{color}-50 dark:bg-{color}-900/10 border-{color}-200"
                    ):
                        ui.icon(icon).classes(f"text-{color}-500 mb-1")
                        ui.label(value).classes(f"text-2xl font-bold text-{color}-700 dark:text-{color}-400")
                        ui.label(label).classes(f"text-[10px] uppercase text-{color}-600/70")

                metric_box("Quality Score", f"{report['avg_quality_score']:.2f}", "blue", "psychology")
                metric_box("Latency", f"{report['avg_latency']:.1f}s", "orange", "timer")
                metric_box("Confidence", "High", "green", "verified")  # Placeholder
                metric_box("Reasoning", "Level 4", "purple", "hub")  # Placeholder

            # Semantic Drift Detection
            history = []
            if self.history_path.exists():
                with open(self.history_path, "r") as f:
                    try:
                        history = json.load(f)
                    except Exception:
                        pass

            if len(history) > 1:
                prev_score = history[-2]["score"]
                diff = report["avg_quality_score"] - prev_score
                color = "text-green-500" if diff >= 0 else "text-red-500"
                sign = "+" if diff >= 0 else ""
                emoji = "📈" if diff >= 0 else "📉"
                with ui.row().classes(
                    "w-full items-center justify-center p-2 bg-gray-50 dark:bg-slate-800 rounded mb-4"
                ):
                    ui.label(
                        f"{emoji} Drift Analysis: {sign}{diff:.2f} performance change detected vs last run."
                    ).classes(f"text-sm font-medium {color}")

            # Detailed results
            ui.label("Evidence & Testimony").classes("text-lg font-bold mt-2 mb-2 " + Styles.TEXT_PRIMARY)
            for res in report["detailed_results"]:
                with (
                    ui.expansion(res["question"], icon="question_answer").classes(
                        "w-full mb-2 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg"
                    ),
                    ui.card().classes("w-full bg-transparent no-shadow"),
                ):
                    ui.markdown(f"**Answer:**\n{res['response']}").classes("text-sm text-gray-600 dark:text-gray-300")
                    with ui.row().classes("mt-2 justify-end"):
                        score_color = "green" if res["score"] > 0.8 else "orange"
                        ui.badge(f"Relevance: {res['score']:.2f}", color=score_color)

    def build(self):
        """Build."""
        with (
            ui.column().classes("w-full p-4 max-w-5xl mx-auto"),
            ui.row().classes("w-full items-center justify-between mb-6"),
            ui.row().classes("items-center gap-3"),
        ):
            ui.avatar("rate_review", color="primary", text_color="white")
            with ui.column().classes("gap-0"):
                ui.label("ZenAI Intelligence Judge").classes("text-2xl font-bold " + Styles.TEXT_PRIMARY)
                ui.label("Automated Quality Assurance System").classes("text-sm text-gray-500")

            ui.button("Run Benchmark", icon="play_circle", on_click=self.run_judge).props(
                "unelevated rounded color=primary"
            )

            self.status_label = ui.label("Ready to evaluate system quality.").classes(
                "text-sm font-medium text-gray-500 mb-4"
            )

            self.results_container = ui.column().classes("w-full animate-fade-in")
            self.update_view()


def create_quality_tab(model_info=None):
    dashboard = QualityDashboard(model_info)
    dashboard.build()
