"""Acceptance for S2/S3 and plan execution boundaries; no provider calls."""

from copy import deepcopy
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from backend.app.main import app
from backend.app.models import TestPlan as Plan, GenerateRequest
from backend.app.generator import DEFAULT_RULE, fixture_plan, generate_plan
from backend.app.plan_validation import validate_plan
from backend.app.plan_store import PlanStore
from backend.app.safety import redact


@pytest.mark.parametrize(
    "change",
    [
        {"case_id": ""},
        {"expected_status": True},
        {"request_body": {"password": "private-value"}},
        {"request_body": {"nested": [float("nan")]}},
        {"request_body": {"text": "x" * 2100}},
        {"expected_json_subset": {}},
        {"unknown_field": True},
    ],
)
def test_invalid_cases_rejected(change):
    case = fixture_plan(DEFAULT_RULE).cases[0].model_dump()
    case.update(change)
    with pytest.raises(ValidationError):
        Plan(cases=[case])


def test_bounds_and_duplicate_ids():
    case = fixture_plan(DEFAULT_RULE).cases[0]
    for cases in ([], [case] * 2, [case] * 11):
        with pytest.raises(ValidationError):
            Plan(cases=cases)


@pytest.mark.parametrize(
    "change",
    [
        {"path": "/undeclared"},
        {"request_body": {"balance": 100, "amount": "fifty"}},
        {"request_body": {"balance": True, "amount": 50}},
        {"request_body": {"balance": 100, "amount": 50, "extra": 1}},
        {"expected_status": 201},
        {"rule_reference": "An invented business rule"},
        {"expected_json_subset": {"approved": False}},
    ],
)
def test_plan_checked_against_spec(wallet_spec, change):
    case = fixture_plan(DEFAULT_RULE).cases[0].model_dump()
    case.update(change)
    with pytest.raises(HTTPException):
        validate_plan(Plan(cases=[case]), wallet_spec, DEFAULT_RULE)


def test_valid_reference_request_body_normalizes_without_mutation(wallet_spec):
    before = deepcopy(wallet_spec)
    body = wallet_spec["paths"]["/withdraw"]["post"]["requestBody"]
    wallet_spec["components"] = {"requestBodies": {"Wallet": body}}
    wallet_spec["paths"]["/withdraw"]["post"]["requestBody"] = {
        "$ref": "#/components/requestBodies/Wallet"
    }
    snapshot = deepcopy(wallet_spec)
    validate_plan(fixture_plan(DEFAULT_RULE), wallet_spec, DEFAULT_RULE)
    assert wallet_spec == snapshot and before["paths"]["/withdraw"]["post"]["requestBody"] == body


def test_model_input_rejects_concrete_secrets_not_schema_property_names(wallet_spec):
    wallet_spec["paths"]["/withdraw"]["post"]["requestBody"]["content"]["application/json"][
        "schema"
    ]["properties"]["password"] = {"type": "string"}
    GenerateRequest(openapi=wallet_spec, business_rule=DEFAULT_RULE)
    wallet_spec["paths"]["/withdraw"]["post"]["requestBody"]["content"]["application/json"][
        "example"
    ] = {"password": "private-password"}
    with pytest.raises(ValidationError):
        GenerateRequest(openapi=wallet_spec, business_rule=DEFAULT_RULE)


def test_fixture_refuses_arbitrary_rules(wallet_spec):
    with pytest.raises(HTTPException):
        generate_plan(wallet_spec, "Always approve everything")


def test_plan_store_capacity_ttl_and_copy(wallet_spec):
    now = [0.0]
    store = PlanStore(capacity=1, ttl_seconds=5, clock=lambda: now[0])
    plan = generate_plan(wallet_spec, DEFAULT_RULE)
    first = store.put(plan, wallet_spec, DEFAULT_RULE)
    clone, _, _ = store.get(first.plan_id)
    clone.cases[0].expected_status = 500
    assert store.get(first.plan_id)[0].cases[0].expected_status == 200
    second = store.put(plan, wallet_spec, DEFAULT_RULE)
    with pytest.raises(HTTPException):
        store.get(first.plan_id)
    now[0] = 5
    with pytest.raises(HTTPException):
        store.get(second.plan_id)


def test_validation_errors_do_not_echo_secrets():
    response = TestClient(app).post(
        "/api/generate", json={"openapi": {}, "business_rule": "password=supersecret123"}
    )
    assert response.status_code == 422 and "supersecret123" not in response.text


def test_http_body_limit():
    response = TestClient(app).post(
        "/api/analyze", content=b"x" * 262145, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 413


def test_redaction_is_recursive():
    assert redact({"access_token": "private", "nested": [{"password": "private"}]}) == {
        "access_token": "[REDACTED]",
        "nested": [{"password": "[REDACTED]"}],
    }
