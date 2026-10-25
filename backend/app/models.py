from typing import Any, Literal
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    openapi: dict[str, Any]


class Operation(BaseModel):
    method: str
    path: str


class AnalyzeResponse(BaseModel):
    title: str
    operations: list[Operation]


class GenerateRequest(BaseModel):
    openapi: dict[str, Any]
    business_rule: str = Field(min_length=5, max_length=2000)


class TestCase(BaseModel):
    case_id: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=500)
    method: Literal["POST"]
    path: str = Field(pattern=r"^/[A-Za-z0-9/_-]+$")
    request_body: dict[str, Any]
    expected_status: int = Field(ge=100, le=599)
    expected_json_subset: dict[str, Any]
    rule_reference: str = Field(min_length=3, max_length=2000)


class TestPlan(BaseModel):
    cases: list[TestCase] = Field(min_length=1, max_length=10)


class GenerateResponse(TestPlan):
    source: Literal["meta_live", "fixture"]
    model: str


class ExecuteRequest(BaseModel):
    base_url: str
    authorized: bool = False
    cases: list[TestCase] = Field(min_length=1, max_length=10)


class TestResult(BaseModel):
    case_id: str
    status: Literal["PASS", "FAIL", "ERROR"]
    expected_status: int
    actual_status: int | None = None
    actual_body: Any | None = None
    reason: str


class ExecuteResponse(BaseModel):
    results: list[TestResult]
