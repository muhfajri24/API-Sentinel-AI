"""Portable, script-free HTML evidence built only from validated receipts."""

from html import escape
import json
from backend.app.models import ExecuteResponse


def render_report(value: dict) -> str:
    receipt = ExecuteResponse.model_validate(value)
    esc = lambda value: escape(str(value), quote=True)
    counts = {
        s: sum(r.status == s for r in receipt.results) for s in ("PASS", "FAIL", "ERROR", "NOT_RUN")
    }
    cards = []
    for result in receipt.results:
        cards.append(f"""<article><h2>{esc(result.status)} · {esc(result.case_id)}</h2>
<p>{esc(result.reason)}</p><p>Expected HTTP {result.expected_status} · Observed HTTP {esc(result.actual_status if result.actual_status is not None else "not available")}</p>
<div class="grid"><section><h3>Expected JSON subset</h3><pre>{esc(json.dumps(result.expected_json_subset, indent=2))}</pre></section>
<section><h3>Observed response</h3><pre>{esc(json.dumps(result.actual_body, indent=2))}</pre></section></div>
<p>Basis: {esc(result.expectation_basis)} · Proposed severity: {esc(result.severity)} · Latency: {esc(result.latency_ms)} ms</p>
<p>Reference: {esc(result.rule_reference)}</p><h3>Reproduction</h3><pre>{esc(json.dumps(result.reproduction, indent=2))}</pre>
<p>{esc(result.started_at)} → {esc(result.finished_at)}</p></article>""")
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>API Sentinel — {esc(receipt.run_id)}</title><style>
body{{font:16px/1.6 system-ui,sans-serif;max-width:1100px;margin:32px auto;padding:0 20px;color:#142638;background:#f4f7fb}}
article,header{{background:white;border:1px solid #cbd5e1;border-radius:12px;padding:24px;margin:20px 0}}
h1,h2,h3{{line-height:1.25}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf2f7;padding:16px;border-radius:8px}}p{{overflow-wrap:anywhere}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}.label{{font-weight:700;color:#704100}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}body{{margin:12px auto}}}}
@media print{{body{{background:white}}article{{break-inside:avoid}}}}</style>
<header><h1>API Sentinel AI</h1><p class="label">Case source: {esc(receipt.source)} · Model: {esc(receipt.model)}</p>
<p>{"OFFLINE FIXTURE — predefined cases; no AI inference." if receipt.source == "fixture" else "Case provenance is reported by the local controller; review expectations independently."}</p>
<p>Run: {esc(receipt.run_id)}<br>{esc(receipt.started_at)} → {esc(receipt.finished_at)}</p>
<p>{" · ".join(f"{s}: {n}" for s, n in counts.items())}</p>
<p>Local synthetic wallet. FAIL means an expectation differed from observation; it is not a security certification.</p></header>
{"".join(cards)}<footer>Standalone evidence snapshot. No scripts, external assets or network requests. Exported files can be edited; this is not a cryptographically signed audit.</footer></html>"""
