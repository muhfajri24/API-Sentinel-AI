import json
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi import HTTPException
from backend.app.openapi_parser import parse_openapi, validate_plan_against_spec
from backend.app.generator import fixture_plan, generate_plan
from backend.app.runner import validate_target, is_subset
from backend.app.models import TestPlan as PlanSchema
from fastapi.testclient import TestClient
from backend.app.demo_api import app as demo_app
from backend.app.main import app as controller_app


SPEC = json.loads((Path(__file__).resolve().parents[1] / "samples" / "withdraw-openapi.json").read_text(encoding="utf-8"))
RULE = "Overdraft amounts must be rejected with 422 and approved=false"


def test_openapi_parser():
    assert parse_openapi(SPEC).operations[0].path == "/withdraw"


def test_openapi_parser_rejects_wrong_version():
    with pytest.raises(HTTPException):
        parse_openapi({"openapi": "2.0", "paths": {"/foo": {"post": {}}}})


def test_fixture_is_not_labelled_meta(monkeypatch):
    monkeypatch.setenv("META_MODE", "fixture")
    plan = generate_plan(SPEC, RULE)
    assert plan.source == "fixture"
    assert plan.model == "offline-fixture-not-AI"
    assert len(plan.cases) == 2


def test_planner_rejects_unlisted_path():
    plan = fixture_plan(RULE)
    spec = deepcopy(SPEC)
    spec["paths"]["/other"] = spec["paths"].pop("/withdraw")
    with pytest.raises(HTTPException, match="undeclared operation"):
        validate_plan_against_spec(plan, spec)


def test_target_requires_authorization():
    with pytest.raises(HTTPException):
        validate_target("http://127.0.0.1:8001", False)


@pytest.mark.parametrize("target", ["http://example.com", "http://localhost:8001", "http://127.0.0.1:9999", "http://127.0.0.1:8001/secret", "http://127.0.0.1:8001@evil.com"])
def test_target_deny_outside_allowlist(target):
    with pytest.raises(HTTPException):
        validate_target(target, True)


def test_json_subset_checker():
    assert is_subset({"approved": True}, {"approved": True, "remaining": 50})
    assert not is_subset({"approved": False}, {"approved": True})


def test_demo_contains_deliberate_overdraft_bug():
    client = TestClient(demo_app)
    ok = client.post("/withdraw", json={"balance": 100, "amount": 50})
    assert ok.status_code == 200
    assert ok.json()["approved"] is True
    buggy = client.post("/withdraw", json={"balance": 100, "amount": 150})
    assert buggy.status_code == 200  # intentionally violates stated business rule
    assert buggy.json()["remaining"] == -50


def test_controller_health():
    assert TestClient(controller_app).get("/health").status_code == 200


def test_meta_live_missing_key_surfaces_error(monkeypatch):
    monkeypatch.setenv("META_MODE", "live")
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        generate_plan(SPEC, RULE)
    assert exc.value.status_code == 503
