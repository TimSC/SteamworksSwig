#!/usr/bin/env python3
"""Generate friendly Go wrappers from the shared Steamworks C ABI model."""

from __future__ import annotations

import argparse
from pathlib import Path

from generator_io import load_json, write_generated_text
from steamworks_model import (
    disambiguate_names,
    friendly_name,
    method_params,
    method_return_type,
    model_methods,
    raw_c_name,
)
from steamworks_types import split_words


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "generated" / "steamworks_c_api_model.json"
DEFAULT_OUTPUT = ROOT / "go" / "steamworks" / "generated.go"
RAW_IMPORT = "github.com/TimSC/SteamworksSwig/go/steamworks/raw"

GO_INITIALISMS = {
    "API",
    "DLC",
    "HTML",
    "HTTP",
    "IP",
    "UGC",
    "URL",
    "VR",
}

HAND_WRITTEN_METHODS = {
    "Global/static": {
        "CallbackDispatchModeAutomatic",
        "CallbackDispatchModeManual",
        "CallbackDispatchModeUninitialized",
        "ClearHelperState",
        "GetHSteamPipe",
        "GetHSteamUser",
        "GetLastInitError",
        "GetLastInitResult",
        "Init",
        "InitEx",
        "IsSteamRunning",
        "RunCallbacks",
        "Shutdown",
    },
    "ManualDispatch": {
        "CallbackIsAPICallCompleted",
        "FreeLastCallback",
        "GetAPICallResult",
        "GetAPICallResultData",
        "GetAPICallResultFailed",
        "GetCallbackData",
        "GetCallbackID",
        "GetCallbackSize",
        "GetCallbackSteamUser",
        "GetCompletedAPICall",
        "GetCompletedCallbackID",
        "GetCompletedCallbackSize",
        "GetNextCallback",
        "Init",
        "RunFrame",
    },
}

GO_KEYWORDS = {
    "break",
    "default",
    "func",
    "interface",
    "select",
    "case",
    "defer",
    "go",
    "map",
    "struct",
    "chan",
    "else",
    "goto",
    "package",
    "switch",
    "const",
    "fallthrough",
    "if",
    "range",
    "type",
    "continue",
    "for",
    "import",
    "return",
    "var",
}


def go_identifier(value: str) -> str:
    if value.startswith("P2P"):
        return "P2P" + go_identifier(value[len("P2P"):])
    words = split_words(value)
    if not words:
        return value
    converted = []
    index = 0
    while index < len(words):
        if (
            index + 2 < len(words)
            and words[index].upper() == "P"
            and words[index + 1] == "2"
            and words[index + 2].upper() == "P"
        ):
            converted.append("P2P")
            index += 3
            continue
        word = words[index]
        upper = word.upper()
        if upper in GO_INITIALISMS:
            converted.append(upper)
        else:
            converted.append(word[:1].upper() + word[1:])
        index += 1
    return "".join(converted)


def receiver_type_name(interface_name: str) -> str:
    if interface_name.startswith("HTML"):
        return "html" + interface_name[len("HTML"):] + "API"
    if interface_name.startswith("HTTP"):
        return "http" + interface_name[len("HTTP"):] + "API"
    return interface_name[:1].lower() + interface_name[1:] + "API"


def wrapper_method_name(raw_method_name: str) -> str:
    if (
        raw_method_name.startswith("B")
        and len(raw_method_name) > 1
        and raw_method_name[1].isupper()
    ):
        raw_method_name = raw_method_name[1:]
    return go_identifier(raw_method_name)


def helper_method_name(interface_name: str, c_name: str, raw_method_name: str) -> str:
    name = raw_method_name
    if name.startswith("Steam_"):
        name = name[len("Steam_"):]
    if interface_name and interface_name != "Global/static":
        prefix = interface_name + "_"
        if name.startswith(prefix):
            name = name[len(prefix):]
    if not name:
        name = c_name.removeprefix("SWS_Steam_")
    return go_identifier(name)


def go_type(c_type: str) -> str:
    return {
        "bool": "bool",
        "char": "byte",
        "const char *": "string",
        "const uint8_t *": "[]byte",
        "double": "float64",
        "float": "float32",
        "int8_t": "int8",
        "uint8_t": "byte",
        "int16_t": "int16",
        "uint16_t": "uint16",
        "int32_t": "int",
        "uint32_t": "uint",
        "int64_t": "int64",
        "uint64_t": "uint64",
        "size_t": "int64",
        "SWS_String": "string",
        "SWS_StringList": "[]string",
        "SWS_Bytes": "[]byte",
        "SWS_BytesList": "[][]byte",
    }[c_type]


def go_param_name(name: str) -> str:
    if name in GO_KEYWORDS:
        return name + "Value"
    return name


def go_args(params: list[dict]) -> str:
    args = []
    index = 0
    while index < len(params):
        param = params[index]
        if (
            param["c_type"] == "const uint8_t *"
            and index + 1 < len(params)
            and params[index + 1]["c_type"] == "size_t"
            and params[index + 1]["name"] == f'{param["name"]}Size'
        ):
            args.append(f'{go_param_name(param["name"])} []byte')
            index += 2
            continue
        args.append(f'{go_param_name(param["name"])} {go_type(param["c_type"])}')
        index += 1
    return ", ".join(args)


def go_arg_names(params: list[dict]) -> str:
    args = []
    index = 0
    while index < len(params):
        param = params[index]
        name = go_param_name(param["name"])
        if (
            param["c_type"] == "const uint8_t *"
            and index + 1 < len(params)
            and params[index + 1]["c_type"] == "size_t"
            and params[index + 1]["name"] == f'{param["name"]}Size'
        ):
            args.extend([f"rawBytePtr({name})", f"int64(len({name}))"])
            index += 2
            continue
        args.append(name)
        index += 1
    return ", ".join(args)


def generate(model: dict) -> str:
    interfaces: dict[str, list[dict[str, str | None]]] = {}
    module_functions: list[dict[str, str | None]] = []
    callback_methods = []
    candidates = []
    for method in model_methods(model):
        c_name = raw_c_name(method)
        if c_name.startswith("SWS_Steam_ManualDispatch_CallbackID"):
            callback_name = c_name.removeprefix("SWS_Steam_ManualDispatch_CallbackID")
            callback_methods.append((go_identifier(callback_name), c_name))
            continue

        interface = method.get("interface")
        raw_method_name = friendly_name(method)
        if not interface or not raw_method_name:
            continue
        if method.get("source") == "sdk":
            classname = method.get("classname")
            if not classname or not classname.startswith("ISteam"):
                continue
            receiver = go_identifier(classname.removeprefix("ISteam"))
            method_name = wrapper_method_name(raw_method_name)
            sdk_flat_name = method.get("sdk_flat_name") or c_name
            c_method_suffix = sdk_flat_name.removeprefix(f"SteamAPI_{classname}_")
        else:
            receiver = interface
            method_name = helper_method_name(interface, c_name, raw_method_name)
            c_method_suffix = c_name.removeprefix("SWS_Steam_")
        if method_name in HAND_WRITTEN_METHODS.get(receiver, set()):
            continue
        candidates.append((receiver, method_name, c_method_suffix, method))

    named_candidates = disambiguate_names(
        candidates,
        key=lambda candidate: candidate[0],
        name=lambda candidate: candidate[1],
        fallback_name=lambda candidate: wrapper_method_name(candidate[2]),
    )

    for (receiver, _, _, method), method_name in named_candidates:
        return_type = method_return_type(method)
        item = {
            "raw_name": raw_c_name(method),
            "method_name": method_name,
            "args": go_args(method_params(method)),
            "arg_names": go_arg_names(method_params(method)),
            "return_type": None if return_type == "void" else go_type(return_type),
                "convert_return": {
                    "SWS_String": "takeRawString",
                    "SWS_StringList": "takeRawStringList",
                    "SWS_Bytes": "takeRawBytes",
                    "SWS_BytesList": "takeRawBytesList",
                }.get(return_type),
        }
        if receiver == "Global/static":
            module_functions.append(item)
        else:
            interfaces.setdefault(receiver, []).append(item)

    lines = [
        "package steamworks",
        "",
        "// Code generated by tools/generate_go.py; DO NOT EDIT.",
        "",
        "import (",
        f'\t"{RAW_IMPORT}"',
        '\t"unsafe"',
        ")",
        "",
        "func rawBytePtr(data []byte) *byte {",
        "\tif len(data) == 0 {",
        "\t\treturn nil",
        "\t}",
        "\treturn (*byte)(unsafe.Pointer(&data[0]))",
        "}",
        "",
    ]
    for receiver in sorted(interfaces):
        receiver_type = receiver_type_name(receiver)
        if receiver not in HAND_WRITTEN_METHODS:
            lines.extend(
                [
                    f"type {receiver_type} struct{{}}",
                    "",
                    f"var {receiver} {receiver_type}",
                    "",
                ]
            )
        for method in sorted(interfaces[receiver], key=lambda item: str(item["method_name"])):
            args = method["args"]
            return_type = method["return_type"]
            arg_names = str(method["arg_names"])
            raw_call = f'raw.{method["raw_name"]}({arg_names})'
            signature_return = f" {return_type}" if return_type else ""
            lines.append(f'func ({receiver_type}) {method["method_name"]}({args}){signature_return} {{')
            if return_type:
                if method["convert_return"]:
                    lines.append(f'\treturn {method["convert_return"]}({raw_call})')
                else:
                    lines.append(f"\treturn {raw_call}")
            else:
                lines.append(f"\t{raw_call}")
            lines.extend(["}", ""])

    for method in sorted(module_functions, key=lambda item: str(item["method_name"])):
        args = method["args"]
        return_type = method["return_type"]
        arg_names = str(method["arg_names"])
        raw_call = f'raw.{method["raw_name"]}({arg_names})'
        signature_return = f" {return_type}" if return_type else ""
        lines.append(f'func {method["method_name"]}({args}){signature_return} {{')
        if return_type:
            if method["convert_return"]:
                lines.append(f'\treturn {method["convert_return"]}({raw_call})')
            else:
                lines.append(f"\treturn {raw_call}")
        else:
            lines.append(f"\t{raw_call}")
        lines.extend(["}", ""])

    for callback_name, raw_name in sorted(callback_methods):
        lines.extend(
            [
                f"func CallbackID{callback_name}() CallbackID {{",
                f"\treturn CallbackID(raw.{raw_name}())",
                "}",
                "",
            ]
        )

    return "\n".join(lines)


def write_go_wrappers(model_path: Path, output_path: Path) -> None:
    write_generated_text(output_path, generate(load_json(model_path)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="Path to steamworks_c_api_model.json")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Go wrapper output path")
    args = parser.parse_args()

    write_go_wrappers(Path(args.model), Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
