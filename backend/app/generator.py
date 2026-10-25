"""Meta-based scenario planner. No automatic fallback from live errors to fixtures."""
import json
import os
from fastapi import HTTPException
from .models import GenerateResponse, TestPlan
from .openapi_parser import validate_plan_against_spec


def fixture_plan(rule: str) -> TestPlan:
    # Explicit offline fixture; not model inference. Deliberately scoped to demo /withdraw.
    return TestPlan(cases=[
        {
            "case_id": "happy-withdraw",
            "description": "Allowed withdrawal within balance",
            "method": "POST", "path": "/withdraw",
            "request_body": {"balance": 100, "amount": 50},
            "expected_status": 200, "expected_json_subset": {"approved": True},
            "rule_reference": "Demo fixture: valid withdrawal"
        },
        {
            "case_id": "overdraft-rule",
            "description": "Reject withdrawal larger than available balance",
            "method": "POST", "path": "/withdraw",
            "request_body": {"balance": 100, "amount": 150},
            "expected_status": 422, "expected_json_subset": {"approved": False},
            "rule_reference": rule
        }
    ])


def generate_plan(spec: dict, rule: str) -> GenerateResponse:
    mode = os.getenv("META_MODE", "fixture").strip().lower()
    if mode not in {"fixture", "live"}:
        raise HTTPException(status_code=500, detail="META_MODE must be fixture or live")
    if mode == "fixture":
        if not ("/withdraw" in spec.get("paths", {}) and "post" in spec["paths"]["/withdraw"]):
            raise HTTPException(status_code=422, detail="Fixture mode only supports provided /withdraw sample")
        plan = fixture_plan(rule)
        validate_plan_against_spec(plan, spec)
        return GenerateResponse(**plan.model_dump(), source="fixture", model="offline-fixture-not-AI")

    api_key = os.getenv("MODEL_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="Meta live mode requires MODEL_API_KEY")
    try:
        from openai import OpenAI
        client = OpenAI(
            base_url=os.getenv("META_BASE_URL", "https://api.meta.ai/v1"),
            api_key=api_key,
            timeout=25,
            max_retries=1,
        )
        model = os.getenv("META_MODEL", "muse-spark-1.3")
        # Official Meta docs support the Pydantic structured-output parsing route.
        response = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "developer", "content": (
                    "You generate up to 6 cautious REST POST API tests. Use ONLY documented paths and methods, "
                    "and only requirements in the user's given business rule and OpenAPI document. "
                    "Prefer simple JSON bodies. Use exact expected status from provided spec/rule; "
                    "if not justified, do not invent an assertion. Never request real production changes. "
                    "Output only the TestPlan structure."
                )},
                {"role": "user", "content": json.dumps({"openapi": spec, "business_rule": rule})},
            ],
            response_format=TestPlan,
        )
        plan = response.choices[0].message.parsed
        if plan is None:
            raise ValueError("Meta returned no parsed test plan")
        validate_plan_against_spec(plan, spec)
        return GenerateResponse(**plan.model_dump(), source="meta_live", model=model)
    except HTTPException:
        raise
    except Exception as exc:
        # Avoid leaking prompts, secrets and vendor response bodies to user interface.
        raise HTTPException(status_code=502, detail=f"Meta inference unavailable ({type(exc).__name__})") from None
