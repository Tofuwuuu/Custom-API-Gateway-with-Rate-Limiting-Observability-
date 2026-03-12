"""API key + JWT validation and claim injection for backend requests."""
from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Header, HTTPException, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
BEARER = HTTPBearer(auto_error=False)


def get_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    credentials: Annotated[HTTPAuthorizationCredentials | None, HTTPBearer()] = None,
) -> str:
    """Resolve API key from X-API-Key header or Bearer token (API key as bearer)."""
    if x_api_key:
        return x_api_key
    if credentials and credentials.scheme.lower() == "bearer":
        return credentials.credentials
    return ""


def validate_api_key(api_key: str) -> bool:
    settings = get_settings()
    return bool(api_key and api_key in settings.valid_api_keys)


def decode_jwt(token: str) -> dict | None:
    """Decode and validate JWT; return claims or None."""
    if not token:
        return None
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.PyJWTError:
        return None


def get_identity_headers(request: Request) -> tuple[str | None, str | None]:
    """
    Validate API key and optional JWT; set request.state and return (user_id, roles).
    Raises HTTPException 401 if API key invalid.
    """
    api_key = get_api_key(
        request.headers.get("X-API-Key"),
        None,  # Bearer parsed below
    )
    if not api_key:
        auth = request.headers.get("Authorization")
        if auth and auth.lower().startswith("bearer "):
            api_key = auth[7:].strip()
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key (X-API-Key or Authorization: Bearer)")
    if not validate_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Optional second Bearer token as JWT (e.g. Authorization: Bearer <jwt> with API key in X-API-Key)
    # For simplicity we use single Bearer: if it looks like JWT (3 parts), decode; else treat as API key.
    jwt_token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        candidate = auth_header[7:].strip()
        if candidate.count(".") == 2:
            jwt_token = candidate
    if not jwt_token and request.headers.get("X-JWT-Token"):
        jwt_token = request.headers.get("X-JWT-Token")

    request.state.api_key = api_key
    request.state.client_id = api_key  # For rate limiting
    user_id = None
    roles = None
    if jwt_token:
        claims = decode_jwt(jwt_token)
        if claims:
            request.state.user_id = claims.get("sub") or claims.get("user_id") or str(claims.get("id", ""))
            request.state.roles = claims.get("roles") or claims.get("role")
            if isinstance(request.state.roles, str):
                request.state.roles = [request.state.roles]
            user_id = request.state.user_id
            roles = request.state.roles
    else:
        request.state.user_id = None
        request.state.roles = None

    return (user_id, roles)
