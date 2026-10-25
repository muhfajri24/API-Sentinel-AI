# API Sentinel AI — Meta Hackathon Starter

**Status:** engineering scaffold / development preview. This is **not** a completed hackathon submission and has **not** been verified against the not-yet-published full Official Rules. Only local demo endpoints are permitted by default.

## What's included

- Revised hackathon master prompt (project-specific): `HACKATHON_MASTER_PROMPT_META.md`
- Codex operating instructions: `AGENTS.md`
- Rules, architecture, day-by-day tasks and demo storyboard under `docs/`
- Minimal FastAPI controller + deliberately buggy local bank-like **synthetic** API, deterministic test runner, simple Streamlit UI.
- Meta Muse Spark structured-output adapter written to documented API; **live service not tested without your key**. Fixture mode clearly labelled.

## Setup (PowerShell / Windows)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m pytest -q
```

If Windows `py -3.11` isn't available, use `python -m venv .venv` with Python 3.11+.

Three terminals (with venv activated in each):

```powershell
python -m uvicorn backend.app.demo_api:app --host 127.0.0.1 --port 8001
```

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

```powershell
python -m streamlit run ui/streamlit_app.py
```

Open Streamlit's displayed localhost URL (usually http://localhost:8501).

## Model modes

- **Fixture development** (default): `.env` has `META_MODE=fixture`; no actual AI inference. Intended only for offline development and demo wiring tests.
- **Live Meta**: set `META_MODE=live` and add your private `MODEL_API_KEY` to `.env` locally; calls `muse-spark-1.3` via `https://api.meta.ai/v1`. **Costs/credits may apply; verify first.** Never commit `.env`.
- `MODEL_API_KEY` should never be posted to ChatGPT or GitHub.

## First execution

1. Confirm `/health` is healthy at http://127.0.0.1:8000/health.
2. Review fixture source label and demo business rule in UI.
3. `Generate` and `Execute` against `http://127.0.0.1:8001` after checking the consent box.
4. The demo is **intentionally buggy**: withdrawing 150 from balance 100 is approved, generating a reproducible FAIL for the overdraft rule. It is a simulated incident, not real banking software.
5. Switch to live Meta mode only after checking API access and limitations.

## Important guardrails

- This starter **only** targets `http://127.0.0.1:8001`; no internet scanning, no use of real payments.
- Request count is bounded; redirects aren't followed; tests require explicit authorization.
- The minimal proof checker compares status code and selected JSON fields; does not certify business correctness broadly.
- The fixture is a development aid only. If Meta inference is unavailable, the UI must report that honestly.

## Official references

- Event: https://dev.meta.ai/events/global-hackathon
- Muse Spark API: https://dev.meta.ai/docs/quickstart
- Structured output: https://dev.meta.ai/docs/cookbook/structured-output
- Existing testing reference: https://schemathesis.io/
