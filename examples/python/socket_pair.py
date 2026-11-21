"""Send binary data, observe queue pressure, and close a local Steam socket pair."""

import time

import steamworks


SEND_BUFFER_SIZE = 9  # k_ESteamNetworkingConfig_SendBufferSize


def exercise_pair(callbacks, sender, peer):
    sockets = steamworks.networking_sockets
    reliable = steamworks.networking_constants.networking_send_reliable()
    events = []
    callbacks.register(steamworks.ConnectionStatusChanged, events.append)

    def send(payload):
        result = sockets.send_message_to_connection_bytes(sender, payload, reliable)
        print(f"send {len(payload)} bytes: {steamworks.result_name(result)} ({result})")
        print(sockets.connection_real_time_status(sender))
        return result

    binary = b"steamworks\x00\xff"
    if send(binary) != steamworks.EResult.OK:
        raise RuntimeError("Initial binary send failed")
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        callbacks.pump()
        messages = sockets.receive_messages_on_connection_bytes(peer, 1)
        if messages:
            if messages != [binary]:
                raise RuntimeError(f"Unexpected payload: {messages!r}")
            break
        time.sleep(0.01)
    else:
        raise RuntimeError("Peer did not receive the binary payload")

    if not steamworks.networking_utils.set_connection_config_value_int_32(sender, SEND_BUFFER_SIZE, 32 * 1024):
        raise RuntimeError("Could not lower the connection's send buffer limit")
    for _ in range(32):
        result = send(bytes(24 * 1024))
        if result == steamworks.EResult.LimitExceeded:
            print("Send queue is full. Retry later while the connection remains open.")
            break
        if result != steamworks.EResult.OK:
            raise RuntimeError("Unexpected send failure while filling the queue")
    else:
        raise RuntimeError("Send queue did not fill within the bounded test")

    sockets.close_connection(peer, 0, "socket pair test complete", False)
    closed_by_peer = steamworks.networking_constants.networking_connection_state_closed_by_peer()
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        callbacks.pump()
        for event in events:
            if event.connection == sender and event.new_state == closed_by_peer:
                print(f"Peer closed: {event}")
                result = send(binary)
                if result not in (steamworks.EResult.NoConnection, steamworks.EResult.InvalidState):
                    raise RuntimeError("Expected a connection failure after peer closure")
                return
        events.clear()
        time.sleep(0.01)
    raise RuntimeError("Peer closure callback timed out")


def main():
    if steamworks.init_ex():
        raise SystemExit(steamworks.last_init_error())
    try:
        callbacks = steamworks.ClientCallbacks()
        sockets = steamworks.networking_sockets
        sender, peer = sockets.create_socket_pair(True)
        if not sender or not peer:
            raise RuntimeError("Steam could not create a loopback socket pair")
        try:
            exercise_pair(callbacks, sender, peer)
        finally:
            sockets.close_connection(sender, 0, "example finished", False)
            sockets.close_connection(peer, 0, "example finished", False)
    finally:
        steamworks.shutdown()


if __name__ == "__main__":
    main()
