"""Steamworks SDK metadata discovery helpers."""

from __future__ import annotations

import re

from steamworks_types import flat_type, safe_name

def interface_name(classname: str | None) -> str | None:
    if not classname:
        return None
    if classname.startswith("ISteam"):
        return classname[len("ISteam") :]
    return classname


def infer_interface_from_wrapper(name: str) -> str:
    if name.startswith("Steam_GameServerNetworkingSockets_"):
        return "GameServerNetworkingSockets"
    if name.startswith("Steam_GameServerNetworkingMessages_"):
        return "GameServerNetworkingMessages"
    if name.startswith("Steam_GameServerHTTP_"):
        return "GameServerHTTP"
    if name.startswith("Steam_GameServer_"):
        return "GameServer"
    if name.startswith("Steam_ManualDispatch_"):
        return "ManualDispatch"
    if name.startswith("Steam_Lobby_"):
        return "Lobby"
    if name.startswith("Steam_LobbyType") or name.startswith("Steam_LobbyComparison"):
        return "LobbyConstants"
    if name.startswith("Steam_FriendFlag") or name.startswith("Steam_PersonaState"):
        return "FriendsConstants"
    if name.startswith("Steam_NetworkingSend_") or name.startswith("Steam_NetConnectionEnd_"):
        return "NetworkingConstants"
    if name.startswith("Steam_NetworkingConnectionState_"):
        return "NetworkingConstants"
    if name.startswith("Steam_"):
        remainder = name[len("Steam_") :]
        if remainder in {
            "Init",
            "InitEx",
            "InitFlat",
            "Shutdown",
            "ShutdownManualDispatch",
            "ClearHelperState",
            "RunCallbacks",
            "IsSteamRunning",
            "RestartAppIfNecessary",
            "ReleaseCurrentThreadMemory",
            "GetSteamInstallPath",
            "SetTryCatchCallbacks",
            "SetMiniDumpComment",
            "GetHSteamPipe",
            "GetHSteamUser",
            "GetCallbackDispatchMode",
            "GetLastInitResult",
            "GetLastInitError",
        }:
            return "Global/static"
        if remainder.startswith("CallbackDispatchMode") or remainder.startswith("ServerMode"):
            return "Global/static"
        return remainder.split("_", 1)[0]
    return "Global/static"


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
