"""HTTP helpers for the dashboard."""

from __future__ import annotations

from typing import Any

import httpx
import streamlit as st


def get_api_base_url() -> str:
    """Return the configured backend base URL."""
    try:
        configured = st.secrets.get("API_BASE_URL", None)
    except Exception:
        configured = None
    return configured or st.session_state.get("api_base_url", "http://localhost:8000")


def render_api_key_input() -> None:
    """Ask for the API key in the sidebar. It is kept only in this browser session."""
    entered = st.sidebar.text_input(
        "API key", value=st.session_state.get("api_key", ""), type="password",
        help="Gateway key for the Playground; the admin key for metrics, traces and policies.",
    )
    st.session_state["api_key"] = entered


def _headers() -> dict[str, str]:
    return {"X-API-Key": st.session_state.get("api_key", "")}


@st.cache_data(ttl=30)
def _cached_get(path: str, params: dict[str, Any] | None, api_key: str) -> dict[str, Any]:
    # api_key is part of the cache key, so one session never sees another session's cached data
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{get_api_base_url()}{path}", params=params, headers={"X-API-Key": api_key})
        response.raise_for_status()
        return response.json()


def fetch_json(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fetch JSON from the backend API."""
    return _cached_get(path, params, st.session_state.get("api_key", ""))


fetch_json.clear = _cached_get.clear  # callers clear the cache through fetch_json


def post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Send a JSON POST request."""
    with httpx.Client(timeout=10.0) as client:
        response = client.post(f"{get_api_base_url()}{path}", json=payload, headers=_headers())
        response.raise_for_status()
        _cached_get.clear()
        return response.json()


def post_json_with_status(path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Send a JSON POST request and return the status code with the parsed body."""
    with httpx.Client(timeout=10.0) as client:
        response = client.post(f"{get_api_base_url()}{path}", json=payload, headers=_headers())
        _cached_get.clear()
        try:
            body = response.json()
        except Exception:
            body = {"message": response.text}
        return response.status_code, body


def patch_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Send a JSON PATCH request."""
    with httpx.Client(timeout=10.0) as client:
        response = client.patch(f"{get_api_base_url()}{path}", json=payload, headers=_headers())
        response.raise_for_status()
        _cached_get.clear()
        return response.json()


def delete_json(path: str) -> None:
    """Send a DELETE request."""
    with httpx.Client(timeout=10.0) as client:
        response = client.delete(f"{get_api_base_url()}{path}", headers=_headers())
        response.raise_for_status()
        _cached_get.clear()
