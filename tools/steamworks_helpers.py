"""Curated C ABI helper function metadata."""

from __future__ import annotations

import json
from pathlib import Path


HELPER_SPECS = Path(__file__).with_name("helper_specs.json")


def _load_specs() -> dict:
    return json.loads(HELPER_SPECS.read_text(encoding="utf-8"))


def _function_tuple(spec: list) -> tuple:
    if len(spec) != 3:
        raise ValueError(f"expected helper spec triple, got {spec!r}")
    return_type, name, params = spec
    return return_type, name, [tuple(param) for param in params]


def _function_list(specs: list[list]) -> list[tuple]:
    return [_function_tuple(spec) for spec in specs]


_SPECS = _load_specs()

C_MANUAL_FUNCTIONS = _function_list(_SPECS["manual_functions"])
C_HELPER_FUNCTIONS = _function_list(_SPECS["helper_functions"])
MANUAL_DISPATCH_FUNCTIONS = _function_list(_SPECS["manual_dispatch_functions"])
