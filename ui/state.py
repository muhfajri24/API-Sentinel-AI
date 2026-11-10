"""Stale-plan invalidation is independent of Streamlit's rendering lifecycle."""

import hashlib
import json


def input_fingerprint(spec_text, rule, controller, mode):
    return hashlib.sha256(
        json.dumps([spec_text, rule, controller, mode], ensure_ascii=False).encode()
    ).hexdigest()


def clear_execution(state):
    for key in ("plan", "receipt", "authorized", "reviewed"):
        state.pop(key, None)


def synchronize_inputs(state, fingerprint):
    if state.get("input_fingerprint") != fingerprint:
        clear_execution(state)
        state["input_fingerprint"] = fingerprint
