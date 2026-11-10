"""One-command offline release check. No model call, credentials, or public target."""

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from backend.app.models import utc_now
from ui.report import render_report
from .local_services import ROOT


def reconcile() -> dict:
    evaluation = json.loads((ROOT / "evidence/evaluation.json").read_text())
    requests = sum(len(run["receipt"]["results"]) for run in evaluation["raw_runs"])
    for source in ("baseline", "fixture"):
        runs = [run for run in evaluation["raw_runs"] if run["receipt"]["source"] == source]
        observed = Counter(case["status"] for run in runs for case in run["receipt"]["results"])
        assert all(
            observed[status] == count
            for status, count in evaluation["metrics"][source]["observed_verdict_counts"].items()
        )
        assert not any(
            case["status"] == "FAIL"
            for run in runs
            if run["condition"] == "corrected"
            for case in run["receipt"]["results"]
        )
    assert evaluation["metrics"]["meta_live"]["status"] == "NOT_RUN"
    for name, expected in [
        ("local_smoke", ["PASS", "FAIL"]),
        ("corrected_smoke", ["PASS", "PASS"]),
    ]:
        smoke = json.loads((ROOT / f"evidence/{name}.json").read_text())
        assert smoke["status"] == "PASS" and smoke["receipt"]["source"] == "fixture"
        assert [case["status"] for case in smoke["receipt"]["results"]] == expected
        (ROOT / f"evidence/{name}.html").write_text(
            render_report(smoke["receipt"]), encoding="utf-8"
        )
    return {
        "status": "PASS",
        "raw_runs": len(evaluation["raw_runs"]),
        "actual_requests": requests,
        "meta_inference": "NOT_RUN",
    }


def main():
    steps = [
        ["-m", "scripts.doctor", "--output", "evidence/setup_check.json"],
        ["-m", "pip", "check"],
        ["-m", "ruff", "check", "backend", "ui", "scripts", "tests"],
        ["-m", "pytest", "-q"],
        ["-m", "scripts.run_demo", "--check"],
        ["-m", "scripts.run_demo", "--check", "--variant", "corrected"],
        ["-m", "scripts.evaluate"],
    ]
    report = {
        "checked_at": utc_now(),
        "status": "RUNNING",
        "meta_inference": "NOT_RUN",
        "steps": [],
    }
    try:
        for step in steps:
            print("Checking: python " + " ".join(step), flush=True)
            result = subprocess.run(
                [sys.executable, *step], cwd=ROOT, capture_output=True, text=True
            )
            report["steps"].append(
                {
                    "command": "python " + " ".join(step),
                    "exit_code": result.returncode,
                    "status": "PASS" if result.returncode == 0 else "FAIL",
                }
            )
            # Local tests only. Model/key preflight is deliberately excluded from this aggregate.
            print(result.stdout, end="", flush=True)
            if result.returncode:
                report["status"] = "FAIL"
                raise SystemExit(result.returncode)
        report["reconciliation"] = reconcile()
        report["status"] = "PASS"
    finally:
        report["finished_at"] = utc_now()
        (ROOT / "evidence/release_check.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
