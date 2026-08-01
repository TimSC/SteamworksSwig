"""Shared Steamworks C ABI model assembly helpers."""

from __future__ import annotations

from collections import Counter

from steamworks_discovery import infer_interface_from_wrapper, interface_accessor, interface_name
from steamworks_types import (
    api_enum_names,
    api_typedef_map,
    normalize_type,
    resolve_c_type,
    swig_safe_type,
    unsupported_type_reason,
)

def sdk_method_key(classname: str | None, flat_name: str | None, methodname: str | None) -> tuple[str | None, str | None, str | None]:
    return classname, flat_name, methodname


def classify_skipped_methods(
    api: dict,
    flat_identifiers: set[str],
    c_methods: list[dict],
) -> list[dict]:
    typedefs = api_typedef_map(api)
    enums = api_enum_names(api)
    supported = {
        sdk_method_key(method.get("classname"), method.get("sdk_flat_name"), method.get("sdk_method_name"))
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
        "helper_name": method["wrapper_name"],
        "raw_c_name": c_wrapper_name(method),
        "helper_return_type": return_type,
        "return_type": c_return_type,
        "classname": method.get("classname"),
        "friendly_name": method.get("methodname"),
        "sdk_method_name": method.get("methodname"),
        "sdk_flat_name": method.get("flat_name"),
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
        result["friendly_name"] = name.removeprefix(f"Steam_{result['interface']}_")
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
    return sorted(manual + helpers + manual_dispatch + generated, key=lambda item: item["raw_c_name"])


def method_friendly_name(method: dict) -> str:
    return method.get("friendly_name") or method["helper_name"]


def method_language_support(method: dict) -> str:
    c_types = [method["return_type"]]
    c_types.extend(param["c_type"] for param in method["params"])
    special_types = {c_type for c_type in c_types if c_type.startswith("SWS_")}
    if not special_types:
        return "scalar"
    if special_types <= {"SWS_String"}:
        return "scalar_string"
    if special_types <= {"SWS_String", "SWS_StringList"}:
        return "string_list"
    if special_types <= {"SWS_Bytes", "SWS_BytesList"}:
        return "bytes_or_bytes_list"
    return "mixed_helper_result"


def method_callback_safe(method: dict) -> bool:
    return method.get("source") != "manual_dispatch"


def disambiguate_names(
    candidates: list,
    *,
    key,
    name,
    fallback_name,
) -> list[tuple[object, str]]:
    counts = Counter((key(candidate), name(candidate)) for candidate in candidates)
    result = []
    for candidate in candidates:
        candidate_key = key(candidate)
        candidate_name = name(candidate)
        if counts[(candidate_key, candidate_name)] > 1:
            candidate_name = fallback_name(candidate)
        result.append((candidate, candidate_name))
    return result


def model_methods(model: dict) -> list[dict]:
    return model.get("methods", [])


def raw_c_name(method: dict) -> str:
    return method["raw_c_name"]


def method_return_type(method: dict) -> str:
    return method["return_type"]


def helper_name(method: dict) -> str:
    return method["helper_name"]


def helper_return_type(method: dict) -> str:
    return method["helper_return_type"]


def friendly_name(method: dict) -> str | None:
    return method.get("friendly_name")


def method_params(method: dict) -> list[dict]:
    return method.get("params", [])


def c_api_model(
    api: dict,
    c_methods: list[dict],
    skipped_methods: list[dict],
    *,
    generated_wrappers: list[dict] | None = None,
    output_helpers: list[dict] | None = None,
    template_features: dict | None = None,
) -> dict:
    sdk_methods = [method for method in c_methods if method.get("source") == "sdk"]
    return {
        "schema_version": 5,
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
        "generated_wrappers": generated_wrappers or [],
        "output_helpers": output_helpers or [],
        "template_features": template_features or {},
        "methods": [
            {
                "raw_c_name": method["raw_c_name"],
                "friendly_name": method_friendly_name(method),
                "return_type": method["return_type"],
                "helper_name": method["helper_name"],
                "helper_return_type": method["helper_return_type"],
                "interface": method.get("interface"),
                "classname": method.get("classname"),
                "sdk_method_name": method.get("sdk_method_name"),
                "sdk_flat_name": method.get("sdk_flat_name"),
                "source": method.get("source", "sdk"),
                "callback_safe": method_callback_safe(method),
                "language_support": method_language_support(method),
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
