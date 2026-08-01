"""Shared Steamworks SDK model and C ABI type helpers."""

from __future__ import annotations

import keyword
import re


SUPPORTED_POINTER_TYPES = {"const char *"}

INITIALISMS = {
    "API",
    "DLC",
    "HTML",
    "HTTP",
    "ID",
    "IP",
    "UGC",
    "URL",
    "VR",
}

FLAT_TYPEDEFS = {
    "uint64_steamid": "unsigned long long",
    "uint64_gameid": "unsigned long long",
}

C_TYPE_MAP = {
    "void": "void",
    "bool": "bool",
    "char": "char",
    "const char *": "const char *",
    "float": "float",
    "double": "double",
    "int": "int32_t",
    "unsigned int": "uint32_t",
    "short": "int16_t",
    "unsigned short": "uint16_t",
    "signed char": "int8_t",
    "unsigned char": "uint8_t",
    "long long": "int64_t",
    "unsigned long long": "uint64_t",
    "int8": "int8_t",
    "uint8": "uint8_t",
    "int16": "int16_t",
    "uint16": "uint16_t",
    "int32": "int32_t",
    "uint32": "uint32_t",
    "int64": "int64_t",
    "uint64": "uint64_t",
    "lint64": "int64_t",
    "ulint64": "uint64_t",
    "uint64_steamid": "uint64_t",
    "uint64_gameid": "uint64_t",
    "size_t": "size_t",
    "std::string": "SWS_String",
    "std::vector<std::string>": "SWS_StringList",
    "SteamworksBytes": "SWS_Bytes",
    "SteamworksBytesVector": "SWS_BytesList",
}


def normalize_type(type_name: str) -> str:
    return " ".join(type_name.replace(" *", "*").replace("*", " *").split())


def split_words(value: str) -> list[str]:
    return re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|\d+", value)


def python_snake_name(value: str, *, drop_get: bool = True) -> str:
    value = value.replace("SWS_", "")
    if value.startswith("SteamAPI_ISteam"):
        value = value.split("_", 2)[-1]
    if value.startswith("Steam_"):
        value = value[len("Steam_") :]
    if value.startswith("B") and len(value) > 1 and value[1].isupper():
        value = value[1:]
    if drop_get and value.startswith("Get") and len(value) > 3 and value[3].isupper():
        value = value[3:]
    words = split_words(value)
    if not words:
        result = value.lower()
    else:
        result = "_".join(word.lower() for word in words)
    if keyword.iskeyword(result):
        return result + "_"
    return result


def swig_safe_type(type_name: str) -> str | None:
    type_name = normalize_type(type_name)
    if "&" in type_name or "[" in type_name or "]" in type_name:
        return None
    if "*" in type_name and type_name not in SUPPORTED_POINTER_TYPES:
        return None
    if type_name.startswith("ISteam"):
        return None
    return type_name


def unsupported_type_reason(type_name: str) -> str:
    type_name = normalize_type(type_name)
    if not type_name:
        return "missing_type"
    if "(" in type_name or ")" in type_name:
        return "function_pointer"
    if "[" in type_name or "]" in type_name:
        return "array_type"
    if "&" in type_name:
        return "reference_type"
    if type_name.startswith("ISteam"):
        return "interface_pointer"
    if "*" in type_name and type_name not in SUPPORTED_POINTER_TYPES:
        return "pointer_output_or_unsupported_pointer"
    return "unsupported_c_type"


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


def api_typedef_map(api: dict) -> dict[str, str]:
    typedefs = dict(C_TYPE_MAP)
    for item in api.get("typedefs", []):
        alias = item.get("typedef")
        target = item.get("type")
        if not alias or not target:
            continue
        typedefs[alias] = normalize_type(target)
    for alias, target in FLAT_TYPEDEFS.items():
        typedefs[alias] = normalize_type(target)
    return typedefs


def api_enum_names(api: dict) -> set[str]:
    return {
        item["enumname"]
        for item in api.get("enums", [])
        if item.get("enumname")
    }


def resolve_c_type(type_name: str, typedefs: dict[str, str], enums: set[str]) -> str | None:
    type_name = normalize_type(type_name)
    if type_name.startswith("const ") and "*" not in type_name:
        type_name = type_name[len("const ") :]
    if type_name in enums:
        return "int32_t"
    if type_name in C_TYPE_MAP:
        return C_TYPE_MAP[type_name]

    seen = set()
    current = type_name
    while current in typedefs and current not in seen:
        seen.add(current)
        current = normalize_type(typedefs[current])
        if current in enums:
            return "int32_t"
        if current in C_TYPE_MAP:
            return C_TYPE_MAP[current]
        if "*" in current or "&" in current or "[" in current or "]" in current or "(" in current:
            return None

    return None


def sdk_method_key(classname: str | None, flat_name: str | None, methodname: str | None) -> tuple[str | None, str | None, str | None]:
    return classname, flat_name, methodname


def classify_skipped_methods(
    api: dict,
    flat_identifiers: set[str],
    c_methods: list[dict],
    interface_accessor,
) -> list[dict]:
    typedefs = api_typedef_map(api)
    enums = api_enum_names(api)
    supported = {
        sdk_method_key(method.get("classname"), method.get("flat_name"), method.get("methodname"))
        for method in c_methods
        if method.get("source") == "sdk"
    }
    skipped = []

    for interface in api.get("interfaces", []):
        classname = interface.get("classname")
        accessor = interface_accessor(interface, flat_identifiers)
        for method in interface.get("methods", []):
            methodname = method.get("methodname")
            flat_name = method.get("methodname_flat")
            key = sdk_method_key(classname, flat_name, methodname)
            if key in supported:
                continue

            reason = None
            detail = ""
            if not classname or not methodname:
                reason = "invalid_metadata"
            elif not accessor:
                reason = "no_flat_accessor"
            elif not flat_name:
                reason = "no_flat_method_name"
            elif flat_name not in flat_identifiers:
                reason = "flat_symbol_missing"

            return_type = method.get("returntype_flat", method.get("returntype", ""))
            params = method.get("params", [])
            if reason is None:
                safe_return = swig_safe_type(return_type)
                if safe_return is None:
                    reason = unsupported_type_reason(return_type)
                    detail = f"return {normalize_type(return_type)}"
                elif resolve_c_type(safe_return, typedefs, enums) is None:
                    reason = "unsupported_c_type"
                    detail = f"return {safe_return}"

            if reason is None:
                for index, param in enumerate(params):
                    param_type = param.get("paramtype_flat", param.get("paramtype", ""))
                    safe_param = swig_safe_type(param_type)
                    param_name = param.get("paramname") or f"arg{index}"
                    if safe_param is None:
                        reason = unsupported_type_reason(param_type)
                        detail = f"{param_name}: {normalize_type(param_type)}"
                        break
                    if resolve_c_type(safe_param, typedefs, enums) is None:
                        reason = "unsupported_c_type"
                        detail = f"{param_name}: {safe_param}"
                        break

            skipped.append(
                {
                    "interface": interface_name(classname),
                    "classname": classname,
                    "methodname": methodname,
                    "flat_name": flat_name,
                    "return_type": normalize_type(return_type),
                    "params": [
                        {
                            "name": param.get("paramname") or f"arg{index}",
                            "type": normalize_type(param.get("paramtype_flat", param.get("paramtype", ""))),
                        }
                        for index, param in enumerate(params)
                    ],
                    "reason": reason or "unknown",
                    "detail": detail,
                }
            )

    return sorted(
        skipped,
        key=lambda item: (
            str(item.get("interface") or ""),
            str(item.get("methodname") or ""),
            str(item.get("flat_name") or ""),
        ),
    )


def c_wrapper_name(method: dict) -> str:
    return f'SWS_{method.get("flat_name", method["wrapper_name"])}'


def c_method(
    method: dict,
    typedefs: dict[str, str],
    enums: set[str],
    *,
    source: str = "sdk",
) -> dict | None:
    return_type = method["return_type"]
    c_return_type = resolve_c_type(return_type, typedefs, enums)
    if c_return_type is None:
        return None

    params = []
    for param_type, param_name in method["params"]:
        c_param_type = resolve_c_type(param_type, typedefs, enums)
        if c_param_type is None:
            return None
        params.append(
            {
                "cpp_type": param_type,
                "c_type": c_param_type,
                "name": param_name,
            }
        )

    return {
        "cpp_name": method["wrapper_name"],
        "c_name": c_wrapper_name(method),
        "cpp_return_type": return_type,
        "c_return_type": c_return_type,
        "classname": method.get("classname"),
        "methodname": method.get("methodname"),
        "flat_name": method.get("flat_name"),
        "interface": interface_name(method.get("classname")),
        "source": source,
        "params": params,
    }


def c_manual_method(
    item: tuple,
    typedefs: dict[str, str],
    enums: set[str],
    *,
    source: str,
) -> dict | None:
    return_type, name, params = item
    method = {
        "wrapper_name": name,
        "return_type": normalize_type(return_type),
        "params": [(normalize_type(param_type), param_name) for param_type, param_name in params],
    }
    result = c_method(method, typedefs, enums, source=source)
    if result is not None:
        result["interface"] = infer_interface_from_wrapper(name)
        result["methodname"] = name.removeprefix(f"Steam_{result['interface']}_")
    return result


def c_api_methods(
    api: dict,
    methods: list[dict],
    *,
    manual_functions: list[tuple],
    helper_functions: list[tuple],
    manual_dispatch_functions: list[tuple],
) -> list[dict]:
    typedefs = api_typedef_map(api)
    enums = api_enum_names(api)
    manual = [
        method
        for item in manual_functions
        if (method := c_manual_method(item, typedefs, enums, source="manual")) is not None
    ]
    helpers = [
        method
        for item in helper_functions
        if (method := c_manual_method(item, typedefs, enums, source="helper")) is not None
    ]
    manual_dispatch = [
        method
        for item in manual_dispatch_functions
        if (method := c_manual_method(item, typedefs, enums, source="manual_dispatch")) is not None
    ]
    generated = [
        method
        for item in methods
        if (method := c_method(item, typedefs, enums, source="sdk")) is not None
    ]
    return sorted(manual + helpers + manual_dispatch + generated, key=lambda item: item["c_name"])


def c_api_model(api: dict, c_methods: list[dict], skipped_methods: list[dict]) -> dict:
    sdk_methods = [method for method in c_methods if method.get("source") == "sdk"]
    return {
        "schema_version": 2,
        "summary": {
            "sdk_methods_total": sum(
                len(interface.get("methods", []))
                for interface in api.get("interfaces", [])
            ),
            "sdk_methods_supported": len(sdk_methods),
            "sdk_methods_skipped": len(skipped_methods),
            "c_abi_functions_total": len(c_methods),
            "manual_functions": sum(1 for method in c_methods if method.get("source") == "manual"),
            "helper_functions": sum(1 for method in c_methods if method.get("source") == "helper"),
            "manual_dispatch_functions": sum(1 for method in c_methods if method.get("source") == "manual_dispatch"),
        },
        "methods": [
            {
                "c_name": method["c_name"],
                "c_return_type": method["c_return_type"],
                "cpp_name": method["cpp_name"],
                "cpp_return_type": method["cpp_return_type"],
                "interface": method.get("interface"),
                "classname": method.get("classname"),
                "methodname": method.get("methodname"),
                "flat_name": method.get("flat_name"),
                "source": method.get("source", "sdk"),
                "params": [
                    {
                        "name": param["name"],
                        "c_type": param["c_type"],
                        "cpp_type": param["cpp_type"],
                    }
                    for param in method["params"]
                ],
            }
            for method in c_methods
        ],
        "skipped_methods": skipped_methods,
    }
