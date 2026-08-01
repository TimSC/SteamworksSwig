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


def parse_payload(data: str | None) -> dict[str, str]:
    fields = {}
    if not data:
        return fields
    for part in data.split("\t"):
        key, separator, value = part.partition("=")
        if separator:
            fields[key] = value
    return fields


def pump_manual_lobby_list(api_call: int, timeout_seconds: float = 10.0):
    pipe = steamworks.h_steam_pipe()
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        steamworks.manual_dispatch.run_frame(pipe)
        while steamworks.manual_dispatch.next_callback(pipe):
            try:
                if (
                    steamworks.manual_dispatch.callback_is_api_call_completed()
                    and steamworks.manual_dispatch.completed_api_call() == api_call
                    and steamworks.manual_dispatch.completed_callback_id()
                    == steamworks.manual_dispatch.callback_id_lobby_match_list()
                ):
                    steamworks.manual_dispatch.api_call_result(
                        pipe,
                        api_call,
                        steamworks.manual_dispatch.completed_callback_size(),
                        steamworks.manual_dispatch.completed_callback_id(),
                    )
                    failed = steamworks.manual_dispatch.api_call_result_failed()
                    payload = steamworks.manual_dispatch.decode_api_call_result_lobby_match_list()
                    return True, failed, parse_payload(payload)
            finally:
                steamworks.manual_dispatch.free_last_callback(pipe)
        time.sleep(0.05)
    return False, False, {}


def print_lobbies(count: int, *, use_auto_helpers: bool) -> None:
    print(f"Found {count} lobbies")
    for index in range(count):
        if use_auto_helpers:
            lobby_id = steamworks.lobby.list_lobby_by_index(index)
            lobby_name = steamworks.lobby.list_lobby_name_by_index(index)
        else:
            lobby_id = steamworks.matchmaking.lobby_by_index(index)
            lobby_name = steamworks.matchmaking.lobby_data(lobby_id, "name")
        members = steamworks.matchmaking.num_lobby_members(lobby_id)
        member_limit = steamworks.matchmaking.lobby_member_limit(lobby_id)
        owner_id = steamworks.matchmaking.lobby_owner(lobby_id)
        print(
            f"{index}: {lobby_id} "
            f"name={lobby_name!r} "
            f"members={members}/{member_limit} "
            f"owner={owner_id}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dispatch", choices=("auto", "manual"), default="auto", help="callback dispatch mode")
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
        if args.dispatch == "manual":
            steamworks.manual_dispatch.init()
            steamworks.matchmaking.add_request_lobby_list_result_count_filter(args.max_results)
            api_call = steamworks.matchmaking.request_lobby_list()
            completed, failed, fields = pump_manual_lobby_list(api_call, args.timeout)
            if not completed:
                print("Timed out waiting for lobby list.", file=sys.stderr)
                return 1
            if failed:
                print("Lobby list request failed with an IO failure.", file=sys.stderr)
                return 1
            print_lobbies(int(fields.get("lobbies_matching", "0")), use_auto_helpers=False)
        else:
            steamworks.matchmaking.add_request_lobby_list_result_count_filter(args.max_results)
            steamworks.lobby.request_list()
            if not pump_until(steamworks.lobby.is_list_complete, args.timeout):
                print("Timed out waiting for lobby list.", file=sys.stderr)
                return 1
            if steamworks.lobby.list_had_io_failure():
                print("Lobby list request failed with an IO failure.", file=sys.stderr)
                return 1
            print_lobbies(steamworks.lobby.list_result_count(), use_auto_helpers=True)
    finally:
        if args.dispatch == "manual":
            steamworks.shutdown_manual_dispatch()
        else:
            steamworks.shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
