# Go Bindings

The Go binding is experimental. It uses the generated C ABI layer as a stable
foundation, then builds a local SWIG/cgo package on top of your separately
obtained Steamworks SDK.

## Generate the Raw Package

From the project root:

```bash
python3 tools/build_go_swig.py --sdk-dir sdk_v165
```

The script regenerates the C++ helper layer, creates `go/steamworks/raw`, runs SWIG
with the Go backend, writes the cgo compiler/linker flags for your local SDK
path, generates grouped Go methods in `go/steamworks/generated.go`, and runs
`go test ./go/...` to confirm the packages compile.

The raw package and generated grouped wrapper file are ignored by git because
they contain SDK-version-specific generated source. The raw package also
contains SDK-path-specific cgo flags.

To generate without compiling:

```bash
python3 tools/build_go_swig.py --sdk-dir sdk_v165 --skip-build
```

## Friendly Go Package

The checked-in `go/steamworks` package is a small idiomatic wrapper around the
raw generated API. It exposes typed initialization errors, Steamworks ID types,
and grouped helpers such as:

```go
steamworks.Init()
steamworks.Shutdown()
steamworks.RunCallbacks()
steamworks.User.GetSteamID()
steamworks.User.LoggedOn()
steamworks.Friends.GetPersonaName()
steamworks.Utils.GetAppID()
steamworks.Apps.IsSubscribed()
```

The raw generated package remains available at:

```go
github.com/TimSC/SteamworksSwig/go/steamworks/raw
```

Most safe scalar/string SDK methods are generated as grouped methods on
interfaces such as `steamworks.Apps`, `steamworks.Friends`,
`steamworks.UserStats`, and `steamworks.UGC`. For example, the raw function:

```go
raw.SWS_SteamAPI_ISteamApps_BIsVACBanned()
```

is available as:

```go
steamworks.Apps.IsVACBanned()
```

The grouped generator also wraps helper functions from the shared C ABI model,
matching the Python grouped surface more closely. This includes friend game
helpers, lobby constants and async-state helpers, game-server lifecycle helpers,
matchmaking server helpers, networking status helpers, byte/list helpers, and
manual-dispatch callback decoders:

```go
steamworks.Friends.GetFriendGamePlayedInfo(friendID)
steamworks.LobbyConstants.LobbyTypePublic()
steamworks.GameServer.GetLastInitError()
steamworks.ManualDispatch.DecodeCallbackLobbyEnter()
steamworks.GetSteamInstallPath()
steamworks.Lobby.GetDataEntries(lobbyID)
steamworks.RemoteStorage.FileReadBytes("settings.json", 4096)
```

Owned C ABI strings, string lists, byte buffers, and byte-buffer lists are copied
into Go `string`, `[]string`, `[]byte`, and `[][]byte` values before the C-owned
memory is released.

## Manual Dispatch Callbacks

The Go package includes an early manual-dispatch callback API:

```go
steamworks.ManualDispatchInit()

for {
	callback, ok := steamworks.PollCallback()
	if !ok {
		break
	}
	fmt.Println(callback.ID, callback.Data)
}
```

`Callback.Data` and `Callback.APICallResultData` contain decoded key/value text
from the existing C++ helper layer. This is intentionally conservative; specialized Go
structs for individual callback payloads can be added on top of this API later.
`steamworks.Shutdown()` clears registered helper callback state before shutting
Steamworks down.

Use `Callback.Payload()` or `ParseCallbackPayload()` for the decoded key/value
view:

```go
steamworks.PollCallbacks(steamworks.OnCallbackID(
	steamworks.CallbackIDGameOverlayActivated(),
	func(callback steamworks.Callback) {
		payload := callback.Payload()
		fmt.Println(payload["active"])
	},
))
```

## Run the Go Smoke Test

After generating the raw wrapper, run the Go smoke test from the project root:

```bash
go run examples/go/test.go
```

It prints the same basic Steamworks state as `examples/python/test.py`.

You need Steam running and logged in, plus `steam_appid.txt` in the project root.

There is also a lobby-list example mirroring `examples/python/list_lobbies.py`:

```bash
go run examples/go/list_lobbies.go --max-results 10 --timeout 10s
```

It applies a result-count filter to the next lobby query, waits for the
`LobbyMatchList` result, and prints each returned lobby's ID, name, member
count, member limit, and owner.

The lobby-list example can use either callback dispatch path:

```bash
go run examples/go/list_lobbies.go --dispatch auto
go run examples/go/list_lobbies.go --dispatch manual
```

To exercise another low-impact async `SteamAPICall_t` request without creating
lobbies or changing account state:

```bash
go run examples/go/enumerate_following.go --dispatch auto
go run examples/go/enumerate_following.go --dispatch manual
```

For a broader low-impact live API sweep:

```bash
go run examples/go/live_api_smoke.go
```

Use `--limit N` to run only the first N calls, or `--json` for machine-readable
output. The example calls a curated set of no-argument read-style APIs and
avoids operations that create auth tickets, write files, update stats, create
lobbies, or otherwise intentionally mutate Steam/account/app state.

## SWIG Warning

SWIG may print a `const char * variable may leak memory` warning while parsing
the C ABI header. The current generated API only returns borrowed Steamworks
strings, so there is nothing to free for those values.
