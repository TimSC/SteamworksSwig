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
wrapped, notably callback-result APIs that take `CallbackMsg_t *`, arbitrary
`void *` buffers, or callback function pointers.

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

The networking-sockets helpers add Python-friendly overloads for the pointer-heavy
payload methods used by the example:

```python
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

The remaining major gap for a full SpaceWar port is callback delivery. Lobby
creation, lobby enter, lobby list results, connection-status changes, and server
browser responses are callback-driven in the C++ example. Those need callback
struct typemaps or a higher-level polling/event shim.

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

## Regenerating

The generator can be run directly:

```bash
python3 tools/generate_swig_shim.py --output-dir generated
```

The generated wrapper currently covers methods with SWIG-friendly value and
`const char *` parameters. Pointer/out/ref-heavy APIs, callbacks, and structured
result handling are intentionally skipped until explicit typemaps are added.
