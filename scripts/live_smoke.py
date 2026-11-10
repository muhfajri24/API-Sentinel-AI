"""Sanitized S5 preflight and optional bounded live Meta generation. No execution."""

import argparse
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import HTTPException
from backend.app.generator import generate_plan, DEFAULT_RULE
from backend.app.models import utc_now
from .local_services import ROOT


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm-credits", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/meta_live_smoke.json")
    args = parser.parse_args()
    key = os.getenv("MODEL_API_KEY", "").strip()
    configured = bool(key) and not key.lower().startswith(("your_", "replace", "changeme"))
    result = {
        "checked_at": utc_now(),
        "configured_key_present": configured,
        "model": os.getenv("META_MODEL", "muse-spark-1.3"),
        "meta_inference": "NOT_RUN",
        "status": "BLOCKED",
        "reason": "No private Meta credential is configured.",
    }
    if configured:
        if not (args.live and args.confirm_credits):
            result["reason"] = "Live call requires --live --confirm-credits; no call was sent."
        else:
            os.environ["META_MODE"] = "live"
            try:
                plan = generate_plan(
                    json.loads((ROOT / "samples/withdraw-openapi.json").read_text()), DEFAULT_RULE
                )
                result.update(
                    status="PASS",
                    meta_inference="LIVE",
                    source=plan.source,
                    case_count=len(plan.cases),
                    model=plan.model,
                    reason="A structured plan was received and validated. No local execution was requested.",
                )
            except HTTPException as exc:
                result.update(status="FAIL", reason=exc.detail)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 2)


if __name__ == "__main__":
    main()
