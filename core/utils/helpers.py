"""General helper utilities for IIMP.

Keep functions here pure (no side effects, no Qt imports) so they
remain easily testable without a display.
"""
from __future__ import annotations

import json
import re
from typing import Any


def parse_version(version_str: str) -> tuple[int, ...]:
    """Parse a semantic version string into a comparable tuple.

    >>> parse_version("1.2.3")
    (1, 2, 3)
    """
    parts = re.split(r"[.\-]", version_str)
    try:
        result = tuple(int(p) for p in parts if p)
    except ValueError as exc:
        raise ValueError(f"Cannot parse version '{version_str}'") from exc
    if not result:
        raise ValueError(f"Cannot parse version '{version_str}'")
    return result


def version_satisfies(current: str, minimum: str) -> bool:
    """Return True if *current* >= *minimum* (semantic comparison).

    >>> version_satisfies("1.2.0", "1.0.0")
    True
    >>> version_satisfies("0.9.0", "1.0.0")
    False
    """
    try:
        return parse_version(current) >= parse_version(minimum)
    except ValueError:
        return False


def safe_json_loads(text: str, fallback: Any = None) -> Any:
    """Deserialize JSON without raising; return *fallback* on error."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return fallback


def safe_json_dumps(obj: Any, fallback: str = "{}") -> str:
    """Serialize to JSON without raising; return *fallback* on error."""
    try:
        return json.dumps(obj, ensure_ascii=False)
    except (TypeError, ValueError):
        return fallback


def truncate(text: str, max_length: int = 80) -> str:
    """Return *text* truncated to *max_length* chars with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 1] + "…"
