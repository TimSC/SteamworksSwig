#!/usr/bin/env python3
"""Generate grouped Python wrappers from the shared C ABI model."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from generator_io import load_json, write_generated_text
from steamworks_model import (
    disambiguate_names,
    friendly_name,
    helper_name,
    method_params,
    model_methods,
    raw_c_name,
)
from steamworks_types import python_snake_name, split_words

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "generated" / "steamworks_c_api_model.json"
INPUT_RESULT_TYPES = {
    "Steam_Input_GetDigitalActionData": ("DigitalActionData", "active pressed"),
    "Steam_Input_GetAnalogActionData": ("AnalogActionData", "active mode x y"),
}
DEFAULT_OUTPUT = ROOT / "python" / "steamworks" / "grouped.py"


def class_name(interface: str) -> str:
    return "_" + "".join(word[:1].upper() + word[1:] for word in split_words(interface)) + "API"


def instance_name(interface: str) -> str:
    if interface == "Global/static":
        return ""
    return python_snake_name(interface)


def param_name(value: str) -> str:
    result = python_snake_name(value)
    if not result:
        result = "arg"
    return result


def grouped_helper_method_name(interface: str, model_helper_name: str, raw_c_name: str, *, drop_get: bool = True) -> str:
    name = model_helper_name or raw_c_name.removeprefix("SWS_")
    if name.startswith("Steam_"):
        name = name[len("Steam_"):]
    if interface and interface != "Global/static":
        prefix = interface + "_"
        if name.startswith(prefix):
            name = name[len(prefix):]
    return python_snake_name(name, drop_get=drop_get)


def method_candidates(model: dict) -> list[tuple[str, str, str, dict]]:
    candidates = []
    for method in model_methods(model):
        interface = method.get("interface")
        c_name = raw_c_name(method)
        if not interface or not c_name:
            continue
        if method.get("source") == "sdk":
            method_name = friendly_name(method)
            if not method_name:
                continue
            grouped_name = python_snake_name(method_name)
        else:
            grouped_name = grouped_helper_method_name(interface, helper_name(method), c_name)
        candidates.append((interface, grouped_name, c_name, method))
    return candidates


def python_collision_name(candidate: tuple[str, str, str, dict]) -> str:
    interface, _, raw_c_name, method = candidate
    if method.get("source") == "sdk":
        sdk_flat_name = method.get("sdk_flat_name") or raw_c_name
        prefix = f"SteamAPI_ISteam{interface}_"
        return python_snake_name(sdk_flat_name.removeprefix(prefix), drop_get=False)
    return grouped_helper_method_name(
        interface,
        helper_name(method),
        raw_c_name,
        drop_get=False,
    )


def python_params_and_args(method: dict) -> tuple[list[str], list[str]]:
    params = []
    arg_names = []
    seen_params: Counter[str] = Counter()
    raw_params = method_params(method)
    if method.get("language_support") == "python_only":
        # SWIG supplies storage for the native output parameters.
        raw_params = [
            param for param in raw_params
            if not param["name"].endswith("Out") and param["name"] != "capacity"
        ]
    index = 0
    while index < len(raw_params):
        param = raw_params[index]
        name = param_name(param.get("name", "arg"))
        if (
            param.get("c_type") == "const uint8_t *"
            and index + 1 < len(raw_params)
            and raw_params[index + 1].get("c_type") == "size_t"
            and raw_params[index + 1].get("name") == f'{param.get("name")}Size'
        ):
            seen_params[name] += 1
            if seen_params[name] > 1:
                name = f"{name}_{seen_params[name]}"
            params.append(name)
            arg_names.append(name)
            index += 2
            continue

        seen_params[name] += 1
        if seen_params[name] > 1:
            name = f"{name}_{seen_params[name]}"
        params.append(name)
        arg_names.append(name)
        index += 1
    return params, arg_names


def generate(model: dict) -> str:
    candidates = method_candidates(model)
    interfaces: dict[str, list[dict]] = {}
    module_functions: list[dict] = []

    result_types = {}
    named_candidates = disambiguate_names(
        candidates,
        key=lambda candidate: candidate[0],
        name=lambda candidate: candidate[1],
        fallback_name=lambda candidate: python_collision_name(candidate),
    )

    for (interface, _, raw_c_name, method), grouped_name in named_candidates:
        params, arg_names = python_params_and_args(method)

        result_type = INPUT_RESULT_TYPES.get(helper_name(method))
        if result_type:
            name, fields = result_type
            result_types[name] = fields

        interfaces.setdefault(interface, []).append(
            {
                "name": grouped_name,
                "raw_c_name": raw_c_name,
                "params": params,
                "arg_names": arg_names,
                "result_type": result_type,
            }
        )

    lines = [
        '"""Grouped Python wrappers for the generated Steamworks module."""',
        "",
        "# Code generated by tools/generate_python.py; DO NOT EDIT.",
        "",
        "from . import steamworks as _raw",
        "from . import _events",
        "",
    ]

    enums = model.get("python_enums", {})
    if enums:
        lines.extend(["from enum import IntEnum as _IntEnum", ""])
        for name, members in enums.items():
            # The functional form also supports SDK names such as EResult["None"].
            lines.extend([f"{name} = _IntEnum({name!r}, ["])
            for member in members:
                lines.append(f"    {tuple(member)!r},")
            lines.extend(["])", ""])
    exported = [*enums, *result_types]
    if result_types:
        lines.extend(["from collections import namedtuple as _namedtuple", ""])
        for name, fields in result_types.items():
            lines.append(f"{name} = _namedtuple({name!r}, {fields!r})")
        lines.append("")
    for interface in sorted(interfaces):
        if interface == "Global/static":
            module_functions.extend(interfaces[interface])
            continue
        cls = class_name(interface)
        instance = instance_name(interface)
        exported.append(instance)
        lines.extend([f"class {cls}:", ""])
        for item in sorted(interfaces[interface], key=lambda value: value["name"]):
            params = ", ".join(["self"] + item["params"])
            args = ", ".join(item["arg_names"])
            call = f'_raw.{item["raw_c_name"]}({args})' if args else f'_raw.{item["raw_c_name"]}()'
            if item["result_type"]:
                result_name, _ = item["result_type"]
                call = f"{result_name}(*{call})"
            lines.append(f"    def {item['name']}({params}):")
            lines.append(f"        return {call}")
            lines.append("")
        if interface == "NetworkingSockets":
            lines.extend([
                "    def connection_real_time_status(self, connection):",
                "        return _events.connection_real_time_status(self.connection_real_time_status_string(connection))",
                "",
                "    def poll_connection_status_changed(self, max_events):",
                "        return tuple(_events.connection_status_changed(payload)",
                "                     for payload in self.poll_connection_status_changed_strings(max_events))",
                "",
            ])
        lines.extend([f"{instance} = {cls}()", ""])

    for item in sorted(module_functions, key=lambda value: value["name"]):
        exported.append(item["name"])
        params = ", ".join(item["params"])
        args = ", ".join(item["arg_names"])
        call = f'_raw.{item["raw_c_name"]}({args})' if args else f'_raw.{item["raw_c_name"]}()'
        lines.append(f"def {item['name']}({params}):")
        lines.append(f"    return {call}")
        lines.append("")

    lines.append(f"__all__ = {exported!r}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="Path to steamworks_c_api_model.json")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Python output path")
    args = parser.parse_args()

    write_generated_text(Path(args.output), generate(load_json(Path(args.model))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
