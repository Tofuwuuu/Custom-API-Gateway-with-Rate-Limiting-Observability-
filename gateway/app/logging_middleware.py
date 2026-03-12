"""Request/response logging middleware: method, path, client_id, status, latency (JSON to stdout)."""
from __future__ import annotations

import json
import time
from typing import Any

from fastapi import Request, Response


async def logging_middleware(request: Request, call_next: Any) -> Response:
    request.state.start_time = time.perf_counter()
    start = request.state.start_time
    path = request.scope.get("path", "")
    method = request.method
    client_id = getattr(request.state, "client_id", None) or (request.client.host if request.client else "unknown")

    response = await call_next(request)
    latency_ms = (time.perf_counter() - start) * 1000
    status = response.status_code

    log_entry = {
        "message": "request",
        "method": method,
        "path": path,
        "client_id": client_id,
        "status": status,
        "latency_ms": round(latency_ms, 2),
    }
    print(json.dumps(log_entry), flush=True)
    return response
