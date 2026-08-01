"""Python bindings for the generated Steamworks SWIG wrapper."""

from __future__ import annotations

try:
    from . import steamworks as _raw
except ImportError as exc:
    raise ImportError(
        "The generated Steamworks extension is not available. "
        "Install this project with `pip install .` from the repository root."
    ) from exc

try:
    from .grouped import *  # noqa: F401,F403
except ImportError:
    pass


def parse_callback_payload(data: str) -> dict[str, str]:
    payload: dict[str, str] = {}
    if not data:
        return payload
    for field in data.split("\t"):
        key, separator, value = field.partition("=")
        if not separator or not key:
            continue
        payload[key] = _unescape_callback_payload_value(value)
    return payload


def _unescape_callback_payload_value(value: str) -> str:
    if "\\" not in value:
        return value

    result = []
    escaped = False
    for ch in value:
        if escaped:
            if ch == "t":
                result.append("\t")
            elif ch == "n":
                result.append("\n")
            elif ch == "r":
                result.append("\r")
            elif ch == "\\":
                result.append("\\")
            else:
                result.append("\\")
                result.append(ch)
            escaped = False
            continue

        if ch == "\\":
            escaped = True
            continue
        result.append(ch)

    if escaped:
        result.append("\\")
    return "".join(result)
