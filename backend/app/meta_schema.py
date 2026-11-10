"""Closed structured-output schema for the executable synthetic-wallet subset."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WalletBody(ClosedModel):
    balance: int = Field(ge=0, le=10**9, strict=True)
    amount: int = Field(gt=0, le=10**9, strict=True)


class WalletExpectation(ClosedModel):
    approved: bool = Field(strict=True)


class MetaCase(ClosedModel):
    case_id: str
    description: str
    method: Literal["POST"]
    path: Literal["/withdraw"]
    request_body: WalletBody
    expected_status: Literal[200, 422]
    expected_json_subset: WalletExpectation
    rule_reference: str
    expectation_basis: Literal["openapi", "business_rule"]
    severity: Literal["info", "medium", "high"]


class MetaPlan(ClosedModel):
    cases: list[MetaCase] = Field(min_length=1, max_length=6)
