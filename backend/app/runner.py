"""Intentionally narrow local development runner, never a production scanner."""
import os
from urllib.parse import urlsplit
import httpx
from fastapi import HTTPException
from .models import ExecuteRequest, ExecuteResponse, TestResult


def validate_target(base_url: str, authorized: bool) -> str:
    if not authorized:
        raise HTTPException(status_code=403, detail="Explicit authorization is required")
    parts = urlsplit(base_url)
    normalized = base_url.rstrip("/")
    allowed = {origin.strip().rstrip("/") for origin in os.getenv(
        "ALLOWED_TEST_ORIGINS", "http://127.0.0.1:8101"
    ).split(",") if origin.strip()}
    # MVP strict policy: never permit other interfaces, credentials, query params, fragments or URL paths.
    if parts.scheme != "http" or parts.hostname != "127.0.0.1" or parts.username or parts.password or parts.path not in ("", "/") or parts.query or parts.fragment or normalized not in allowed:
        raise HTTPException(status_code=403, detail="Target is not an allowed local sandbox origin")
    return normalized


def is_subset(expected: dict, actual: object) -> bool:
    if not isinstance(actual, dict):
        return False
    return all(key in actual and actual[key] == value for key, value in expected.items())


async def execute_tests(request: ExecuteRequest) -> ExecuteResponse:
    origin = validate_target(request.base_url, request.authorized)
    results: list[TestResult] = []
    async with httpx.AsyncClient(timeout=3, follow_redirects=False, trust_env=False) as client:
        for case in request.cases:
            # Runner deliberately only supports the single isolated demo endpoint in this starter.
            if case.path != "/withdraw" or case.method != "POST":
                results.append(TestResult(case_id=case.case_id, status="ERROR", expected_status=case.expected_status, reason="Only POST /withdraw demo endpoint is permitted in starter"))
                continue
            try:
                response = await client.post(origin + case.path, json=case.request_body)
                try:
                    payload = response.json()
                except ValueError:
                    payload = {"non_json_response": True}
                status_ok = response.status_code == case.expected_status
                body_ok = is_subset(case.expected_json_subset, payload)
                passed = status_ok and body_ok
                results.append(TestResult(
                    case_id=case.case_id,
                    status="PASS" if passed else "FAIL",
                    expected_status=case.expected_status,
                    actual_status=response.status_code,
                    actual_body=payload,
                    reason="Expectation matched" if passed else "Observed response did not match expected HTTP status and/or JSON fields",
                ))
            except httpx.RequestError as exc:
                results.append(TestResult(case_id=case.case_id, status="ERROR", expected_status=case.expected_status, reason=f"Request failed: {type(exc).__name__}"))
    return ExecuteResponse(results=results)
