# Lua Bindings

The Lua binding is generated from the same C ABI model used by Python and Go.
It uses SWIG to build a raw Lua C module, then layers a generated Lua wrapper on
top for grouped APIs such as `steamworks.apps.is_subscribed()`.

## Build

Install Lua development headers, `pkg-config`, SWIG, and a C++ compiler. On a
system with Lua 5.3 available through `pkg-config`:

```bash
python3 tools/build_lua_swig.py --sdk-dir sdk_v165
```

If your Lua package has a different `pkg-config` name, pass it explicitly:

```bash
python3 tools/build_lua_swig.py --sdk-dir sdk_v165 --lua-pkg-config lua5.4
```

The build writes:

- `lua/steamworks_raw.so`: raw SWIG module
- `lua/steamworks.lua`: generated friendly wrapper

## Run

Run examples from the repository root so Steam can find `steam_appid.txt`:

```bash
LUA_PATH="./lua/?.lua;;" LUA_CPATH="./lua/?.so;;" lua examples/lua/test.lua
```

For a broader low-impact live API sweep, run:

```bash
LUA_PATH="./lua/?.lua;;" LUA_CPATH="./lua/?.so;;" lua examples/lua/live_api_smoke.lua
```

The live smoke test also supports `--limit N`, `--limit=N`, and `--json`.

To query public lobbies with the same helper path used by the Python and Go
examples:

```bash
LUA_PATH="./lua/?.lua;;" LUA_CPATH="./lua/?.so;;" lua examples/lua/list_lobbies.lua
```

The lobby example also supports `--max-results N`, `--max-results=N`,
`--timeout N`, `--timeout=N`, and the diagnostic `--skip-shutdown` flag.

## Callbacks

The Lua wrapper exposes the generic callback helpers:

```lua
steamworks.manual_dispatch_init()
steamworks.manual_dispatch_run_frame()
local callback = steamworks.poll_callback()
```

`steamworks.poll_callback()` returns `nil` when no callback is queued.
Otherwise it returns a table with fields such as `id`, `data`, `size`,
`api_call_completed`, `completed_api_call`, `completed_callback_id`,
`api_call_result_data`, and `api_call_result_failed`.

Decoded `key=value` payloads are available through:

```lua
local fields = callback:payload()
local result_fields = callback:api_call_result_payload()
```

You can also parse payload strings directly:

```lua
local fields = steamworks.parse_callback_payload(data)
```

Manual dispatch and automatic dispatch are mutually exclusive for a Steamworks
lifetime. The lobby example uses the higher-level automatic callback helper, so
do not call `steamworks.manual_dispatch_init()` before running that flow.

`steamworks.shutdown()` clears generated helper state and then calls the shared
C ABI shutdown helper, which drains Steam networking and Steam callbacks before
`SteamAPI_Shutdown()`.
