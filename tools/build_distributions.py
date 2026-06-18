#!/usr/bin/env python3
"""Build an SDK-free sdist and a platform wheel from the source checkout."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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


def run_build(*args: str, env: dict[str, str]) -> None:
    subprocess.run(
        [sys.executable, "-m", "build", *args],
        cwd=ROOT,
        env=env,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the source archive without Valve SDK files and build the "
            "platform wheel directly from the checkout."
        )
    )
    parser.add_argument("--sdk-dir", help="Path to an authorized Steamworks SDK")
    parser.add_argument("--outdir", default="dist", help="Artifact output directory")
    parser.add_argument(
        "--no-isolation",
        action="store_true",
        help="Use the current Python environment for both builds",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove the output directory before building",
    )
    args = parser.parse_args()

    sdk_dir = resolve_sdk_dir(args.sdk_dir)
    outdir = (ROOT / args.outdir).resolve()
    if args.clean and outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["STEAMWORKS_SDK_DIR"] = str(sdk_dir)
    common_args = ["--outdir", str(outdir)]
    if args.no_isolation:
        common_args.extend(["--no-isolation", "--skip-dependency-check"])

    # Do not use bare `python -m build`: it builds the wheel from the sdist,
    # which intentionally contains no Valve SDK headers or binaries.
    run_build("--sdist", *common_args, env=env)
    run_build("--wheel", *common_args, env=env)

    print(f"Built distributions in {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
