from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from .safety import bounded_json, has_sensitive_data, reject_spec_secrets


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AnalyzeRequest(StrictModel):
    openapi: dict[str, Any]

    @field_validator("openapi")
    @classmethod
    def bounded_spec(cls, value):
        bounded_json(value, 131072)
        reject_spec_secrets(value)
        return value


class Operation(StrictModel):
    method: str
    path: str


class AnalyzeResponse(StrictModel):
    title: str
    operations: list[Operation]


class GenerateRequest(AnalyzeRequest):
    business_rule: str = Field(min_length=5, max_length=2000)

    @field_validator("business_rule")
    @classmethod
    def synthetic_rule(cls, value):
        if has_sensitive_data(value):
            raise ValueError("Remove secret-like values from the rule")
        return value


class TestCase(StrictModel):
    case_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    description: str = Field(min_length=1, max_length=500)
    method: Literal["POST"]
    path: str = Field(pattern=r"^/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*/?$")
    request_body: dict[str, Any]
    expected_status: int = Field(ge=100, le=599, strict=True)
    expected_json_subset: dict[str, Any]
    rule_reference: str = Field(min_length=3, max_length=2000)
    expectation_basis: Literal["openapi", "business_rule"] = "business_rule"
    severity: Literal["info", "medium", "high"] = "medium"

    @field_validator("request_body", "expected_json_subset")
    @classmethod
    def bounded_synthetic_payload(cls, value):
        bounded_json(value, 2048, max_depth=10)
        if has_sensitive_data(value):
            raise ValueError("Only synthetic, non-sensitive payloads are accepted")
        return value

    @field_validator("expected_json_subset")
    @classmethod
    def nonempty_assertions(cls, value):
        if not value:
            raise ValueError("At least one JSON field assertion is required")
        return value


class TestPlan(StrictModel):
    cases: list[TestCase] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def unique_ids(self):
        if len({case.case_id for case in self.cases}) != len(self.cases):
            raise ValueError("Case IDs must be unique")
        return self


class GenerateResponse(TestPlan):
    source: Literal["meta_live", "fixture"]
    model: str
    plan_id: str | None = None
    generated_at: str = Field(default_factory=utc_now)
    review_required: bool = True


class ExecutePlanRequest(StrictModel):
    base_url: str = Field(max_length=200)
    plan_id: str = Field(min_length=1, max_length=80)
    authorized: bool = Field(default=False, strict=True)
    reviewed: bool = Field(default=False, strict=True)


class ExecuteRequest(TestPlan):
    """Internal runner contract; public execution uses a server-issued plan_id."""

    base_url: str
    authorized: bool = Field(default=False, strict=True)
    source: Literal["baseline", "meta_live", "fixture"] = "fixture"
    model: str = "offline-fixture-not-AI"
    plan_id: str | None = None


class TestResult(StrictModel):
    case_id: str
    status: Literal["PASS", "FAIL", "ERROR", "NOT_RUN"]
    expected_status: int
    expected_json_subset: dict[str, Any] = Field(default_factory=dict)
    actual_status: int | None = None
    actual_body: Any | None = None
    reason: str
    rule_reference: str = ""
    expectation_basis: Literal["openapi", "business_rule"] = "business_rule"
    severity: Literal["info", "medium", "high"] = "medium"
    started_at: str | None = None
    finished_at: str | None = None
    latency_ms: float | None = None
    reproduction: dict[str, Any] = Field(default_factory=dict)


class ExecuteResponse(StrictModel):
    run_id: str
    source: Literal["baseline", "meta_live", "fixture"]
    model: str
    plan_id: str | None = None
    started_at: str
    finished_at: str
    results: list[TestResult]
