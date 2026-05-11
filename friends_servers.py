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
    if not steamworks.Steam_IsSteamRunning():
        print("Steam is not running.", file=sys.stderr)
        return 1

    init_result = steamworks.Steam_InitEx()
    if init_result != 0:
        print(f"Steam_InitEx failed ({init_result}): {steamworks.Steam_GetLastInitError()}", file=sys.stderr)
        return 1

    try:
        steamworks.Steam_RunCallbacks()
        time.sleep(0.1)
        steamworks.Steam_RunCallbacks()

        current_app_id = steamworks.Steam_Utils_GetAppID()
        friend_count = steamworks.Steam_Friends_GetFriendCountImmediate()
        print(f"Checking {friend_count} friends for game/server state")

        found = 0
        for index in range(friend_count):
            friend_id = steamworks.Steam_Friends_GetFriendByIndexImmediate(index)
            if not friend_id or not steamworks.Steam_Friends_GetFriendGamePlayedInfo(friend_id):
                continue

            name = steamworks.Steam_Friends_GetFriendPersonaName(friend_id)
            app_id = steamworks.Steam_Friends_GetFriendGameAppID(friend_id)
            lobby_id = steamworks.Steam_Friends_GetFriendGameLobbyID(friend_id)
            game_ip = steamworks.Steam_Friends_GetFriendGameIP(friend_id)
            game_port = steamworks.Steam_Friends_GetFriendGamePort(friend_id)
            query_port = steamworks.Steam_Friends_GetFriendGameQueryPort(friend_id)
            connect = steamworks.Steam_Friends_GetFriendRichPresence(friend_id, "connect")
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
        steamworks.Steam_Shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
