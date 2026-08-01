#!/usr/bin/env python3
"""Minimal ISteamNetworkingSockets P2P demo.

Run one Steam account in listen mode, then run another account in connect mode
using the listener's SteamID.
"""

from __future__ import annotations

import argparse
import sys
import time

import steamworks


def parse_event(line: str) -> dict[str, str]:
    event: dict[str, str] = {}
    for part in line.split("\t"):
        key, _, value = part.partition("=")
        event[key] = value
    return event


def event_int(event: dict[str, str], key: str) -> int:
    try:
        return int(event.get(key, "0"))
    except ValueError:
        return 0


def init_steam() -> bool:
    if not steamworks.is_steam_running():
        print("Steam is not running.", file=sys.stderr)
        return False

    result = steamworks.init_ex()
    if result != 0:
        print(f"steamworks.init_ex() failed ({result}): {steamworks.last_init_error()}", file=sys.stderr)
        return False

    steamworks.networking_utils.init_relay_network_access()
    steamworks.networking_sockets.enable_connection_status_callbacks()
    steamworks.networking_sockets.clear_connection_status_changed_events()
    return True


def print_events(connections: set[int]) -> None:
    connecting = steamworks.networking_constants.networking_connection_state_connecting()
    connected = steamworks.networking_constants.networking_connection_state_connected()
    closed = steamworks.networking_constants.networking_connection_state_closed_by_peer()
    problem = steamworks.networking_constants.networking_connection_state_problem_detected_locally()

    for line in steamworks.networking_sockets.poll_connection_status_changed_strings(32):
        event = parse_event(line)
        connection = event_int(event, "connection")
        listen_socket = event_int(event, "listen_socket")
        state = event_int(event, "state")
        old_state = event_int(event, "old_state")
        remote = event_int(event, "remote_steam_id")
        description = event.get("description", "")
        end_debug = event.get("end_debug", "")

        print(f"event conn={connection} remote={remote} {old_state}->{state} {description}")
        if end_debug:
            print(f"  end: {end_debug}")

        if state == connecting and listen_socket:
            result = steamworks.networking_sockets.accept_connection(connection)
            print(f"  accept result: {result}")
        elif state == connected:
            connections.add(connection)
        elif state in (closed, problem):
            connections.discard(connection)
            steamworks.networking_sockets.close_connection(
                connection,
                steamworks.networking_constants.net_connection_end_app_generic(),
                "closed",
                False,
            )


def pump(connections: set[int], message: str | None, interval_seconds: float) -> None:
    last_send = 0.0
    while True:
        steamworks.run_callbacks()
        print_events(connections)

        for connection in list(connections):
            for payload in steamworks.networking_sockets.receive_messages_on_connection_strings(connection, 32):
                print(f"recv {connection}: {payload}")

            if message and time.monotonic() - last_send >= interval_seconds:
                result = steamworks.networking_sockets.send_message_to_connection_string(
                    connection,
                    message,
                    steamworks.networking_constants.networking_send_reliable(),
                )
                print(f"send {connection}: {result}")
                last_send = time.monotonic()

        time.sleep(0.05)


def listen(args: argparse.Namespace) -> int:
    listen_socket = steamworks.networking_sockets.create_listen_socket_2_p_no_options(args.port)
    if not listen_socket:
        print("Failed to create P2P listen socket.", file=sys.stderr)
        return 1

    print(f"SteamID: {steamworks.user.steam_id()}")
    print(f"Listening on virtual port {args.port}")
    pump(set(), args.message, args.interval)
    return 0


def connect(args: argparse.Namespace) -> int:
    connection = steamworks.networking_sockets.connect_2_p_steam_id_no_options(args.peer, args.port)
    if not connection:
        print("Failed to create P2P connection.", file=sys.stderr)
        return 1

    print(f"SteamID: {steamworks.user.steam_id()}")
    print(f"Connecting to {args.peer} on virtual port {args.port}, connection {connection}")
    pump(set(), args.message, args.interval)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0, help="Steam networking virtual port")
    parser.add_argument("--message", default=None, help="Message to send repeatedly after connecting")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between repeated sends")

    subparsers = parser.add_subparsers(dest="mode", required=True)
    subparsers.add_parser("listen")
    connect_parser = subparsers.add_parser("connect")
    connect_parser.add_argument("peer", type=int, help="Remote SteamID64")

    args = parser.parse_args()
    if not init_steam():
        return 1

    try:
        if args.mode == "listen":
            return listen(args)
        return connect(args)
    finally:
        steamworks.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
