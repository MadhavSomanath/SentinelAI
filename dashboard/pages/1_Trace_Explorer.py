"""Trace explorer dashboard page."""

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from components.api_client import fetch_json
from components.api_client import render_api_key_input
from components.theme import load_css

st.set_page_config(page_title="Trace Explorer", page_icon="S", layout="wide")
load_css()
render_api_key_input()

st.title("Trace Explorer")

provider_filter = st.selectbox("Provider", ["all", "mock", "openai", "anthropic", "ollama"])
status_filter = st.selectbox("Status", ["all", "blocked", "passed"])
limit = st.slider("Rows", min_value=10, max_value=100, value=25, step=5)

params = {"limit": limit}
if provider_filter != "all":
    params["provider"] = provider_filter
if status_filter == "blocked":
    params["blocked"] = "true"
elif status_filter == "passed":
    params["blocked"] = "false"

try:
    response = fetch_json("/api/v1/traces", params=params)
except Exception as exc:
    st.error(f"Unable to load traces: {exc}")
    st.stop()

items = response["items"]
if not items:
    st.info("No trace records match the current filters.")
    st.stop()

table = pd.DataFrame(items)
table["prompt_preview"] = table["prompt"].str.slice(0, 100)
table["output_preview"] = table["output"].fillna("").str.slice(0, 100)
st.dataframe(
    table[
        [
            "trace_id",
            "provider",
            "model",
            "feature_tag",
            "blocked",
            "policy_id",
            "similarity_score",
            "latency_ms",
            "total_cost_usd",
            "created_at",
            "prompt_preview",
            "output_preview",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)

st.markdown("### Trace Details")
for item in items[:10]:
    with st.expander(f"{item['trace_id']} | {'BLOCKED' if item['blocked'] else 'PASSED'}"):
        st.write(f"Provider: {item['provider']} | Model: {item['model']}")
        st.write(f"Feature Tag: {item['feature_tag']} | Prompt Version: {item['prompt_version']}")
        st.write(f"Latency: {item['latency_ms']} ms | Cost: ${item['total_cost_usd']}")
        st.code(item["prompt"], language="text")
        if item["output"]:
            st.code(item["output"], language="text")
