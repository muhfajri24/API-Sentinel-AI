# API Sentinel AI

**OpenAPI + business rule → reviewed local tests → observed evidence.** A local verification MVP for a deliberately faulty synthetic wallet. No real funds, arbitrary API scanning, or production-readiness claim.

The complete local fixture flow is implemented and exercised over actual loopback HTTP. **Meta live inference, the live AI comparison, final event rules/eligibility and official submission remain unverified.** See [final audit](docs/FINAL_AUDIT.md) and [remaining operator tasks](docs/REMAINING_TASKS.md). Source on `feature/complete-local-mvp` incorporates the existing parser work from `feature/openapi-analyzer`; existing branches/main are preserved.

## Offline portfolio release — 11 November 2026

No API key or payment method is required for the complete fixture demonstration. The live Meta gate stays blocked; do not purchase a subscription merely to reproduce this demo. Current work: [full requirement breakdown](docs/RELEASE_PLAN.md), [operations/troubleshooting](docs/OPERATIONS.md), and [release verification](evidence/release_check.json).

Standalone reports built from actual local requests: [buggy target](evidence/local_smoke.html) / [corrected target](evidence/corrected_smoke.html). Download and open the HTML locally. Neither report claims AI inference.

## Quick start

Python 3.11+ (tested on Python 3.12). From the repository root:

```sh
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead:
# .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Optional configuration: copy `.env.example` to `.env` (`Copy-Item .env.example .env` on PowerShell, `cp .env.example .env` on Linux/macOS). Keep keys private; no key is needed for the offline fixture flow.

```sh
python -m scripts.run_demo
```

Open **http://127.0.0.1:8501**. The launcher starts three owned local processes: controller **8100**, synthetic API **8101**, Streamlit **8501**. Ctrl+C stops its own children. If a port is occupied it stops with an explanation and does not kill the existing process.

1. Use the provided OpenAPI and overdraft rule, then Generate test plan.
2. Review full requests, expected HTTP/JSON, references and severity. Fixture mode uses a predefined plan, not natural-language inference.
3. Check the separate expectation-review and local-authorization boxes, then Execute local tests.
4. Observe happy withdrawal **PASS**, overdraft **FAIL** (expected 422/approved=false; intentionally buggy API returns 200/approved=true and remaining=-50).
5. Inspect timestamps, latency, sanitized reproduction and response; download JSON evidence.

Changing inputs invalidates the old plan, consent and receipt. Failed generation/execution cannot leave a stale result displayed. UI and controller mode must agree before generation.

## Verification commands

```sh
python -m scripts.doctor
python -m pytest -q
python -m scripts.run_demo --check
python -m scripts.evaluate
python -m scripts.live_smoke
python -m pip check
```

- `--check`: actual socket-backed controller/demo calls driven through Streamlit AppTest; UI HTTP startup also checked. This is not a visual/browser usability test.
- Evaluation: baseline and predefined fixture against the same buggy API and corrected control, three repetitions per condition. Raw observations and computed metrics are in [evaluation.json](evidence/evaluation.json). It is a one-bug illustration, not proof of AI superiority.
- Live smoke: no call unless a real key and both `--live --confirm-credits` are supplied. Exit **2** means blocked/not run, not a successful live integration. Current [runtime evidence](evidence/meta_live_smoke.json) records absent credentials honestly.
- For lint: `pip install -r requirements-dev.txt`, then `ruff check backend ui scripts tests`. `requirements.lock` captures the verified environment; use it for an exact rebuild on a compatible Python/platform.

For one command that runs setup/lint/tests, actual widget+HTTP smoke on **both** target variants and fixture evaluation, install `requirements-dev.txt` then run `python -m scripts.verify_release`. This never calls Meta. To explore the corrected API interactively, stop the old launcher and run `python -m scripts.run_demo --variant corrected`.

The dashboard also exports a standalone HTML report with escaped text and no external assets/scripts. Changing the target configuration invalidates consent as well as changing the rule/spec. Optional browser capture was attempted but Chromium startup is blocked by this execution environment; see [observed browser status](evidence/browser_check.json). No screenshot/video or human mobile QA is claimed.

## Live Meta mode

Official setup: https://dev.meta.ai/docs/quickstart and https://dev.meta.ai/docs/cookbook/structured-output . The adapter uses the documented Pydantic parse route, a closed synthetic-wallet schema and configurable `muse-spark-1.3`; no arbitrary model proxy is accepted.

Set `META_MODE=live`, private `MODEL_API_KEY`, and the desired eligible `META_MODEL` in `.env`. The launcher intentionally remains a fixture demonstration; to run live, start the three services manually with matching environment:

```sh
python -m uvicorn backend.app.demo_api:app --host 127.0.0.1 --port 8101
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8100
python -m streamlit run ui/streamlit_app.py --server.address=127.0.0.1 --server.port=8501
```

The above commands run in separate activated terminals. Check your account's credits first. For one bounded generation without local execution: `python -m scripts.live_smoke --live --confirm-credits`. For a live evaluation use `python -m scripts.evaluate --live --confirm-credits`; it prints the actual plan and requires you to type `REVIEWED` before sending local test requests. No automatic retry or fixture fallback masks a live error.

No key should appear in a prompt, chat, GitHub, screenshot or client-side file. Only synthetic payloads are permitted; credential-like examples/defaults are rejected before model use and sensitive response keys are redacted from evidence. This filtering is not a comprehensive DLP guarantee.

## Contracts and scope

- `GET /health`: liveness and configured mode, not proof of live inference.
- `POST /api/analyze`: bounded OpenAPI supported-subset analysis.
- `POST /api/generate`: validates inputs/cases/assertions, returns server-issued `plan_id`, source/model/cases and review requirement. Local cache: max 20 plans, 30-minute TTL, lost on process restart.
- `POST /api/execute`: `{ "base_url":"http://127.0.0.1:8101", "plan_id":"<issued-id>", "reviewed":true, "authorized":true }`. **Breaking change:** client-supplied cases/source/model are no longer accepted on the public execution route. Generate a new issued plan after an upgrade/restart.

Execution is limited to **POST /withdraw**, exact allowlisted loopback origin, bounded integer balance/amount, at most 10 cases, 2 KiB per request/expectation, 3-second request timeout, 35-second run budget, 32 KiB response capture and one active execution. No redirects/proxies. Unsupported cases are NOT_RUN; interrupted attempts are ERROR with unknown outcome. Expected JSON uses type-aware recursive subset checks; boolean true is not numeric 1.

Parser scope is a deliberate OpenAPI 3.x POST/JSON subset with typed local component references. It is not complete OpenAPI/JSON Schema support. Complex regular expressions are rejected during payload validation. Planner output is checked against declared operations, response statuses, request/response schemas and exact rule/pointer references. Those structural checks **do not prove that a natural-language expectation is semantically correct**; human review remains required.

## Release status

Local automated checks and evidence are recorded in [FINAL_AUDIT.md](docs/FINAL_AUDIT.md). The official event page still lists a **4 November 2026, 9 PM ET** submission deadline when checked on 10 November; full final rules/owner eligibility/portal acceptance were not verified. Do not claim an on-time or completed submission.

This application remains local-only. Public deployment, generic authenticated APIs, broader methods, multi-step state and a hosted scanner require a separate design/review. See [MIT license](LICENSE); dependencies/model services retain their own terms.
