import json
from pathlib import Path
from ui.report import render_report
from backend.app.models import ExecuteResponse
from pydantic import ValidationError
import pytest


def receipt():
    return json.loads(
        (Path(__file__).resolve().parents[1] / "evidence/local_smoke.json").read_text()
    )["receipt"]


def test_portable_report_preserves_observations_and_escapes_untrusted_text():
    value = receipt()
    value["results"][1]["reason"] = '<script>alert("unsafe")</script>'
    html = render_report(value)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "OFFLINE FIXTURE" in html and "no AI inference" in html
    assert "Expected HTTP 422" in html and "Observed HTTP 200" in html
    assert "default-src" in html and "<script src=" not in html
    assert ExecuteResponse.model_validate(value).source == "fixture"


def test_invalid_evidence_is_not_exported_as_a_report():
    value = receipt()
    value["results"][0]["status"] = "FABRICATED"
    with pytest.raises(ValidationError):
        render_report(value)
