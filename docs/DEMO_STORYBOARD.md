# 90-second Judge Demo — evidence over buzzwords

- **0–10 s — Problem**: "Your API returned 200 OK. But did it follow the business rule?"
- **10–25 s — Setup**: show fake wallet demo, `/withdraw`, synthetic balance 100, OpenAPI JSON.
- **25–40 s — Intelligence**: enter rule "withdrawals above balance must be rejected"; press Generate. Show **Meta LIVE** badge only if real API call succeeded. Point at overdraft test case.
- **40–60 s — Execution**: press Run tests (owner-authorized sandbox) and observe real HTTP request/response.
- **60–75 s — Evidence**: expected 422, got 200; expected `approved=false`, got `approved=true`. Explain as a violation of demo business rule.
- **75–90 s — Why it matters**: test design driven by business intent + reproducible execution. Acknowledge MVP only supports controlled local sandbox, not production scanning.

Side-by-side baseline: happy path passes while business-rule test reveals seeded bug. This is an illustrative example, **not a controlled scientific superiority claim**. Do not use fixture clips to assert live Meta performance.
