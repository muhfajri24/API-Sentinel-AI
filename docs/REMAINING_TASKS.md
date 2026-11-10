# Follow-up tasks discovered by final crosscheck

These are concrete uncompleted gates, not claims that an unavailable check passed. Engineering code for the local fixture path is complete; live/event/manual gates need separate evidence.

| ID | Small task | Acceptance | Dependency |
| --- | --- | --- | --- |
| A01 | Configure private Meta key locally | `MODEL_API_KEY` is available only to the local controller | Owner account access |
| A02 | Confirm available credits/model access | Account limits checked before one bounded call; no paid subscription assumed | A01 |
| A03 | Run the structured live smoke | `evidence/meta_live_smoke.json` contains actual LIVE/PASS, model and validated case count | A02; `python -m scripts.live_smoke --live --confirm-credits` |
| A04 | Review and execute actual AI cases | Owner reviews expectations; actual local receipts show source=meta_live with honest verdicts | A03; matching live UI/controller |
| A05 | Repeat live comparison against corrected control | Raw live observations collected under the same conditions; false positives/limits reported | A04; `python -m scripts.evaluate --live --confirm-credits` |
| A06 | Manual desktop/mobile and keyboard QA | Human follows README, confirms readability/focus/disabled states and records actual duration | Local UI |
| A07 | Capture authentic screenshot and 60–90 sec footage | Actual source label, request and observed verdict visible; no secrets; no fixture mislabeled live | A04/A06 if presenting Meta |
| A08 | Obtain final official rules and participation status | Final rules/source/clauses, reuse/eligibility and owner acceptance recorded | Owner portal/organizer |
| A09 | Resolve past event deadline before any submission claim | Explicit organizer/portal evidence of allowed submission timing | A08; page still lists 4 Nov ET as of 10 Nov |
| A10 | Complete actual submission, if still permitted | Real portal confirmation and final artifact links; no guessed submitted state | A03–A09 |

## Extra details checked and fixed in this work

- Later parser branch was missing from main; preserved and used as the baseline.
- Request/expected JSON byte/depth caps, strict authorization booleans, duplicate IDs, declared statuses, schema validity and exact expectation references were missing or incomplete.
- Model schema had arbitrary objects; it now uses closed typed wallet fields and bounded cases.
- Client-submitted source/cases could bypass origin/spec grounding; execution now resolves server-issued immutable plans with TTL/capacity.
- UI stale results/consent after edits or failed generation/execution were removed.
- A fixture-configured dashboard could otherwise call a live-configured controller; mode agreement is checked before generation.
- Python boolean/numeric equality caused misleading matches; recursive JSON comparison now distinguishes them.
- Oversized/non-JSON/deep responses and redirects have bounded error paths; secret response fields are redacted.
- An in-flight request interrupted by the total timeout must be ERROR/unknown, while untouched later cases are NOT_RUN.
- Baseline/fixture/live labels, corrected negative control, raw receipts and conditional validity metrics are kept separate.
- One-command launch/smoke manages only its own processes and refuses occupied ports.

## Intentionally outside this MVP

Public scanner/deployment, arbitrary API targets, auth tokens, extra methods, multi-step stateful testing, databases, agent swarms and autonomous repair remain excluded. This code does not certify API correctness/security or general AI superiority. Plan loss after restart is expected; regenerate and re-review instead of pretending a plan is durable.
