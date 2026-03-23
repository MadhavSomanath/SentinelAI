"""SentinelAI dashboard home page."""

from pathlib import Path
import sys

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from components.api_client import fetch_json
from components.api_client import post_json
from components.theme import load_css

st.set_page_config(page_title="SentinelAI", page_icon="S", layout="wide")
load_css()

st.title("SentinelAI")
st.caption("LLM governance dashboard")

if "demo_latency_samples" not in st.session_state:
    st.session_state["demo_latency_samples"] = []
if "demo_last_latency_ms" not in st.session_state:
    st.session_state["demo_last_latency_ms"] = None
if "demo_last_trace_id" not in st.session_state:
    st.session_state["demo_last_trace_id"] = None

controls = st.columns([1, 1, 1])

if controls[0].button("Refresh Metrics"):
    fetch_json.clear()
    st.rerun()

if controls[1].button("Warm Up Gateway"):
    try:
        post_json(
            "/api/v1/gateway/mock",
            {
                "session_id": "dashboard-warmup",
                "user_id": "dashboard",
                "prompt": "Warm up the SentinelAI mock gateway.",
                "provider": "mock",
                "model": "gpt-4o-mini",
                "max_tokens": 32,
                "feature_tag": "dashboard_warmup",
                "prompt_version": "v1",
            },
        )
        st.success("Warm-up request sent. Refreshing metrics now.")
    except Exception as exc:
        st.error(f"Unable to warm up the gateway: {exc}")

if controls[2].button("Reset Demo Latency"):
    st.session_state["demo_latency_samples"] = []
    st.session_state["demo_last_latency_ms"] = None
    st.session_state["demo_last_trace_id"] = None
    st.success("Demo latency tracker reset. The next Prompt Playground run becomes the new baseline.")

try:
    metrics = fetch_json("/api/v1/metrics/overview")
except Exception as exc:
    st.error(f"Unable to load overview metrics: {exc}")
    st.stop()

columns = st.columns(4)
columns[0].metric("Total Requests", metrics["total_requests"])
columns[1].metric("Blocked Requests", metrics["blocked_requests"])
columns[2].metric("Stored Avg Latency (ms)", metrics["average_latency_ms"])
columns[3].metric("Estimated Cost (USD)", metrics["total_estimated_cost_usd"])

demo_samples = st.session_state["demo_latency_samples"]
demo_last_latency = st.session_state["demo_last_latency_ms"]
demo_average_latency = round(sum(demo_samples) / len(demo_samples), 2) if demo_samples else 0.0

st.markdown("### Demo Latency Tracker")
demo_columns = st.columns(3)
demo_columns[0].metric("Last Playground Request (ms)", demo_last_latency or 0.0)
demo_columns[1].metric("Demo Session Avg (ms)", demo_average_latency)
demo_columns[2].metric("Tracked Demo Requests", len(demo_samples))

if st.session_state["demo_last_trace_id"]:
    st.caption(f"Latest demo trace: {st.session_state['demo_last_trace_id']}")
st.caption(
    "Use Reset Demo Latency before a demo, then send prompts from Prompt Playground to measure a fresh run."
)

st.markdown("### Quick Start")
st.write("1. Click Reset Demo Latency if you want a fresh demo timing.")
st.write("2. Open Prompt Playground and send a safe or blocked prompt.")
st.write("3. Return here to see the latest measured latency for this demo session.")
