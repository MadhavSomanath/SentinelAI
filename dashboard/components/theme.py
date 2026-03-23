"""Shared dashboard theming helpers."""

from pathlib import Path

import streamlit as st


def load_css() -> None:
    """Load the shared SentinelAI CSS theme."""
    css_path = Path(__file__).resolve().parents[1] / "styles" / "sentinel_theme.css"
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
