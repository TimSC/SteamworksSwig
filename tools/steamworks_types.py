"""Steamworks type normalization and language naming helpers."""

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
    "const uint8_t *": "const uint8_t *",
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
