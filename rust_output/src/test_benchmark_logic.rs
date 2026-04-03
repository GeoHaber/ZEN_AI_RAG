use anyhow::{Result, Context};
use crate::profiler::{PerformanceMonitor, monitor};

/// Test performance monitor singleton.
pub fn test_performance_monitor_singleton() -> () {
    // Test performance monitor singleton.
    let mut m1 = PerformanceMonitor();
    let mut m2 = PerformanceMonitor();
    assert!(m1 == m2);
    assert!(m1.metrics == m2.metrics);
}

/// Test add metric and average.
pub fn test_add_metric_and_average() -> () {
    // Test add metric and average.
    monitor.metrics["test_metric".to_string()] = deque(/* maxlen= */ 50);
    monitor.add_metric("test_metric".to_string(), 10.0_f64);
    monitor.add_metric("test_metric".to_string(), 20.0_f64);
    let mut avgs = monitor.get_averages();
    assert!(avgs["test_metric".to_string()] == 15.0_f64);
}

/// Test tps calculation simulation.
pub fn test_tps_calculation_simulation() -> () {
    // Test tps calculation simulation.
    let mut start_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    let mut chunk_count = 10;
    std::thread::sleep(std::time::Duration::from_secs_f64(0.1_f64));
    let mut total_time = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_time);
    let mut tps = (chunk_count / total_time);
    monitor.add_metric("llm_tps".to_string(), tps);
    let mut avgs = monitor.get_averages();
    assert!(avgs["llm_tps".to_string()] > 0);
    println!("Calculated TPS: {:.2}", avgs["llm_tps".to_string()]);
}
