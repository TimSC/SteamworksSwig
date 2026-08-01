#!/usr/bin/env python3
"""Generate and build an experimental Go/cgo SWIG wrapper."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from generate_go import write_go_wrappers


ROOT = Path(__file__).resolve().parents[1]
GENERATED_DIR = ROOT / "generated"
DEFAULT_OUTDIR = ROOT / "go" / "steamworks" / "raw"
FRIENDLY_DIR = ROOT / "go" / "steamworks"


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
        "steamworks_helpers.cpp",
        "steamworks_helpers.h",
    ]:
        shutil.copy2(GENERATED_DIR / filename, outdir / filename)


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
            str(ROOT / "tools" / "generate_core.py"),
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
    write_go_wrappers(
        GENERATED_DIR / "steamworks_c_api_model.json",
        FRIENDLY_DIR / "generated.go",
    )

    if not args.skip_build:
        env = os.environ.copy()
        env.setdefault("GOCACHE", str(Path("/tmp") / "steamworks-swig-go-build-cache"))
        run(["go", "test", "./go/..."], cwd=ROOT, env=env)

    print(f"Generated Go SWIG package in {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
