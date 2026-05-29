# Steamworks SWIG Python Wrapper

Experimental Python bindings for the Steamworks SDK using SWIG and Valve's flat
Steamworks API.

The wrapper is generated from:

```text
sdk/public/steam/steam_api.json
sdk/public/steam/steam_api_flat.h
```

At runtime it links against the Steamworks redistributable for the current
platform:

```text
Linux x86_64:  sdk/redistributable_bin/linux64/libsteam_api.so
Linux arm64:   sdk/redistributable_bin/linuxarm64/libsteam_api.so
macOS:         sdk/redistributable_bin/osx/libsteam_api.dylib
Windows x64:   sdk/redistributable_bin/win64/steam_api64.dll
Windows x86:   sdk/redistributable_bin/steam_api.dll
```

## Requirements

- Linux, macOS, or Windows
- Python 3.9+
- `swig`
- A C++17 compiler
- Python development headers
- Steam running and logged in
- `steam_appid.txt` in the project root for local development

## SDK Layout

This project expects the Steamworks SDK to be available at:

```text
sdk/
```

For this repo, `sdk` may be a symlink to a versioned SDK directory such as
`sdk_v164`.

## Install

From the project root:

```bash
pip install .
```

The install step regenerates the SWIG shim from Valve's `steam_api.json`, runs
SWIG, builds the Python extension, and bundles the platform-specific Steamworks
runtime library into the installed package.

## Smoke Test

Use Valve's public Spacewar AppID for basic testing:

```bash
printf "480\n" > steam_appid.txt
python3 test.py
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

The smoke test uses `Steam_InitEx()` and prints `Steam_GetLastInitError()` if
Steamworks initialization fails.

## Global Helpers

The generated module includes a small hand-written global API shim in addition
to the JSON-derived interface methods:

```python
steamworks.Steam_Init()
steamworks.Steam_InitEx()
steamworks.Steam_InitFlat()
steamworks.Steam_GetLastInitResult()
steamworks.Steam_GetLastInitError()
steamworks.Steam_Shutdown()
steamworks.Steam_RunCallbacks()
steamworks.Steam_IsSteamRunning()
steamworks.Steam_RestartAppIfNecessary(app_id)
steamworks.Steam_ReleaseCurrentThreadMemory()
steamworks.Steam_WriteMiniDump(structured_exception_code, build_id)
steamworks.Steam_GetSteamInstallPath()
steamworks.Steam_SetTryCatchCallbacks(enabled)
steamworks.Steam_SetMiniDumpComment(message)
steamworks.Steam_ManualDispatch_Init()
steamworks.Steam_ManualDispatch_RunFrame(pipe)
steamworks.Steam_ManualDispatch_GetNextCallback(pipe)
steamworks.Steam_ManualDispatch_GetCallbackSteamUser()
steamworks.Steam_ManualDispatch_GetCallbackID()
steamworks.Steam_ManualDispatch_GetCallbackData()
steamworks.Steam_ManualDispatch_GetCallbackSize()
steamworks.Steam_ManualDispatch_CallbackIsAPICallCompleted()
steamworks.Steam_ManualDispatch_GetCompletedAPICall()
steamworks.Steam_ManualDispatch_GetCompletedCallbackID()
steamworks.Steam_ManualDispatch_GetCompletedCallbackSize()
steamworks.Steam_ManualDispatch_GetAPICallResult(pipe, api_call, callback_size, callback_id)
steamworks.Steam_ManualDispatch_GetAPICallResultData()
steamworks.Steam_ManualDispatch_GetAPICallResultFailed()
steamworks.Steam_ManualDispatch_FreeLastCallback(pipe)
steamworks.Steam_GetHSteamPipe()
steamworks.Steam_GetHSteamUser()
steamworks.Steam_GameServer_Init(ip, game_port, query_port, server_mode, version)
steamworks.Steam_GameServer_InitEx(ip, game_port, query_port, server_mode, version)
steamworks.Steam_GameServer_GetLastInitResult()
steamworks.Steam_GameServer_GetLastInitError()
steamworks.Steam_GameServer_Shutdown()
steamworks.Steam_GameServer_RunCallbacks()
steamworks.Steam_GameServer_ReleaseCurrentThreadMemory()
steamworks.Steam_GameServer_GlobalBSecure()
steamworks.Steam_GameServer_GlobalGetSteamID()
steamworks.Steam_GameServer_GetHSteamPipe()
steamworks.Steam_GameServer_GetHSteamUser()
steamworks.Steam_ServerModeInvalid()
steamworks.Steam_ServerModeNoAuthentication()
steamworks.Steam_ServerModeAuthentication()
steamworks.Steam_ServerModeAuthenticationAndSecure()
steamworks.Steam_GameServer_QueryPortShared()
```

Some global SDK functions still need explicit typemaps before they can be safely
wrapped, notably callback function pointer registration APIs.

## API Coverage

Coverage is measured against the interface methods listed in
`sdk/public/steam/steam_api.json`. The wrapper currently generates methods when
the flat API has a matching accessor and the signature can be represented safely
with Python scalar/string types. Methods that require output structs, pointer
buffers, callbacks, or interface pointers usually need explicit shim code.

Current generated interface coverage is **620 of 913 SDK method overloads, or
67.9%**. Those 620 SDK methods collapse to 614 unique Python function names
where Valve exposes C++ overloads with the same method name.

The generated module currently exports **709 unique `Steam_*` Python
functions**. Of those, **95 are hand-written helper functions** for
initialization, game-server initialization, networking payloads,
`ISteamNetworkingSockets` connection-status polling, lobby async calls, and
friend game/server state. Those helpers are useful API surface, but they are not
counted in the table below because they do not correspond one-to-one with JSON
methods.

| Steamworks group | SDK methods | Wrapped | Coverage |
| --- | ---: | ---: | ---: |
| `Apps` | 33 | 24 | 72.7% |
| `Client` | 33 | 0 | 0.0% |
| `Controller` | 34 | 29 | 85.3% |
| `Friends` | 78 | 72 | 92.3% |
| `GameServer` | 41 | 36 | 87.8% |
| `GameServerStats` | 10 | 7 | 70.0% |
| `HTMLSurface` | 37 | 30 | 81.1% |
| `HTTP` | 25 | 15 | 60.0% |
| `Input` | 48 | 42 | 87.5% |
| `Inventory` | 38 | 15 | 39.5% |
| `Matchmaking` | 38 | 33 | 86.8% |
| `MatchmakingPingResponse` | 2 | 0 | 0.0% |
| `MatchmakingPlayersResponse` | 3 | 0 | 0.0% |
| `MatchmakingRulesResponse` | 3 | 0 | 0.0% |
| `MatchmakingServerListResponse` | 3 | 0 | 0.0% |
| `MatchmakingServers` | 17 | 7 | 41.2% |
| `Music` | 9 | 9 | 100.0% |
| `Networking` | 22 | 11 | 50.0% |
| `NetworkingFakeUDPPort` | 4 | 0 | 0.0% |
| `NetworkingMessages` | 6 | 0 | 0.0% |
| `NetworkingSockets` | 47 | 15 | 31.9% |
| `NetworkingUtils` | 41 | 21 | 51.2% |
| `ParentalSettings` | 6 | 6 | 100.0% |
| `Parties` | 12 | 7 | 58.3% |
| `RemotePlay` | 20 | 17 | 85.0% |
| `RemoteStorage` | 59 | 43 | 72.9% |
| `Screenshots` | 9 | 8 | 88.9% |
| `Timeline` | 18 | 18 | 100.0% |
| `UGC` | 99 | 74 | 74.7% |
| `User` | 33 | 24 | 72.7% |
| `UserStats` | 44 | 24 | 54.5% |
| `Utils` | 37 | 31 | 83.8% |
| `Video` | 4 | 2 | 50.0% |

## SpaceWar Server, Lobby, And Networking

The wrapper exposes the main APIs used by the Steamworks `steamworksexample`
lobby and game-server flow.

Lobby methods are generated from `steam_api.json`, for example:

```python
steamworks.Steam_Matchmaking_RequestLobbyList()
steamworks.Steam_Matchmaking_CreateLobby(lobby_type, max_members)
steamworks.Steam_Matchmaking_JoinLobby(lobby_id)
steamworks.Steam_Matchmaking_LeaveLobby(lobby_id)
steamworks.Steam_Matchmaking_GetNumLobbyMembers(lobby_id)
steamworks.Steam_Matchmaking_GetLobbyMemberByIndex(lobby_id, index)
steamworks.Steam_Matchmaking_GetLobbyData(lobby_id, key)
steamworks.Steam_Matchmaking_SetLobbyData(lobby_id, key, value)
steamworks.Steam_Matchmaking_SetLobbyMemberData(lobby_id, key, value)
steamworks.Steam_Matchmaking_SetLobbyGameServer(lobby_id, ip, port, server_steam_id)
```

Game-server setup methods include:

```python
steamworks.Steam_GameServer_InitEx(ip, game_port, query_port, server_mode, version)
steamworks.Steam_GameServer_SetModDir("spacewar")
steamworks.Steam_GameServer_SetProduct("SteamworksExample")
steamworks.Steam_GameServer_SetGameDescription("Steamworks Example")
steamworks.Steam_GameServer_LogOnAnonymous()
steamworks.Steam_GameServer_SetAdvertiseServerActive(True)
steamworks.Steam_GameServer_RunCallbacks()
steamworks.Steam_GameServer_Shutdown()
```

Manual dispatch is available when you want to pull Steam callbacks one at a
time. After initialization, call `Steam_ManualDispatch_Init()` before using the
manual-dispatch loop. For each frame, run the pipe once, then keep fetching
callbacks until `Steam_ManualDispatch_GetNextCallback()` returns `False`.
Whenever it returns `True`, finish inspecting the callback and call
`Steam_ManualDispatch_FreeLastCallback(pipe)` before fetching the next one:

```python
pipe = steamworks.Steam_GetHSteamPipe()
steamworks.Steam_ManualDispatch_Init()

steamworks.Steam_ManualDispatch_RunFrame(pipe)
while steamworks.Steam_ManualDispatch_GetNextCallback(pipe):
    callback_id = steamworks.Steam_ManualDispatch_GetCallbackID()
    payload = steamworks.Steam_ManualDispatch_GetCallbackData()

    if steamworks.Steam_ManualDispatch_CallbackIsAPICallCompleted():
        api_call = steamworks.Steam_ManualDispatch_GetCompletedAPICall()
        result_callback = steamworks.Steam_ManualDispatch_GetCompletedCallbackID()
        result_size = steamworks.Steam_ManualDispatch_GetCompletedCallbackSize()
        if steamworks.Steam_ManualDispatch_GetAPICallResult(
            pipe,
            api_call,
            result_size,
            result_callback,
        ):
            result_payload = steamworks.Steam_ManualDispatch_GetAPICallResultData()
            failed = steamworks.Steam_ManualDispatch_GetAPICallResultFailed()

    steamworks.Steam_ManualDispatch_FreeLastCallback(pipe)
```

Manual dispatch replaces `Steam_RunCallbacks()` and
`Steam_GameServer_RunCallbacks()` for code using that pipe. Do not mix it with
the higher-level callback shims in the same callback flow.

The networking-sockets helpers add Python-friendly overloads for the pointer-heavy
payload methods used by the example:

```python
steamworks.Steam_NetworkingUtils_InitRelayNetworkAccess()
steamworks.Steam_NetworkingSockets_EnableConnectionStatusCallbacks()

listen_socket = steamworks.Steam_GameServerNetworkingSockets_CreateListenSocketP2PNoOptions(0)
poll_group = steamworks.Steam_GameServerNetworkingSockets_CreatePollGroup()
steamworks.Steam_GameServerNetworkingSockets_AcceptConnection(connection)
steamworks.Steam_GameServerNetworkingSockets_SetConnectionPollGroup(connection, poll_group)
steamworks.Steam_GameServerNetworkingSockets_SendMessageToConnectionString(
    connection,
    "payload",
    steamworks.Steam_NetworkingSend_Reliable(),
)
messages = steamworks.Steam_GameServerNetworkingSockets_ReceiveMessagesOnPollGroupStrings(poll_group, 128)

connection = steamworks.Steam_NetworkingSockets_ConnectP2PSteamIDNoOptions(server_steam_id, 0)
steamworks.Steam_NetworkingSockets_SendMessageToConnectionString(
    connection,
    "payload",
    steamworks.Steam_NetworkingSend_UnreliableNoDelay(),
)
messages = steamworks.Steam_NetworkingSockets_ReceiveMessagesOnConnectionStrings(connection, 32)
```

`ISteamNetworkingSockets` connection status callbacks are exposed as a small
polling shim. Call `Steam_RunCallbacks()`, then drain queued status changes:

```python
for line in steamworks.Steam_NetworkingSockets_PollConnectionStatusChangedStrings(32):
    fields = dict(part.split("=", 1) for part in line.split("\t"))
    connection = int(fields["connection"])
    state = int(fields["state"])

    if state == steamworks.Steam_NetworkingConnectionState_Connecting():
        steamworks.Steam_NetworkingSockets_AcceptConnection(connection)
```

You can try a basic NAT-friendly Steam P2P connection with two Steam accounts.
Run this on the listening account:

```bash
python3 p2p_sockets_demo.py --message "hello from listener" listen
```

Then run this from the connecting account, using the SteamID printed by the
listener:

```bash
python3 p2p_sockets_demo.py --message "hello from connector" connect 7656119...
```

The remaining major gap for a full SpaceWar port is broad callback delivery.
Lobby creation, lobby enter, lobby list results, and server browser responses
are callback-driven in the C++ example. Those still need callback struct
typemaps or higher-level polling/event shims.

There is currently a small higher-level lobby shim for listing and joining
lobbies:

```python
steamworks.Steam_Lobby_RequestList()
while not steamworks.Steam_Lobby_IsListComplete():
    steamworks.Steam_RunCallbacks()

for index in range(steamworks.Steam_Lobby_GetListResultCount()):
    lobby_id = steamworks.Steam_Lobby_GetListLobbyByIndex(index)
    lobby_name = steamworks.Steam_Lobby_GetListLobbyNameByIndex(index)
    print(lobby_id, lobby_name)

steamworks.Steam_Lobby_Join(lobby_id)
while not steamworks.Steam_Lobby_IsJoinComplete():
    steamworks.Steam_RunCallbacks()
print(steamworks.Steam_Lobby_JoinSucceeded())
```

You can try lobby listing with:

```bash
python3 list_lobbies.py
```

See [interactive.md](interactive.md) for the interactive lobby/P2P demo.

Friend game/server state is exposed through a Python-friendly wrapper around
`ISteamFriends::GetFriendGamePlayed`, which avoids the raw `FriendGameInfo_t *`
output parameter:

```python
count = steamworks.Steam_Friends_GetFriendCountImmediate()
for index in range(count):
    friend_id = steamworks.Steam_Friends_GetFriendByIndexImmediate(index)
    if not steamworks.Steam_Friends_GetFriendGamePlayedInfo(friend_id):
        continue

    app_id = steamworks.Steam_Friends_GetFriendGameAppID(friend_id)
    lobby_id = steamworks.Steam_Friends_GetFriendGameLobbyID(friend_id)
    game_ip = steamworks.Steam_Friends_GetFriendGameIP(friend_id)
    game_port = steamworks.Steam_Friends_GetFriendGamePort(friend_id)
    query_port = steamworks.Steam_Friends_GetFriendGameQueryPort(friend_id)
```

You can try that with:

```bash
python3 friends_servers.py
```

## Regenerating

The generator can be run directly:

```bash
python3 tools/generate_swig_shim.py --output-dir generated
```

The generated wrapper currently covers methods with SWIG-friendly value and
`const char *` parameters. Pointer/out/ref-heavy APIs, callbacks, and structured
result handling are intentionally skipped until explicit typemaps are added.
