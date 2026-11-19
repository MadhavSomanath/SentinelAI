"""Policy manager dashboard page."""

from pathlib import Path
import sys

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from components.api_client import delete_json, fetch_json, patch_json, post_json
from components.api_client import render_api_key_input
from components.theme import load_css

st.set_page_config(page_title="Policy Manager", page_icon="S", layout="wide")
load_css()
render_api_key_input()

st.title("Policy Manager")

try:
    policies_response = fetch_json("/api/v1/policies")
    settings_response = fetch_json("/api/v1/policies/settings")
except Exception as exc:
    st.error(f"Unable to load policy data: {exc}")
    st.stop()

threshold = st.slider(
    "Firewall Threshold",
    min_value=0.50,
    max_value=1.00,
    value=float(settings_response["firewall_threshold"]),
    step=0.01,
)

if st.button("Save Threshold"):
    try:
        patch_json("/api/v1/policies/settings", {"firewall_threshold": threshold})
        st.success("Threshold updated.")
    except Exception as exc:
        st.error(f"Unable to update threshold: {exc}")

st.markdown("### Add Policy")
with st.form("create_policy"):
    policy_id = st.text_input("Policy ID")
    category = st.text_input("Category", value="security")
    intent_text = st.text_area("Intent Text")
    submitted = st.form_submit_button("Create Policy")
    if submitted:
        try:
            post_json(
                "/api/v1/policies",
                {
                    "policy_id": policy_id,
                    "category": category,
                    "intent_text": intent_text,
                    "is_active": True,
                },
            )
            st.success("Policy created.")
        except Exception as exc:
            st.error(f"Unable to create policy: {exc}")

st.markdown("### Current Policies")
for policy in policies_response["items"]:
    columns = st.columns([3, 2, 1, 1])
    columns[0].write(f"**{policy['policy_id']}**")
    columns[0].caption(policy["intent_text"])
    columns[1].write(policy["category"])
    columns[2].write("Active" if policy["is_active"] else "Disabled")
    if columns[3].button("Delete", key=f"delete-{policy['policy_id']}"):
        try:
            delete_json(f"/api/v1/policies/{policy['policy_id']}")
            st.success(f"Deleted {policy['policy_id']}.")
        except Exception as exc:
            st.error(f"Unable to delete policy: {exc}")

st.markdown("### Prompt Simulator")
simulated_prompt = st.text_area("Test prompt", max_chars=500)
if st.button("Run Firewall Check"):
    try:
        result = post_json("/api/v1/policies/simulate", {"prompt": simulated_prompt})
        label = "BLOCKED" if result["blocked"] else "PASSED"
        st.write(f"Result: **{label}**")
        st.write(f"Risk Score: {result['similarity_score']}")
        st.write(f"Policy: {result.get('policy_id') or 'None'}")
    except Exception as exc:
        st.error(f"Unable to run simulator: {exc}")
