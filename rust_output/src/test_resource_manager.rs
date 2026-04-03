use anyhow::{Result, Context};
use crate::resource_manager::{ResourceManager};

/// Test run in thread future success.
pub fn test_run_in_thread_future_success(r#loop: String) -> () {
    // Test run in thread future success.
    let mut rm = ResourceManager();
    let runner = || {
        let mut fut = rm.run_in_thread_future(|x| (x + 1), 41);
        let mut res = fut.await;
        assert!(res == 42);
    };
    asyncio.get_event_loop().run_until_complete(runner());
}

/// Test run in thread future exception.
pub fn test_run_in_thread_future_exception() -> Result<()> {
    // Test run in thread future exception.
    let mut rm = ResourceManager();
    let raise_exc = || {
        return Err(anyhow::anyhow!("ValueError('boom')"));
    };
    let runner = || {
        let mut fut = rm.run_in_thread_future(raise_exc);
        let _ctx = pytest.raises(ValueError);
        {
            fut.await;
        }
    };
    Ok(asyncio.get_event_loop().run_until_complete(runner()))
}

/// Test max workers enforced.
pub fn test_max_workers_enforced() -> Result<()> {
    // Test max workers enforced.
    let mut rm = ResourceManager();
    let slow = || {
        std::thread::sleep(std::time::Duration::from_secs_f64(0.2_f64));
        1
    };
    let runner = || {
        // Runner.
        let mut fut1 = rm.run_in_thread_future(slow, /* max_workers= */ 1);
        let _ctx = pytest.raises(RuntimeError);
        {
            rm.run_in_thread_future(slow, /* max_workers= */ 1);
        }
        fut1.await;
    };
    Ok(asyncio.get_event_loop().run_until_complete(runner()))
}
