#!/usr/bin/env python3
"""Show friends currently playing a game, including lobby/server details."""

from __future__ import annotations

import ipaddress
import sys
import time

import steamworks


def format_ip(value: int) -> str:
    if value == 0:
        return ""
    return str(ipaddress.IPv4Address(value))


def main() -> int:
    if not steamworks.is_steam_running():
        print("Steam is not running.", file=sys.stderr)
        return 1

    init_result = steamworks.init_ex()
    if init_result != 0:
        print(f"steamworks.init_ex() failed ({init_result}): {steamworks.last_init_error()}", file=sys.stderr)
        return 1

    try:
        steamworks.run_callbacks()
        time.sleep(0.1)
        steamworks.run_callbacks()

        current_app_id = steamworks.utils.app_id()
        friend_count = steamworks.friends.friend_count_immediate()
        print(f"Checking {friend_count} friends for game/server state")

        found = 0
        for index in range(friend_count):
            friend_id = steamworks.friends.friend_by_index_immediate(index)
            if not friend_id or not steamworks.friends.friend_game_played_info(friend_id):
                continue

            name = steamworks.friends.friend_persona_name(friend_id)
            app_id = steamworks.friends.friend_game_app_id(friend_id)
            lobby_id = steamworks.friends.friend_game_lobby_id(friend_id)
            game_ip = steamworks.friends.friend_game_ip(friend_id)
            game_port = steamworks.friends.friend_game_port(friend_id)
            query_port = steamworks.friends.friend_game_query_port(friend_id)
            connect = steamworks.friends.friend_rich_presence(friend_id, "connect")
            in_current_game = app_id == current_app_id

            found += 1
            print(f"{name} ({friend_id})")
            print(f"  app_id: {app_id}" + (" (current app)" if in_current_game else ""))
            if lobby_id:
                print(f"  lobby_id: {lobby_id}")
            if game_ip:
                print(f"  server: {format_ip(game_ip)}:{game_port} query:{query_port}")
            if connect:
                print(f"  connect: {connect}")

        if found == 0:
            print("No friends are currently reporting game/server details.")
    finally:
        steamworks.shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
