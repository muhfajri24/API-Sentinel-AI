"""Deterministic runner evidence from real ASGI request handling or mock transport."""

import asyncio
import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from backend.app.demo_api import create_demo_app
from backend.app.generator import fixture_plan, DEFAULT_RULE
from backend.app.models import ExecuteRequest
from backend.app.runner import execute_tests, validate_target, is_subset
from backend.app import main as controller
from backend.app import runner


def request():
    return ExecuteRequest(
        base_url="http://127.0.0.1:8101", authorized=True, cases=fixture_plan(DEFAULT_RULE).cases
    )


def test_buggy_and_corrected_actual_handlers():
    for buggy, expected in [(True, ["PASS", "FAIL"]), (False, ["PASS", "PASS"])]:
        receipt = asyncio.run(
            execute_tests(request(), transport=httpx.ASGITransport(app=create_demo_app(buggy)))
        )
        assert [r.status for r in receipt.results] == expected
        assert receipt.source == "fixture" and receipt.model == "offline-fixture-not-AI"
        for result in receipt.results:
            assert result.started_at.endswith("Z") and result.finished_at.endswith("Z")
            assert result.latency_ms >= 0 and result.reproduction["url"].endswith("/withdraw")
            assert result.expected_json_subset and result.rule_reference
        if buggy:
            assert receipt.results[1].actual_body["remaining"] == -50
            assert (
                receipt.results[1].expected_status == 422
                and receipt.results[1].actual_status == 200
            )


@pytest.mark.parametrize(
    "kind",
    ["redirect", "timeout", "offline", "nonjson", "oversize", "secret", "bool_number", "deep_json"],
)
def test_adversarial_responses_are_bounded_and_sanitized(kind):
    calls = []

    def respond(req):
        calls.append(str(req.url))
        if kind == "timeout":
            raise httpx.ReadTimeout("PRIVATE KEY")
        if kind == "offline":
            raise httpx.ConnectError("PRIVATE KEY")
        if kind == "redirect":
            return httpx.Response(302, headers={"Location": "http://unapproved.test"})
        if kind == "nonjson":
            return httpx.Response(200, text="PRIVATE non-json response")
        if kind == "oversize":
            return httpx.Response(200, content=b"x" * 32769)
        if kind == "deep_json":
            return httpx.Response(200, content=b"[" * 2000 + b"0" + b"]" * 2000)
        if kind == "bool_number":
            return httpx.Response(200, json={"approved": 1})
        return httpx.Response(
            200,
            json={
                "approved": True,
                "access_token": "PRIVATE KEY",
                "nested": {"password": "PRIVATE KEY"},
            },
        )

    value = request()
    value.cases = value.cases[:1]
    receipt = asyncio.run(execute_tests(value, transport=httpx.MockTransport(respond)))
    result = receipt.results[0]
    assert len(calls) == 1 and calls[0] == "http://127.0.0.1:8101/withdraw"
    assert "PRIVATE" not in receipt.model_dump_json()
    if kind == "secret":
        assert result.status == "PASS" and result.actual_body["access_token"] == "[REDACTED]"
    else:
        assert result.status == "FAIL" if kind == "bool_number" else result.status == "ERROR"


@pytest.mark.parametrize(
    "target",
    [
        "http://127.0.0.1:bad",
        "http://127.0.0.1:8101?x=1",
        "http://127.0.0.1:8101#x",
        "http://127.0.0.1:8101/path",
        "http://127.0.0.1:8101@evil.test",
        "http://127.0.0.1:8101\\x",
        " http://127.0.0.1:8101",
        "http://[::1]:8101",
    ],
)
def test_target_variants_denied(target):
    with pytest.raises(HTTPException):
        validate_target(target, True)


def test_boolean_is_not_number_and_nested_subsets_are_checked():
    assert not is_subset({"a": True}, {"a": 1})
    assert not is_subset({"a": False}, {"a": 0})
    assert is_subset({"a": {"b": [1, 2]}}, {"a": {"b": [1, 2], "other": 0}})
    assert not is_subset({"a": [1, 2]}, {"a": [1]})


def test_unsupported_operation_is_not_sent():
    value = request()
    value.cases = value.cases[:1]
    value.cases[0].path = "/other"

    def send(_):
        raise AssertionError("Should not send")

    receipt = asyncio.run(execute_tests(value, transport=httpx.MockTransport(send)))
    assert receipt.results[0].status == "NOT_RUN" and receipt.results[0].actual_status is None


def test_total_budget_marks_remaining_not_run(monkeypatch):
    async def slow(_):
        await asyncio.sleep(0.1)
        return httpx.Response(200, json={"approved": True})

    monkeypatch.setattr(runner, "TOTAL_TIMEOUT_SECONDS", 0.001)
    receipt = asyncio.run(execute_tests(request(), transport=httpx.MockTransport(slow)))
    assert [r.status for r in receipt.results] == ["ERROR", "NOT_RUN"]


def test_controller_requires_issued_plan_review_and_authorization(wallet_spec, monkeypatch):
    client = TestClient(controller.app)
    plan = client.post(
        "/api/generate", json={"openapi": wallet_spec, "business_rule": DEFAULT_RULE}
    ).json()
    payload = {
        "base_url": "http://127.0.0.1:8101",
        "plan_id": plan["plan_id"],
        "authorized": True,
        "reviewed": True,
    }
    for missing in ["authorized", "reviewed"]:
        assert client.post("/api/execute", json={**payload, missing: False}).status_code == 403
    assert client.post("/api/execute", json={**payload, "plan_id": "missing"}).status_code == 404
    assert client.post("/api/execute", json={**payload, "source": "meta_live"}).status_code == 422
    assert client.post("/api/execute", json={**payload, "authorized": "true"}).status_code == 422
    assert (
        client.post(
            "/api/execute",
            json={"base_url": payload["base_url"], "authorized": True, "cases": plan["cases"]},
        ).status_code
        == 422
    )

    async def execute_local(value):
        return await execute_tests(value, transport=httpx.ASGITransport(app=create_demo_app(True)))

    monkeypatch.setattr(controller, "execute_tests", execute_local)
    result = client.post("/api/execute", json=payload)
    assert result.status_code == 200 and result.json()["source"] == "fixture"
    assert [r["status"] for r in result.json()["results"]] == ["PASS", "FAIL"]


def test_concurrent_execution_is_rejected_without_sending(wallet_spec, monkeypatch):
    client = TestClient(controller.app)
    plan = client.post(
        "/api/generate", json={"openapi": wallet_spec, "business_rule": DEFAULT_RULE}
    ).json()

    class Locked:
        def locked(self):
            return True

    monkeypatch.setattr(controller, "_execution_lock", Locked())
    response = client.post(
        "/api/execute",
        json={
            "base_url": "http://127.0.0.1:8101",
            "plan_id": plan["plan_id"],
            "authorized": True,
            "reviewed": True,
        },
    )
    assert response.status_code == 429 and response.headers["retry-after"] == "3"
