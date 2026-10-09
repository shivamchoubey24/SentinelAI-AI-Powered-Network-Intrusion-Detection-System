"""Prometheus metrics for the API."""
from prometheus_client import Counter, Gauge, Histogram

REQUESTS = Counter("sentinel_http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("sentinel_http_request_duration_seconds", "HTTP request latency", ["method", "path"])
PREDICTIONS = Counter("sentinel_records_analyzed_total", "Records analysed by /predict")
THREATS = Counter("sentinel_threats_detected_total", "Records classified as attacks")
AUTH_FAILURES = Counter("sentinel_auth_failures_total", "Rejected authentications", ["reason"])
RATE_LIMITED = Counter("sentinel_rate_limited_total", "Requests rejected by the rate limiter")
MODEL_LOADED = Gauge("sentinel_model_loaded", "1 if a trained model is loaded")
AUDIT_CHAIN_VALID = Gauge("sentinel_audit_chain_valid", "1 if the last audit-chain verification passed")
