# Steamworks SWIG Python Wrapper

Experimental Python bindings for the Steamworks SDK using SWIG and Valve's flat
Steamworks API. This project currently targets SDK v164 and may require changes to
build against a different version. This version primarily targets v1.65.

The wrapper is generated from:

```text
sdk/public/steam/steam_api.json
sdk/public/steam/steam_api_flat.h
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

The Steamworks SDK is not included in this repository or its source
distribution. Obtain an authorized copy directly from Valve through Steamworks.
This project expects that local SDK to be available at:

```text
sdk/
```

For this repo, `sdk` may be a symlink to a versioned SDK directory such as
`sdk_v165`.

Alternatively, set `STEAMWORKS_SDK_DIR` to build against a specific installed
SDK without changing the symlink:

```bash
STEAMWORKS_SDK_DIR=/path/to/steamworks/sdk_158a pip install .
```

The generator validates each JSON-described interface accessor and method
against that SDK version's actual `steam_api_flat.h`. This handles SDK releases
whose `steam_api.json` contains entries that are absent from their shipped
headers. Functions unavailable in the selected SDK are omitted from that build.
Builds are currently verified against Steamworks SDK 1.58a, 1.59, and 1.64.

Do not commit, vendor, or republish the SDK headers, API JSON, examples, tools,
or other SDK source files with this project.

## Install

From the project root:

```bash
pip install .
```

The install step regenerates the SWIG shim from Valve's `steam_api.json`, runs
SWIG, builds the Python extension, and bundles the platform-specific Steamworks
runtime library into the installed package.

Source archives contain only SteamworksSwig project files. Consequently, a
source archive cannot be built directly by `pip` until the developer has
unpacked it and supplied their separately obtained SDK at `sdk/`.

Release artifacts should be platform-specific binary wheels. Each wheel
contains only the Steamworks runtime for its target platform from
`redistributable_bin`; it must not contain SDK headers, API JSON, examples, or
other Valve SDK source files.

Build release artifacts with:

```bash
python3 tools/build_distributions.py --sdk-dir /path/to/steamworks/sdk --clean
```

This runs the two required builds separately:

```bash
STEAMWORKS_SDK_DIR=/path/to/steamworks/sdk python3 -m build --sdist
STEAMWORKS_SDK_DIR=/path/to/steamworks/sdk python3 -m build --wheel
```

Do not use bare `python3 -m build` for this project. Its default workflow first
creates the intentionally SDK-free source archive and then attempts to compile
a wheel from that isolated archive. Such a wheel build cannot succeed unless
the external SDK location is explicitly available inside the second build.

### Linux wheels for PyPI

PyPI does not accept generic `linux_x86_64` wheels. Build repaired manylinux
wheels using Docker or Podman:

```bash
tools/build_manylinux_wheels.sh --sdk-dir sdk
```

By default this uses `quay.io/pypa/manylinux2014_x86_64` and builds CPython
3.9-3.13 wheels into `wheelhouse/`. Limit the matrix when required:

```bash
tools/build_manylinux_wheels.sh \
  --sdk-dir sdk_158a \
  --python-tags "cp311-cp311 cp312-cp312"
```

Use Podman with `--engine podman`. Validate and upload the repaired wheels:

```bash
python3 -m twine check wheelhouse/*.whl
python3 -m twine upload wheelhouse/*.whl
```

### Windows wheels for PyPI

Run the PowerShell build script on 64-bit Windows with Visual Studio Build Tools,
SWIG, and the Python Launcher installed:

```powershell
.\tools\build_windows_wheels.ps1 -SdkDir C:\path\to\steamworks\sdk
```

It builds CPython 3.9-3.13 `win_amd64` wheels into `wheelhouse`. Build a smaller
matrix with:

```powershell
.\tools\build_windows_wheels.ps1 `
  -SdkDir C:\path\to\steamworks\sdk `
  -PythonVersions 3.11,3.12
```

The script expects each selected 64-bit Python version to be registered with
the Windows `py.exe` launcher. It validates each wheel with Twine and checks
that the resulting filename has a `win_amd64` platform tag. Upload with:

```powershell
py -3.12 -m twine upload wheelhouse\*.whl
```

## Licensing

Original SteamworksSwig code is licensed under BSD-3-Clause. Valve's Steamworks
runtime libraries are excluded from that grant and remain governed by Valve's
Steamworks terms. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).


## Other Language Targets

Although this project currently generates Python bindings, its C++ shim and
most of its SWIG interface declarations can be adapted to other SWIG-supported
languages, such as C#, Java, Ruby, Lua, or JavaScript.

Supporting another target requires a separate language-specific build and
package layer. Exception mapping, callback/event delivery, native object
ownership, string and buffer typemaps, and runtime-library loading must be
reviewed for that language. The manual-versus-automatic callback dispatch
restriction must also remain enforced.

Go is possible through SWIG, but a direct cgo wrapper may provide a simpler
interface and more predictable ownership semantics.

The same Steamworks SDK distribution rules apply to every target language:
obtain the SDK separately from Valve, do not redistribute SDK headers, API JSON,
examples, or tools, and distribute only the permitted platform runtime files
from `redistributable_bin` with generated or compiled wrapper outputs.

At runtime it links against the Steamworks redistributable for the current
platform:

```text
Linux x86_64:  sdk/redistributable_bin/linux64/libsteam_api.so
Linux arm64:   sdk/redistributable_bin/linuxarm64/libsteam_api.so
macOS:         sdk/redistributable_bin/osx/libsteam_api.dylib
Windows x64:   sdk/redistributable_bin/win64/steam_api64.dll
Windows x86:   sdk/redistributable_bin/steam_api.dll
```

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

The smoke test uses `Steam_InitEx()` and prints `Steam_GetLastInitError()` if
Steamworks initialization fails.

## Global Helpers

The generated module includes a small hand-written global API shim in addition
to the JSON-derived interface methods. Some global SDK functions still need explicit 
typemaps before they can be safely wrapped, notably callback function pointer 
registration APIs.

## C ABI Layer

The generator also emits `generated/steamworks_c_api.h` and
`generated/steamworks_c_api.cpp` as a language-neutral ABI foundation for
Go/cgo, Zig, Rust FFI, Lua, Ruby, and similar bindings. The public header avoids
Steam C++ types and STL containers; generated functions use fixed-width C types,
`bool`, and `const char *`.

Automatically generated C ABI functions are named after Valve's unique flat API
symbols with an `SWS_` prefix, for example
`SWS_SteamAPI_ISteamApps_BIsSubscribed()`. Curated global helpers keep their
existing shim names with the same prefix, for example `SWS_Steam_Init()`.

This layer currently covers the same scalar/string-safe JSON methods as the
Python generator plus core init and game-server helpers. Pointer buffers,
callback registration, owned string results, and vector results still need
explicit C-safe adapters.

## Experimental Go SWIG Wrapper

You can generate a local Go/cgo package from the C ABI layer with:

```bash
python3 tools/build_go_swig.py --sdk-dir sdk_v165
```

The script regenerates the C++ shim, creates `go/steamworks`, runs SWIG with
the Go backend, writes the cgo compiler/linker flags for your local SDK path,
and runs `go test` to confirm the package compiles. The generated Go package is
ignored by git because it contains SDK-path-specific build flags and generated
source.

After generating the wrapper, run the Go smoke test from the project root:

```bash
GO111MODULE=off go run examples/go/test.go
```

It prints the same basic Steamworks state as `examples/python/test.py`.

To generate without compiling:

```bash
python3 tools/build_go_swig.py --sdk-dir sdk_v165 --skip-build
```

SWIG may print a `const char * variable may leak memory` warning while parsing
the C ABI header. The current generated API only returns borrowed Steamworks
strings, so there is nothing to free for those values.

## API Coverage

Coverage is measured against the interface methods listed in
`sdk/public/steam/steam_api.json`. The wrapper currently generates methods when
the flat API has a matching accessor and the signature can be represented safely
with Python scalar/string types. Methods that require output structs, pointer
buffers, callbacks, or interface pointers usually need explicit shim code.

Current generated interface coverage is **624 of 921 SDK method overloads, or
67.8%**. Those 624 SDK methods collapse to **618 unique Python function names**
where Valve exposes C++ overloads with the same method name.

The generated module currently exports **761 unique `Steam_*` Python
functions**: **618 JSON-derived functions** plus **143 hand-written
static/helper functions**. Helper functions cover initialization, manual
dispatch, game-server initialization, networking payloads,
`ISteamNetworkingSockets` connection-status and query helpers, lobby async
calls, matchmaking server pings/friend queries, and friend game/server state.

| Steamworks group | JSON SDK methods | JSON wrapped | JSON coverage | JSON Python funcs | Static/helper funcs | Total Python funcs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `Global/static` | - | - | - | 0 | 31 | 31 |
| `Apps` | 35 | 26 | 74.3% | 26 | 0 | 26 |
| `Client` | 33 | 0 | 0.0% | 0 | 0 | 0 |
| `Controller` | 34 | 29 | 85.3% | 29 | 0 | 29 |
| `Friends` | 78 | 72 | 92.3% | 72 | 13 | 85 |
| `GameServer` | 41 | 36 | 87.8% | 36 | 16 | 52 |
| `GameServerStats` | 10 | 7 | 70.0% | 6 | 0 | 6 |
| `HTMLSurface` | 37 | 30 | 81.1% | 30 | 0 | 30 |
| `HTTP` | 25 | 15 | 60.0% | 15 | 0 | 15 |
| `Input` | 48 | 42 | 87.5% | 42 | 0 | 42 |
| `Inventory` | 38 | 15 | 39.5% | 12 | 0 | 12 |
| `Matchmaking` | 38 | 33 | 86.8% | 33 | 27 | 60 |
| `MatchmakingPingResponse` | 2 | 0 | 0.0% | 0 | 0 | 0 |
| `MatchmakingPlayersResponse` | 3 | 0 | 0.0% | 0 | 0 | 0 |
| `MatchmakingRulesResponse` | 3 | 0 | 0.0% | 0 | 0 | 0 |
| `MatchmakingServerFriendsResponse` | 3 | 0 | 0.0% | 0 | 0 | 0 |
| `MatchmakingServerListResponse` | 3 | 0 | 0.0% | 0 | 0 | 0 |
| `MatchmakingServers` | 18 | 7 | 38.9% | 7 | 14 | 21 |
| `Music` | 9 | 9 | 100.0% | 9 | 0 | 9 |
| `Networking` | 22 | 11 | 50.0% | 11 | 0 | 11 |
| `NetworkingFakeUDPPort` | 4 | 0 | 0.0% | 0 | 0 | 0 |
| `NetworkingMessages` | 6 | 0 | 0.0% | 0 | 0 | 0 |
| `NetworkingSockets` | 47 | 15 | 31.9% | 15 | 42 | 57 |
| `NetworkingUtils` | 41 | 21 | 51.2% | 21 | 0 | 21 |
| `ParentalSettings` | 6 | 6 | 100.0% | 6 | 0 | 6 |
| `Parties` | 12 | 7 | 58.3% | 7 | 0 | 7 |
| `RemotePlay` | 20 | 17 | 85.0% | 17 | 0 | 17 |
| `RemoteStorage` | 59 | 43 | 72.9% | 43 | 0 | 43 |
| `Screenshots` | 9 | 8 | 88.9% | 8 | 0 | 8 |
| `Timeline` | 18 | 18 | 100.0% | 18 | 0 | 18 |
| `UGC` | 99 | 74 | 74.7% | 73 | 0 | 73 |
| `User` | 33 | 24 | 72.7% | 24 | 0 | 24 |
| `UserStats` | 44 | 24 | 54.5% | 23 | 0 | 23 |
| `Utils` | 39 | 33 | 84.6% | 33 | 0 | 33 |
| `Video` | 4 | 2 | 50.0% | 2 | 0 | 2 |
| **Total** | **921** | **624** | **67.8%** | **618** | **143** | **761** |

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

    if callback_id == steamworks.Steam_ManualDispatch_CallbackIDSteamNetConnectionStatusChanged():
        fields = dict(
            part.split("=", 1)
            for part in steamworks.Steam_ManualDispatch_DecodeCallbackSteamNetConnectionStatusChanged().split("\t")
        )
        connection = int(fields["connection"])
        state = int(fields["state"])

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
            failed = steamworks.Steam_ManualDispatch_GetAPICallResultFailed()
            if result_callback == steamworks.Steam_ManualDispatch_CallbackIDLobbyCreated():
                fields = dict(
                    part.split("=", 1)
                    for part in steamworks.Steam_ManualDispatch_DecodeAPICallResultLobbyCreated().split("\t")
                )
            elif result_callback == steamworks.Steam_ManualDispatch_CallbackIDLobbyMatchList():
                fields = dict(
                    part.split("=", 1)
                    for part in steamworks.Steam_ManualDispatch_DecodeAPICallResultLobbyMatchList().split("\t")
                )

    steamworks.Steam_ManualDispatch_FreeLastCallback(pipe)
```

The wrapper supports both callback models, but they are mutually exclusive for
each Steamworks lifetime. `Steam_ManualDispatch_Init()` selects manual dispatch.
The first call to `Steam_RunCallbacks()`, `Steam_GameServer_RunCallbacks()`, or
a higher-level helper that registers a callback selects automatic dispatch.
Once selected, calls into the other model raise `RuntimeError` until
`Steam_Shutdown()` or `Steam_GameServer_Shutdown()` resets the mode. The current
selection is available through `Steam_GetCallbackDispatchMode()` and the three
`Steam_CallbackDispatchMode*()` constants.

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
`tools/generate_swig_shim.py`. Add simple callback structs there rather than
hand-editing the C++ templates; keep only special nested serializers in the
template.

Manual dispatch replaces `Steam_RunCallbacks()` and
`Steam_GameServer_RunCallbacks()` for code using that pipe. Higher-level
callback shims that depend on automatic dispatch are disabled after manual
dispatch is selected.

Individual server pings are wrapped with a small polling shim around
`ISteamMatchmakingPingResponse`:

```python
query = steamworks.Steam_MatchmakingServers_PingServer(ip, query_port)
while steamworks.Steam_MatchmakingServers_IsPingPending():
    steamworks.Steam_RunCallbacks()

if steamworks.Steam_MatchmakingServers_PingSucceeded():
    fields = dict(
        part.split("=", 1)
        for part in steamworks.Steam_MatchmakingServers_GetPingServer().split("\t")
    )
    print(fields["name"], fields["ping"], fields["players"], fields["max_players"])
else:
    print("Server failed to respond")
```

The ping result is returned as tab-separated `key=value` fields, matching the
other event shims. `Steam_MatchmakingServers_ClearPingResult()` resets the
single stored result before starting another ping. With SDK 1.65 and newer,
the same polling shape is available for querying friends who have played on a
server:

```python
query = steamworks.Steam_MatchmakingServers_ServerFriends(ip, query_port)
while steamworks.Steam_MatchmakingServers_IsServerFriendsPending():
    steamworks.Steam_RunCallbacks()

if steamworks.Steam_MatchmakingServers_ServerFriendsSucceeded():
    for entry in steamworks.Steam_MatchmakingServers_GetServerFriends():
        fields = dict(part.split("=", 1) for part in entry.split("\t"))
        print(fields["steam_id"], fields["name"], fields["currently_connected"])
```

`Steam_MatchmakingServers_GetPingServer()` also includes
`current_friend_count` and `total_friend_count` fields when built against SDK
1.65 or newer.

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
python3 examples/python/list_lobbies.py
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
python3 examples/python/friends_servers.py
```

## Regenerating

The generator can be run directly:

```bash
python3 tools/generate_swig_shim.py --output-dir generated
```

The generated wrapper currently covers methods with SWIG-friendly value and
`const char *` parameters. Pointer/out/ref-heavy APIs, callbacks, and structured
result handling are intentionally skipped until explicit typemaps are added.
