# Codex Task Board (execute ONE TASK at a time)

Use this exact preamble for Codex: **"Read AGENTS.md and the docs. Execute ONLY task [ID]. Make a small diff, add tests, run pytest, return evidence. No unrelated features."**

## 00 — Rules and repository checks (Owner + ChatGPT)
- Verify Official Rules published at kickoff; update `docs/RULES_COMPLIANCE.md` with exact clauses; check if starter/template reuse is allowed.
- Acceptance: R0 marked PASS only with documented evidence. This cannot be delegated to assumptions.

## 01 — Repo bootstrap and smoke (day 1)
- Install Python requirements, run `python -m pytest -q`, run controller, demo API, UI locally.
- Acceptance: `/health` responds 200, UI displays model mode, tests pass. Fix dependency/platform issues only.

## 02 — Robust OpenAPI parser (day 2)
- Validate real OpenAPI 3.x JSON and supported operations; accept required request body references only after safe normalization; no speculative support.
- Acceptance: invalid spec rejected with useful detail; no path/method phantom; unit tests cover invalid spec and missing paths.

## 03 — Business rule test-plan fixture (day 2)
- Implement typed `TestPlan` / `TestCase`, bounded 10 cases, rule_reference mandatory, off-line fixture with clear label.
- Acceptance: overdraft fixture includes 150 from balance100; fixture mode cannot be displayed as Meta inference.

## 04 — Meta Muse Spark live integration (days 3–4)
- Use Model API base URL `https://api.meta.ai/v1`, key from environment, `muse-spark-1.3` configurable. Request structured JSON, parse Pydantic, validate cases against declared OpenAPI paths/methods; add mocked API unit tests.
- Acceptance: mocked-path test passes; owner manually runs live smoke with own key and captures redacted result and model ID; errors clearly surfaced without silently using fixture.

## 05 — Safe local executor (day 5)
- Implement `httpx` runner, consent, exact origin allowlist, request caps, timeouts and no redirects. No arbitrary URL/credential support.
- Acceptance: reject non-allowlisted targets and consent=false; PASS valid withdraw, FAIL overdraft on demo; test errors clear.

## 06 — Evidence contract + tests (day 6)
- Implement expected vs actual status and JSON subset, timestamps/latency, severity tied to rule, concise reproduction without sensitive data.
- Acceptance: no invented results; tests show PASS, FAIL, ERROR paths.

## 07 — Dashboard (day 7)
- Streamlit: text input business rule, default OpenAPI example, generate button, execute button guarded by consent, Meta LIVE vs FIXTURE prominent.
- Acceptance: reviewer can run complete flow in under 2 mins on demo; error handling visible.

## 08 — Evaluation vs baseline (day 8)
- Baseline deterministic test, AI-generated or validated live case, seeded demo bug; collect raw evidence and measured rates, discuss limitations.
- Acceptance: saved `evaluation.json` with origin labels and real measurements, no fabricated benchmark.

## 09 — Polish and presentation (day 9)
- README reproducible setup, 60–90 sec demo storyboard, clearer visual hierarchy, maybe JSON report download. No motion-heavy marketing work.
- Acceptance: independent reviewer follows README and reproduces results; screenshot shows actual verdict and source label.

## 10 — Submission audit (day 10)
- Verify rules, license, repo visibility, links, attribution, no secret leakage, actual live Meta usage proof, submission-form artifacts. Complete using project owner's account.
- Acceptance: owner confirms official submission after uploading; Codex MUST NOT assert submission without portal evidence.

## Highest-priority Codex instruction to copy now

```text
Read AGENTS.md, docs/RULES_COMPLIANCE.md, docs/PROJECT_FRAMEWORK.md,
and docs/CODEX_TASKS.md. Start only TASK 01. Verify Python dependencies,
run all tests, start smoke-test controller and demo endpoints, fix only
bootstrap errors. Do not implement future tasks, call paid services, deploy,
or push to GitHub. Return files changed, exact commands and outputs,
remaining issues, and which acceptance criteria passed.
```
