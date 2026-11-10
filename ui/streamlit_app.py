"""Local, review-first API testing workbench. All demo inputs are synthetic."""

import json
import os
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from backend.app.generator import DEFAULT_RULE
from backend.app.models import GenerateResponse, ExecuteResponse
from ui.client import request_api, ControllerError
from ui.state import input_fingerprint, synchronize_inputs, clear_execution

load_dotenv()
st.set_page_config(page_title="API Sentinel AI", page_icon="🧪", layout="wide")
st.title("API Sentinel AI")
st.caption("OpenAPI + business rule → reviewed scenarios → observed evidence")
mode = os.getenv("META_MODE", "fixture").strip().lower()
if mode == "fixture":
    st.warning("OFFLINE FIXTURE MODE — test plan is predefined; no Meta inference is running.")
elif mode == "live":
    st.info(
        "LIVE MODE configured. A successful generated plan must report source=meta_live; configuration alone is not proof of inference."
    )
else:
    st.error("Invalid model mode. Configure fixture or live before generating tests.")
st.caption(
    "Local synthetic wallet only · POST /withdraw · at most 10 cases · no redirects · no real funds or credentials"
)
controller = os.getenv("CONTROLLER_URL", "http://127.0.0.1:8100")
demo_api = os.getenv("DEMO_API_URL", "http://127.0.0.1:8101")
def_spec = (Path(__file__).resolve().parents[1] / "samples/withdraw-openapi.json").read_text(
    encoding="utf-8"
)
left, right = st.columns([1, 1])
with left:
    st.subheader("1 · Define the check")
    rule = st.text_area(
        "Business rule",
        DEFAULT_RULE,
        key="business_rule",
        help="Use only synthetic data. Fixture mode only supports the documented overdraft rule.",
    )
    spec_text = st.text_area("OpenAPI JSON", def_spec, height=220, key="spec_text")
    st.caption("Changing the rule or specification discards the old plan, consent and results.")
synchronize_inputs(st.session_state, input_fingerprint(spec_text, rule, controller, mode))
try:
    spec = json.loads(spec_text)
    if not isinstance(spec, dict):
        raise ValueError("object")
except (ValueError, RecursionError):
    st.error("OpenAPI must be a valid JSON object.")
    st.stop()
with left:
    if st.button("Analyze OpenAPI"):
        try:
            analysis = request_api(controller, "/api/analyze", {"openapi": spec})
            st.success(
                f"{len(analysis['operations'])} supported POST operation(s) declared. Execution remains restricted to the local wallet demo."
            )
        except (ControllerError, KeyError):
            st.error(
                "OpenAPI analysis failed. Check the controller and the documented supported subset."
            )
    if st.button("1. Generate test plan", type="primary", disabled=mode not in {"fixture", "live"}):
        clear_execution(st.session_state)
        try:
            health = request_api(controller, "/health")
            if health.get("mode") != mode or health.get("status") != "ok":
                raise ControllerError(
                    "Controller and dashboard model modes differ. Align their configuration before generating a plan."
                )
            plan = GenerateResponse.model_validate(
                request_api(controller, "/api/generate", {"openapi": spec, "business_rule": rule})
            )
            if not plan.plan_id:
                raise ValueError("Missing issued ID")
            st.session_state["plan"] = plan.model_dump()
        except ControllerError as exc:
            st.error(str(exc))
        except ValueError:
            st.error("The controller returned an invalid plan. Nothing is executable.")

with right:
    st.subheader("2 · Review and authorize")
    plan = st.session_state.get("plan")
    if not plan:
        st.info("Generate a plan to review every request and expectation before execution.")
    else:
        st.write(f"Source: **{plan['source']}** · Model: `{plan['model']}`")
        if plan["source"] == "fixture":
            st.warning(
                "These are predefined fixture cases. Execution results will be real local observations, not Meta-generated findings."
            )
        st.dataframe(
            [
                {
                    "id": c["case_id"],
                    "expected HTTP": c["expected_status"],
                    "basis": c["expectation_basis"],
                    "severity": c["severity"],
                }
                for c in plan["cases"]
            ],
            width="stretch",
        )
        with st.expander("Review complete requests and expected JSON", expanded=True):
            st.json(plan["cases"])
        st.checkbox(
            "I reviewed the expected outcomes against the OpenAPI and business rule.",
            key="reviewed",
        )
        st.checkbox(
            "I own/control the local test environment and authorize these requests.",
            key="authorized",
        )
        st.caption(f"Target: {demo_api} · Model-proposed expectations still require human review.")
        if st.button(
            "2. Execute local tests",
            disabled=not (st.session_state.get("reviewed") and st.session_state.get("authorized")),
            type="primary",
        ):
            st.session_state.pop("receipt", None)
            try:
                receipt = ExecuteResponse.model_validate(
                    request_api(
                        controller,
                        "/api/execute",
                        {
                            "base_url": demo_api,
                            "plan_id": plan["plan_id"],
                            "reviewed": True,
                            "authorized": True,
                        },
                    )
                )
                st.session_state["receipt"] = receipt.model_dump()
            except ControllerError as exc:
                st.error(str(exc))
            except ValueError:
                st.error(
                    "The controller returned invalid execution evidence. No verdict is displayed."
                )

receipt = st.session_state.get("receipt")
if receipt:
    st.divider()
    st.subheader("3 · Observed execution evidence")
    st.caption(
        f"Case source: {receipt['source']} · Model: {receipt['model']} · Run: {receipt['run_id']}"
    )
    columns = st.columns(4)
    for column, status in zip(columns, ("PASS", "FAIL", "ERROR", "NOT_RUN")):
        column.metric(status, sum(r["status"] == status for r in receipt["results"]))
    for result in receipt["results"]:
        with st.expander(
            f"{result['status']} — {result['case_id']}", expanded=result["status"] != "PASS"
        ):
            st.write(result["reason"])
            st.json(result)
    st.download_button(
        "Download evidence (JSON)",
        json.dumps(receipt, indent=2),
        file_name=f"{receipt['run_id']}.json",
        mime="application/json",
    )
    st.caption(
        "FAIL means a reviewed expectation differed from the observed response. It is not independent proof that an arbitrary rule or AI oracle is correct."
    )
