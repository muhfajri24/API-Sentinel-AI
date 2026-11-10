"""Local-only controller; plans and test source labels are issued by this process."""

from dotenv import load_dotenv

load_dotenv()

import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from .models import (
    AnalyzeRequest,
    AnalyzeResponse,
    GenerateRequest,
    GenerateResponse,
    ExecutePlanRequest,
    ExecuteRequest,
    ExecuteResponse,
)
from .openapi_parser import parse_openapi
from .plan_validation import validate_plan
from .plan_store import plan_store
from .generator import generate_plan, meta_mode
from .runner import execute_tests, validate_target


class BodyLimit:
    """Bound requests before JSON/Pydantic parsing; no raw input echoes."""

    def __init__(self, app, max_bytes=262144):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > self.max_bytes:
                response = JSONResponse(
                    status_code=413, content={"detail": "Request exceeds the local demo size limit"}
                )
                return await response(scope, receive, send)
            if not message.get("more_body", False):
                break
        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        return await self.app(scope, replay, send)


app = FastAPI(title="API Sentinel AI — local verification MVP", version="0.2")
app.add_middleware(BodyLimit)


@app.exception_handler(RequestValidationError)
async def validation_error(_request, _exc):
    # Default FastAPI validation errors can include submitted private input.
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Invalid request: check the documented schema, synthetic-data and size limits"
        },
    )


@app.get("/health")
def health():
    return {"status": "ok", "mode": meta_mode()}


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    return parse_openapi(request.openapi)


@app.post("/api/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest):
    parse_openapi(request.openapi)
    plan = generate_plan(request.openapi, request.business_rule)
    return plan_store.put(plan, request.openapi, request.business_rule)


_execution_lock = asyncio.Lock()


@app.post("/api/execute", response_model=ExecuteResponse)
async def execute(request: ExecutePlanRequest):
    validate_target(request.base_url, request.authorized)
    if not request.reviewed:
        raise HTTPException(status_code=403, detail="Review the expected outcomes before executing")
    plan, spec, rule = plan_store.get(request.plan_id)
    validate_plan(plan, spec, rule)
    if _execution_lock.locked():
        raise HTTPException(
            status_code=429,
            detail="Another local execution is active; retry after it finishes",
            headers={"Retry-After": "3"},
        )
    async with _execution_lock:
        return await execute_tests(
            ExecuteRequest(
                base_url=request.base_url,
                authorized=True,
                cases=plan.cases,
                source=plan.source,
                model=plan.model,
                plan_id=plan.plan_id,
            )
        )
