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

    if not steamworks.Steam_IsSteamRunning():
        print("Steam_IsSteamRunning returned false.", file=sys.stderr)
        print("Start Steam, log in, then run this program again from this directory.", file=sys.stderr)
        return 1

    if not steamworks.Steam_Init():
        print("Steam_Init failed.", file=sys.stderr)
        print("Make sure Steam is running and steam_appid.txt is in the working directory.", file=sys.stderr)
        return 1

    try:
        steamworks.Steam_RunCallbacks()

        print("Hello from Steamworks!")
        print(f"App ID: {steamworks.Steam_Utils_GetAppID()}")
        print(f"Logged on: {yes_no(steamworks.Steam_User_BLoggedOn())}")
        print(f"Persona name: {steamworks.Steam_Friends_GetPersonaName()}")
        print(f"Steam ID: {steamworks.Steam_User_GetSteamID()}")
        print(f"Subscribed to app: {yes_no(steamworks.Steam_Apps_BIsSubscribed())}")
    finally:
        steamworks.Steam_Shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
