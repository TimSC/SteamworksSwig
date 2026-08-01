# Go Bindings

The Go binding is experimental. It uses the generated C ABI layer as a stable
foundation, then builds a local SWIG/cgo package on top of your separately
obtained Steamworks SDK.

## Generate the Raw Package

From the project root:

```bash
python3 tools/build_go_swig.py --sdk-dir sdk_v165
```

The script regenerates the C++ shim, creates `go/steamworks/raw`, runs SWIG
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
top-level convenience helpers, and grouped helpers such as:

```go
steamworks.Init()
steamworks.Shutdown()
steamworks.RunCallbacks()
steamworks.CurrentSteamID()
steamworks.CurrentAppID()
steamworks.User.SteamID()
steamworks.User.LoggedOn()
steamworks.Friends.PersonaName()
steamworks.Utils.AppID()
steamworks.Apps.IsSubscribed()
```

The raw generated package remains available at:

```go
github.com/TimSC/SteamworksSwig/go/steamworks/raw
```

Most safe scalar/string methods are generated as grouped methods on interfaces
such as `steamworks.Apps`, `steamworks.Friends`, `steamworks.UserStats`, and
`steamworks.UGC`. For example, the raw function:

```go
raw.SWS_SteamAPI_ISteamApps_BIsVACBanned()
```

is available as:

```go
steamworks.Apps.IsVACBanned()
```

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
from the existing C++ shim. This is intentionally conservative; specialized Go
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
go run examples/go/list_lobbies.go
```

## SWIG Warning

SWIG may print a `const char * variable may leak memory` warning while parsing
the C ABI header. The current generated API only returns borrowed Steamworks
strings, so there is nothing to free for those values.
