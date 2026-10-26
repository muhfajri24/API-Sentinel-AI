# API Sentinel AI — Product & Engineering Framework

## Product thesis
**Business-rule-aware API test planning with executable evidence.** Users provide OpenAPI JSON, a clear business rule, and an authorized local sandbox target; Meta Muse Spark produces structured scenarios; a deterministic runner sends requests and reports real observed outcomes.

### Problem hierarchy
- Technical pain: contract/schema checking alone does not specify all business rules.
- User: independent backend developer and small QA team.
- Differentiator to TEST, not promise: translate a natural language rule into executable API scenarios, not just generic malformed-input fuzzing.
- Alternatives: manual pytest tests, Postman, Schemathesis (already supports schema + stateful tests; do NOT claim otherwise).
- Business hypothesis: faster creation of meaningful regression tests. No validated willingness-to-pay yet.

## System architecture

```text
Streamlit (presentation only)
    |  OpenAPI JSON + business rule
    v
FastAPI /api/analyze, /api/generate, /api/execute
    |      |           |
    |      |           +--> Local-safe HTTPX runner --> evidence
    |      +--> MetaAdapter (Muse Spark, structured output)
    |                 or labelled fixture mode
    +--> OpenAPI validator --> endpoint allowlist --> test plan schema
                           |
                           +--> Pydantic validation of plan
```

Separate processes: test-target `backend.app.demo_api` on `127.0.0.1:8101`; API Sentinel controller `backend.app.main` on `127.0.0.1:8100`; Streamlit UI on port `8502`.

## Responsibility table

| Component | Owns | Must NOT do |
|---|---|---|
| Meta model | propose scenario inputs, expected outputs grounded in the given rule | independently declare PASS or access arbitrary tools |
| OpenAPI parser | identify declared methods and paths | accept arbitrary non-OpenAPI text as a spec |
| Plan validator | test case bounds, declared operations, type checks | treat model JSON as trusted |
| HTTP runner | authorized requests, network timeout, capture actual responses | execute on arbitrary production endpoints |
| Result evaluator | compare status and selected JSON expectations | hallucinate outcomes or hide errors |
| UI | present live / fixture labels and evidence | style/mock results as proven live tests |

## Strict MVP boundaries

- OpenAPI JSON v3.x only. MVP focus: HTTP POST, JSON request bodies, simple response assertion.
- Max 10 cases per request; 3-second timeout each; no redirects; 2KB payload cap recommended before broadening.
- Default allowlisted origin: `http://127.0.0.1:8101`; dev-only demonstration endpoint `/withdraw`.
- Tests that mutate state should run only in isolated, resettable demo environment. Clear consent checkbox required.
- Never touch live bank/real money. All examples are fake simulated transactions with synthetic data.
- Error modes: invalid spec, Meta API not configured, Meta API timeout/error, invalid AI output, unsafe target, target offline, failed assertion.

## Core API contracts

`POST /api/analyze` input `{ "openapi": {...} }`; output `{ "title": str, "operations": [{ "method": str, "path": str }] }`.

`POST /api/generate` input `{ "openapi": {...}, "business_rule": str }`; output `{ "source": "meta_live"|"fixture", "model": str, "cases": [...] }`.

`POST /api/execute` input `{ "base_url": "http://127.0.0.1:8101", "authorized": true, "cases": [...] }`; output `{ "results": [{ "case_id": str, "status": "PASS"|"FAIL"|"ERROR", "expected_status": int, "actual_status": int|null, "actual_body": object|null, "reason": str }] }`.

Case schema: `{ "case_id": str, "description": str, "method": "POST", "path": str, "request_body": object, "expected_status": int, "expected_json_subset": object, "rule_reference": str }`. One case must directly address a given rule. Do not invent undocumented behavior without flagging that expectation derives from user-supplied rule.

## Demo story

1. Dashboard shows `POST /withdraw` (OpenAPI structurally valid), balance=100 synthetic units.
2. Basic positive test (withdraw=50) passes; existing 200 response alone doesn't prove safety.
3. User gives rule: "A withdrawal must be rejected if amount exceeds available balance."
4. Muse Spark produces test for amount=150 expecting rejection (e.g., HTTP 422 + approved=false in **this demo's spec**).
5. Runner executes in local sandbox. Buggy demo API returns 200 + approved=true for 150 -> `FAIL`.
6. Report shows exact request, expected status, actual status and response. No absolute claim about production safety.

## Evidence & comparison framework

- Baseline: specified schema/happy-path test suite. AI: business-rule-aware test generation.
- Need the **same API**, same version/seed, explicit rule, bounded number of requests, repeated 3 times if runtime allows.
- Capture: number of executed tests, valid-case rate, unique seeded business-rule faults identified, false positives, latency and model use/cost if available.
- Label every source of cases: `baseline`, `meta_live`, `fixture`.
- Do not infer outperformance from a contrived one-case demo: say "illustrative demonstration" unless a larger benchmark exists.

## Dependency priorities

P0: Meta call using safe structured output; OpenAPI parsing; bounded runner; verdict by deterministic comparison; dashboard evidence.

P1: baseline side-by-side, sanitized copyable curl, structured logs, downloadable JSON report.

P2 after submission (out of MVP): CI, GitHub integration, broader OpenAPI support, auth flows, multi-step stateful tests, billing, autonomous patching.

## Practical technology

- Python 3.11+, `fastapi`, `uvicorn`, `httpx`, `pydantic`, `openai`, `python-dotenv`, `pytest`, `streamlit`.
- Local start uses three terminal commands (see README); **do not add containers or a separate database** unless blockers justify it.

## Governance / release gate

Never claim production readiness. Before any public deployment, design a stronger SSRF/security boundary, authentication, rate limiting, audit and abuse prevention. On the hackathon MVP, default to local only.
