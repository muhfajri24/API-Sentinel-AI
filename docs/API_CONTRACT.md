# Local API contract v0.2

## Generate and execute

Generate: `POST /api/generate` with `{openapi, business_rule}`. Response fields: `plan_id`, `generated_at`, `source` (`fixture` or `meta_live`), `model`, `review_required`, `cases`. Fixture origin is explicit, and clients cannot select origin/model on execution. Cases include `expectation_basis` (`openapi` or `business_rule`), exact pointer/rule reference and a proposed severity label.

Execute: `POST /api/execute` with `base_url`, server-issued `plan_id`, strict boolean `authorized=true` and `reviewed=true`. It resolves immutable source/spec/rule/cases from the local bounded store and revalidates the plan. Arbitrary client `cases`, `source` or `model` fields are rejected. This deliberately replaces the starter's cases-only route. Plans expire after 1800 seconds, capacity is 20, and process restart requires regeneration.

Errors: 403 missing review/authorization or unsafe target; 404 missing/expired plan; 413 oversized request; 422 schema/privacy/plan violation; 429 concurrent execution (Retry-After 3); 502 unusable Meta response; 503 model configuration unavailable. Validation errors do not echo submitted values. UI uses safe fixed messages.

## Evidence

Receipt: run ID, plan ID, actual source/model, UTC start/end, results. Result fields: case ID, verdict, expected HTTP/JSON, observed HTTP/sanitized JSON, reason, rule reference/basis/severity, start/end, measured latency, method/URL/JSON reproduction. Severity is the test author's proposed impact, not a measured exploit severity.

- PASS: reviewed expected status and JSON subset matched.
- FAIL: a response was received and a reviewed assertion differed. A mistaken oracle may also cause FAIL.
- ERROR: attempted execution could not be evaluated (network, timeout, invalid/oversized/deep response, denied redirect, in-flight total timeout).
- NOT_RUN: unsupported synthetic operation/payload or a later case skipped after the run budget expired. It has no inferred response or verdict.

No curl command containing unescaped inputs is generated; reproduction is structured JSON. Redaction occurs after comparison so masking does not change the assertion. Non-JSON bodies are omitted; sensitive keys are redacted. Capture is bounded, and no raw vendor exception body is shown.

## Fixed boundaries

Controller and UI should bind to loopback only. Default target is 127.0.0.1:8101. The allowlist never permits external hosts, alternate hostnames, userinfo, target paths, query strings, fragments or redirects. No headers/credential fields are accepted for execution. The model endpoint is fixed to the official Meta HTTPS origin; provider errors never invoke fixtures silently.
