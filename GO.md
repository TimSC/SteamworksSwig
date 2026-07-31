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
path, and runs `go test` to confirm the raw package compiles.

The raw generated Go package is ignored by git because it contains
SDK-path-specific build flags and generated source.

To generate without compiling:

```bash
python3 tools/build_go_swig.py --sdk-dir sdk_v165 --skip-build
```

## Friendly Go Package

The checked-in `go/steamworks` package is a small idiomatic wrapper around the
raw generated API. It exposes grouped helpers such as:

```go
steamworks.Init()
steamworks.Shutdown()
steamworks.RunCallbacks()
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

## Run the Go Smoke Test

After generating the raw wrapper, run the Go smoke test from the project root:

```bash
go run examples/go/test.go
```

It prints the same basic Steamworks state as `examples/python/test.py`.

You need Steam running and logged in, plus `steam_appid.txt` in the project root.

## SWIG Warning

SWIG may print a `const char * variable may leak memory` warning while parsing
the C ABI header. The current generated API only returns borrowed Steamworks
strings, so there is nothing to free for those values.
