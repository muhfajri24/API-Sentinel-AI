"""Offline checks for the documented local bootstrap path."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from backend.app.main import app


def test_health_reports_fixture_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("META_MODE", "fixture")
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "fixture"}


def test_ui_boots_with_explicit_fixture_label(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("META_MODE", "fixture")
    script = Path(__file__).resolve().parents[1] / "ui" / "streamlit_app.py"
    ui = AppTest.from_file(str(script)).run(timeout=15)
    assert not ui.exception
    assert any("OFFLINE FIXTURE MODE" in item.value for item in ui.warning)
    assert any("no Meta inference is running" in item.value for item in ui.warning)
