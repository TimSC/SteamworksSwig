#!/usr/bin/env python3
"""Generate C ABI header/source files from the shared Steamworks model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "tools" / "templates"
DEFAULT_MODEL = ROOT / "generated" / "steamworks_c_api_model.json"
DEFAULT_OUTPUT_DIR = ROOT / "generated"


def render_template(template_name: str, **values: str) -> str:
    rendered = (TEMPLATE_DIR / template_name).read_text(encoding="utf-8")
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{ {key} }}}}", value)
    return rendered


def c_signature(method: dict) -> str:
    params = ", ".join(
        f'{param["c_type"]} {param["name"]}' for param in method["params"]
    )
    if not params:
        params = "void"
    return f'{method["c_return_type"]} {method["c_name"]}( {params} )'


def c_declaration(method: dict) -> str:
    return f"SWS_API {c_signature(method)};"


def c_argument(param_type: str, param_name: str, c_type: str) -> str:
    if c_type == param_type:
        return param_name
    if param_type == "const char *":
        return param_name
    return f"static_cast<{param_type}>( {param_name} )"


def c_return(expression: str, c_type: str, cpp_type: str) -> str:
    if cpp_type == "void":
        return f"\t\t{expression};"
    if c_type == "SWS_String":
        return f"\t\treturn CopyStringForC( {expression} );"
    if c_type == "SWS_StringList":
        return f"\t\treturn CopyStringListForC( {expression} );"
    if c_type == "SWS_Bytes":
        return f"\t\treturn CopyBytesForC( {expression} );"
    if c_type == "SWS_BytesList":
        return f"\t\treturn CopyBytesListForC( {expression} );"
    if c_type == cpp_type:
        return f"\t\treturn {expression};"
    return f"\t\treturn static_cast<{c_type}>( {expression} );"


def c_default_return(c_type: str) -> str:
    if c_type == "void":
        return "\t\treturn;"
    if c_type == "bool":
        return "\t\treturn false;"
    if c_type == "const char *":
        return "\t\treturn EmptyCString();"
    return "\t\treturn {};"


def c_definition(method: dict) -> str:
    args = ", ".join(
        c_argument(param["cpp_type"], param["name"], param["c_type"])
        for param in method["params"]
    )
    expression = f'{method["cpp_name"]}( {args} )' if args else f'{method["cpp_name"]}()'
    lines = [
        c_signature(method),
        "{",
        "\ttry",
        "\t{",
        c_return(expression, method["c_return_type"], method["cpp_return_type"]),
        "\t}",
        "\tcatch ( const std::exception & )",
        "\t{",
        c_default_return(method["c_return_type"]),
        "\t}",
        "}",
    ]
    return "\n".join(lines)


def render_c_header(model: dict) -> str:
    return (
        render_template(
            "steamworks_c_api.h.in",
            c_declarations="\n".join(c_declaration(method) for method in model["methods"]),
        )
        + "\n"
    )


def render_c_source(model: dict) -> str:
    return (
        render_template(
            "steamworks_c_api.cpp.in",
            c_definitions="\n\n".join(c_definition(method) for method in model["methods"]),
        )
        + "\n"
    )


def write_c_abi_files(model: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "steamworks_c_api.h").write_text(render_c_header(model), encoding="utf-8")
    (output_dir / "steamworks_c_api.cpp").write_text(render_c_source(model), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="Path to steamworks_c_api_model.json")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for C ABI files")
    args = parser.parse_args()

    model = json.loads(Path(args.model).read_text(encoding="utf-8"))
    write_c_abi_files(model, Path(args.output_dir))
    print(f"Wrote C ABI files in {Path(args.output_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
