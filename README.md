# Custom API Gateway (with Rate Limiting & Observability)

A custom API gateway that sits in front of microservices, handling cross-cutting concerns: traffic routing, load balancing, API key auth, rate limiting, and centralized metrics/logging.

## Quick start

1. **Copy env and run with Docker Compose**

   ```bash
   cp .env.example .env
   docker compose up --build
   ```

2. **Endpoints**

   - **Gateway:** http://localhost:8000  
   - **Dashboard:** http://localhost:3000  
   - **API docs:** http://localhost:8000/docs  

3. **Call the API (use the API key from `.env`)**

   ```bash
   # List orders (API key in header)
   curl -H "X-API-Key: dev-api-key-12345" http://localhost:8000/orders

   # List locations
   curl -H "X-API-Key: dev-api-key-12345" http://localhost:8000/locations
   ```

## Environment variables

See [.env.example](.env.example). Main ones:

| Variable | Description |
|----------|-------------|
| `API_KEYS` | Comma-separated valid API keys (same as `GATEWAY_API_KEY` for dev). |
| `JWT_SECRET` | Secret used to verify JWTs (optional; for JWT header injection to backends). |
| `REDIS_URL` | Redis connection URL (required for rate limiting). |
| `ORDERS_BACKENDS` | Comma-separated URLs for orders service instances. |
| `LOCATIONS_BACKENDS` | Comma-separated URLs for locations service instances. |

## Authentication

- **API key:** Send via `X-API-Key` or `Authorization: Bearer <api_key>`. Required for `/orders` and `/locations`.
- **JWT (optional):** Send via `Authorization: Bearer <jwt>` (if the token has 3 parts) or `X-JWT-Token`. Claims `sub` / `user_id` and `roles` are forwarded to backends as `X-User-Id` and `X-Roles`.

Example with API key and JWT:

```bash
curl -H "X-API-Key: dev-api-key-12345" \
     -H "Authorization: Bearer YOUR_JWT" \
     http://localhost:8000/orders
```

## Rate limiting

- Per-client (by API key) using Redis, fixed-window.
- Default: 100 requests per 60 seconds. Configure with `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS`.
- When exceeded: HTTP 429 with `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`.

## Metrics and dashboard

- **JSON metrics:** `GET http://localhost:8000/metrics` — total requests, 2xx/4xx/5xx, rate-limited count, latency percentiles.
- **Dashboard:** Open http://localhost:3000 — request rate, status breakdown, latencies, and rate-limited over time (polls gateway every 3s).

## Project layout

- **gateway/** — FastAPI gateway (routing, auth, rate limit, logging, metrics).
- **services/orders**, **services/locations** — Demo backends (two instances each behind gateway).
- **dashboard/** — React (Vite) app that charts gateway metrics.

## Example requests

```bash
# Health
curl http://localhost:8000/health

# Metrics (no auth)
curl http://localhost:8000/metrics

# Orders (auth required)
curl -H "X-API-Key: dev-api-key-12345" http://localhost:8000/orders
curl -H "X-API-Key: dev-api-key-12345" -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" -d '{"item":"Thing","quantity":3}'

# Locations (auth required)
curl -H "X-API-Key: dev-api-key-12345" http://localhost:8000/locations
curl -H "X-API-Key: dev-api-key-12345" -X POST http://localhost:8000/locations \
  -H "Content-Type: application/json" -d '{"name":"Site C","city":"Chicago"}'
```

## Logs

Gateway logs each request as JSON to stdout (method, path, client_id, status, latency_ms). View with:

```bash
docker compose logs -f gateway
```
