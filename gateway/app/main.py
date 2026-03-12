"""FastAPI gateway: routing, auth, rate limit, logging, metrics."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .config import get_settings
from .proxy import proxy_orders, proxy_locations
from .logging_middleware import logging_middleware
from .auth_middleware import auth_middleware
from .rate_limit import rate_limit_middleware
from .metrics import get_metrics, metrics_middleware

app = FastAPI(title="API Gateway", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        return await metrics_middleware(request, call_next)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        return await rate_limit_middleware(request, call_next)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        return await auth_middleware(request, call_next)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        return await logging_middleware(request, call_next)


app.add_middleware(MetricsMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(LoggingMiddleware)


ALL_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


@app.get("/health")
def health():
    """Health check for Docker/orchestration."""
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    """JSON metrics for dashboard."""
    return get_metrics()


@app.get("/")
def root():
    """Root info."""
    settings = get_settings()
    return {
        "service": "API Gateway",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
        "backends": {
            "orders": settings.orders_backend_list,
            "locations": settings.locations_backend_list,
        },
    }


@app.api_route("/orders", methods=ALL_METHODS)
async def orders_root(request: Request):
    return await proxy_orders(request)


@app.api_route("/orders/{path:path}", methods=ALL_METHODS)
async def orders_path(request: Request, path: str):
    return await proxy_orders(request)


@app.api_route("/locations", methods=ALL_METHODS)
async def locations_root(request: Request):
    return await proxy_locations(request)


@app.api_route("/locations/{path:path}", methods=ALL_METHODS)
async def locations_path(request: Request, path: str):
    return await proxy_locations(request)
