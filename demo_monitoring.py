from app.monitoring import get_logger, MetricsCollector, RequestTimer
import time
import json

logger = get_logger("demo_monitoring")
metrics = MetricsCollector()

print("=== Structured Logging ===")
print()
logger.info("Application started", extra={"event": "app_start", "version": "1.0.0"}) 
logger.info("Processing request", extra={"extra_data": {"user_id": 123, "thread_id": "query"}})
logger.warning("Rate limit approaching", extra={"extra_data": {"current_rate": 18, "limit": 20}})

print()
print("=== Metrics Collection ===")
print()

# Simulate some requests
with RequestTimer() as timer:
    time.sleep(0.1)  # Simulate processing time
metrics.record_request(latency=timer.elapsed_ms / 1000.0, tokens_input=50, tokens_output=200, cache_hit=True)
print(f"Request 1: {timer.elapsed_ms:.2f} ms, Cache Hit: True")

with RequestTimer() as timer:
    time.sleep(0.05)  # Simulate processing time
metrics.record_request(latency=timer.elapsed_ms / 1000.0, tokens_input=30, tokens_output=100, cache_hit=False)
print(f"Request 2: {timer.elapsed_ms:.2f} ms, Cache Hit: False")

metrics.record_request(latency=5.0, tokens_input=100, tokens_output=300, error=True)
print("Request 3: Simulated error")

print()
print("=== Metrics Summary ===")
print(json.dumps(metrics.get_summary(), indent=2))