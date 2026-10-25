"""Small verification-first UI; requires three local services as described in README."""
import json
import os
from pathlib import Path
import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="API Sentinel AI", page_icon="🧪", layout="wide")
st.title("API Sentinel AI")
st.caption("Business rules → executable API tests → observed evidence")
mode = os.getenv("META_MODE", "fixture")
if mode == "fixture":
    st.warning("OFFLINE FIXTURE MODE — test plan is predefined; no Meta inference is running.")
else:
    st.info("META LIVE MODE configured — verify real API responses before claiming model usage.")

controller = os.getenv("CONTROLLER_URL", "http://127.0.0.1:8000")
def_spec = (Path(__file__).resolve().parents[1] / "samples" / "withdraw-openapi.json").read_text(encoding="utf-8")
rule = st.text_area("Business rule", "Withdrawals exceeding the available balance must be rejected with HTTP 422 and approved=false.")
spec_text = st.text_area("OpenAPI JSON", def_spec, height=180)
try:
    spec = json.loads(spec_text)
except json.JSONDecodeError:
    st.error("OpenAPI must be valid JSON")
    st.stop()

if st.button("1. Generate test plan", type="primary"):
    try:
        response = httpx.post(controller + "/api/generate", json={"openapi": spec, "business_rule": rule}, timeout=35)
        response.raise_for_status()
        st.session_state["plan"] = response.json()
    except Exception as exc:
        st.error(f"Could not generate plan: {type(exc).__name__}: {str(exc)[:160]}")

plan = st.session_state.get("plan")
if plan:
    st.subheader("Generated scenarios")
    st.write(f"Source: **{plan['source']}** | Model: `{plan['model']}`")
    st.dataframe([{"id": c["case_id"], "description": c["description"], "expected": c["expected_status"]} for c in plan["cases"]], use_container_width=True)
    authorized = st.checkbox("I own/control the local test environment and authorize these requests.")
    if st.button("2. Execute local tests", disabled=not authorized):
        try:
            response = httpx.post(controller + "/api/execute", json={"base_url": "http://127.0.0.1:8001", "authorized": True, "cases": plan["cases"]}, timeout=40)
            response.raise_for_status()
            st.session_state["results"] = response.json()["results"]
        except Exception as exc:
            st.error(f"Could not execute tests: {type(exc).__name__}: {str(exc)[:160]}")

if st.session_state.get("results"):
    st.subheader("Actual execution evidence")
    for result in st.session_state["results"]:
        with st.expander(f"{result['status']} — {result['case_id']}", expanded=result["status"] == "FAIL"):
            st.json(result)
