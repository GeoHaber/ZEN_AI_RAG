import pytest
import time
from collections import deque
from zena_mode.profiler import PerformanceMonitor, monitor

def test_performance_monitor_singleton():
    """Test performance monitor singleton."""
    m1 = PerformanceMonitor()
    m2 = PerformanceMonitor()
    assert m1 is m2
    assert m1.metrics is m2.metrics

def test_add_metric_and_average():
    """Test add metric and average."""
    # Clear metrics for test
    monitor.metrics['test_metric'] = deque(maxlen=50)
    
    monitor.add_metric('test_metric', 10.0)
    monitor.add_metric('test_metric', 20.0)
    
    avgs = monitor.get_averages()
    assert avgs['test_metric'] == 15.0

def test_tps_calculation_simulation():
    """Test tps calculation simulation."""
    # Simulates the logic in async_backend
    start_time = time.time()
    chunk_count = 10
    time.sleep(0.1) # Ensure > 0 duration
    total_time = time.time() - start_time
    
    tps = chunk_count / total_time
    monitor.add_metric('llm_tps', tps)
    
    avgs = monitor.get_averages()
    assert avgs['llm_tps'] > 0
    print(f"Calculated TPS: {avgs['llm_tps']:.2f}")

if __name__ == "__main__":
    pytest.main([__file__])
