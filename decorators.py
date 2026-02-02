# -*- coding: utf-8 -*-
"""
decorators.py - ZenAI v3.1 Telemetry & Execution Decorators
=========================================================
Provides @monitor, @profile_execution, and @trace for system-wide auditing.
"""
import time
import functools
import logging
import asyncio
from typing import Callable, Any
from zena_mode.profiler import monitor

logger = logging.getLogger("Telemetry")

def profile_execution(label: str):
    """Sync/Async decorator to profile execution time and log to monitor."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.time() - start) * 1000
                monitor.add_metric(f"exec_{label.lower().replace(' ', '_')}", duration_ms)
                logger.info(f"[Profile] {label}: {duration_ms:.2f}ms")
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.time() - start) * 1000
                monitor.add_metric(f"exec_{label.lower().replace(' ', '_')}", duration_ms)
                logger.info(f"[Profile] {label}: {duration_ms:.2f}ms")

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def trace(component: str):
    """Decorator to log entry/exit and arguments for critical logic paths."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.info(f"[{component}] ENTER: {func_name} | Args: {len(args)}, Kwargs: {list(kwargs.keys())}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"[{component}] EXIT: {func_name} | Success")
                return result
            except Exception as e:
                logger.error(f"[{component}] ERROR: {func_name} | {type(e).__name__}: {e}")
                raise
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.info(f"[{component}] ENTER (async): {func_name} | Args: {len(args)}, Kwargs: {list(kwargs.keys())}")
            try:
                result = await func(*args, **kwargs)
                logger.debug(f"[{component}] EXIT (async): {func_name} | Success")
                return result
            except Exception as e:
                logger.error(f"[{component}] ERROR (async): {func_name} | {type(e).__name__}: {e}")
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
    return decorator

# --- Legacy Shims for Backward Compatibility (Required by existing Test Suite) ---

def retry(max_attempts: int = 3, delay: float = 1.0):
    """Legacy shim for @retry."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_err = None
            for _ in range(max_attempts):
                try: return func(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    time.sleep(delay)
            raise last_err
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_err = None
            for _ in range(max_attempts):
                try: return await func(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    await asyncio.sleep(delay)
            raise last_err
        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
    return decorator

def log_errors(default_return: Any = None, notify: bool = False):
    """Legacy shim for @log_errors."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try: return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                return default_return
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try: return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                return default_return
        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
    return decorator

def timer(func: Callable):
    """Legacy shim for @timer."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try: return func(*args, **kwargs)
        finally:
            dur = (time.time() - start) * 1000
            logger.info(f"Method {func.__name__} completed in {dur:.2f}ms")
    return wrapper

def performance_critical(threshold_ms: float = 100):
    """Legacy shim for @performance_critical."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            res = func(*args, **kwargs)
            dur = (time.time() - start) * 1000
            if dur > threshold_ms: logger.warning(f"SLOW EXECUTION: {func.__name__} took {dur:.2f}ms")
            return res
        return wrapper
    return decorator
