import logging 
import json
import time
from datetime import datetime, timezone
from functools import wraps
from typing import Callable, Any

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for log aggregation."""

    def format(self, record):
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }

        if hasattr(record, "extra_data"):
            log_obj.update(record.extra_data)

        return json.dumps(log_obj)

def get_logger(name: str = "production-api") -> logging.Logger:
    """Get a logger with JSON formatting."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# === Metrics Collector ===

class MetricsCollector:
    """Collects and aggregates application metrics.

    In production, replace with prometheus client or similar.
        from prometheus_client import Counter, Histogram
    """

    def __init__(self):
        self.metrics = {
            "requests_total": 0,
            "errors_total": 0,
            "latency_sum": 0.0,
            "latency_count": 0,
            "tokens_input": 0,
            "tokens_output": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }
        
    def record_request(self, 
        latency: float, 
        tokens_input: int = 0, 
        tokens_output: int = 0,
        error: bool = False,
        cache_hit: bool = False,
    ):
        self.metrics["requests_total"] += 1
        self.metrics["latency_sum"] += latency
        self.metrics["latency_count"] += 1
        self.metrics["tokens_input"] += tokens_input
        self.metrics["tokens_output"] += tokens_output

        if error:
            self.metrics["errors_total"] += 1
        
        if cache_hit:
            self.metrics["cache_hits"] += 1
        else:
            self.metrics["cache_misses"] += 1
        
    def get_summary(self) -> dict:
        avg_latency = (self.metrics["latency_sum"] / self.metrics["latency_count"]) if self.metrics["latency_count"] > 0 else 0.0
        cache_hit_rate = (self.metrics["cache_hits"] / self.metrics["requests_total"]) if self.metrics["requests_total"] > 0 else 0.0
        error_rate = (self.metrics["errors_total"] / self.metrics["requests_total"]) if self.metrics["requests_total"] > 0 else 0.0

        return {
            "total_requests": self.metrics["requests_total"],
            "total_errors": self.metrics["errors_total"],
            "avg_latency_ms": round(avg_latency * 1000, 2),
            "total_input_tokens": self.metrics["tokens_input"],
            "total_output_tokens": self.metrics["tokens_output"],
            "cache_hit_rate": round(cache_hit_rate, 4),
            "error_rate": round(error_rate, 4),
        }

# === Request Timer (utility) ===

class RequestTimer:
    """Context manager for measuring the latency of a block of code."""

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = (time.time() - self.start_time) * 1000  # Convert to milliseconds