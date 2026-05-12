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
        )
        + "\n",
        encoding="utf-8",
    )

    source.write_text(
        render_template(
            "steamworks_swig_shim.cpp.in",
            generated_definitions=generated_definitions,
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
