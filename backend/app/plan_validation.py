"""Validate candidate requests and assertion grounding against the approved subset."""

import re
from typing import Any
from jsonschema import Draft202012Validator, ValidationError
from .models import TestPlan
from .openapi_parser import parse_openapi
from .openapi_validation import DocumentValidator, invalid


def normalized_schema(spec: dict, value: dict, subset: bool = False) -> dict:
    validator = DocumentValidator(spec)

    def normalize(node, depth=0):
        if depth > 32:
            invalid("plan", "schema expansion limit")
        if "$ref" in node:
            _, target = validator.target(node["$ref"], "schemas", "plan.schema")
            return normalize(target, depth + 1)
        result = {k: v for k, v in node.items() if k not in {"nullable", "example", "default"}}
        if node.get("nullable"):
            result["type"] = [result["type"], "null"]
        if "pattern" in result:
            pattern = result["pattern"]
            if (
                len(pattern) > 128
                or any(char in pattern for char in "()|")
                or len(re.findall(r"[+*{]", pattern)) > 1
                or re.search(r"\\[1-9]", pattern)
            ):
                invalid(
                    "plan.schema",
                    "complex regular expressions are unsupported for payload validation",
                )
        for key in ("exclusiveMinimum", "exclusiveMaximum"):
            if isinstance(result.get(key), bool):
                enabled = result.pop(key)
                limit = "minimum" if key.endswith("Minimum") else "maximum"
                if enabled and limit in result:
                    result[key] = result.pop(limit)
        if "properties" in result:
            result["properties"] = {
                k: normalize(v, depth + 1) for k, v in result["properties"].items()
            }
        for key in ("items", "additionalProperties"):
            if isinstance(result.get(key), dict):
                result[key] = normalize(result[key], depth + 1)
        if subset and result.get("type") == "object":
            result.pop("required", None)
            result.pop("minProperties", None)
        return result

    return normalize(value)


def validate_plan(plan: TestPlan, spec: dict[str, Any], rule: str) -> None:
    operations = {(op.method, op.path) for op in parse_openapi(spec).operations}
    validator = DocumentValidator(spec)
    for case in plan.cases:
        if (case.method, case.path) not in operations:
            invalid("plan", "case operation is not declared")
        operation = spec["paths"][case.path]["post"]
        body = validator.validate(operation["requestBody"], "requestBodies", "plan.requestBody")
        schema = normalized_schema(spec, body["content"]["application/json"]["schema"])
        try:
            Draft202012Validator(schema).validate(case.request_body)
        except (ValidationError, re.error):
            invalid("plan.request_body", "case does not match the supported request schema")
        code = str(case.expected_status)
        response_key = (
            code
            if code in operation["responses"]
            else code[0] + "XX"
            if code[0] + "XX" in operation["responses"]
            else "default"
            if "default" in operation["responses"]
            else None
        )
        if response_key is None:
            invalid(
                "plan.expected_status", "expected status is not declared by the OpenAPI operation"
            )
        if case.expectation_basis == "business_rule":
            if " ".join(case.rule_reference.split()) != " ".join(rule.split()):
                invalid(
                    "plan.rule_reference",
                    "business-rule cases must quote the supplied rule exactly",
                )
        else:
            pointer = (
                "#/paths/"
                + case.path.replace("~", "~0").replace("/", "~1")
                + "/post/responses/"
                + response_key
            )
            if case.rule_reference != pointer:
                invalid(
                    "plan.rule_reference",
                    "OpenAPI assertions must reference the declared response pointer",
                )
        response = validator.validate(
            operation["responses"][response_key], "responses", "plan.response"
        )
        response_schema = response.get("content", {}).get("application/json", {}).get("schema")
        if response_schema:
            try:
                Draft202012Validator(
                    normalized_schema(spec, response_schema, subset=True)
                ).validate(case.expected_json_subset)
            except (ValidationError, re.error):
                invalid(
                    "plan.expected_json_subset",
                    "expected fields contradict the declared response schema",
                )
