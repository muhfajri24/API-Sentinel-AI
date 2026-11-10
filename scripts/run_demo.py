"""One-command local fixture launch, or real-socket offline acceptance (--check)."""

import argparse
import json
import os
from pathlib import Path
import time
import httpx
from .local_services import local_services, ROOT


def check(variant="buggy"):
    from streamlit.testing.v1 import AppTest
    from backend.app.models import utc_now

    # AppTest runs the actual UI code; its HTTP requests use the real child controller/demo sockets.
    os.environ["META_MODE"] = "fixture"
    os.environ["CONTROLLER_URL"] = "http://127.0.0.1:8100"
    os.environ["DEMO_API_URL"] = "http://127.0.0.1:8101"
    at = AppTest.from_file(str(ROOT / "ui/streamlit_app.py")).run(timeout=20)

    def widget(items, label):
        return next(x for x in items if x.label == label)

    widget(at.button, "1. Generate test plan").click().run(timeout=20)
    assert not at.exception and at.session_state["plan"]["source"] == "fixture"
    assert widget(at.button, "2. Execute local tests").disabled
    widget(
        at.checkbox, "I reviewed the expected outcomes against the OpenAPI and business rule."
    ).check().run()
    widget(
        at.checkbox, "I own/control the local test environment and authorize these requests."
    ).check().run()
    widget(at.button, "2. Execute local tests").click().run(timeout=20)
    assert not at.exception
    receipt = at.session_state["receipt"]
    assert [r["status"] for r in receipt["results"]] == (
        ["PASS", "FAIL"] if variant == "buggy" else ["PASS", "PASS"]
    )
    with httpx.Client(timeout=3, trust_env=False) as client:
        health = client.get("http://127.0.0.1:8100/health").json()
        ui_status = client.get("http://127.0.0.1:8501/").status_code
    result = {
        "checked_at": utc_now(),
        "status": "PASS",
        "target_variant": variant,
        "transport": "actual loopback HTTP; UI widget flow via Streamlit AppTest",
        "meta_inference": "NOT RUN",
        "controller_health": health,
        "ui_http_status": ui_status,
        "receipt": receipt,
    }
    (ROOT / "evidence").mkdir(exist_ok=True)
    (
        ROOT
        / ("evidence/local_smoke.json" if variant == "buggy" else "evidence/corrected_smoke.json")
    ).write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": "PASS",
                "verdicts": [r["status"] for r in receipt["results"]],
                "source": receipt["source"],
                "meta_inference": "NOT RUN",
                "evidence": "evidence/local_smoke.json"
                if variant == "buggy"
                else "evidence/corrected_smoke.json",
            },
            indent=2,
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--variant", choices=("buggy", "corrected"), default="buggy")
    args = parser.parse_args()
    with local_services(variant=args.variant, controller=True, ui=True) as processes:
        if args.check:
            check(args.variant)
            return
        print(
            f"Fixture demo ({args.variant} target): http://127.0.0.1:8501 | controller 8100 | synthetic target 8101. Ctrl+C stops owned services.",
            flush=True,
        )
        while True:
            if any(process.poll() is not None for process in processes):
                raise RuntimeError("A local service stopped; all owned services will be stopped.")
            time.sleep(0.5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
