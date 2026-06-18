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
import re
from pathlib import Path


SUPPORTED_POINTER_TYPES = {"const char *"}
FLAT_TYPEDEFS = {
    "uint64_steamid": "unsigned long long",
    "uint64_gameid": "unsigned long long",
}
TEMPLATE_DIR = Path(__file__).with_name("templates")


MANUAL_DISPATCH_CALLBACKS = [
    {
        "name": "LowBatteryPower",
        "type": "LowBatteryPower_t",
        "reserve": 64,
        "fields": [
            ("minutes_battery_left", "std::to_string( callback.m_nMinutesBatteryLeft )"),
        ],
    },
    {
        "name": "SteamShutdown",
        "type": "SteamShutdown_t",
        "reserve": 32,
        "fields": [
            ("shutdown", 'std::string( "1" )'),
        ],
    },
    {
        "name": "SteamServersConnected",
        "type": "SteamServersConnected_t",
        "reserve": 32,
        "fields": [
            ("connected", 'std::string( "1" )'),
        ],
    },
    {
        "name": "SteamServerConnectFailure",
        "type": "SteamServerConnectFailure_t",
        "reserve": 96,
        "fields": [
            ("result", "std::to_string( static_cast<int>( callback.m_eResult ) )"),
            ("still_retrying", "std::to_string( callback.m_bStillRetrying ? 1 : 0 )"),
        ],
    },
    {
        "name": "SteamServersDisconnected",
        "type": "SteamServersDisconnected_t",
        "reserve": 64,
        "fields": [
            ("result", "std::to_string( static_cast<int>( callback.m_eResult ) )"),
        ],
    },
    {
        "name": "IPCFailure",
        "type": "IPCFailure_t",
        "reserve": 64,
        "fields": [
            ("failure_type", "std::to_string( callback.m_eFailureType )"),
        ],
    },
    {
        "name": "LicensesUpdated",
        "type": "LicensesUpdated_t",
        "reserve": 32,
        "fields": [
            ("updated", 'std::string( "1" )'),
        ],
    },
    {
        "name": "ValidateAuthTicketResponse",
        "type": "ValidateAuthTicketResponse_t",
        "reserve": 160,
        "fields": [
            ("steam_id", "std::to_string( callback.m_SteamID.ConvertToUint64() )"),
            ("auth_session_response", "std::to_string( static_cast<int>( callback.m_eAuthSessionResponse ) )"),
            ("owner_steam_id", "std::to_string( callback.m_OwnerSteamID.ConvertToUint64() )"),
        ],
    },
    {
        "name": "MicroTxnAuthorizationResponse",
        "type": "MicroTxnAuthorizationResponse_t",
        "reserve": 128,
        "fields": [
            ("app_id", "std::to_string( callback.m_unAppID )"),
            ("order_id", "std::to_string( callback.m_ulOrderID )"),
            ("authorized", "std::to_string( callback.m_bAuthorized ? 1 : 0 )"),
        ],
    },
    {
        "name": "ClientGameServerDeny",
        "type": "ClientGameServerDeny_t",
        "reserve": 160,
        "fields": [
            ("app_id", "std::to_string( callback.m_uAppID )"),
            ("game_server_ip", "std::to_string( callback.m_unGameServerIP )"),
            ("game_server_port", "std::to_string( callback.m_usGameServerPort )"),
            ("secure", "std::to_string( callback.m_bSecure ? 1 : 0 )"),
            ("reason", "std::to_string( callback.m_uReason )"),
        ],
    },
    {
        "name": "EncryptedAppTicketResponse",
        "type": "EncryptedAppTicketResponse_t",
        "reserve": 64,
        "fields": [
            ("result", "std::to_string( static_cast<int>( callback.m_eResult ) )"),
        ],
    },
    {
        "name": "GetAuthSessionTicketResponse",
        "type": "GetAuthSessionTicketResponse_t",
        "reserve": 96,
        "fields": [
            ("auth_ticket", "std::to_string( callback.m_hAuthTicket )"),
            ("result", "std::to_string( static_cast<int>( callback.m_eResult ) )"),
        ],
    },
    {
        "name": "GameWebCallback",
        "type": "GameWebCallback_t",
        "reserve": 320,
        "fields": [
            ("url", "EscapeEventField( callback.m_szURL )"),
        ],
    },
    {
        "name": "DlcInstalled",
        "type": "DlcInstalled_t",
        "reserve": 64,
        "fields": [
            ("app_id", "std::to_string( callback.m_nAppID )"),
        ],
    },
    {
        "name": "NewUrlLaunchParameters",
        "type": "NewUrlLaunchParameters_t",
        "reserve": 32,
        "fields": [
            ("new_url_launch_parameters", 'std::string( "1" )'),
        ],
    },
    {
        "name": "FavoritesListChanged",
        "type": "FavoritesListChanged_t",
        "reserve": 192,
        "fields": [
            ("ip", "std::to_string( callback.m_nIP )"),
            ("query_port", "std::to_string( callback.m_nQueryPort )"),
            ("connection_port", "std::to_string( callback.m_nConnPort )"),
            ("app_id", "std::to_string( callback.m_nAppID )"),
            ("flags", "std::to_string( callback.m_nFlags )"),
            ("add", "std::to_string( callback.m_bAdd ? 1 : 0 )"),
            ("account_id", "std::to_string( callback.m_unAccountId )"),
        ],
    },
    {
        "name": "LobbyInvite",
        "type": "LobbyInvite_t",
        "reserve": 160,
        "fields": [
            ("user", "std::to_string( callback.m_ulSteamIDUser )"),
            ("lobby", "std::to_string( callback.m_ulSteamIDLobby )"),
            ("game_id", "std::to_string( callback.m_ulGameID )"),
        ],
    },
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
        "name": "LobbyKicked",
        "type": "LobbyKicked_t",
        "reserve": 128,
        "fields": [
            ("lobby", "std::to_string( callback.m_ulSteamIDLobby )"),
            ("admin", "std::to_string( callback.m_ulSteamIDAdmin )"),
            ("kicked_due_to_disconnect", "std::to_string( callback.m_bKickedDueToDisconnect ? 1 : 0 )"),
        ],
    },
    {
        "name": "GameServerChangeRequested",
        "type": "GameServerChangeRequested_t",
        "reserve": 160,
        "fields": [
            ("server", "EscapeEventField( callback.m_rgchServer )"),
            ("password", "EscapeEventField( callback.m_rgchPassword )"),
        ],
    },
    {
        "name": "GameOverlayActivated",
        "type": "GameOverlayActivated_t",
        "reserve": 128,
        "fields": [
            ("active", "std::to_string( callback.m_bActive ? 1 : 0 )"),
            ("user_initiated", "std::to_string( callback.m_bUserInitiated ? 1 : 0 )"),
            ("app_id", "std::to_string( callback.m_nAppID )"),
            ("overlay_pid", "std::to_string( callback.m_dwOverlayPID )"),
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
        "name": "AvatarImageLoaded",
        "type": "AvatarImageLoaded_t",
        "reserve": 128,
        "fields": [
            ("steam_id", "std::to_string( callback.m_steamID.ConvertToUint64() )"),
            ("image", "std::to_string( callback.m_iImage )"),
            ("wide", "std::to_string( callback.m_iWide )"),
            ("tall", "std::to_string( callback.m_iTall )"),
        ],
    },
    {
        "name": "FriendRichPresenceUpdate",
        "type": "FriendRichPresenceUpdate_t",
        "reserve": 96,
        "fields": [
            ("friend", "std::to_string( callback.m_steamIDFriend.ConvertToUint64() )"),
            ("app_id", "std::to_string( callback.m_nAppID )"),
        ],
    },
    {
        "name": "GameRichPresenceJoinRequested",
        "type": "GameRichPresenceJoinRequested_t",
        "reserve": 384,
        "fields": [
            ("friend", "std::to_string( callback.m_steamIDFriend.ConvertToUint64() )"),
            ("connect", "EscapeEventField( callback.m_rgchConnect )"),
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
        "name": "P2PSessionRequest",
        "type": "P2PSessionRequest_t",
        "reserve": 64,
        "fields": [
            ("remote_steam_id", "std::to_string( callback.m_steamIDRemote.ConvertToUint64() )"),
        ],
    },
    {
        "name": "P2PSessionConnectFail",
        "type": "P2PSessionConnectFail_t",
        "reserve": 96,
        "fields": [
            ("remote_steam_id", "std::to_string( callback.m_steamIDRemote.ConvertToUint64() )"),
            ("error", "std::to_string( callback.m_eP2PSessionError )"),
        ],
    },
    {
        "name": "SocketStatusCallback",
        "type": "SocketStatusCallback_t",
        "reserve": 160,
        "fields": [
            ("socket", "std::to_string( callback.m_hSocket )"),
            ("listen_socket", "std::to_string( callback.m_hListenSocket )"),
            ("remote_steam_id", "std::to_string( callback.m_steamIDRemote.ConvertToUint64() )"),
            ("state", "std::to_string( callback.m_eSNetSocketState )"),
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
    {
        "name": "SteamNetworkingFakeIPResult",
        "type": "SteamNetworkingFakeIPResult_t",
        "reserve": 512,
        "fields": [
            ("result", "std::to_string( static_cast<int>( callback.m_eResult ) )"),
        ],
        "append": [
            "SerializeNetworkingIdentity( callback.m_identity )",
            'std::string( "ip=" ) + std::to_string( callback.m_unIP )',
            'std::string( "port0=" ) + std::to_string( callback.m_unPorts[0] )',
            'std::string( "port1=" ) + std::to_string( callback.m_unPorts[1] )',
            'std::string( "port2=" ) + std::to_string( callback.m_unPorts[2] )',
            'std::string( "port3=" ) + std::to_string( callback.m_unPorts[3] )',
            'std::string( "port4=" ) + std::to_string( callback.m_unPorts[4] )',
            'std::string( "port5=" ) + std::to_string( callback.m_unPorts[5] )',
            'std::string( "port6=" ) + std::to_string( callback.m_unPorts[6] )',
            'std::string( "port7=" ) + std::to_string( callback.m_unPorts[7] )',
        ],
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


def declared_identifiers(header_text: str) -> set[str]:
    return set(re.findall(r"\b(?:SteamAPI|SteamGameServer)_[A-Za-z0-9_]+\b", header_text))


def interface_accessor(interface: dict, flat_identifiers: set[str]) -> str | None:
    for accessor in interface.get("accessors") or []:
        versioned = accessor.get("name_flat")
        if versioned and versioned in flat_identifiers:
            return versioned

        unversioned_name = accessor.get("name")
        if unversioned_name:
            unversioned = f"SteamAPI_{unversioned_name}"
            if unversioned in flat_identifiers:
                return unversioned
    return None


def iter_wrappable_methods(api: dict, flat_identifiers: set[str]):
    for interface in api.get("interfaces", []):
        accessor = interface_accessor(interface, flat_identifiers)
        classname = interface.get("classname")
        if not accessor or not classname:
            continue

        for method in interface.get("methods", []):
            methodname = method.get("methodname")
            flat_name = method.get("methodname_flat")
            return_type = flat_type(method, "returntype")
            if (
                not methodname
                or not flat_name
                or flat_name not in flat_identifiers
                or return_type is None
            ):
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
            f'\tRequireCallbackDispatchMode( k_CallbackDispatchModeManual, "Steam_ManualDispatch_DecodeCallback{item["name"]}" );',
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
            f'\tRequireCallbackDispatchMode( k_CallbackDispatchModeManual, "Steam_ManualDispatch_DecodeAPICallResult{item["name"]}" );',
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


def generate(api: dict, output_dir: Path, steam_include: Path) -> None:
    flat_header = steam_include / "steam" / "steam_api_flat.h"
    flat_header_text = flat_header.read_text(encoding="utf-8", errors="replace")
    flat_identifiers = declared_identifiers(flat_header_text)
    methods = sorted(
        iter_wrappable_methods(api, flat_identifiers),
        key=lambda item: item["wrapper_name"],
    )
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
            connection_realtime_optional_fields=connection_realtime_optional_fields(
                steam_include
            ),
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

    print(
        f"Generated {len(methods)} wrapper functions in {output_dir} "
        f"using {flat_header}"
    )


def connection_realtime_optional_fields(steam_include: Path) -> str:
    networking_types = steam_include / "steam" / "steamnetworkingtypes.h"
    header_text = networking_types.read_text(encoding="utf-8", errors="replace")
    if "m_usecMaxJitter" not in header_text:
        return ""
    return (
        '\tserialized += "\\tmax_jitter_usec=" '
        "+ std::to_string( status.m_usecMaxJitter );"
    )


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
    parser.add_argument("--steam-include")
    parser.add_argument("--output-dir", default="generated")
    args = parser.parse_args()

    api_json = Path(args.api_json)
    steam_include = (
        Path(args.steam_include)
        if args.steam_include
        else api_json.parent.parent
    )
    api = json.loads(api_json.read_text(encoding="utf-8"))
    generate(api, Path(args.output_dir), steam_include)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
