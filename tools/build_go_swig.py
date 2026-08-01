#!/usr/bin/env python3
"""Generate and build an experimental Go/cgo SWIG wrapper."""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATED_DIR = ROOT / "generated"
DEFAULT_OUTDIR = ROOT / "go" / "steamworks" / "raw"
FRIENDLY_DIR = ROOT / "go" / "steamworks"

INITIALISMS = {
    "API",
    "DLC",
    "HTML",
    "HTTP",
    "IP",
    "UGC",
    "URL",
    "VR",
}

HAND_WRITTEN_METHODS = {
    "Apps": {"IsSubscribed"},
    "Friends": {"PersonaName"},
    "User": {"LoggedOn", "SteamID"},
    "Utils": {"AppID"},
}


def resolve_sdk_dir(value: str | None) -> Path:
    sdk_dir = Path(value or os.environ.get("STEAMWORKS_SDK_DIR", ROOT / "sdk"))
    sdk_dir = sdk_dir.expanduser().resolve()
    api_json = sdk_dir / "public" / "steam" / "steam_api.json"
    if not api_json.is_file():
        raise SystemExit(
            "Steamworks SDK not found. Pass --sdk-dir or set STEAMWORKS_SDK_DIR.\n"
            f"Expected: {api_json}"
        )
    return sdk_dir


def platform_library_dir(sdk_dir: Path) -> tuple[Path, str, str]:
    system = platform.system()
    redistributable_dir = sdk_dir / "redistributable_bin"
    if system == "Linux":
        machine = platform.machine().lower()
        if machine in {"aarch64", "arm64"}:
            return redistributable_dir / "linuxarm64", "steam_api", "linux"
        if machine in {"i386", "i686", "x86"}:
            return redistributable_dir / "linux32", "steam_api", "linux"
        return redistributable_dir / "linux64", "steam_api", "linux"
    if system == "Darwin":
        return redistributable_dir / "osx", "steam_api", "darwin"
    if system == "Windows":
        if platform.architecture()[0] == "64bit":
            return redistributable_dir / "win64", "steam_api64", "windows"
        return redistributable_dir, "steam_api", "windows"
    raise SystemExit(f"Unsupported platform for Steamworks SDK: {system}")


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def write_go_interface(outdir: Path) -> Path:
    interface = outdir / "steamworks_go.i"
    interface.write_text(
        "\n".join(
            [
                "%module raw",
                "%{",
                '#include "steamworks_c_api.h"',
                "%}",
                "%include \"stdint.i\"",
                "%include \"steamworks_c_api.h\"",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return interface


def write_cgo_flags(outdir: Path, sdk_dir: Path) -> None:
    include_dir = sdk_dir / "public"
    lib_dir, library, goos = platform_library_dir(sdk_dir)
    if not lib_dir.is_dir():
        raise SystemExit(f"Steamworks redistributable directory not found: {lib_dir}")

    lines = [
        "package raw",
        "",
        "/*",
        f"#cgo CFLAGS: -I{include_dir.as_posix()} -I${{SRCDIR}}",
        f"#cgo CXXFLAGS: -std=c++17 -I{include_dir.as_posix()} -I${{SRCDIR}}",
    ]
    if goos in {"linux", "darwin"}:
        lines.append(
            f"#cgo {goos} LDFLAGS: -L{lib_dir.as_posix()} -l{library} -lstdc++ -Wl,-rpath,{lib_dir.as_posix()}"
        )
    else:
        lines.append(f"#cgo windows LDFLAGS: -L{lib_dir.as_posix()} -l{library} -lstdc++")
    lines.extend(
        [
            "*/",
            'import "C"',
            "",
        ]
    )
    (outdir / "cgo_flags.go").write_text("\n".join(lines), encoding="utf-8")


def copy_generated_sources(outdir: Path) -> None:
    for filename in [
        "steamworks_c_api.cpp",
        "steamworks_c_api.h",
        "steamworks_swig_shim.cpp",
        "steamworks_swig_shim.h",
    ]:
        shutil.copy2(GENERATED_DIR / filename, outdir / filename)


def split_camel(value: str) -> list[str]:
    return re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|\d+", value)


def go_identifier(value: str) -> str:
    if value.startswith("P2P"):
        return "P2P" + go_identifier(value[len("P2P"):])
    words = split_camel(value)
    if not words:
        return value
    converted = []
    for word in words:
        upper = word.upper()
        if upper in INITIALISMS:
            converted.append(upper)
        else:
            converted.append(word[:1].upper() + word[1:])
    return "".join(converted)


def receiver_type_name(interface_name: str) -> str:
    return interface_name[:1].lower() + interface_name[1:] + "API"


def wrapper_method_name(raw_method_name: str) -> str:
    if (
        raw_method_name.startswith("B")
        and len(raw_method_name) > 1
        and raw_method_name[1].isupper()
    ):
        raw_method_name = raw_method_name[1:]
    return go_identifier(raw_method_name)


def parse_go_args(args: str) -> list[str]:
    args = args.strip()
    if not args:
        return []
    names = []
    for item in args.split(","):
        name = item.strip().split(" ", 1)[0]
        if name:
            names.append(name)
    return names


def write_friendly_generated_wrappers(raw_go: Path) -> None:
    pattern = re.compile(
        r"^func (SWS_SteamAPI_ISteam([A-Za-z0-9]+)_([A-Za-z0-9_]+))"
        r"\(([^)]*)\)(?: \(_swig_ret ([^)]+)\))? \{"
    )
    interfaces: dict[str, list[dict[str, str | list[str] | None]]] = {}
    for line in raw_go.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        raw_name, interface_name, raw_method_name, args, return_type = match.groups()
        receiver = go_identifier(interface_name)
        method_name = wrapper_method_name(raw_method_name)
        if method_name in HAND_WRITTEN_METHODS.get(receiver, set()):
            continue
        interfaces.setdefault(receiver, []).append(
            {
                "raw_name": raw_name,
                "method_name": method_name,
                "args": args.strip(),
                "arg_names": parse_go_args(args),
                "return_type": return_type,
            }
        )

    lines = [
        "package steamworks",
        "",
        "// Code generated by tools/build_go_swig.py; DO NOT EDIT.",
        "",
        'import "github.com/TimSC/SteamworksSwig/go/steamworks/raw"',
        "",
    ]
    for receiver in sorted(interfaces):
        receiver_type = receiver_type_name(receiver)
        if receiver not in HAND_WRITTEN_METHODS:
            lines.extend(
                [
                    f"type {receiver_type} struct{{}}",
                    "",
                    f"var {receiver} {receiver_type}",
                    "",
                ]
            )
        for method in sorted(interfaces[receiver], key=lambda item: str(item["method_name"])):
            args = method["args"]
            return_type = method["return_type"]
            arg_names = ", ".join(method["arg_names"])
            raw_call = f'raw.{method["raw_name"]}({arg_names})'
            signature_return = f" {return_type}" if return_type else ""
            lines.append(f'func ({receiver_type}) {method["method_name"]}({args}){signature_return} {{')
            if return_type:
                lines.append(f"\treturn {raw_call}")
            else:
                lines.append(f"\t{raw_call}")
            lines.extend(["}", ""])

    callback_pattern = re.compile(
        r"^func (SWS_Steam_ManualDispatch_CallbackID([A-Za-z0-9]+))"
        r"\(\) \(_swig_ret int\) \{"
    )
    callback_methods = []
    for line in raw_go.read_text(encoding="utf-8").splitlines():
        match = callback_pattern.match(line)
        if not match:
            continue
        raw_name, callback_name = match.groups()
        callback_methods.append((go_identifier(callback_name), raw_name))

    for callback_name, raw_name in sorted(callback_methods):
        lines.extend(
            [
                f"func CallbackID{callback_name}() CallbackID {{",
                f"\treturn CallbackID(raw.{raw_name}())",
                "}",
                "",
            ]
        )

    FRIENDLY_DIR.mkdir(parents=True, exist_ok=True)
    (FRIENDLY_DIR / "generated.go").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate an experimental Go SWIG package from the C ABI layer."
    )
    parser.add_argument("--sdk-dir", help="Path to an authorized Steamworks SDK")
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR), help="Go package output directory")
    parser.add_argument("--skip-build", action="store_true", help="Generate files but do not run go test")
    args = parser.parse_args()

    sdk_dir = resolve_sdk_dir(args.sdk_dir)
    outdir = Path(args.outdir).expanduser()
    if not outdir.is_absolute():
        outdir = (ROOT / outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    api_json = sdk_dir / "public" / "steam" / "steam_api.json"
    steam_include = sdk_dir / "public"
    run(
        [
            sys.executable,
            str(ROOT / "tools" / "generate_swig_shim.py"),
            "--api-json",
            str(api_json),
            "--steam-include",
            str(steam_include),
            "--output-dir",
            str(GENERATED_DIR),
        ],
        cwd=ROOT,
    )
    copy_generated_sources(outdir)
    interface = write_go_interface(outdir)
    write_cgo_flags(outdir, sdk_dir)

    run(
        [
            "swig",
            "-go",
            "-cgo",
            "-intgosize",
            "64",
            "-package",
            "raw",
            f"-I{outdir}",
            "-outdir",
            str(outdir),
            "-o",
            str(outdir / "steamworks_go_wrap.c"),
            str(interface),
        ],
        cwd=ROOT,
    )
    write_friendly_generated_wrappers(outdir / "raw.go")

    if not args.skip_build:
        env = os.environ.copy()
        env.setdefault("GOCACHE", str(Path("/tmp") / "steamworks-swig-go-build-cache"))
        run(["go", "test", "./go/..."], cwd=ROOT, env=env)

    print(f"Generated Go SWIG package in {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
