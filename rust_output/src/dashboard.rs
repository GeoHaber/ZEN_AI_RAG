use anyhow::{Result, Context};
use crate::profiler::{monitor};

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Build the performance metrics dashboard row.
pub fn build_performance_dashboard(ui_state: String) -> () {
    // Build the performance metrics dashboard row.
    let _ctx = ui.row().classes("w-full px-4 py-1 bg-gray-50/50 dark:bg-slate-800/50 backdrop-blur-sm border-b border-gray-100 dark:border-slate-800 gap-4 justify-center items-center".to_string());
    let _ctx = ui.row().classes("items-center gap-1".to_string());
    {
        ui.label("⚡TPS:".to_string()).classes("text-[10px] font-bold text-blue-500 uppercase".to_string());
        ui_state::tps_label = ui.label("0.0".to_string()).classes("text-[10px] font-mono text-blue-600 dark:text-blue-400".to_string());
        let _ctx = ui.row().classes("items-center gap-1".to_string());
        {
            ui.label("⏱️TTFT:".to_string()).classes("text-[10px] font-bold text-orange-500 uppercase".to_string());
            ui_state::ttft_label = ui.label("0ms".to_string()).classes("text-[10px] font-mono text-orange-600 dark:text-orange-400".to_string());
        }
        let _ctx = ui.row().classes("items-center gap-1".to_string());
        {
            ui.label("📚RAG:".to_string()).classes("text-[10px] font-bold text-green-500 uppercase".to_string());
            ui_state::rag_latency_label = ui.label("0ms".to_string()).classes("text-[10px] font-mono text-green-600 dark:text-green-400".to_string());
        }
    }
    let update_metrics = || {
        // Update metrics.
        let mut avgs = monitor.get_averages();
        ui_state::tps_label.text = format!("{:.1}", avgs["llm_tps".to_string()]);
        ui_state::ttft_label.text = format!("{}ms", avgs["llm_ttft".to_string()].to_string().parse::<i64>().unwrap_or(0));
        ui_state::rag_latency_label.text = format!("{}ms", avgs["rag_retrieval".to_string()].to_string().parse::<i64>().unwrap_or(0));
    };
    ui.timer(1.0_f64, update_metrics);
}
