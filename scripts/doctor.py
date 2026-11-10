"""Offline setup diagnosis. Never prints credentials or sends model requests."""

import importlib.metadata
import json
import socket
import sys
from pathlib import Path
from backend.app.generator import DEFAULT_RULE, generate_plan
from backend.app.models import utc_now
from .local_services import ROOT
import os


def inspect_setup() -> dict:
    checks = []
    checks.append(
        {
            "name": "python",
            "status": "PASS" if sys.version_info >= (3, 11) else "FAIL",
            "detail": sys.version.split()[0],
        }
    )
    for name in (
        "fastapi",
        "uvicorn",
        "pydantic",
        "httpx",
        "python-dotenv",
        "openai",
        "streamlit",
        "jsonschema",
    ):
        try:
            version = importlib.metadata.version(name)
            checks.append({"name": name, "status": "PASS", "detail": version})
        except importlib.metadata.PackageNotFoundError:
            checks.append(
                {
                    "name": name,
                    "status": "FAIL",
                    "detail": "Install requirements.txt in the active environment",
                }
            )
    for port in (8100, 8101, 8501):
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
                state = "PASS"
            except OSError:
                state = "BLOCKED"
        checks.append(
            {
                "name": f"port_{port}",
                "status": state,
                "detail": "Available"
                if state == "PASS"
                else "Occupied; stop its owner or use another session. No process was killed.",
            }
        )
    previous = os.environ.get("META_MODE")
    try:
        os.environ["META_MODE"] = "fixture"
        plan = generate_plan(
            json.loads((ROOT / "samples/withdraw-openapi.json").read_text()), DEFAULT_RULE
        )
        checks.append(
            {
                "name": "fixture_plan",
                "status": "PASS",
                "detail": f"{len(plan.cases)} validated predefined cases; no inference",
            }
        )
    finally:
        if previous is None:
            os.environ.pop("META_MODE", None)
        else:
            os.environ["META_MODE"] = previous
    return {
        "checked_at": utc_now(),
        "status": "PASS" if all(c["status"] == "PASS" for c in checks) else "BLOCKED",
        "meta_inference": "NOT_RUN",
        "checks": checks,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = inspect_setup()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 2)


if __name__ == "__main__":
    main()
