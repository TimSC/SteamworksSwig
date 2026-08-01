#!/usr/bin/env python3
"""Generate helpers for simple Steamworks output-parameter APIs.

The command-line report lists all conservative candidates. The build consumes
only the promoted allowlist so new helpers are deliberate, reviewable changes.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from generator_io import load_json, write_text
from steamworks_discovery import declared_identifiers, interface_accessor, interface_name, wrapper_name
from steamworks_types import api_enum_names, api_typedef_map, normalize_type, resolve_c_type, safe_name


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "generated" / "output_helpers"

PROMOTED_OUTPUT_HELPERS = {
    "Steam_Apps_IsTimedTrialString",
    "Steam_Controller_GetControllerBindingRevisionString",
    "Steam_Friends_GetClanActivityCountsString",
    "Steam_HTTP_GetHTTPDownloadProgressPctString",
    "Steam_HTTP_GetHTTPRequestWasTimedOutString",
    "Steam_HTTP_GetHTTPResponseBodySizeString",
    "Steam_Input_GetDeviceBindingRevisionString",
    "Steam_Matchmaking_GetFavoriteGameString",
    "Steam_Matchmaking_GetLobbyDataByIndexString",
    "Steam_Networking_IsDataAvailableOnSocketString",
    "Steam_Networking_IsDataAvailableString",
    "Steam_Networking_IsP2PPacketAvailableString",
    "Steam_Parties_GetNumAvailableBeaconLocationsString",
    "Steam_RemotePlay_GetSessionClientResolutionString",
    "Steam_RemoteStorage_GetQuotaString",
    "Steam_RemoteStorage_GetUGCDownloadProgressString",
    "Steam_UGC_GetQueryUGCKeyValueTagString",
    "Steam_UGC_GetQueryUGCStatisticString",
    "Steam_UserStats_GetMostAchievedAchievementInfoString",
    "Steam_UserStats_GetNextMostAchievedAchievementInfoString",
    "Steam_Utils_IsAPICallCompletedString",
}

HELPER_NAME_OVERRIDES = {
    ("ISteamRemotePlay", "BGetSessionClientResolution"): "Steam_RemotePlay_GetSessionClientResolutionString",
}

INTEGER_SIZE_TYPES = {"int", "uint32", "uint32_t", "int32", "int32_t", "size_t"}
STRING_BUFFER_HINTS = ("cch", "cub", "cb", "size", "len", "length")
ARRAY_OR_BUFFER_NAME_HINTS = (
    "handlesout",
    "originsout",
    "pvec",
    "parray",
    "pdata",
    "pbuffer",
    "poutbuffer",
    "pub",
    "pv",
    "pauth",
    "pdest",
    "list",
    "plist",
    "pbgra",
    "pcompressed",
    "puncompressed",
)


@dataclass(frozen=True)
class Param:
    type: str
    name: str


@dataclass(frozen=True)
class Output:
    kind: str
    type: str
    name: str
    size_name: str | None = None


@dataclass(frozen=True)
class Candidate:
    helper_name: str
    return_type: str
    classname: str
    interface: str
    methodname: str
    flat_name: str
    accessor: str
    sdk_return_type: str
    inputs: tuple[Param, ...]
    outputs: tuple[Output, ...]
    call_args: tuple[str, ...]
    reason: str


def resolve_sdk_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.sdk_dir:
        sdk_dir = Path(args.sdk_dir)
        return sdk_dir / "public" / "steam" / "steam_api.json", sdk_dir / "public"

    api_json = Path(args.api_json)
    steam_include = Path(args.steam_include) if args.steam_include else api_json.parent.parent
    return api_json, steam_include


def cpp_string_literal(value: str) -> str:
    return json.dumps(value)


def field_name(name: str) -> str:
    name = re.sub(r"^(pArray|pcub|pvec|pun|pch|psz|pfl|pe|pu|pn|pb|p|un)", "", name)
    name = re.sub(r"Out$", "", name)
    words = re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|\d+", name)
    return "_".join(word.lower() for word in words) or name.lower()


def is_pointer(type_name: str) -> bool:
    return "*" in normalize_type(type_name)


def pointer_base(type_name: str) -> str:
    type_name = normalize_type(type_name)
    return normalize_type(type_name.replace("*", "").removeprefix("const "))


def is_char_pointer(type_name: str) -> bool:
    base = pointer_base(type_name)
    return is_pointer(type_name) and base == "char"


def is_scalar_pointer(type_name: str, typedefs: dict[str, str], enums: set[str]) -> bool:
    if not is_pointer(type_name) or is_char_pointer(type_name):
        return False
    base = pointer_base(type_name)
    if base in {"void", "uint8", "int8", "unsigned char", "char"}:
        return False
    return resolve_c_type(base, typedefs, enums) is not None


def looks_like_array_or_buffer_pointer(param: Param) -> bool:
    lowered = param.name.lower()
    if any(lowered.startswith(hint) for hint in ARRAY_OR_BUFFER_NAME_HINTS):
        return True
    if lowered.endswith("ids"):
        return True
    field = field_name(param.name)
    if field.endswith(("ids", "priorities", "weights", "details", "descriptors")):
        return True
    if "array" in lowered and "arraysize" not in lowered:
        return True
    if lowered.endswith("out") and not lowered.startswith(("pn", "pun", "pb", "pfl", "pe")):
        return True
    return False


def is_size_param(param: Param) -> bool:
    if normalize_type(param.type) not in INTEGER_SIZE_TYPES:
        return False
    lowered = param.name.lower()
    return any(hint in lowered for hint in STRING_BUFFER_HINTS) or lowered.startswith("nbyte")


def is_count_pointer(param: Param) -> bool:
    if not is_pointer(param.type):
        return False
    base = pointer_base(param.type)
    lowered = param.name.lower()
    return base in {"uint32", "int", "int32"} and ("count" in lowered or "size" in lowered or "num" in lowered)


def has_supported_value_type(type_name: str, typedefs: dict[str, str], enums: set[str]) -> bool:
    if is_pointer(type_name):
        return False
    return resolve_c_type(type_name, typedefs, enums) is not None


def method_params(method: dict) -> list[Param]:
    params = []
    for index, param in enumerate(method.get("params", [])):
        param_type = normalize_type(param.get("paramtype_flat", param.get("paramtype", "")))
        if not param_type:
            continue
        params.append(Param(param_type, safe_name(param.get("paramname", ""), f"arg{index}")))
    return params


def method_return_type(method: dict) -> str:
    return normalize_type(method.get("returntype_flat", method.get("returntype", "void")))


def candidate_helper_name(classname: str, methodname: str) -> str:
    if (override := HELPER_NAME_OVERRIDES.get((classname, methodname))) is not None:
        return override
    if methodname.startswith("B") and len(methodname) > 1 and methodname[1].isupper():
        methodname = methodname[1:]
    return f"{wrapper_name(classname, methodname)}String"


def classify_method(
    *,
    classname: str,
    accessor: str,
    method: dict,
    typedefs: dict[str, str],
    enums: set[str],
) -> Candidate | None:
    methodname = method.get("methodname")
    flat_name = method.get("methodname_flat")
    if not methodname or not flat_name:
        return None

    params = method_params(method)
    sdk_return_type = method_return_type(method)
    inputs: list[Param] = []
    outputs: list[Output] = []
    call_args: list[str] = []
    consumed: set[int] = set()

    index = 0
    while index < len(params):
        param = params[index]
        if index in consumed:
            index += 1
            continue
        if is_char_pointer(param.type) and index + 1 < len(params) and is_size_param(params[index + 1]):
            outputs.append(Output("string", param.type, param.name, params[index + 1].name))
            call_args.append(param.name)
            call_args.append(f"sizeof( {param.name} )")
            consumed.update({index, index + 1})
            index += 2
            continue
        if is_scalar_pointer(param.type, typedefs, enums) and not looks_like_array_or_buffer_pointer(param):
            outputs.append(Output("scalar", pointer_base(param.type), param.name))
            call_args.append(f"&{param.name}")
            consumed.add(index)
            index += 1
            continue
        if is_pointer(param.type):
            return None
        if not has_supported_value_type(param.type, typedefs, enums):
            return None
        inputs.append(param)
        call_args.append(param.name)
        index += 1

    if not outputs:
        return None

    string_outputs = [output for output in outputs if output.kind == "string"]
    scalar_outputs = [output for output in outputs if output.kind == "scalar"]
    iface = interface_name(classname) or classname

    if len(outputs) == 1 and string_outputs:
        return_type = "std::string"
        suffix = "String"
        reason = "single_string_buffer"
    else:
        return_type = "std::string"
        suffix = "String"
        reason = "multi_output_payload"

    # Avoid low-level allocators and APIs that return raw pointers; these need
    # hand-written ownership rules rather than a simple payload wrapper.
    if is_pointer(sdk_return_type):
        return None

    if not has_supported_value_type(sdk_return_type, typedefs, enums):
        return None

    if not string_outputs and len(scalar_outputs) == 1 and sdk_return_type == "bool":
        reason = "single_scalar_payload"

    helper = candidate_helper_name(classname, methodname)
    return Candidate(
        helper_name=helper,
        return_type=return_type,
        classname=classname,
        interface=iface,
        methodname=methodname,
        flat_name=flat_name,
        accessor=accessor,
        sdk_return_type=sdk_return_type,
        inputs=tuple(inputs),
        outputs=tuple(outputs),
        call_args=tuple(call_args),
        reason=reason,
    )


def iter_candidates(api: dict, flat_identifiers: set[str]) -> list[Candidate]:
    typedefs = api_typedef_map(api)
    enums = api_enum_names(api)
    candidates: list[Candidate] = []
    for interface in api.get("interfaces", []):
        classname = interface.get("classname")
        accessor = interface_accessor(interface, flat_identifiers)
        if not classname or not accessor:
            continue
        for method in interface.get("methods", []):
            flat_name = method.get("methodname_flat")
            if not flat_name or flat_name not in flat_identifiers:
                continue
            candidate = classify_method(
                classname=classname,
                accessor=accessor,
                method=method,
                typedefs=typedefs,
                enums=enums,
            )
            if candidate is not None:
                candidates.append(candidate)

    counts = Counter(candidate.helper_name for candidate in candidates)
    return sorted(
        [candidate for candidate in candidates if counts[candidate.helper_name] == 1],
        key=lambda candidate: candidate.helper_name,
    )


def promoted_candidates(api: dict, flat_identifiers: set[str]) -> list[Candidate]:
    return [
        candidate
        for candidate in iter_candidates(api, flat_identifiers)
        if candidate.helper_name in PROMOTED_OUTPUT_HELPERS
    ]


def generated_output_helper_functions(api: dict, flat_identifiers: set[str]) -> list[tuple]:
    return [
        (
            candidate.return_type,
            candidate.helper_name,
            [(param.type, param.name) for param in candidate.inputs],
        )
        for candidate in promoted_candidates(api, flat_identifiers)
    ]


def generated_output_helper_declarations(api: dict, flat_identifiers: set[str]) -> str:
    return "\n".join(declaration(candidate) for candidate in promoted_candidates(api, flat_identifiers))


def generated_output_helper_definitions(api: dict, flat_identifiers: set[str]) -> str:
    return "\n\n".join(definition(candidate) for candidate in promoted_candidates(api, flat_identifiers))


def metadata_tuple(candidate: Candidate) -> str:
    params = ", ".join(f"({cpp_string_literal(param.type)}, {cpp_string_literal(param.name)})" for param in candidate.inputs)
    return f"    ({cpp_string_literal(candidate.return_type)}, {cpp_string_literal(candidate.helper_name)}, [{params}]),"


def declaration(candidate: Candidate) -> str:
    params = ", ".join(f"{param.type} {param.name}" for param in candidate.inputs)
    return f"{candidate.return_type} {candidate.helper_name}( {params} );" if params else f"{candidate.return_type} {candidate.helper_name}();"


def default_success_expression(candidate: Candidate) -> str:
    if candidate.sdk_return_type == "bool":
        return "ok"
    if candidate.sdk_return_type == "void":
        return "true"
    return "true"


def default_failure_check(candidate: Candidate) -> str | None:
    if candidate.sdk_return_type == "bool":
        return "!ok"
    return None


def output_local(output: Output) -> list[str]:
    if output.kind == "string":
        return [f"\tchar {output.name}[4096] = {{ 0 }};"]
    if output.kind == "scalar":
        return [f"\t{output.type} {output.name} = {{}};"]
    raise ValueError(output.kind)


def output_args(output: Output) -> list[str]:
    if output.kind == "string":
        return [output.name, f"sizeof( {output.name} )"]
    if output.kind == "scalar":
        return [f"&{output.name}"]
    raise ValueError(output.kind)


def flat_call_args(candidate: Candidate) -> str:
    return ", ".join(["self", *candidate.call_args])


def payload_lines(candidate: Candidate) -> list[str]:
    lines = ["\tstd::string payload;"]
    if candidate.sdk_return_type != "bool":
        lines.append('\tAppendPayloadNumber( payload, "result", result );')
    for output in candidate.outputs:
        key = field_name(output.name)
        if output.kind == "string":
            lines.append(f"\tAppendPayloadField( payload, {cpp_string_literal(key)}, {output.name} );")
        elif output.kind == "scalar":
            if output.type == "bool":
                lines.append(f"\tAppendPayloadField( payload, {cpp_string_literal(key)}, {output.name} );")
            else:
                lines.append(f"\tAppendPayloadNumber( payload, {cpp_string_literal(key)}, {output.name} );")
    lines.append("\treturn payload;")
    return lines


def definition(candidate: Candidate) -> str:
    params = ", ".join(f"{param.type} {param.name}" for param in candidate.inputs)
    lines = [
        f"{candidate.return_type} {candidate.helper_name}( {params} )" if params else f"{candidate.return_type} {candidate.helper_name}()",
        "{",
        f"\tauto *self = {candidate.accessor}();",
        "\tif ( !self )",
        "\t{",
        "\t\treturn {};",
        "\t}",
        "",
    ]
    for output in candidate.outputs:
        lines.extend(output_local(output))
    call = f"{candidate.flat_name}( {flat_call_args(candidate)} )"
    if candidate.sdk_return_type == "void":
        lines.append(f"\t{call};")
    else:
        lines.append(f"\tconst auto result = {call};")
        if candidate.sdk_return_type == "bool":
            lines.append("\tconst bool ok = result;")
        failure = default_failure_check(candidate)
        if failure:
            lines.extend(["\tif ( " + failure + " )", "\t{", "\t\treturn {};", "\t}"])

    if len(candidate.outputs) == 1 and candidate.outputs[0].kind == "string":
        lines.append(f"\treturn std::string( {candidate.outputs[0].name} );")
    else:
        lines.extend(payload_lines(candidate))
    lines.append("}")
    return "\n".join(lines)


def report(candidates: list[Candidate], promoted: set[str] | None = None) -> str:
    promoted = promoted or set()
    counts = Counter(candidate.reason for candidate in candidates)
    lines = [
        "# Generated Output Helper Candidates",
        "",
        "This file is generated by `tools/generate_output_helpers.py`.",
        "Promoted candidates are consumed by `tools/generate_core.py`; the rest are review-only.",
        "",
        "## Summary",
        "",
    ]
    for reason, count in sorted(counts.items()):
        lines.append(f"- {reason}: {count}")
    lines.extend(["", "## Candidates", ""])
    for candidate in candidates:
        params = ", ".join(f"{param.type} {param.name}" for param in candidate.inputs)
        outputs = ", ".join(f"{output.kind}:{output.name}" for output in candidate.outputs)
        marker = " promoted" if candidate.helper_name in promoted else ""
        lines.append(f"- `{candidate.helper_name}({params}) -> {candidate.return_type}` from `{candidate.interface}.{candidate.methodname}` ({candidate.reason}; outputs: {outputs}){marker}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-dir", help="Steamworks SDK root, e.g. sdk_v165")
    parser.add_argument("--api-json", default=str(ROOT / "sdk" / "public" / "steam" / "steam_api.json"))
    parser.add_argument("--steam-include", help="Steamworks public include root")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    api_json, steam_include = resolve_sdk_paths(args)
    api = load_json(api_json)
    flat_header = steam_include / "steam" / "steam_api_flat.h"
    flat_identifiers = declared_identifiers(flat_header.read_text(encoding="utf-8", errors="replace"))
    candidates = iter_candidates(api, flat_identifiers)
    promoted = {candidate.helper_name for candidate in promoted_candidates(api, flat_identifiers)}

    output_dir = Path(args.output_dir)
    write_text(output_dir / "helper_metadata.py", "\n".join(metadata_tuple(candidate) for candidate in candidates) + "\n")
    write_text(output_dir / "helper_declarations.h", "\n".join(declaration(candidate) for candidate in candidates) + "\n")
    write_text(output_dir / "helper_definitions.cpp", "\n\n".join(definition(candidate) for candidate in candidates) + "\n")
    write_text(output_dir / "promoted_helper_metadata.py", "\n".join(metadata_tuple(candidate) for candidate in promoted_candidates(api, flat_identifiers)) + "\n")
    write_text(output_dir / "promoted_helper_declarations.h", generated_output_helper_declarations(api, flat_identifiers) + "\n")
    write_text(output_dir / "promoted_helper_definitions.cpp", generated_output_helper_definitions(api, flat_identifiers) + "\n")
    write_text(output_dir / "README.md", report(candidates, promoted))
    print(f"Wrote {len(candidates)} output-helper candidates ({len(promoted)} promoted) to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
