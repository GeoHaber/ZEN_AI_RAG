import time
import functools
import logging
import uuid
from collections import deque

logger = logging.getLogger("ZenAIProfiler")


class PerformanceMonitor:
    """
    Singleton class to track and hold performance metrics.
    """

    _instance = None

    def __new__(cls):
        """New."""
        if cls._instance is not None:
            return

        cls._instance = super(PerformanceMonitor, cls).__new__(cls)
        cls._instance.metrics = {
            "llm_tps": deque(maxlen=50),  # Tokens per second
            "llm_ttft": deque(maxlen=50),  # Time to first token
            "rag_retrieval": deque(maxlen=50),  # ms for RAG fetch
            "expert_latency": deque(maxlen=50),  # ms for swarm consensus
            "traces": {},  # Trace ID -> detailed logs
        }
        return cls._instance

    def start_trace(self) -> str:
        """Generates a new trace ID for a request batch."""
        trace_id = str(uuid.uuid4())[:8]
        self.metrics["traces"][trace_id] = []
        return trace_id

    def log_trace(self, trace_id: str, message: str):
        """Append a message to a specific trace."""
        if trace_id not in self.metrics["traces"]:
            return

        self.metrics["traces"][trace_id].append(f"[{time.strftime('%H:%M:%S')}] {message}")
        logger.debug(f"[Trace:{trace_id}] {message}")

    def add_metric(self, key: str, value: float):
        if key not in self.metrics:
            return

        self.metrics[key].append(value)
        logger.debug(f"[Metric] {key}: {value:.2f}")

    def get_averages(self):
        return {k: (sum(v) / len(v) if v else 0) for k, v in self.metrics.items()}


monitor = PerformanceMonitor()


def profile_execution(name: str):
    """
    Decorator to measure execution time of a function.
    Automatically logs results to PerformanceMonitor.
    """

    def decorator(func):
        """Decorator."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            """Wrapper."""
            start = time.time()
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start) * 1000

            # Map function names to internal metric keys
            if "rag" in name.lower():
                monitor.add_metric("rag_retrieval", duration_ms)
            elif "expert" in name.lower():
                monitor.add_metric("expert_latency", duration_ms)

            logger.info(f"[Profiler] {name} took {duration_ms:.1f}ms")
            return result

        return wrapper

    return decorator


def profile_async_execution(name: str):
    """
    Async version of the execution profiler.
    """

    def decorator(func):
        """Decorator."""

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            """Wrapper."""
            start = time.time()
            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start) * 1000

            if "rag" in name.lower():
                monitor.add_metric("rag_retrieval", duration_ms)

            logger.info(f"[Profiler] {name} took {duration_ms:.1f}ms")
            return result

        return wrapper

    return decorator
