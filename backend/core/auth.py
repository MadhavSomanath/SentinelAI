"""API key authentication. Every route except /health needs a key."""

from __future__ import annotations

from secrets import compare_digest

from fastapi import Depends, Header, HTTPException, Request

from backend.core.dependencies import get_container


def _is_admin_key(key: str, request: Request) -> bool:
    admin = get_container(request).settings.admin_api_key
    return bool(admin) and compare_digest(key.encode(), admin.get_secret_value().encode())


def require_user(request: Request, x_api_key: str | None = Header(default=None)) -> str:
    """Return the user_id bound to the caller's API key, or reject with 401."""
    if x_api_key:
        if _is_admin_key(x_api_key, request):
            return "admin"
        for key, user_id in get_container(request).settings.api_keys.items():
            if compare_digest(x_api_key.encode(), key.encode()):
                return user_id
    raise HTTPException(
        status_code=401,
        detail={"code": "UNAUTHORIZED", "message": "Missing or invalid X-API-Key header."},
    )


def require_admin(
    request: Request, x_api_key: str | None = Header(default=None), _: str = Depends(require_user)
) -> None:
    """Allow only the admin key (policy, settings and trace routes)."""
    if not _is_admin_key(x_api_key or "", request):
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "This route needs the admin API key."},
        )
