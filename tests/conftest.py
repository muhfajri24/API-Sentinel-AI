"""All automated tests are offline by default; keys are never read from test env."""

import json
from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def offline_environment(monkeypatch):
    monkeypatch.setenv("META_MODE", "fixture")
    monkeypatch.setenv("MODEL_API_KEY", "")
    monkeypatch.setenv("META_BASE_URL", "https://api.meta.ai/v1")
    monkeypatch.setenv("ALLOWED_TEST_ORIGINS", "http://127.0.0.1:8101")


@pytest.fixture
def wallet_spec():
    return json.loads(
        (Path(__file__).resolve().parents[1] / "samples/withdraw-openapi.json").read_text()
    )
