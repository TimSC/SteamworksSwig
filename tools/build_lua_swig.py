#!/usr/bin/env python3
"""Generate and build a Lua SWIG wrapper from the C ABI layer."""

from __future__ import annotations

import argparse
import os
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from generate_lua import write_lua_wrappers


ROOT = Path(__file__).resolve().parents[1]
GENERATED_DIR = ROOT / "generated"
DEFAULT_OUTDIR = ROOT / "lua"


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


def run(command: list[str], *, cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def command_output(command: list[str], *, cwd: Path) -> str:
    return subprocess.check_output(command, cwd=cwd, text=True).strip()


def pkg_config_flags(package: str) -> tuple[list[str], list[str]]:
    try:
        cflags = shlex.split(command_output(["pkg-config", "--cflags", package], cwd=ROOT))
        libs = shlex.split(command_output(["pkg-config", "--libs", package], cwd=ROOT))
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise SystemExit(
            f"Could not resolve Lua compiler flags with pkg-config package {package!r}. "
            "Pass --lua-pkg-config with an installed Lua package name."
        ) from exc
    return cflags, libs


def copy_generated_sources(outdir: Path) -> None:
    for filename in [
        "steamworks_c_api.cpp",
        "steamworks_c_api.h",
        "steamworks_helpers.cpp",
        "steamworks_helpers.h",
    ]:
        shutil.copy2(GENERATED_DIR / filename, outdir / filename)


def write_lua_interface(outdir: Path) -> Path:
    interface = outdir / "steamworks_lua.i"
    interface.write_text(
        "\n".join(
            [
                "%module steamworks_raw",
                "%{",
                '#include "steamworks_c_api.h"',
                "%}",
                "",
                "%include \"stdint.i\"",
                "",
                "%typemap(out) SWS_String {",
                "    lua_pushlstring(L, $1.data ? $1.data : \"\", $1.size);",
                "    SWS_FreeString($1);",
                "    SWIG_arg++;",
                "}",
                "",
                "%typemap(out) SWS_StringList {",
                "    lua_newtable(L);",
                "    for (size_t i = 0; i < $1.size; ++i) {",
                "        SWS_String item = $1.items[i];",
                "        lua_pushinteger(L, static_cast<lua_Integer>(i + 1));",
                "        lua_pushlstring(L, item.data ? item.data : \"\", item.size);",
                "        lua_settable(L, -3);",
                "    }",
                "    SWS_FreeStringList($1);",
                "    SWIG_arg++;",
                "}",
                "",
                "%typemap(out) SWS_Bytes {",
                "    lua_pushlstring(L, reinterpret_cast<const char *>($1.data), $1.size);",
                "    SWS_FreeBytes($1);",
                "    SWIG_arg++;",
                "}",
                "",
                "%typemap(out) SWS_BytesList {",
                "    lua_newtable(L);",
                "    for (size_t i = 0; i < $1.size; ++i) {",
                "        SWS_Bytes item = $1.items[i];",
                "        lua_pushinteger(L, static_cast<lua_Integer>(i + 1));",
                "        lua_pushlstring(L, reinterpret_cast<const char *>(item.data), item.size);",
                "        lua_settable(L, -3);",
                "    }",
                "    SWS_FreeBytesList($1);",
                "    SWIG_arg++;",
                "}",
                "",
                "%typemap(in) (const uint8_t * data, size_t dataSize) (size_t length = 0) {",
                "    $1 = const_cast<uint8_t *>(reinterpret_cast<const uint8_t *>(luaL_checklstring(L, $input, &length)));",
                "    $2 = length;",
                "}",
                "",
                "%include \"steamworks_c_api.h\"",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return interface


def shared_output_path(outdir: Path) -> Path:
    if platform.system() == "Windows":
        return outdir / "steamworks_raw.dll"
    return outdir / "steamworks_raw.so"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-dir", help="Path to an authorized Steamworks SDK")
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR), help="Lua output directory")
    parser.add_argument(
        "--lua-pkg-config",
        default=os.environ.get("LUA_PKG_CONFIG", "lua5.3"),
        help="pkg-config package that provides Lua compiler/linker flags",
    )
    parser.add_argument("--debug", action="store_true", help="Compile the Lua module with debug symbols")
    parser.add_argument("--skip-build", action="store_true", help="Generate files but do not compile the Lua module")
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
            str(ROOT / "tools" / "generate_model.py"),
            "--api-json",
            str(api_json),
            "--steam-include",
            str(steam_include),
            "--output",
            str(GENERATED_DIR / "steamworks_c_api_model.json"),
        ],
        cwd=ROOT,
    )
    run(
        [
            sys.executable,
            str(ROOT / "tools" / "generate_core.py"),
            "--model",
            str(GENERATED_DIR / "steamworks_c_api_model.json"),
            "--output-dir",
            str(GENERATED_DIR),
        ],
        cwd=ROOT,
    )
    copy_generated_sources(outdir)
    interface = write_lua_interface(outdir)
    wrapper = outdir / "steamworks_lua_wrap.cpp"

    run(
        [
            "swig",
            "-lua",
            "-c++",
            f"-I{outdir}",
            "-o",
            str(wrapper),
            str(interface),
        ],
        cwd=ROOT,
    )
    write_lua_wrappers(
        GENERATED_DIR / "steamworks_c_api_model.json",
        outdir / "steamworks.lua",
    )

    if not args.skip_build:
        cflags, lua_libs = pkg_config_flags(args.lua_pkg_config)
        lib_dir, library, goos = platform_library_dir(sdk_dir)
        if not lib_dir.is_dir():
            raise SystemExit(f"Steamworks redistributable directory not found: {lib_dir}")
        output = shared_output_path(outdir)
        compile_command = [
            "c++",
            "-std=c++17",
            "-fPIC",
            "-shared",
            f"-I{steam_include}",
            f"-I{outdir}",
            *cflags,
            str(wrapper),
            str(outdir / "steamworks_c_api.cpp"),
            str(outdir / "steamworks_helpers.cpp"),
            f"-L{lib_dir}",
            f"-l{library}",
            *lua_libs,
            "-o",
            str(output),
        ]
        if args.debug:
            compile_command[1:1] = ["-g", "-O0"]
        if goos in {"linux", "darwin"}:
            compile_command.insert(-2, f"-Wl,-rpath,{lib_dir}")
        run(compile_command, cwd=ROOT)

    print(f"Generated Lua SWIG package in {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
