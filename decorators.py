# -*- coding: utf-8 -*-
"""
decorators.py - Performance monitoring and error handling decorators
Provides @timer, @retry, @log_errors for production-ready code
"""
import time
import logging
import functools
import asyncio
from typing import Callable, Any, Optional
from config_system import EMOJI

logger = logging.getLogger(__name__)


def timer(func: Callable) -> Callable:
    """
    Decorator to measure function execution time.
    
    Usage:
        @timer
        def my_function():
            ...
    
    Logs execution time at INFO level.
    """
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        
        logger.info(f"{EMOJI['timer']} [{func.__name__}] completed in {elapsed:.2f}s")
        return result
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        elapsed = time.time() - start_time
        
        logger.info(f"{EMOJI['timer']} [{func.__name__}] completed in {elapsed:.2f}s")
        return result
    
    # Return appropriate wrapper based on function type
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator to retry function on failure with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
    
    Usage:
        @retry(max_attempts=3, delay=1.0, backoff=2.0)
        def unstable_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            current_delay = delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        logger.error(
                            f"{EMOJI['error']} [{func.__name__}] Failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"{EMOJI['warning']} [{func.__name__}] Attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_delay = delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        logger.error(
                            f"{EMOJI['error']} [{func.__name__}] Failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"{EMOJI['warning']} [{func.__name__}] Attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_errors(default_return: Any = None, notify: bool = True):
    """
    Decorator to log errors and return default value on failure.
    
    Args:
        default_return: Value to return if function fails
        notify: Whether to show user notification on error
    
    Usage:
        @log_errors(default_return=[], notify=True)
        def risky_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{EMOJI['error']} [{func.__name__}] Error: {e}", exc_info=True)
                
                if notify:
                    # Lazy import to avoid circular dependency
                    try:
                        from state_management import handle_error
                        handle_error(e, func.__name__, notify_user=True)
                    except ImportError:
                        pass  # state_management not available
                
                return default_return
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{EMOJI['error']} [{func.__name__}] Error: {e}", exc_info=True)
                
                if notify:
                    # Lazy import to avoid circular dependency
                    try:
                        from state_management import handle_error
                        handle_error(e, func.__name__, notify_user=True)
                    except ImportError:
                        pass  # state_management not available
                
                return default_return
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def performance_critical(threshold_ms: float = 100.0):
    """
    Decorator to monitor performance-critical functions.
    Logs warning if execution exceeds threshold.
    
    Args:
        threshold_ms: Warning threshold in milliseconds
    
    Usage:
        @performance_critical(threshold_ms=100.0)
        def critical_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed_ms = (time.time() - start_time) * 1000
            
            if elapsed_ms > threshold_ms:
                logger.warning(
                    f"{EMOJI['warning']} [{func.__name__}] SLOW: {elapsed_ms:.1f}ms "
                    f"(threshold: {threshold_ms:.1f}ms)"
                )
            else:
                logger.debug(f"[{func.__name__}] {elapsed_ms:.1f}ms")
            
            return result
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            elapsed_ms = (time.time() - start_time) * 1000
            
            if elapsed_ms > threshold_ms:
                logger.warning(
                    f"{EMOJI['warning']} [{func.__name__}] SLOW: {elapsed_ms:.1f}ms "
                    f"(threshold: {threshold_ms:.1f}ms)"
                )
            else:
                logger.debug(f"[{func.__name__}] {elapsed_ms:.1f}ms")
            
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Convenience decorator combining common patterns
def robust(max_retries: int = 3, log_time: bool = True, default: Any = None):
    """
    Combination decorator for robust production functions.
    Combines @retry, @timer, and @log_errors.
    
    Usage:
        @robust(max_retries=3, log_time=True, default=[])
        def production_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        # Apply decorators in order: log_errors -> retry -> timer
        decorated = func
        
        if default is not None:
            decorated = log_errors(default_return=default, notify=True)(decorated)
        
        if max_retries > 1:
            decorated = retry(max_attempts=max_retries)(decorated)
        
        if log_time:
            decorated = timer(decorated)
        
        return decorated
    
    return decorator
