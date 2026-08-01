#!/usr/bin/env python3
"""Basic Steamworks smoke test using the generated SWIG Python wrapper."""

from __future__ import annotations

import sys


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def main() -> int:
    try:
        import steamworks
    except ImportError as exc:
        print(f"Failed to import steamworks wrapper: {exc}", file=sys.stderr)
        print("Install it first with `pip install .` from this directory.", file=sys.stderr)
        return 1

    if not steamworks.is_steam_running():
        print("steamworks.is_steam_running() returned false.", file=sys.stderr)
        print("Start Steam, log in, then run this program again from this directory.", file=sys.stderr)
        return 1

    init_result = steamworks.init_ex()
    if init_result != 0:
        print(f"steamworks.init_ex() failed ({init_result}): {steamworks.last_init_error()}", file=sys.stderr)
        print("Make sure Steam is running and steam_appid.txt is in the working directory.", file=sys.stderr)
        return 1

    try:
        steamworks.run_callbacks()

        print("Hello from Steamworks!")
        print(f"App ID: {steamworks.utils.app_id()}")
        print(f"Logged on: {yes_no(steamworks.user.logged_on())}")
        print(f"Persona name: {steamworks.friends.persona_name()}")
        print(f"Steam ID: {steamworks.user.steam_id()}")
        print(f"Subscribed to app: {yes_no(steamworks.apps.is_subscribed())}")
    finally:
        steamworks.shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
