"""Repeatable, actual-socket synthetic evaluation; fixture is never labelled AI."""

import argparse
import asyncio
import json
import os
from pathlib import Path
from backend.app.models import ExecuteRequest, TestPlan, utc_now
from backend.app.generator import fixture_plan, generate_plan, DEFAULT_RULE
from backend.app.plan_validation import validate_plan
from backend.app.runner import execute_tests
from .local_services import local_services, ROOT


def evaluate(repeats: int = 3, live_plan=None):
    spec = json.loads((ROOT / "samples/withdraw-openapi.json").read_text())
    fixture = fixture_plan(DEFAULT_RULE)
    validate_plan(fixture, spec, DEFAULT_RULE)
    variants = [
        ("baseline", "handwritten-positive-only", fixture.cases[:1]),
        ("fixture", "offline-fixture-not-AI", fixture.cases),
    ]
    if live_plan is not None:
        if live_plan.source != "meta_live":
            raise ValueError("Live variant must originate from actual live generation")
        validate_plan(live_plan, spec, DEFAULT_RULE)
        variants.append(("meta_live", live_plan.model, live_plan.cases))
    raw = []
    for condition in ("buggy", "corrected"):
        with local_services(variant=condition):
            for source, model, cases in variants:
                for repetition in range(repeats):
                    receipt = asyncio.run(
                        execute_tests(
                            ExecuteRequest(
                                base_url="http://127.0.0.1:8101",
                                authorized=True,
                                source=source,
                                model=model,
                                cases=cases,
                            )
                        )
                    )
                    raw.append(
                        {
                            "condition": condition,
                            "repetition": repetition + 1,
                            "receipt": receipt.model_dump(),
                        }
                    )
    metrics = {}
    for source, model, cases in variants:
        runs = [entry for entry in raw if entry["receipt"]["source"] == source]
        results = [r for entry in runs for r in entry["receipt"]["results"]]
        faulty = [
            r
            for entry in runs
            if entry["condition"] == "buggy"
            for r in entry["receipt"]["results"]
        ]
        controls = [
            r
            for entry in runs
            if entry["condition"] == "corrected"
            for r in entry["receipt"]["results"]
        ]
        latencies = [r["latency_ms"] for r in results if r["latency_ms"] is not None]
        validated_count = 0
        for case in cases:
            validate_plan(TestPlan(cases=[case]), spec, DEFAULT_RULE)
            validated_count += 1
        metrics[source] = {
            "model": model,
            "cases_per_run": len(cases),
            "validated_case_rate": validated_count / len(cases),
            "observed_verdict_counts": {
                s: sum(r["status"] == s for r in results)
                for s in ("PASS", "FAIL", "ERROR", "NOT_RUN")
            },
            "unique_seeded_faults_found": int(
                any(
                    r["status"] == "FAIL"
                    and r["expected_status"] == 422
                    and r["actual_status"] == 200
                    and r["actual_body"].get("approved") is True
                    and r["reproduction"]["json"]["amount"] > r["reproduction"]["json"]["balance"]
                    for r in faulty
                )
            ),
            "control_false_positive_count": sum(r["status"] == "FAIL" for r in controls),
            "mean_request_latency_ms": round(sum(latencies) / len(latencies), 3)
            if latencies
            else None,
            "model_cost": None,
        }
    if live_plan is None:
        metrics["meta_live"] = {
            "status": "NOT_RUN",
            "reason": "No configured, credit-confirmed, human-reviewed live plan was used.",
        }
    return {
        "generated_at": utc_now(),
        "transport": "actual loopback HTTP",
        "scope": "illustrative single seeded overdraft bug; corrected control; not a representative benchmark",
        "repeats_per_condition": repeats,
        "seeded_fault_count": 1,
        "metrics": metrics,
        "raw_runs": raw,
        "limitations": [
            "Baseline deliberately tests only the documented positive case.",
            "Fixture cases are predefined, not AI generation.",
            "Validity rate is conditional on the accepted plan; invalid model generations were not sampled.",
            "The same synthetic API/inputs are reused; no real-world effectiveness claim.",
            "Latency is local observation, not a provider/production performance benchmark.",
        ],
    }


def main():
    from dotenv import load_dotenv

    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/evaluation.json")
    parser.add_argument("--repeats", type=int, choices=range(1, 6), default=3)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Request one actual Meta plan, then require interactive review before execution",
    )
    parser.add_argument(
        "--confirm-credits",
        action="store_true",
        help="Owner confirms available API credits and accepts the bounded call",
    )
    args = parser.parse_args()
    live_plan = None
    if args.live:
        if not args.confirm_credits:
            parser.error("Live calls require --confirm-credits; no call was made")
        os.environ["META_MODE"] = "live"
        spec = json.loads((ROOT / "samples/withdraw-openapi.json").read_text())
        live_plan = generate_plan(spec, DEFAULT_RULE)
        print(live_plan.model_dump_json(indent=2))
        if (
            input("Review every expected outcome. Type REVIEWED to allow local requests: ").strip()
            != "REVIEWED"
        ):
            raise SystemExit("Review not confirmed; no test requests were sent.")
    result = evaluate(args.repeats, live_plan)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["metrics"], indent=2))


if __name__ == "__main__":
    main()
