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


@st.cache_data(ttl=30)
def fetch_json(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fetch JSON from the backend API."""
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{get_api_base_url()}{path}", params=params)
        response.raise_for_status()
        return response.json()


def post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Send a JSON POST request."""
    with httpx.Client(timeout=10.0) as client:
        response = client.post(f"{get_api_base_url()}{path}", json=payload)
        response.raise_for_status()
        fetch_json.clear()
        return response.json()


def post_json_with_status(path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Send a JSON POST request and return the status code with the parsed body."""
    with httpx.Client(timeout=10.0) as client:
        response = client.post(f"{get_api_base_url()}{path}", json=payload)
        fetch_json.clear()
        try:
            body = response.json()
        except Exception:
            body = {"message": response.text}
        return response.status_code, body


def patch_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Send a JSON PATCH request."""
    with httpx.Client(timeout=10.0) as client:
        response = client.patch(f"{get_api_base_url()}{path}", json=payload)
        response.raise_for_status()
        fetch_json.clear()
        return response.json()


def delete_json(path: str) -> None:
    """Send a DELETE request."""
    with httpx.Client(timeout=10.0) as client:
        response = client.delete(f"{get_api_base_url()}{path}")
        response.raise_for_status()
        fetch_json.clear()
