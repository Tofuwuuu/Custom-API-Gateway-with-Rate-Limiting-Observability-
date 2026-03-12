"""Auth middleware: validate API key and optional JWT for /orders and /locations; set request.state."""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, Response

from .auth import get_identity_headers

PROTECTED_PREFIXES = ("/orders", "/locations")


def _is_protected(path: str) -> bool:
    return path == "/orders" or path.startswith("/orders/") or path == "/locations" or path.startswith("/locations/")


async def auth_middleware(request: Request, call_next: Any) -> Response:
    if not _is_protected(request.scope.get("path", "")):
        request.state.client_id = request.client.host if request.client else "unknown"
        request.state.user_id = None
        request.state.roles = None
        request.state.api_key = None
        return await call_next(request)

    try:
        get_identity_headers(request)
    except HTTPException as e:
        detail = e.detail if isinstance(e.detail, str) else str(e.detail)
        return Response(content=b'{"detail":"' + detail.encode() + b'"}', status_code=e.status_code, media_type="application/json")
    except Exception:
        return Response(content=b'{"detail":"Unauthorized"}', status_code=401, media_type="application/json")

    return await call_next(request)
