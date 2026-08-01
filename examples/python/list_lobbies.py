#!/usr/bin/env python3
"""Query Steam lobbies using the generated Python lobby call-result shim."""

from __future__ import annotations

import argparse
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-results", type=int, default=10, help="maximum lobby results to request")
    parser.add_argument("--timeout", type=float, default=10.0, help="seconds to wait for the lobby query")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not steamworks.is_steam_running():
        print("Steam is not running.", file=sys.stderr)
        return 1

    init_result = steamworks.init_ex()
    if init_result != 0:
        print(f"steamworks.init_ex() failed ({init_result}): {steamworks.last_init_error()}", file=sys.stderr)
        return 1

    try:
        steamworks.matchmaking.add_request_lobby_list_result_count_filter(args.max_results)
        steamworks.lobby.request_list()
        if not pump_until(steamworks.lobby.is_list_complete, args.timeout):
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
            members = steamworks.matchmaking.num_lobby_members(lobby_id)
            member_limit = steamworks.matchmaking.lobby_member_limit(lobby_id)
            owner_id = steamworks.matchmaking.lobby_owner(lobby_id)
            print(
                f"{index}: {lobby_id} "
                f"name={lobby_name!r} "
                f"members={members}/{member_limit} "
                f"owner={owner_id}"
            )
    finally:
        steamworks.shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
