"""
Performance Monitoring and Latency Telemetry for Government Scheme Assistant.
Measures, logs, and tracks execution times across key system operations:
- Application startup
- Page navigation
- ChromaDB initialization
- Embedding model loading
- SQLite queries
- PDF processing
- Vector retrieval
- LLM response generation
"""

import time
import logging
from typing import Dict, Any, List, Optional, Callable
from collections import deque
from functools import wraps

# Setup specialized performance logger
logger = logging.getLogger("performance_monitor")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [PERF] %(message)s", datefmt="%H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# In-memory ring buffer of recent timing measurements
MAX_HISTORY = 100
_TIMING_LOGS = deque(maxlen=MAX_HISTORY)
_METRIC_STATS: Dict[str, List[float]] = {}


def record_timing(category: str, operation: str, duration_sec: float, metadata: Optional[Dict[str, Any]] = None):
    """Record an operation's latency, update aggregate stats, and log."""
    rounded_duration = round(duration_sec, 4)
    record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "category": category,
        "operation": operation,
        "duration_sec": rounded_duration,
        "metadata": metadata or {}
    }
    _TIMING_LOGS.append(record)

    if category not in _METRIC_STATS:
        _METRIC_STATS[category] = []
    _METRIC_STATS[category].append(rounded_duration)
    # Keep last 100 per category to prevent memory leak
    if len(_METRIC_STATS[category]) > 100:
        _METRIC_STATS[category].pop(0)

    logger.info(f"[{category.upper()}] {operation} took {rounded_duration:.4f}s")


class TimingContext:
    """Context manager for timing code blocks."""
    def __init__(self, category: str, operation: str, metadata: Optional[Dict[str, Any]] = None):
        self.category = category
        self.operation = operation
        self.metadata = metadata
        self.start_time = 0.0
        self.elapsed = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.perf_counter() - self.start_time
        record_timing(self.category, self.operation, self.elapsed, self.metadata)


def measure_timing(category: str, operation: Optional[str] = None):
    """Decorator to measure and log function execution time."""
    def decorator(func: Callable):
        op_name = operation or func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = time.perf_counter() - start
                record_timing(category, op_name, elapsed)

        return wrapper
    return decorator


def get_performance_summary() -> Dict[str, Dict[str, float]]:
    """Return summary statistics (avg, min, max, count) grouped by category."""
    summary = {}
    for cat, durations in _METRIC_STATS.items():
        if durations:
            summary[cat] = {
                "count": len(durations),
                "avg_sec": round(sum(durations) / len(durations), 4),
                "min_sec": round(min(durations), 4),
                "max_sec": round(max(durations), 4),
                "last_sec": round(durations[-1], 4)
            }
    return summary


def get_recent_timings(limit: int = 50) -> List[Dict[str, Any]]:
    """Return the most recent latency logs."""
    return list(_TIMING_LOGS)[-limit:]
