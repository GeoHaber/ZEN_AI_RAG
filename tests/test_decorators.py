
import pytest
import asyncio
import time
import logging
from unittest.mock import MagicMock, patch
from decorators import retry, log_errors, performance_critical, timer

class TestDecorators:
    """TestDecorators class."""
    
    def test_retry_sync_success(self):
        """Test retry wrapper succeeds eventually."""
        attempts = [0]
        
        @retry(max_attempts=3, delay=0.01)
        def flaky():
            """Flaky."""
            attempts[0] += 1
            if attempts[0] < 2:
                raise ValueError("Fail")
            return "Success"
        
        assert flaky() == "Success"
        assert attempts[0] == 2  # 1 fail, 1 success

    def test_retry_sync_failure(self):
        """Test retry wrapper fails after max attempts."""
        attempts = [0]
        
        @retry(max_attempts=2, delay=0.01)
        def failure():
            attempts[0] += 1
            raise ValueError("Always fail")
        
        with pytest.raises(ValueError):
            failure()
        
        assert attempts[0] == 2

    @pytest.mark.asyncio
    async def test_retry_async(self):
        """Test async retry wrapper."""
        attempts = [0]
        
        @retry(max_attempts=3, delay=0.01)
        async def flaky_async():
            """Flaky async."""
            attempts[0] += 1
            if attempts[0] < 2:
                raise ValueError("Async Fail")
            return "Async Success"
        
        result = await flaky_async()
        assert result == "Async Success"
        assert attempts[0] == 2

    def test_log_errors_default(self):
        """Test @log_errors returns default value on exception."""
        @log_errors(default_return="Default", notify=False)
        def crasher():
            raise RuntimeError("Crash")
        
        assert crasher() == "Default"

    @pytest.mark.asyncio
    async def test_log_errors_async(self):
        """Test async @log_errors."""
        @log_errors(default_return="AsyncDefault", notify=False)
        async def async_crasher():
            raise RuntimeError("Async Crash")
        
        assert await async_crasher() == "AsyncDefault"

    def test_performance_critical_warning(self, caplog):
        """Test @performance_critical logs warning when slow."""
        @performance_critical(threshold_ms=10)
        def slow_func():
            time.sleep(0.02) # 20ms > 10ms
            return "Done"
        
        slow_func()
        assert "SLOW" in caplog.text

    def test_timer_logs(self, caplog):
        """Test @timer logs info."""
        caplog.set_level(logging.INFO)
        @timer
        def timed_func():
            return "ok"
        
        timed_func()
        assert "timed_func" in caplog.text
        assert "completed in" in caplog.text
