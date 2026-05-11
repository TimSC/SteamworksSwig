#!/usr/bin/env python3
"""List Steam lobbies using the generated Python lobby call-result shim."""

from __future__ import annotations

import sys
import time

import steamworks


def pump_until(predicate, timeout_seconds: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        steamworks.Steam_RunCallbacks()
        if predicate():
            return True
        time.sleep(0.05)
    return False


def main() -> int:
    if not steamworks.Steam_IsSteamRunning():
        print("Steam is not running.", file=sys.stderr)
        return 1

    init_result = steamworks.Steam_InitEx()
    if init_result != 0:
        print(f"Steam_InitEx failed ({init_result}): {steamworks.Steam_GetLastInitError()}", file=sys.stderr)
        return 1

    try:
        steamworks.Steam_Lobby_RequestList()
        if not pump_until(steamworks.Steam_Lobby_IsListComplete):
            print("Timed out waiting for lobby list.", file=sys.stderr)
            return 1

        if steamworks.Steam_Lobby_ListHadIOFailure():
            print("Lobby list request failed with an IO failure.", file=sys.stderr)
            return 1

        count = steamworks.Steam_Lobby_GetListResultCount()
        print(f"Found {count} lobbies")
        for index in range(count):
            lobby_id = steamworks.Steam_Lobby_GetListLobbyByIndex(index)
            lobby_name = steamworks.Steam_Lobby_GetListLobbyNameByIndex(index)
            print(f"{index}: {lobby_id} {lobby_name}")
    finally:
        steamworks.Steam_Shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
