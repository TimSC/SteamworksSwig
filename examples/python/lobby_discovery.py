"""Merge a friend's lobby with a filtered public lobby search."""

import argparse
import time

import steamworks


def discover(friend_id, metadata_key, metadata_value):
    callbacks = steamworks.ClientCallbacks()
    matchmaking = steamworks.matchmaking
    callbacks.pump()

    friend_lobby = 0
    friends = steamworks.friends
    if friends.friend_game_played_info(friend_id) and friends.friend_game_app_id(friend_id) == steamworks.utils.app_id():
        friend_lobby = friends.friend_game_lobby_id(friend_id)

    friend_update = None

    def on_lobby_data(event):
        nonlocal friend_update
        if event.lobby_id == friend_lobby and event.member_id == friend_lobby:
            friend_update = event.success

    callbacks.register(steamworks.LobbyDataUpdate, on_lobby_data)
    if friend_lobby and not matchmaking.request_lobby_data(friend_lobby):
        print(f"Steam rejected the metadata request for lobby {friend_lobby}")
        friend_update = False

    matchmaking.add_request_lobby_list_distance_filter(steamworks.ELobbyDistanceFilter.Worldwide)
    matchmaking.add_request_lobby_list_filter_slots_available(1)
    matchmaking.add_request_lobby_list_string_filter(
        metadata_key, metadata_value, steamworks.lobby_constants.lobby_comparison_equal()
    )
    search = callbacks.request_lobby_list()
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        callbacks.pump()
        if search.poll() is not None and (not friend_lobby or friend_update is not None):
            break
        time.sleep(0.02)

    found = {}
    if friend_update is True:
        found[friend_lobby] = matchmaking.lobby_data(friend_lobby, metadata_key)
    elif friend_lobby:
        print(f"Metadata unavailable for friend's lobby {friend_lobby}")

    result = search.poll()
    if result is not None and result.status == "complete" and not result.io_failure:
        for lobby_id in result.lobby_ids:
            if lobby_id and lobby_id not in found:
                found[lobby_id] = matchmaking.lobby_data(lobby_id, metadata_key)
    else:
        print(f"Public search failed or timed out: {result}")

    for lobby_id, value in found.items():
        print(f"{lobby_id}  {metadata_key}={value!r}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("friend_id", type=int, help="Steam ID of a friend playing this app")
    parser.add_argument("metadata_key")
    parser.add_argument("metadata_value")
    args = parser.parse_args()
    if steamworks.init_ex():
        raise SystemExit(steamworks.last_init_error())
    try:
        discover(args.friend_id, args.metadata_key, args.metadata_value)
    finally:
        steamworks.shutdown()


if __name__ == "__main__":
    main()
