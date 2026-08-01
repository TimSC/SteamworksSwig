#!/usr/bin/env python3
"""List Steam lobbies using the generated Python lobby call-result shim."""

from __future__ import annotations

import sys
import time

import steamworks


def pump_until(predicate, timeout_seconds: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        steamworks.run_callbacks()
        if predicate():
            return True
        time.sleep(0.05)
    return False


def main() -> int:
    if not steamworks.is_steam_running():
        print("Steam is not running.", file=sys.stderr)
        return 1

    init_result = steamworks.init_ex()
    if init_result != 0:
        print(f"steamworks.init_ex() failed ({init_result}): {steamworks.last_init_error()}", file=sys.stderr)
        return 1

    try:
        steamworks.lobby.request_list()
        if not pump_until(steamworks.lobby.is_list_complete):
            print("Timed out waiting for lobby list.", file=sys.stderr)
            return 1

        if steamworks.lobby.list_had_io_failure():
            print("Lobby list request failed with an IO failure.", file=sys.stderr)
            return 1

        count = steamworks.lobby.list_result_count()
        print(f"Found {count} lobbies")
        for index in range(count):
            lobby_id = steamworks.lobby.list_lobby_by_index(index)
            lobby_name = steamworks.lobby.list_lobby_name_by_index(index)
            print(f"{index}: {lobby_id} {lobby_name}")
    finally:
        steamworks.shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
