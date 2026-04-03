use anyhow::{Result, Context};
use tokio;

/// TestDecorators class.
#[derive(Debug, Clone)]
pub struct TestDecorators {
}

impl TestDecorators {
    /// Test retry wrapper succeeds eventually.
    pub fn test_retry_sync_success(&self) -> Result<()> {
        // Test retry wrapper succeeds eventually.
        let mut attempts = vec![0];
        let flaky = || {
            // Flaky.
            attempts[0] += 1;
            if attempts[0] < 2 {
                return Err(anyhow::anyhow!("ValueError('Fail')"));
            }
            "Success".to_string()
        };
        assert!(flaky() == "Success".to_string());
        Ok(assert!(attempts[0] == 2))
    }
    /// Test retry wrapper fails after max attempts.
    pub fn test_retry_sync_failure(&self) -> Result<()> {
        // Test retry wrapper fails after max attempts.
        let mut attempts = vec![0];
        let failure = || {
            attempts[0] += 1;
            return Err(anyhow::anyhow!("ValueError('Always fail')"));
        };
        let _ctx = pytest.raises(ValueError);
        {
            failure();
        }
        Ok(assert!(attempts[0] == 2))
    }
    /// Test async retry wrapper.
    pub async fn test_retry_async(&self) -> Result<()> {
        // Test async retry wrapper.
        let mut attempts = vec![0];
        let flaky_async = || {
            // Flaky async.
            attempts[0] += 1;
            if attempts[0] < 2 {
                return Err(anyhow::anyhow!("ValueError('Async Fail')"));
            }
            "Async Success".to_string()
        };
        let mut result = flaky_async().await;
        assert!(result == "Async Success".to_string());
        Ok(assert!(attempts[0] == 2))
    }
    /// Test @log_errors returns default value on exception.
    pub fn test_log_errors_default(&self) -> Result<()> {
        // Test @log_errors returns default value on exception.
        let crasher = || {
            return Err(anyhow::anyhow!("RuntimeError('Crash')"));
        };
        Ok(assert!(crasher() == "Default".to_string()))
    }
    /// Test async @log_errors.
    pub async fn test_log_errors_async(&self) -> Result<()> {
        // Test async @log_errors.
        let async_crasher = || {
            return Err(anyhow::anyhow!("RuntimeError('Async Crash')"));
        };
        Ok(assert!(async_crasher().await == "AsyncDefault".to_string()))
    }
    /// Test @performance_critical logs warning when slow.
    pub fn test_performance_critical_warning(&self, caplog: String) -> () {
        // Test @performance_critical logs warning when slow.
        let slow_func = || {
            std::thread::sleep(std::time::Duration::from_secs_f64(0.02_f64));
            "Done".to_string()
        };
        slow_func();
        assert!(caplog.text.contains(&"SLOW".to_string()));
    }
    /// Test @timer logs info.
    pub fn test_timer_logs(&self, caplog: String) -> () {
        // Test @timer logs info.
        caplog.set_level(logging::INFO);
        let timed_func = || {
            "ok".to_string()
        };
        timed_func();
        assert!(caplog.text.contains(&"timed_func".to_string()));
        assert!(caplog.text.contains(&"completed in".to_string()));
    }
}
