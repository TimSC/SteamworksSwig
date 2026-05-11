# Steamworks SWIG Python Wrapper

Experimental Python bindings for the Steamworks SDK using SWIG and Valve's flat
Steamworks API.

The wrapper is generated from:

```text
sdk/public/steam/steam_api.json
sdk/public/steam/steam_api_flat.h
```

At runtime it links against:

```text
sdk/redistributable_bin/linux64/libsteam_api.so
```

## Requirements

- Linux x86_64
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
SWIG, builds the Python extension, and bundles `libsteam_api.so` into the
installed package.

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

## Regenerating

The generator can be run directly:

```bash
python3 tools/generate_swig_shim.py --output-dir generated
```

The generated wrapper currently covers methods with SWIG-friendly value and
`const char *` parameters. Pointer/out/ref-heavy APIs, callbacks, and structured
result handling are intentionally skipped until explicit typemaps are added.
