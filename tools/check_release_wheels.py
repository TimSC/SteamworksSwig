#!/usr/bin/env python3
"""Check that release wheels contain a runtime and no SDK source material."""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
from zipfile import ZipFile


def check_wheel(path: Path) -> None:
    platform_tag = path.stem.rsplit("-", 1)[-1]
    if platform_tag == "win_amd64":
        runtime = "steam_api64.dll"
    elif platform_tag.startswith("macosx_"):
        runtime = "libsteam_api.dylib"
    else:
        runtime = "libsteam_api.so"
    with ZipFile(path) as archive:
        names = archive.namelist()
    if f"steamworks/{runtime}" not in names:
        raise ValueError(f"{path.name}: missing bundled {runtime}")
    for name in names:
        member = PurePosixPath(name)
        if (
            any(part == "sdk" or part.startswith(("sdk_", "_steamworks_sdk")) for part in member.parts)
            or member.suffix.lower() in {".h", ".hpp", ".lib", ".cpp", ".c"}
            or member.name == "steam_api.json"
        ):
            raise ValueError(f"{path.name}: forbidden SDK/build file: {name}")
    print(f"Checked {path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheelhouse", type=Path)
    args = parser.parse_args()
    wheels = sorted(args.wheelhouse.glob("*.whl"))
    if not wheels:
        parser.error(f"No wheels found in {args.wheelhouse}")
    for wheel in wheels:
        check_wheel(wheel)


if __name__ == "__main__":
    main()
