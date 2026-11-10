"""S4: all SDK responses simulated, never represented as actual Meta usage."""

from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from backend.app.generator import generate_plan, DEFAULT_RULE, build_meta_client
from backend.app.meta_schema import MetaPlan
from backend.app.models import TestPlan as Plan
from backend.app.generator import fixture_plan


class FakeMeta:
    def __init__(self, parsed=None, refusal=None, error=None):
        self.parsed, self.refusal, self.error = parsed, refusal, error
        self.calls = []
        self.beta = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(parse=self.parse))
        )

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(
            model="muse-spark-1.3",
            choices=[
                SimpleNamespace(message=SimpleNamespace(parsed=self.parsed, refusal=self.refusal))
            ],
        )


def test_valid_structured_meta_plan_is_validated(wallet_spec, monkeypatch):
    monkeypatch.setenv("META_MODE", "live")
    candidate = MetaPlan.model_validate(fixture_plan(DEFAULT_RULE).model_dump())
    client = FakeMeta(candidate)
    result = generate_plan(wallet_spec, DEFAULT_RULE, client=client)
    assert result.source == "meta_live" and result.model == "muse-spark-1.3"
    assert client.calls[0]["response_format"] is MetaPlan
    assert client.calls[0]["max_completion_tokens"] == 4000
    assert "untrusted" in client.calls[0]["messages"][0]["content"]
    assert "test-key" not in str(client.calls)


@pytest.mark.parametrize(
    "kind",
    ["refusal", "empty", "exception", "malformed", "invalid_status", "wrong_rule", "invented_path"],
)
def test_meta_failures_never_fall_back(wallet_spec, monkeypatch, kind):
    monkeypatch.setenv("META_MODE", "live")
    value = fixture_plan(DEFAULT_RULE).model_dump()
    if kind == "invalid_status":
        value["cases"][0]["expected_status"] = 201
    if kind == "wrong_rule":
        value["cases"][1]["rule_reference"] = "An invented rule"
    if kind == "invented_path":
        value["cases"][0]["path"] = "/private"
    client = FakeMeta(value)
    if kind == "refusal":
        client.refusal = "PRIVATE refusal text"
    if kind == "empty":
        client.parsed = None
    if kind == "exception":
        client.error = RuntimeError("PRIVATE vendor body test-key")
    if kind == "malformed":
        client.parsed = {"cases": "bad"}
    with pytest.raises(HTTPException) as error:
        generate_plan(wallet_spec, DEFAULT_RULE, client=client)
    assert error.value.status_code in {422, 502}
    assert "PRIVATE" not in error.value.detail and "test-key" not in error.value.detail


def test_missing_key_and_wrong_host_are_not_contacted(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "")
    with pytest.raises(HTTPException) as error:
        build_meta_client()
    assert error.value.status_code == 503
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("META_BASE_URL", "https://unapproved.test/v1")
    with pytest.raises(HTTPException) as error:
        build_meta_client()
    assert error.value.status_code == 503


def test_closed_meta_schema_has_no_arbitrary_object_properties():
    schema = MetaPlan.model_json_schema()
    for model in [schema, *schema["$defs"].values()]:
        if model.get("type") == "object":
            assert model.get("additionalProperties") is False
            assert set(model.get("required", [])) == set(model["properties"])


def test_invalid_spec_never_reaches_model(wallet_spec, monkeypatch):
    monkeypatch.setenv("META_MODE", "live")
    del wallet_spec["paths"]
    client = FakeMeta(fixture_plan(DEFAULT_RULE))
    with pytest.raises(HTTPException):
        generate_plan(wallet_spec, DEFAULT_RULE, client=client)
    assert not client.calls
