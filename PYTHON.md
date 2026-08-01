# Python Bindings

Python bindings are installed with the main package build described in
[README.md](README.md). Run examples from the repository root with Steam running
and `steam_appid.txt` present.

## Smoke Test

Use Valve's public Spacewar AppID for basic testing:

```bash
printf "480\n" > steam_appid.txt
python3 examples/python/test.py
```

Expected output is similar to:

```text
Hello from Steamworks!
App ID: 480
Logged on: yes
Persona name: YourName
Steam ID: 7656119...
Subscribed to app: yes
```

The smoke test uses `steamworks.init_ex()` and prints
`steamworks.last_init_error()` if Steamworks initialization fails.

For a broader low-impact live API sweep, run:

```bash
python3 examples/python/live_api_smoke.py
```

The live smoke script calls no-argument read-style APIs across many Steamworks
interfaces. It is intended for local manual testing with Steam running, not for
default CI, and avoids operations such as auth-ticket creation, file writes,
lobby creation, stat updates, and other state-changing calls.

To compare automatic and manual callback dispatch on async calls:

```bash
python3 examples/python/list_lobbies.py --dispatch auto
python3 examples/python/list_lobbies.py --dispatch manual
python3 examples/python/enumerate_following.py --dispatch auto
python3 examples/python/enumerate_following.py --dispatch manual
```

The following-list example exercises `Friends.EnumerateFollowingList`, a
low-impact `SteamAPICall_t` request that does not create lobbies or change
account state.

## Python API

Python exposes a generated grouped API over the C ABI:

```python
import steamworks

steamworks.apps.is_subscribed()
steamworks.user.steam_id()
steamworks.friends.persona_name()
```

Grouped wrappers are generated from `generated/steamworks_c_api_model.json` by
`tools/generate_python.py` during the normal build.

## SpaceWar Server, Lobby, And Networking

The wrapper exposes the main APIs used by the Steamworks `steamworksexample`
lobby and game-server flow.

Lobby methods are generated from `steam_api.json`, for example:

```python
steamworks.matchmaking.request_lobby_list()
steamworks.matchmaking.create_lobby(lobby_type, max_members)
steamworks.matchmaking.join_lobby(lobby_id)
steamworks.matchmaking.leave_lobby(lobby_id)
steamworks.matchmaking.num_lobby_members(lobby_id)
steamworks.matchmaking.lobby_member_by_index(lobby_id, index)
steamworks.matchmaking.lobby_data(lobby_id, key)
steamworks.matchmaking.set_lobby_data(lobby_id, key, value)
steamworks.matchmaking.set_lobby_member_data(lobby_id, key, value)
steamworks.matchmaking.set_lobby_game_server(lobby_id, ip, port, server_steam_id)
```

Game-server setup methods include:

```python
steamworks.game_server.init_ex(ip, game_port, query_port, server_mode, version)
steamworks.game_server.set_mod_dir("spacewar")
steamworks.game_server.set_product("SteamworksExample")
steamworks.game_server.set_game_description("Steamworks Example")
steamworks.game_server.log_on_anonymous()
steamworks.game_server.set_advertise_server_active(True)
steamworks.game_server.run_callbacks()
steamworks.game_server.shutdown()
```

Manual dispatch is available when you want to pull Steam callbacks one at a
time. After initialization, call `steamworks.manual_dispatch.init()` before
using the manual-dispatch loop. For each frame, run the pipe once, then keep
fetching callbacks until `steamworks.manual_dispatch.next_callback()` returns
`False`. Whenever it returns `True`, finish inspecting the callback and call
`steamworks.manual_dispatch.free_last_callback(pipe)` before fetching the next
one:

```python
pipe = steamworks.h_steam_pipe()
steamworks.manual_dispatch.init()

steamworks.manual_dispatch.run_frame(pipe)
while steamworks.manual_dispatch.next_callback(pipe):
    callback_id = steamworks.manual_dispatch.callback_id()

    if callback_id == steamworks.manual_dispatch.callback_id_steam_net_connection_status_changed():
        fields = steamworks.parse_callback_payload(
            steamworks.manual_dispatch.decode_callback_steam_net_connection_status_changed()
        )
        connection = int(fields["connection"])
        state = int(fields["state"])

    if steamworks.manual_dispatch.callback_is_api_call_completed():
        api_call = steamworks.manual_dispatch.completed_api_call()
        result_callback = steamworks.manual_dispatch.completed_callback_id()
        result_size = steamworks.manual_dispatch.completed_callback_size()
        if steamworks.manual_dispatch.api_call_result(
            pipe,
            api_call,
            result_size,
            result_callback,
        ):
            failed = steamworks.manual_dispatch.api_call_result_failed()
            if result_callback == steamworks.manual_dispatch.callback_id_lobby_created():
                fields = steamworks.parse_callback_payload(
                    steamworks.manual_dispatch.decode_api_call_result_lobby_created()
                )
            elif result_callback == steamworks.manual_dispatch.callback_id_lobby_match_list():
                fields = steamworks.parse_callback_payload(
                    steamworks.manual_dispatch.decode_api_call_result_lobby_match_list()
                )

    steamworks.manual_dispatch.free_last_callback(pipe)
```

The wrapper supports both callback models, but they are mutually exclusive for
each Steamworks lifetime. `steamworks.manual_dispatch.init()` selects manual
dispatch. The first call to `steamworks.run_callbacks()`,
`steamworks.game_server.run_callbacks()`, or a higher-level helper that
registers a callback selects automatic dispatch. Once selected, calls into the
other model raise `RuntimeError` until `steamworks.shutdown()` or
`steamworks.game_server.shutdown()` resets the mode. The current selection is
available through `steamworks.callback_dispatch_mode()` and the three
`steamworks.callback_dispatch_mode_*()` constants.

The raw byte accessors remain available, but prefer the typed decoders for
callback structs that the shim knows about. `SteamNetConnectionStatusChanged`
decodes the current connection handle, previous state, and the full
`SteamNetConnectionInfo_t` field set. Direct callback decoders also cover lobby
invite/enter/data/chat/game-created/kicked events, Steam overlay and rich
presence joins, friend presence/avatar updates, legacy P2P session events, Steam
connectivity/shutdown/low-battery/license/auth/payment/web callbacks, DLC and
URL launch callbacks, network auth/relay/fake-IP status, and
SteamNetworkingMessages session request/failure events. Lobby API-call results
currently decode `LobbyMatchList_t`, `LobbyEnter_t`, and `LobbyCreated_t`.

ManualDispatch callback decoders are generated from curated metadata in
`tools/steamworks_callbacks.py` and renderer helpers in
`tools/generate_callbacks.py`. Add simple callback structs there rather than
hand-editing the C++ templates; keep only special nested serializers in the
template.

Manual dispatch replaces `steamworks.run_callbacks()` and
`steamworks.game_server.run_callbacks()` for code using that pipe. Higher-level
callback shims that depend on automatic dispatch are disabled after manual
dispatch is selected.

Individual server pings are wrapped with a small polling shim around
`ISteamMatchmakingPingResponse`:

```python
query = steamworks.matchmaking_servers.ping_server(ip, query_port)
while steamworks.matchmaking_servers.is_ping_pending():
    steamworks.run_callbacks()

if steamworks.matchmaking_servers.ping_succeeded():
    fields = steamworks.parse_callback_payload(steamworks.matchmaking_servers.get_ping_server())
    print(fields["name"], fields["ping"], fields["players"], fields["max_players"])
else:
    print("Server failed to respond")
```

The ping result is returned as tab-separated `key=value` fields, matching the
other event shims. `steamworks.matchmaking_servers.clear_ping_result()` resets the
single stored result before starting another ping. With SDK 1.65 and newer,
the same polling shape is available for querying friends who have played on a
server:

```python
query = steamworks.matchmaking_servers.server_friends(ip, query_port)
while steamworks.matchmaking_servers.is_server_friends_pending():
    steamworks.run_callbacks()

if steamworks.matchmaking_servers.server_friends_succeeded():
    for entry in steamworks.matchmaking_servers.get_server_friends():
        fields = steamworks.parse_callback_payload(entry)
        print(fields["steam_id"], fields["name"], fields["currently_connected"])
```

`steamworks.matchmaking_servers.get_ping_server()` also includes
`current_friend_count` and `total_friend_count` fields when built against SDK
1.65 or newer.

The networking-sockets helpers add Python-friendly overloads for the pointer-heavy
payload methods used by the example:

```python
steamworks.networking_utils.init_relay_network_access()
steamworks.networking_sockets.enable_connection_status_callbacks()

listen_socket = steamworks.game_server_networking_sockets.create_listen_socket_2_p_no_options(0)
poll_group = steamworks.game_server_networking_sockets.create_poll_group()
steamworks.game_server_networking_sockets.accept_connection(connection)
steamworks.game_server_networking_sockets.set_connection_poll_group(connection, poll_group)
steamworks.game_server_networking_sockets.send_message_to_connection_string(
    connection,
    "payload",
    steamworks.networking_constants.networking_send_reliable(),
)
messages = steamworks.game_server_networking_sockets.receive_messages_on_poll_group_strings(poll_group, 128)

connection = steamworks.networking_sockets.connect_2_p_steam_id_no_options(server_steam_id, 0)
steamworks.networking_sockets.send_message_to_connection_string(
    connection,
    "payload",
    steamworks.networking_constants.networking_send_unreliable_no_delay(),
)
messages = steamworks.networking_sockets.receive_messages_on_connection_strings(connection, 32)
```

`ISteamNetworkingSockets` connection status callbacks are exposed as a small
polling shim. Call `steamworks.run_callbacks()`, then drain queued status
changes:

```python
for line in steamworks.networking_sockets.poll_connection_status_changed_strings(32):
    fields = dict(part.split("=", 1) for part in line.split("\t"))
    connection = int(fields["connection"])
    state = int(fields["state"])

    if state == steamworks.networking_constants.networking_connection_state_connecting():
        steamworks.networking_sockets.accept_connection(connection)
```

You can try a basic NAT-friendly Steam P2P connection with two Steam accounts.
Run this on the listening account:

```bash
python3 examples/python/p2p_sockets_demo.py --message "hello from listener" listen
```

Then run this from the connecting account, using the SteamID printed by the
listener:

```bash
python3 examples/python/p2p_sockets_demo.py --message "hello from connector" connect 7656119...
```

The remaining major gap for a full SpaceWar port is broad callback delivery.
Lobby creation, lobby enter, and lobby list results are available through the
ManualDispatch API-call result decoders above. Server browser responses still
need callback struct typemaps or higher-level polling/event shims.

There is currently a small higher-level lobby shim for listing and joining
lobbies:

```python
steamworks.lobby.request_list()
while not steamworks.lobby.is_list_complete():
    steamworks.run_callbacks()

for index in range(steamworks.lobby.list_result_count()):
    lobby_id = steamworks.lobby.list_lobby_by_index(index)
    lobby_name = steamworks.lobby.list_lobby_name_by_index(index)
    print(lobby_id, lobby_name)

steamworks.lobby.join(lobby_id)
while not steamworks.lobby.is_join_complete():
    steamworks.run_callbacks()
print(steamworks.lobby.join_succeeded())
```

You can try lobby listing with:

```bash
python3 examples/python/list_lobbies.py --max-results 10 --timeout 10
```

This applies a result-count filter to the next lobby query, waits for the
`LobbyMatchList` result, and prints each returned lobby's ID, name, member
count, member limit, and owner.

See [interactive.md](interactive.md) for the interactive lobby/P2P demo.

Friend game/server state is exposed through a Python-friendly wrapper around
`ISteamFriends::GetFriendGamePlayed`, which avoids the raw `FriendGameInfo_t *`
output parameter:

```python
count = steamworks.friends.friend_count_immediate()
for index in range(count):
    friend_id = steamworks.friends.friend_by_index_immediate(index)
    if not steamworks.friends.friend_game_played_info(friend_id):
        continue

    app_id = steamworks.friends.friend_game_app_id(friend_id)
    lobby_id = steamworks.friends.friend_game_lobby_id(friend_id)
    game_ip = steamworks.friends.friend_game_ip(friend_id)
    game_port = steamworks.friends.friend_game_port(friend_id)
    query_port = steamworks.friends.friend_game_query_port(friend_id)
```

You can try that with:

```bash
python3 examples/python/friends_servers.py
```
