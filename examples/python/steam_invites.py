"""Receive Steam lobby and rich-presence joins, including a cold lobby launch."""

import argparse
import time

import steamworks


def lobby_id_arg(value):
    try:
        lobby_id = int(value, 10)
    except ValueError:
        raise argparse.ArgumentTypeError("expected a numeric lobby Steam ID") from None
    if not 0 < lobby_id < 2**64:
        raise argparse.ArgumentTypeError("lobby Steam ID must fit in an unsigned 64-bit integer")
    return lobby_id


def listen(cold_lobby_id):
    callbacks = steamworks.ClientCallbacks()
    pending = {}

    def start_join(lobby_id):
        if lobby_id not in pending:
            pending[lobby_id] = (callbacks.join_lobby(lobby_id), time.monotonic() + 20)

    def on_lobby_join(event):
        print(f"Lobby invite from {event.friend_id} for lobby {event.lobby_id}")
        start_join(event.lobby_id)

    def on_presence_join(event):
        # The app should interpret its own rich-presence connect format here.
        print(f"Rich-presence join from {event.friend_id}, connect value {event.connect!r}")

    callbacks.register(steamworks.GameLobbyJoinRequested, on_lobby_join)
    callbacks.register(steamworks.GameRichPresenceJoinRequested, on_presence_join)

    if cold_lobby_id:
        start_join(cold_lobby_id)

    print("Waiting for Steam join requests. Press Ctrl+C to exit.")
    while True:
        callbacks.pump()
        for lobby_id, (request, deadline) in list(pending.items()):
            result = request.poll()
            if result is None and time.monotonic() < deadline:
                continue
            del pending[lobby_id]
            if result is None:
                print(f"Join request for {lobby_id} timed out locally")
            elif result.status != "complete" or result.io_failure:
                print(f"Could not join {lobby_id}: {result}")
            elif result.join_response == steamworks.EChatRoomEnterResponse.Success:
                print(f"Joined lobby {result.lobby_id}")
            else:
                print(f"Steam refused the join for {lobby_id}: response {result.join_response}")
        time.sleep(0.02)


def main():
    parser = argparse.ArgumentParser(description=__doc__, prefix_chars="-+")
    parser.add_argument("+connect_lobby", type=lobby_id_arg, metavar="LOBBY_ID")
    args, _ = parser.parse_known_args()
    if steamworks.init_ex():
        raise SystemExit(steamworks.last_init_error())
    try:
        listen(args.connect_lobby)
    except KeyboardInterrupt:
        pass
    finally:
        steamworks.shutdown()


if __name__ == "__main__":
    main()
