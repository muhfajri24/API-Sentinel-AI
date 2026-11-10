"""Bounded JSON and synthetic-data privacy helpers; never log rejected values."""

import json
import math
import re
from typing import Any

SENSITIVE = re.compile(
    r"password|passwd|secret|token|authorization|cookie|api[_-]?key|private[_-]?key|credit[_-]?card",
    re.I,
)
SECRET_TEXT = re.compile(
    r"(?:\bBearer\s+\S{8,}|\bsk-[A-Za-z0-9_-]{12,}|\b(?:api[_-]?key|password|secret|token)\s*[:=]\s*\S{6,})",
    re.I,
)


def bounded_json(value: Any, max_bytes: int, max_depth: int = 32) -> Any:
    nodes = 0

    def visit(item: Any, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if depth > max_depth or nodes > 10000:
            raise ValueError("JSON exceeds structural limits")
        if isinstance(item, dict):
            if any(not isinstance(k, str) for k in item):
                raise ValueError("JSON object keys must be strings")
            for child in item.values():
                visit(child, depth + 1)
        elif isinstance(item, list):
            for child in item:
                visit(child, depth + 1)
        elif item is not None and type(item) not in (str, int, float, bool):
            raise ValueError("Only JSON values are permitted")
        elif isinstance(item, float) and not math.isfinite(item):
            raise ValueError("Nonfinite numbers are not JSON values")

    visit(value, 0)
    if len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode()) > max_bytes:
        raise ValueError("JSON exceeds byte limit")
    return value


def has_sensitive_data(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            (SENSITIVE.search(key) and child not in (None, "")) or has_sensitive_data(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(has_sensitive_data(child) for child in value)
    return isinstance(value, str) and bool(SECRET_TEXT.search(value))


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if SENSITIVE.search(key) else redact(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [redact(child) for child in value]
    return SECRET_TEXT.sub("[REDACTED]", value) if isinstance(value, str) else value


def reject_spec_secrets(value: Any) -> None:
    # Schema property names are definitions; only concrete example/default payloads are inspected.
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"example", "examples", "default"} and has_sensitive_data(child):
                raise ValueError("Remove sensitive example/default data before model use")
            if isinstance(child, str) and SECRET_TEXT.search(child):
                raise ValueError("Remove secret-like text before model use")
            reject_spec_secrets(child)
    elif isinstance(value, list):
        for child in value:
            reject_spec_secrets(child)
