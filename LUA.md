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

The Lua wrapper currently covers the generated C ABI function surface. Callback
helpers should be added next, following the Python and Go callback examples.
