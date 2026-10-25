from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from .models import (AnalyzeRequest, AnalyzeResponse, GenerateRequest, GenerateResponse,
                     ExecuteRequest, ExecuteResponse)
from .openapi_parser import parse_openapi
from .generator import generate_plan
from .runner import execute_tests

app = FastAPI(title="API Sentinel AI — development scaffold", version="0.1")


@app.get("/health")
def health():
    import os
    return {"status": "ok", "mode": os.getenv("META_MODE", "fixture")}


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    return parse_openapi(request.openapi)


@app.post("/api/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest):
    parse_openapi(request.openapi)
    return generate_plan(request.openapi, request.business_rule)


@app.post("/api/execute", response_model=ExecuteResponse)
async def execute(request: ExecuteRequest):
    return await execute_tests(request)
