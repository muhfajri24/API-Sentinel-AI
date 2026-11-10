"""Execute bounded synthetic-wallet tests only; deterministic observed evidence."""

import asyncio
import json
import os
import time
import uuid
from urllib.parse import urlsplit
from typing import Any
import httpx
from fastapi import HTTPException
from .models import ExecuteRequest, ExecuteResponse, TestResult, utc_now
from .safety import redact, bounded_json

MAX_RESPONSE_BYTES = 32768
TOTAL_TIMEOUT_SECONDS = 35


def validate_target(base_url: str, authorized: bool) -> str:
    if authorized is not True:
        raise HTTPException(status_code=403, detail="Explicit local-test authorization is required")
    try:
        parts = urlsplit(base_url)
        port = parts.port
    except (ValueError, TypeError):
        raise HTTPException(status_code=403, detail="Invalid local sandbox origin") from None
    normalized = base_url.rstrip("/")
    allowed = {
        origin.strip().rstrip("/")
        for origin in os.getenv("ALLOWED_TEST_ORIGINS", "http://127.0.0.1:8101").split(",")
        if origin.strip()
    }
    if (
        parts.scheme != "http"
        or parts.hostname != "127.0.0.1"
        or not port
        or parts.username
        or parts.password
        or parts.path not in ("", "/")
        or parts.query
        or parts.fragment
        or normalized not in allowed
        or base_url.strip() != base_url
        or "\\" in base_url
    ):
        raise HTTPException(status_code=403, detail="Target is not an allowed local sandbox origin")
    return normalized


def is_subset(expected: Any, actual: Any) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and is_subset(value, actual[key]) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(expected) == len(actual)
            and all(is_subset(a, b) for a, b in zip(expected, actual))
        )
    if isinstance(expected, bool) or isinstance(actual, bool):
        return type(expected) is type(actual) and expected == actual
    return expected == actual and (
        type(expected) is type(actual)
        or type(expected) in (int, float)
        and type(actual) in (int, float)
    )


def result_for(case, origin: str, **kwargs):
    return TestResult(
        case_id=case.case_id,
        expected_status=case.expected_status,
        expected_json_subset=redact(case.expected_json_subset),
        rule_reference=redact(case.rule_reference),
        expectation_basis=case.expectation_basis,
        severity=case.severity,
        reproduction={
            "method": case.method,
            "url": origin + case.path,
            "json": redact(case.request_body),
        },
        **kwargs,
    )


def synthetic_withdrawal(body: dict) -> bool:
    # Even an otherwise valid spec cannot broaden the local demo's payload contract.
    return (
        set(body) == {"balance", "amount"}
        and type(body["balance"]) is int
        and type(body["amount"]) is int
        and 0 <= body["balance"] <= 10**9
        and 0 < body["amount"] <= 10**9
    )


async def execute_tests(request: ExecuteRequest, *, transport=None) -> ExecuteResponse:
    origin = validate_target(request.base_url, request.authorized)
    started = utc_now()
    results = []
    inflight = None
    # Environment proxies and redirect targets cannot change the network destination.
    async with httpx.AsyncClient(
        timeout=3, follow_redirects=False, trust_env=False, transport=transport
    ) as client:
        try:
            async with asyncio.timeout(TOTAL_TIMEOUT_SECONDS):
                for case in request.cases:
                    if (
                        case.path != "/withdraw"
                        or case.method != "POST"
                        or not synthetic_withdrawal(case.request_body)
                    ):
                        results.append(
                            result_for(
                                case,
                                origin,
                                status="NOT_RUN",
                                reason="Only synthetic POST /withdraw with bounded integer balance/amount is executable",
                            )
                        )
                        continue
                    start, t0, actual_status = utc_now(), time.perf_counter(), None
                    inflight = case
                    payload, verdict, reason = None, "ERROR", "Request could not complete"
                    try:
                        async with client.stream(
                            "POST", origin + case.path, json=case.request_body
                        ) as response:
                            actual_status = response.status_code
                            if 300 <= actual_status < 400:
                                reason = "Redirect refused; no follow-up request was sent"
                            else:
                                content = bytearray()
                                async for chunk in response.aiter_bytes():
                                    content.extend(chunk)
                                    if len(content) > MAX_RESPONSE_BYTES:
                                        break
                                if len(content) > MAX_RESPONSE_BYTES:
                                    reason = "Response exceeded the capture limit; body omitted"
                                else:
                                    try:
                                        payload = json.loads(
                                            content,
                                            parse_constant=lambda _: (_ for _ in ()).throw(
                                                ValueError("Nonfinite JSON")
                                            ),
                                        )
                                        bounded_json(payload, MAX_RESPONSE_BYTES, max_depth=16)
                                        matched = (
                                            actual_status == case.expected_status
                                            and is_subset(case.expected_json_subset, payload)
                                        )
                                        verdict = "PASS" if matched else "FAIL"
                                        reason = (
                                            "Expected status and JSON fields matched"
                                            if matched
                                            else "Observed status and/or JSON fields differed from the reviewed expectation"
                                        )
                                    except (ValueError, UnicodeError, RecursionError):
                                        payload = None
                                        reason = "Invalid JSON or excessive nesting; assertions were not evaluated"
                    except httpx.TimeoutException:
                        reason = "Local request timed out"
                    except httpx.RequestError:
                        reason = "Local sandbox could not be reached"
                    results.append(
                        result_for(
                            case,
                            origin,
                            status=verdict,
                            actual_status=actual_status,
                            actual_body=redact(payload),
                            reason=reason,
                            started_at=start,
                            finished_at=utc_now(),
                            latency_ms=round((time.perf_counter() - t0) * 1000, 3),
                        )
                    )
                    inflight = None
        except TimeoutError:
            if inflight is not None:
                results.append(
                    result_for(
                        inflight,
                        origin,
                        status="ERROR",
                        actual_status=actual_status,
                        reason="Execution budget expired during an in-flight request; outcome is unknown",
                        started_at=start,
                        finished_at=utc_now(),
                        latency_ms=round((time.perf_counter() - t0) * 1000, 3),
                    )
                )
            for case in request.cases[len(results) :]:
                results.append(
                    result_for(
                        case,
                        origin,
                        status="NOT_RUN",
                        reason="Total execution budget exhausted; no verdict was inferred",
                    )
                )
    return ExecuteResponse(
        run_id="run-" + uuid.uuid4().hex,
        source=request.source,
        model=request.model,
        plan_id=request.plan_id,
        started_at=started,
        finished_at=utc_now(),
        results=results,
    )
