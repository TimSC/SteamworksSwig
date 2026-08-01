#!/usr/bin/env python3
"""Exercise Friends.EnumerateFollowingList with automatic or manual dispatch."""

from __future__ import annotations

import argparse
import sys
import time

import steamworks


def parse_payload(data: str | None) -> dict[str, str]:
    fields = {}
    if not data:
        return fields
    for part in data.split("\t"):
        key, separator, value = part.partition("=")
        if separator:
            fields[key] = value
    return fields


def wait_for_auto_api_call(api_call: int, timeout_seconds: float):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        steamworks.run_callbacks()
        payload = steamworks.utils.is_api_call_completed_string(api_call)
        if payload:
            return True, parse_payload(payload), payload
        time.sleep(0.05)
    return False, {}, ""


def wait_for_manual_api_call(api_call: int, timeout_seconds: float):
    pipe = steamworks.h_steam_pipe()
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        steamworks.manual_dispatch.run_frame(pipe)
        while steamworks.manual_dispatch.next_callback(pipe):
            try:
                if (
                    steamworks.manual_dispatch.callback_is_api_call_completed()
                    and steamworks.manual_dispatch.completed_api_call() == api_call
                ):
                    steamworks.manual_dispatch.api_call_result(
                        pipe,
                        api_call,
                        steamworks.manual_dispatch.completed_callback_size(),
                        steamworks.manual_dispatch.completed_callback_id(),
                    )
                    return True, {
                        "callback_id": str(steamworks.manual_dispatch.completed_callback_id()),
                        "failed": str(steamworks.manual_dispatch.api_call_result_failed()).lower(),
                    }
            finally:
                steamworks.manual_dispatch.free_last_callback(pipe)
        time.sleep(0.05)
    return False, {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dispatch", choices=("auto", "manual"), default="auto", help="callback dispatch mode")
    parser.add_argument("--start-index", type=int, default=0, help="following-list start index")
    parser.add_argument("--timeout", type=float, default=10.0, help="seconds to wait for completion")
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

        api_call = steamworks.friends.enumerate_following_list(args.start_index)
        print(f"Friends.EnumerateFollowingList call: {api_call}")
        if not api_call:
            print("Friends.EnumerateFollowingList returned an invalid SteamAPICall_t.", file=sys.stderr)
            return 1

        if args.dispatch == "manual":
            completed, fields = wait_for_manual_api_call(api_call, args.timeout)
            payload = ""
        else:
            completed, fields, payload = wait_for_auto_api_call(api_call, args.timeout)

        if not completed:
            print("Timed out waiting for Friends.EnumerateFollowingList.", file=sys.stderr)
            return 1

        print("Completed: yes")
        print(f"Failed: {fields.get('failed', 'unknown')}")
        if fields.get("callback_id"):
            print(f"Callback ID: {fields['callback_id']}")
        if payload:
            print(f"Completion payload: {payload}")
        return 0
    finally:
        if args.dispatch == "manual":
            steamworks.shutdown_manual_dispatch()
        else:
            steamworks.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
