"""In-memory counters and latency buffer; GET /metrics JSON for dashboard."""
from __future__ import annotations

import time
from collections import deque
from typing import Any

from fastapi import Request, Response

# In-memory store (single process)
_total = 0
_status_2xx = 0
_status_4xx = 0
_status_5xx = 0
_rate_limited = 0
_latencies_ms: deque[float] = deque(maxlen=1000)

LATENCY_MAX_SAMPLES = 1000


def record_request(status: int, latency_ms: float, rate_limited: bool = False) -> None:
    global _total, _status_2xx, _status_4xx, _status_5xx, _rate_limited
    _total += 1
    if rate_limited:
        _rate_limited += 1
    if 200 <= status < 300:
        _status_2xx += 1
    elif 400 <= status < 500:
        _status_4xx += 1
    elif status >= 500:
        _status_5xx += 1
    _latencies_ms.append(latency_ms)
    while len(_latencies_ms) > LATENCY_MAX_SAMPLES:
        _latencies_ms.popleft()


def get_metrics() -> dict[str, Any]:
    latencies = list(_latencies_ms)
    latencies.sort()
    n = len(latencies)
    if n == 0:
        p50 = p95 = p99 = avg = 0.0
    else:
        p50 = latencies[int(n * 0.5)]
        p95 = latencies[int(n * 0.95)] if n >= 20 else latencies[-1]
        p99 = latencies[int(n * 0.99)] if n >= 100 else latencies[-1]
        avg = sum(latencies) / n
    return {
        "totalRequests": _total,
        "status2xx": _status_2xx,
        "status4xx": _status_4xx,
        "status5xx": _status_5xx,
        "rateLimited": _rate_limited,
        "latenciesMs": latencies[-100:] if n > 100 else latencies,  # Last 100 for sparkline
        "latencyP50Ms": round(p50, 2),
        "latencyP95Ms": round(p95, 2),
        "latencyP99Ms": round(p99, 2),
        "latencyAvgMs": round(avg, 2),
    }


async def metrics_middleware(request: Request, call_next: Any) -> Response:
    """Record status and latency after response; skip for /metrics and /health."""
    path = request.scope.get("path", "")
    if path in ("/metrics", "/health", "/", "/docs", "/openapi.json", "/redoc") or path.startswith("/docs") or path.startswith("/openapi"):
        return await call_next(request)

    start = time.perf_counter()
    response = await call_next(request)
    latency_ms = (time.perf_counter() - start) * 1000
    rate_limited = getattr(request.state, "rate_limited", False)
    record_request(response.status_code, latency_ms, rate_limited=rate_limited)
    return response
