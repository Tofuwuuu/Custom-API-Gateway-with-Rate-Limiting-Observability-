"""Redis-based fixed-window rate limiter; 429 + standard headers."""
from __future__ import annotations

import time
from typing import Any

from fastapi import Request, Response
from redis.asyncio import Redis

from .config import get_settings
from .metrics import record_request as metrics_record

_redis: Redis | None = None


async def get_redis() -> Redis | None:
    global _redis
    if _redis is not None:
        return _redis
    settings = get_settings()
    try:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
        await _redis.ping()
        return _redis
    except Exception:
        return None


def _key(client_id: str) -> str:
    return f"ratelimit:{client_id}"


async def check_rate_limit(client_id: str) -> tuple[bool, int, int, int]:
    """
    Fixed-window rate limit. Returns (allowed, current_count, limit, retry_after_seconds).
    """
    settings = get_settings()
    limit = settings.rate_limit_requests
    window = settings.rate_limit_window_seconds
    r = await get_redis()
    if not r:
        return (True, 0, limit, 0)  # Allow if Redis down

    key = _key(client_id)
    now = int(time.time())
    window_key = f"{key}:{now // window}"
    try:
        count = await r.incr(window_key)
        if count == 1:
            await r.expire(window_key, window)
        allowed = count <= limit
        remaining = max(0, limit - count)
        retry_after = window - (now % window) if not allowed else 0
        return (allowed, count, limit, retry_after)
    except Exception:
        return (True, 0, limit, 0)


async def rate_limit_middleware(request: Request, call_next: Any) -> Response:
    """Run after auth so request.state.client_id is set. Skip for /health, /metrics, /docs, etc."""
    path = request.scope.get("path", "")
    if path in ("/health", "/metrics", "/", "/docs", "/openapi.json", "/redoc") or path.startswith("/docs") or path.startswith("/openapi"):
        return await call_next(request)

    client_id = getattr(request.state, "client_id", None) or request.client.host if request.client else "unknown"
    allowed, current, limit, retry_after = await check_rate_limit(client_id)

    if not allowed:
        request.state.rate_limited = True
        start = getattr(request.state, "start_time", None)
        latency_ms = (time.perf_counter() - start) * 1000 if start else 0
        metrics_record(429, latency_ms, rate_limited=True)
        return Response(
            content=b'{"detail":"Rate limit exceeded"}',
            status_code=429,
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(retry_after),
                "Content-Type": "application/json",
            },
        )
    request.state.rate_limited = False
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(max(0, limit - current))
    return response
