"""Proxy: forward requests to backends with aiohttp, round-robin, JWT header injection."""
from __future__ import annotations

import itertools
from typing import Callable

import aiohttp
from fastapi import Request, Response

from .config import get_settings


def _round_robin(backends: list[str]):
    """Infinite round-robin iterator over backend URLs."""
    return itertools.cycle(backends) if backends else iter(())


# Per-service round-robin state (in-memory)
_orders_cycle = None
_locations_cycle = None


def _get_orders_next() -> str | None:
    global _orders_cycle
    settings = get_settings()
    backends = settings.orders_backend_list
    if not backends:
        return None
    if _orders_cycle is None:
        _orders_cycle = _round_robin(backends)
    return next(_orders_cycle)


def _get_locations_next() -> str | None:
    global _locations_cycle
    settings = get_settings()
    backends = settings.locations_backend_list
    if not backends:
        return None
    if _locations_cycle is None:
        _locations_cycle = _round_robin(backends)
    return next(_locations_cycle)


# Headers we forward from client (strip hop-by-hop and auth that we replace)
FORWARD_HEADERS = {
    "content-type",
    "accept",
    "accept-encoding",
    "cache-control",
    "x-request-id",
    "traceparent",
    "tracestate",
}


def _forward_headers(request: Request, inject_user_id: str | None, inject_roles: str | None) -> dict[str, str]:
    """Build headers to send to backend: filtered client headers + JWT-derived identity."""
    out: dict[str, str] = {}
    for name, value in request.headers.items():
        if name.lower() in FORWARD_HEADERS and value:
            out[name] = value
    if inject_user_id:
        out["X-User-Id"] = inject_user_id
    if inject_roles:
        out["X-Roles"] = inject_roles
    return out


async def proxy_request(
    request: Request,
    path_prefix: str,
    get_backend_url: Callable[[], str | None],
) -> Response:
    """Forward request to the next backend in round-robin. Path: path_prefix + rest."""
    backend_base = get_backend_url()
    if not backend_base:
        return Response(content=b'{"detail":"No backend configured"}', status_code=503)

    # Path: e.g. /orders/foo -> backend path /orders/foo (backends serve under same prefix)
    path = request.url.path
    query = request.url.query
    backend_url = backend_base.rstrip("/") + path
    if query:
        backend_url += "?" + query

    body = await request.body()

    # Identity from auth middleware (set on request.state)
    user_id = getattr(request.state, "user_id", None)
    roles = getattr(request.state, "roles", None)
    roles_str = ",".join(roles) if isinstance(roles, (list, tuple)) else (roles or "")

    headers = _forward_headers(request, user_id, roles_str or None)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(
                method=request.method,
                url=backend_url,
                headers=headers,
                data=body if body else None,
            ) as resp:
                content = await resp.read()
                return Response(
                    content=content,
                    status_code=resp.status,
                    headers=dict(resp.headers),
                )
        except aiohttp.ClientError as e:
            return Response(
                content=f'{{"detail":"Backend error: {e!s}"}}'.encode(),
                status_code=502,
            )


async def proxy_orders(request: Request) -> Response:
    return await proxy_request(request, "/orders", _get_orders_next)


async def proxy_locations(request: Request) -> Response:
    return await proxy_request(request, "/locations", _get_locations_next)
