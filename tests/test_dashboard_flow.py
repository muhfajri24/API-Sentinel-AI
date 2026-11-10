"""Full Streamlit widget flow against real controller/demo ASGI handlers, offline."""

from pathlib import Path
import httpx
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest
from backend.app import main as controller
from backend.app.demo_api import create_demo_app
from backend.app.runner import execute_tests
from ui.state import synchronize_inputs
import ui.client

SCRIPT = Path(__file__).resolve().parents[1] / "ui/streamlit_app.py"


def widget(items, label):
    return next(item for item in items if item.label == label)


def prepare(monkeypatch):
    client = TestClient(controller.app)

    async def execute_local(request):
        return await execute_tests(
            request, transport=httpx.ASGITransport(app=create_demo_app(True))
        )

    monkeypatch.setattr(controller, "execute_tests", execute_local)

    def api(_origin, path, payload=None):
        response = client.get(path) if payload is None else client.post(path, json=payload)
        if response.status_code >= 400:
            raise ui.client.ControllerError("Local request did not succeed.")
        return response.json()

    monkeypatch.setattr(ui.client, "request_api", api)
    return AppTest.from_file(str(SCRIPT)).run(timeout=15)


def test_complete_review_consent_execution_and_export_flow(monkeypatch):
    at = prepare(monkeypatch)
    widget(at.button, "1. Generate test plan").click().run(timeout=15)
    assert not at.exception and at.session_state["plan"]["source"] == "fixture"
    assert widget(at.button, "2. Execute local tests").disabled
    widget(
        at.checkbox, "I reviewed the expected outcomes against the OpenAPI and business rule."
    ).check().run()
    assert widget(at.button, "2. Execute local tests").disabled
    widget(
        at.checkbox, "I own/control the local test environment and authorize these requests."
    ).check().run()
    assert not widget(at.button, "2. Execute local tests").disabled
    widget(at.button, "2. Execute local tests").click().run(timeout=15)
    assert not at.exception
    receipt = at.session_state["receipt"]
    assert receipt["source"] == "fixture" and [r["status"] for r in receipt["results"]] == [
        "PASS",
        "FAIL",
    ]
    assert {m.label: m.value for m in at.metric} == {
        "PASS": "1",
        "FAIL": "1",
        "ERROR": "0",
        "NOT_RUN": "0",
    }
    assert len(at.get("download_button")) == 2
    widget(at.text_area, "Business rule").set_value("A different unsupported rule").run()
    assert "plan" not in at.session_state and "receipt" not in at.session_state
    assert not any(b.label == "2. Execute local tests" for b in at.button)


def test_failed_generation_cannot_leave_old_executable_plan(monkeypatch):
    at = prepare(monkeypatch)
    widget(at.button, "1. Generate test plan").click().run(timeout=15)
    assert at.session_state["plan"]

    def broken(*_args, **_kwargs):
        raise ui.client.ControllerError("The model is unavailable.")

    monkeypatch.setattr(ui.client, "request_api", broken)
    widget(at.button, "1. Generate test plan").click().run(timeout=15)
    assert not at.exception and "plan" not in at.session_state
    assert any("unavailable" in e.value for e in at.error)


def test_invalid_json_clears_old_plan_before_render(monkeypatch):
    at = prepare(monkeypatch)
    widget(at.button, "1. Generate test plan").click().run(timeout=15)
    widget(at.text_area, "OpenAPI JSON").set_value("{invalid").run()
    assert "plan" not in at.session_state
    assert any("valid JSON" in e.value for e in at.error)


def test_input_changes_clear_consent_and_receipts():
    state = {
        "input_fingerprint": "old",
        "plan": {},
        "receipt": {},
        "authorized": True,
        "reviewed": True,
    }
    synchronize_inputs(state, "new")
    assert state == {"input_fingerprint": "new"}


def test_mismatched_controller_mode_cannot_trigger_generation(monkeypatch):
    at = prepare(monkeypatch)
    calls = []

    def api(_origin, path, payload=None):
        calls.append(path)
        assert path == "/health"
        return {"status": "ok", "mode": "live"}

    monkeypatch.setattr(ui.client, "request_api", api)
    widget(at.button, "1. Generate test plan").click().run(timeout=15)
    assert calls == ["/health"] and "plan" not in at.session_state
    assert any("modes differ" in e.value for e in at.error)
