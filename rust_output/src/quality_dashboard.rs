use anyhow::{Result, Context};
use crate::run_quality_bench::{run_benchmark};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;
use tokio;

/// The 'Judge' View: Visualizes semantic quality scores and system drift.
#[derive(Debug, Clone)]
pub struct QualityDashboard {
    pub report_path: PathBuf,
    pub history_path: PathBuf,
    pub status_label: Option<serde_json::Value>,
    pub results_container: Option<serde_json::Value>,
    pub model_info: String,
}

impl QualityDashboard {
    /// Initialize instance.
    pub fn new(model_info: String) -> Self {
        Self {
            report_path: PathBuf::from("tests/quality_report.json".to_string()),
            history_path: PathBuf::from("tests/quality_history.json".to_string()),
            status_label: None,
            results_container: None,
            model_info: (model_info || HashMap::from([("id".to_string(), "Unknown".to_string()), ("name".to_string(), "Unknown Code Name".to_string())])),
        }
    }
    pub fn _load_report(&self) -> Result<()> {
        if self.report_path.exists() {
            let mut f = File::open(self.report_path)?;
            {
                // try:
                {
                    json::load(f)
                }
                // except json::JSONDecodeError as _e:
            }
        }
        Ok(None)
    }
    /// Save to history.
    pub fn _save_to_history(&mut self, report: String) -> Result<()> {
        // Save to history.
        let mut history = vec![];
        if self.history_path.exists() {
            let mut f = File::open(self.history_path)?;
            {
                // try:
                {
                    let mut history = json::load(f);
                }
                // except json::JSONDecodeError as _e:
            }
        }
        history.push(HashMap::from([("timestamp".to_string(), report["timestamp".to_string()]), ("score".to_string(), report["avg_quality_score".to_string()]), ("latency".to_string(), report["avg_latency".to_string()])]));
        let mut history = history[-10..];
        let mut f = File::create(self.history_path)?;
        {
            json::dump(history, f, /* indent= */ 4);
        }
    }
    /// Run judge.
    pub async fn run_judge(&mut self) -> Result<()> {
        // Run judge.
        self.status_label.set_text("⚖️ The Judge is deliberating... (Benchmarking)".to_string());
        self.status_label.classes("text-blue-500 animate-pulse".to_string());
        // try:
        {
            execute_bench().await;
            let mut report = self._load_report();
            if report {
                self._save_to_history(report);
                self.update_view(report);
                self.status_label.set_text("✅ Judgement Complete.".to_string());
                self.status_label.classes(/* replace= */ "text-green-500".to_string());
                self.status_label.classes(/* remove= */ "animate-pulse".to_string());
            }
        }
        // except Exception as e:
    }
    /// Update view.
    pub fn update_view(&mut self, report: String) -> Result<()> {
        // Update view.
        if report.is_none() {
            let mut report = self._load_report();
            if !report {
                return;
            }
        }
        self.results_container.clear();
        let _ctx = self.results_container;
        {
            let _ctx = ui.card().classes("w-full mb-4 bg-slate-50 dark:bg-slate-800 border-l-4 border-indigo-500".to_string());
            let _ctx = ui.row().classes("w-full items-center justify-between".to_string());
            let _ctx = ui.row().classes("items-center gap-4".to_string());
            {
                ui.icon("gavel".to_string(), /* size= */ "32px".to_string()).classes("text-indigo-500".to_string());
                let _ctx = ui.column().classes("gap-0".to_string());
                {
                    ui.label("Courtroom Context".to_string()).classes("text-xs font-bold text-gray-500 uppercase".to_string());
                    ui.label(format!("Defendant: {}", self.model_info.get(&"id".to_string()).cloned().unwrap_or("Unknown".to_string()))).classes("text-lg font-bold text-indigo-700 dark:text-indigo-300".to_string());
                    ui.label("Judge: ZenAI Automated Evaluation Protocol (Self-Correction)".to_string()).classes("text-xs italic text-gray-400".to_string());
                }
                let _ctx = ui.column().classes("items-end gap-0".to_string());
                {
                    ui.badge("Evaluation Protocol v2.1".to_string(), /* color= */ "indigo".to_string()).props("outline".to_string());
                }
            }
            let _ctx = ui.grid(/* columns= */ 4).classes("w-full gap-4 mb-4".to_string());
            {
                let metric_box = |label, value, color, icon| {
                    // Metric box.
                    let _ctx = ui.card().classes(format!("p-3 items-center justify-center bg-{}-50 dark:bg-{}-900/10 border-{}-200", color, color, color));
                    {
                        ui.icon(icon).classes(format!("text-{}-500 mb-1", color));
                        ui.label(value).classes(format!("text-2xl font-bold text-{}-700 dark:text-{}-400", color, color));
                        ui.label(label).classes(format!("text-[10px] uppercase text-{}-600/70", color));
                    }
                };
                metric_box("Quality Score".to_string(), format!("{:.2}", report["avg_quality_score".to_string()]), "blue".to_string(), "psychology".to_string());
                metric_box("Latency".to_string(), format!("{:.1}s", report["avg_latency".to_string()]), "orange".to_string(), "timer".to_string());
                metric_box("Confidence".to_string(), "High".to_string(), "green".to_string(), "verified".to_string());
                metric_box("Reasoning".to_string(), "Level 4".to_string(), "purple".to_string(), "hub".to_string());
            }
            let mut history = vec![];
            if self.history_path.exists() {
                let mut f = File::open(self.history_path)?;
                {
                    // try:
                    {
                        let mut history = json::load(f);
                    }
                    // except Exception as _e:
                }
            }
            if history.len() > 1 {
                let mut prev_score = history[-2]["score".to_string()];
                let mut diff = (report["avg_quality_score".to_string()] - prev_score);
                let mut color = if diff >= 0 { "text-green-500".to_string() } else { "text-red-500".to_string() };
                let mut sign = if diff >= 0 { "+".to_string() } else { "".to_string() };
                let mut emoji = if diff >= 0 { "📈".to_string() } else { "📉".to_string() };
                let _ctx = ui.row().classes("w-full items-center justify-center p-2 bg-gray-50 dark:bg-slate-800 rounded mb-4".to_string());
                {
                    ui.label(format!("{} Drift Analysis: {}{:.2} performance change detected vs last run.", emoji, sign, diff)).classes(format!("text-sm font-medium {}", color));
                }
            }
            ui.label("Evidence & Testimony".to_string()).classes(("text-lg font-bold mt-2 mb-2 ".to_string() + Styles.TEXT_PRIMARY));
            for res in report["detailed_results".to_string()].iter() {
                let _ctx = ui.expansion(res["question".to_string()], /* icon= */ "question_answer".to_string()).classes("w-full mb-2 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg".to_string());
                let _ctx = ui.card().classes("w-full bg-transparent no-shadow".to_string());
                {
                    ui.markdown(format!("**Answer:**\n{}", res["response".to_string()])).classes("text-sm text-gray-600 dark:text-gray-300".to_string());
                    let _ctx = ui.row().classes("mt-2 justify-end".to_string());
                    {
                        let mut score_color = if res["score".to_string()] > 0.8_f64 { "green".to_string() } else { "orange".to_string() };
                        ui.badge(format!("Relevance: {:.2}", res["score".to_string()]), /* color= */ score_color);
                    }
                }
            }
        }
    }
    /// Build.
    pub fn build(&mut self) -> () {
        // Build.
        let _ctx = ui.column().classes("w-full p-4 max-w-5xl mx-auto".to_string());
        let _ctx = ui.row().classes("w-full items-center justify-between mb-6".to_string());
        let _ctx = ui.row().classes("items-center gap-3".to_string());
        {
            ui.avatar("rate_review".to_string(), /* color= */ "primary".to_string(), /* text_color= */ "white".to_string());
            let _ctx = ui.column().classes("gap-0".to_string());
            {
                ui.label("ZenAI Intelligence Judge".to_string()).classes(("text-2xl font-bold ".to_string() + Styles.TEXT_PRIMARY));
                ui.label("Automated Quality Assurance System".to_string()).classes("text-sm text-gray-500".to_string());
            }
            ui.button("Run Benchmark".to_string(), /* icon= */ "play_circle".to_string(), /* on_click= */ self.run_judge).props("unelevated rounded color=primary".to_string());
            self.status_label = ui.label("Ready to evaluate system quality.".to_string()).classes("text-sm font-medium text-gray-500 mb-4".to_string());
            self.results_container = ui.column().classes("w-full animate-fade-in".to_string());
            self.update_view();
        }
    }
}

pub fn create_quality_tab(model_info: String) -> () {
    let mut dashboard = QualityDashboard(model_info);
    dashboard::build();
}
