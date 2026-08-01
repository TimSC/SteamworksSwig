#!/usr/bin/env python3
"""Generate C ABI header/source files from the shared Steamworks model."""

from __future__ import annotations

import argparse
from pathlib import Path

from generator_io import load_json, render_template, write_text
from steamworks_model import helper_name, helper_return_type, method_params, method_return_type, raw_c_name


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "generated" / "steamworks_c_api_model.json"
DEFAULT_OUTPUT_DIR = ROOT / "generated"


def c_signature(method: dict) -> str:
    params = ", ".join(
        f'{param["c_type"]} {param["name"]}' for param in method_params(method)
    )
    if not params:
        params = "void"
    return f'{method_return_type(method)} {raw_c_name(method)}( {params} )'


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
        for param in method_params(method)
    )
    expression = f'{helper_name(method)}( {args} )' if args else f'{helper_name(method)}()'
    lines = [
        c_signature(method),
        "{",
        "\ttry",
        "\t{",
        c_return(expression, method_return_type(method), helper_return_type(method)),
        "\t}",
        "\tcatch ( const std::exception & )",
        "\t{",
        c_default_return(method_return_type(method)),
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
    write_text(output_dir / "steamworks_c_api.h", render_c_header(model))
    write_text(output_dir / "steamworks_c_api.cpp", render_c_source(model))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="Path to steamworks_c_api_model.json")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for C ABI files")
    args = parser.parse_args()

    model = load_json(Path(args.model))
    write_c_abi_files(model, Path(args.output_dir))
    print(f"Wrote C ABI files in {Path(args.output_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
