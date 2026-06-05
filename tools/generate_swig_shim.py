#!/usr/bin/env python3
"""Generate a small SWIG-facing Steamworks shim from steam_api.json.

This intentionally starts with the subset that maps cleanly to scripting
languages: interface methods with a known flat accessor and value-like
parameters. Pointer/out/ref APIs, callbacks, structs, and raw interface-returning
functions are skipped until they have explicit typemaps.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SUPPORTED_POINTER_TYPES = {"const char *"}
FLAT_TYPEDEFS = {
    "uint64_steamid": "unsigned long long",
    "uint64_gameid": "unsigned long long",
}
TEMPLATE_DIR = Path(__file__).with_name("templates")


MANUAL_DISPATCH_CALLBACKS = [
    {
        "name": "SteamNetConnectionStatusChanged",
        "type": "SteamNetConnectionStatusChangedCallback_t",
        "reserve": 1152,
        "fields": [
            ("connection", "std::to_string( static_cast<uint32>( callback.m_hConn ) )"),
            ("old_state", "std::to_string( static_cast<int>( callback.m_eOldState ) )"),
        ],
        "append": ["SerializeConnectionInfo( callback.m_info )"],
    },
    {
        "name": "LobbyEnter",
        "type": "LobbyEnter_t",
        "reserve": 160,
        "fields": [
            ("lobby", "std::to_string( callback.m_ulSteamIDLobby )"),
            ("chat_permissions", "std::to_string( callback.m_rgfChatPermissions )"),
            ("locked", "std::to_string( callback.m_bLocked ? 1 : 0 )"),
            ("response", "std::to_string( callback.m_EChatRoomEnterResponse )"),
        ],
    },
    {
        "name": "LobbyDataUpdate",
        "type": "LobbyDataUpdate_t",
        "reserve": 128,
        "fields": [
            ("lobby", "std::to_string( callback.m_ulSteamIDLobby )"),
            ("member", "std::to_string( callback.m_ulSteamIDMember )"),
            ("success", "std::to_string( callback.m_bSuccess ? 1 : 0 )"),
        ],
    },
    {
        "name": "LobbyChatUpdate",
        "type": "LobbyChatUpdate_t",
        "reserve": 192,
        "fields": [
            ("lobby", "std::to_string( callback.m_ulSteamIDLobby )"),
            ("user_changed", "std::to_string( callback.m_ulSteamIDUserChanged )"),
            ("making_change", "std::to_string( callback.m_ulSteamIDMakingChange )"),
            ("state_change", "std::to_string( callback.m_rgfChatMemberStateChange )"),
        ],
    },
    {
        "name": "LobbyChatMsg",
        "type": "LobbyChatMsg_t",
        "reserve": 160,
        "fields": [
            ("lobby", "std::to_string( callback.m_ulSteamIDLobby )"),
            ("user", "std::to_string( callback.m_ulSteamIDUser )"),
            ("type", "std::to_string( callback.m_eChatEntryType )"),
            ("chat_id", "std::to_string( callback.m_iChatID )"),
        ],
    },
    {
        "name": "LobbyGameCreated",
        "type": "LobbyGameCreated_t",
        "reserve": 160,
        "fields": [
            ("lobby", "std::to_string( callback.m_ulSteamIDLobby )"),
            ("game_server", "std::to_string( callback.m_ulSteamIDGameServer )"),
            ("ip", "std::to_string( callback.m_unIP )"),
            ("port", "std::to_string( callback.m_usPort )"),
        ],
    },
    {
        "name": "GameLobbyJoinRequested",
        "type": "GameLobbyJoinRequested_t",
        "reserve": 128,
        "fields": [
            ("lobby", "std::to_string( callback.m_steamIDLobby.ConvertToUint64() )"),
            ("friend", "std::to_string( callback.m_steamIDFriend.ConvertToUint64() )"),
        ],
    },
    {
        "name": "PersonaStateChange",
        "type": "PersonaStateChange_t",
        "reserve": 96,
        "fields": [
            ("steam_id", "std::to_string( callback.m_ulSteamID )"),
            ("change_flags", "std::to_string( callback.m_nChangeFlags )"),
        ],
    },
    {
        "name": "SteamNetAuthenticationStatus",
        "type": "SteamNetAuthenticationStatus_t",
        "reserve": 320,
        "fields": [
            ("availability", "std::to_string( static_cast<int>( callback.m_eAvail ) )"),
            ("debug", "EscapeEventField( callback.m_debugMsg )"),
        ],
    },
    {
        "name": "SteamRelayNetworkStatus",
        "type": "SteamRelayNetworkStatus_t",
        "reserve": 448,
        "fields": [
            ("availability", "std::to_string( static_cast<int>( callback.m_eAvail ) )"),
            ("ping_measurement_in_progress", "std::to_string( callback.m_bPingMeasurementInProgress )"),
            ("network_config_availability", "std::to_string( static_cast<int>( callback.m_eAvailNetworkConfig ) )"),
            ("any_relay_availability", "std::to_string( static_cast<int>( callback.m_eAvailAnyRelay ) )"),
            ("debug", "EscapeEventField( callback.m_debugMsg )"),
        ],
    },
    {
        "name": "SteamNetworkingMessagesSessionRequest",
        "type": "SteamNetworkingMessagesSessionRequest_t",
        "reserve": 192,
        "append": ["SerializeNetworkingIdentity( callback.m_identityRemote )"],
    },
    {
        "name": "SteamNetworkingMessagesSessionFailed",
        "type": "SteamNetworkingMessagesSessionFailed_t",
        "reserve": 1024,
        "append": ["SerializeConnectionInfo( callback.m_info )"],
    },
]

MANUAL_DISPATCH_API_CALL_RESULTS = [
    {
        "name": "LobbyMatchList",
        "type": "LobbyMatchList_t",
        "reserve": 48,
        "fields": [
            ("lobbies_matching", "std::to_string( callback.m_nLobbiesMatching )"),
        ],
    },
    {
        "name": "LobbyEnter",
        "type": "LobbyEnter_t",
    },
    {
        "name": "LobbyCreated",
        "type": "LobbyCreated_t",
        "reserve": 96,
        "fields": [
            ("result", "std::to_string( static_cast<int>( callback.m_eResult ) )"),
            ("lobby", "std::to_string( callback.m_ulSteamIDLobby )"),
        ],
    },
]


CPP_KEYWORDS = {
    "alignas",
    "alignof",
    "and",
    "and_eq",
    "asm",
    "auto",
    "bitand",
    "bitor",
    "bool",
    "break",
    "case",
    "catch",
    "char",
    "class",
    "compl",
    "const",
    "constexpr",
    "continue",
    "decltype",
    "default",
    "delete",
    "do",
    "double",
    "dynamic_cast",
    "else",
    "enum",
    "explicit",
    "export",
    "extern",
    "false",
    "float",
    "for",
    "friend",
    "goto",
    "if",
    "inline",
    "int",
    "long",
    "mutable",
    "namespace",
    "new",
    "noexcept",
    "not",
    "not_eq",
    "nullptr",
    "operator",
    "or",
    "or_eq",
    "private",
    "protected",
    "public",
    "register",
    "reinterpret_cast",
    "return",
    "short",
    "signed",
    "sizeof",
    "static",
    "static_assert",
    "static_cast",
    "struct",
    "switch",
    "template",
    "this",
    "thread_local",
    "throw",
    "true",
    "try",
    "typedef",
    "typeid",
    "typename",
    "union",
    "unsigned",
    "using",
    "virtual",
    "void",
    "volatile",
    "wchar_t",
    "while",
    "xor",
    "xor_eq",
}


def normalize_type(type_name: str) -> str:
    return " ".join(type_name.replace(" *", "*").replace("*", " *").split())


def swig_safe_type(type_name: str) -> str | None:
    type_name = normalize_type(type_name)
    if "&" in type_name or "[" in type_name or "]" in type_name:
        return None
    if "*" in type_name and type_name not in SUPPORTED_POINTER_TYPES:
        return None
    if type_name.startswith("ISteam"):
        return None
    return type_name


def safe_name(name: str, fallback: str) -> str:
    name = name or fallback
    if name in CPP_KEYWORDS:
        return f"{name}_"
    return name


def flat_type(entry: dict, key: str) -> str | None:
    value = entry.get(f"{key}_flat", entry.get(key))
    if not value:
        return None
    return swig_safe_type(value)


def wrapper_name(classname: str, methodname: str) -> str:
    if classname.startswith("ISteam"):
        classname = classname[len("ISteam") :]
    return f"Steam_{classname}_{methodname}"


def iter_wrappable_methods(api: dict):
    for interface in api.get("interfaces", []):
        accessors = interface.get("accessors") or []
        if not accessors:
            continue

        accessor = accessors[0].get("name_flat")
        classname = interface.get("classname")
        if not accessor or not classname:
            continue

        for method in interface.get("methods", []):
            methodname = method.get("methodname")
            flat_name = method.get("methodname_flat")
            return_type = flat_type(method, "returntype")
            if not methodname or not flat_name or return_type is None:
                continue

            params = []
            for index, param in enumerate(method.get("params", [])):
                param_type = flat_type(param, "paramtype")
                if param_type is None:
                    break
                param_name = safe_name(param.get("paramname", ""), f"arg{index}")
                params.append((param_type, param_name))
            else:
                yield {
                    "classname": classname,
                    "accessor": accessor,
                    "methodname": methodname,
                    "flat_name": flat_name,
                    "return_type": return_type,
                    "params": params,
                    "wrapper_name": wrapper_name(classname, methodname),
                }


def declaration(method: dict) -> str:
    params = ", ".join(f"{type_name} {name}" for type_name, name in method["params"])
    return f'{method["return_type"]} {method["wrapper_name"]}( {params} );'


def definition(method: dict) -> str:
    params = ", ".join(f"{type_name} {name}" for type_name, name in method["params"])
    args = ", ".join(["self"] + [name for _, name in method["params"]])
    lines = [
        f'{method["return_type"]} {method["wrapper_name"]}( {params} )',
        "{",
        f'\tauto *self = {method["accessor"]}();',
        "\tif ( !self )",
        "\t{",
    ]
    if method["return_type"] == "void":
        lines.append("\t\treturn;")
    else:
        lines.append("\t\treturn {};")
    lines.extend(
        [
            "\t}",
        ]
    )
    if method["return_type"] == "void":
        lines.append(f'\t{method["flat_name"]}( {args} );')
    else:
        lines.append(f'\treturn {method["flat_name"]}( {args} );')
    lines.append("}")
    return "\n".join(lines)


def manual_dispatch_entries() -> list[dict]:
    entries = []
    seen_types = set()
    for item in MANUAL_DISPATCH_CALLBACKS + MANUAL_DISPATCH_API_CALL_RESULTS:
        if item["type"] in seen_types:
            continue
        entries.append(item)
        seen_types.add(item["type"])
    return entries


def manual_dispatch_declarations() -> str:
    lines = ["int Steam_ManualDispatch_CallbackIDSteamAPICallCompleted();"]
    for item in manual_dispatch_entries():
        lines.append(f'int Steam_ManualDispatch_CallbackID{item["name"]}();')
    for item in MANUAL_DISPATCH_CALLBACKS:
        lines.append(f'std::string Steam_ManualDispatch_DecodeCallback{item["name"]}();')
    for item in MANUAL_DISPATCH_API_CALL_RESULTS:
        lines.append(f'std::string Steam_ManualDispatch_DecodeAPICallResult{item["name"]}();')
    return "\n".join(lines)


def serializer_name(item: dict) -> str:
    return f'Serialize{item["name"]}'


def manual_dispatch_serializer_forward_declarations() -> str:
    return "\n".join(
        f'std::string {serializer_name(item)}( const {item["type"]} &callback );'
        for item in manual_dispatch_entries()
    )


def serialize_field_lines(item: dict) -> list[str]:
    fields = item.get("fields", [])
    append = item.get("append", [])
    lines: list[str] = []
    first = True
    for key, expr in fields:
        prefix = "" if first else "\\t"
        lines.append(f'\tresult += "{prefix}{key}=" + {expr};')
        first = False
    for expr in append:
        if first:
            lines.append(f"\tresult += {expr};")
        else:
            lines.append(f'\tresult += "\\t" + {expr};')
        first = False
    if first:
        lines.append('\treturn {};')
    else:
        lines.append("\treturn result;")
    return lines


def manual_dispatch_serializer(item: dict) -> str:
    reserve = item.get("reserve", 128)
    lines = [
        f'std::string {serializer_name(item)}( const {item["type"]} &callback )',
        "{",
        "\tstd::string result;",
        f"\tresult.reserve( {reserve} );",
    ]
    lines.extend(serialize_field_lines(item))
    lines.append("}")
    return "\n".join(lines)


def manual_dispatch_serializers() -> str:
    return "\n\n".join(manual_dispatch_serializer(item) for item in manual_dispatch_entries())


def manual_dispatch_callback_id_definition(item: dict) -> str:
    return "\n".join(
        [
            f'int Steam_ManualDispatch_CallbackID{item["name"]}()',
            "{",
            f'\treturn {item["type"]}::k_iCallback;',
            "}",
        ]
    )


def manual_dispatch_decode_callback_definition(item: dict) -> str:
    return "\n".join(
        [
            f'std::string Steam_ManualDispatch_DecodeCallback{item["name"]}()',
            "{",
            f'\t{item["type"]} callback = {{}};',
            "\tif ( !CopyCurrentManualDispatchCallback( &callback ) )",
            "\t{",
            "\t\treturn {};",
            "\t}",
            f"\treturn {serializer_name(item)}( callback );",
            "}",
        ]
    )


def manual_dispatch_decode_api_call_result_definition(item: dict) -> str:
    return "\n".join(
        [
            f'std::string Steam_ManualDispatch_DecodeAPICallResult{item["name"]}()',
            "{",
            f'\tif ( g_manualDispatchAPICallResultCallbackID != {item["type"]}::k_iCallback )',
            "\t{",
            "\t\treturn {};",
            "\t}",
            "",
            f'\t{item["type"]} callback = {{}};',
            "\tif ( !CopyCallbackPayload( g_manualDispatchAPICallResultData, &callback ) )",
            "\t{",
            "\t\treturn {};",
            "\t}",
            f"\treturn {serializer_name(item)}( callback );",
            "}",
        ]
    )


def manual_dispatch_definitions() -> str:
    blocks = [
        "\n".join(
            [
                "int Steam_ManualDispatch_CallbackIDSteamAPICallCompleted()",
                "{",
                "\treturn SteamAPICallCompleted_t::k_iCallback;",
                "}",
            ]
        )
    ]
    blocks.extend(manual_dispatch_callback_id_definition(item) for item in manual_dispatch_entries())
    blocks.extend(manual_dispatch_decode_callback_definition(item) for item in MANUAL_DISPATCH_CALLBACKS)
    blocks.extend(
        manual_dispatch_decode_api_call_result_definition(item)
        for item in MANUAL_DISPATCH_API_CALL_RESULTS
    )
    return "\n\n".join(blocks)


def render_template(template_name: str, **values: str) -> str:
    rendered = (TEMPLATE_DIR / template_name).read_text(encoding="utf-8")
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{ {key} }}}}", value)
    return rendered


def generate(api: dict, output_dir: Path) -> None:
    methods = sorted(iter_wrappable_methods(api), key=lambda item: item["wrapper_name"])
    output_dir.mkdir(parents=True, exist_ok=True)

    header = output_dir / "steamworks_swig_shim.h"
    source = output_dir / "steamworks_swig_shim.cpp"
    interface = output_dir / "steamworks.i"

    generated_declarations = "\n".join(declaration(method) for method in methods)
    generated_definitions = "\n\n".join(definition(method) for method in methods)
    swig_declarations = "\n".join(swig_type_declarations(api, methods))

    header.write_text(
        render_template(
            "steamworks_swig_shim.h.in",
            generated_declarations=generated_declarations,
            manual_dispatch_declarations=manual_dispatch_declarations(),
        )
        + "\n",
        encoding="utf-8",
    )

    source.write_text(
        render_template(
            "steamworks_swig_shim.cpp.in",
            generated_definitions=generated_definitions,
            manual_dispatch_serializer_forward_declarations=manual_dispatch_serializer_forward_declarations(),
            manual_dispatch_serializers=manual_dispatch_serializers(),
            manual_dispatch_definitions=manual_dispatch_definitions(),
        )
        + "\n",
        encoding="utf-8",
    )

    interface.write_text(
        render_template(
            "steamworks.i.in",
            swig_type_declarations=swig_declarations,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Generated {len(methods)} wrapper functions in {output_dir}")


def swig_type_declarations(api: dict, methods: list[dict]) -> list[str]:
    lines = [
        "/* SWIG-only type declarations. The compiled extension uses Valve's real headers. */",
    ]

    for item in api.get("typedefs", []):
        alias = item.get("typedef")
        target = item.get("type")
        if not alias or not target:
            continue
        target = normalize_type(target)
        if "*" in target or "[" in target or "]" in target or "(" in target:
            continue
        lines.append(f"typedef {target} {alias};")

    for alias, target in FLAT_TYPEDEFS.items():
        lines.append(f"typedef {target} {alias};")

    lines.append("")

    used_types = {method["return_type"] for method in methods}
    for method in methods:
        used_types.update(type_name for type_name, _ in method["params"])

    for item in api.get("enums", []):
        enum_name = item.get("enumname")
        if not enum_name or enum_name not in used_types:
            continue
        values = [
            value["name"]
            for value in item.get("values", [])
            if value.get("name") and value["name"].replace("_", "").isalnum()
        ]
        if not values:
            continue
        lines.append(f"enum {enum_name} {{")
        for value in values:
            lines.append(f"\t{value},")
        lines.append("};")

    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-json", default="sdk/public/steam/steam_api.json")
    parser.add_argument("--output-dir", default="generated")
    args = parser.parse_args()

    api = json.loads(Path(args.api_json).read_text(encoding="utf-8"))
    generate(api, Path(args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
