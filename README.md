# Steamworks SWIG Python Wrapper

Experimental Python bindings for the Steamworks SDK using SWIG over a generated
C ABI. This project currently targets SDK v1.65 and may require changes to build
against a different version.

The wrapper is generated from:

```text
sdk/public/steam/steam_api.json
sdk/public/steam/steam_api_flat.h
```

See [PYTHON.md](PYTHON.md) for Python API usage and examples. The project also
includes experimental Go and Lua wrappers; see [GO.md](GO.md) for Go binding
generation and [LUA.md](LUA.md) for Lua SWIG build instructions.

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
distribution. Obtain an authorized copy directly from Valve through the
[Steamworks downloads page](https://partner.steamgames.com/downloads/list).
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
Builds are currently verified against Steamworks SDK 1.65.

Do not commit, vendor, or republish the SDK headers, API JSON, examples, tools,
or other SDK source files with this project.

## Install

From the project root:

```bash
pip install .
```

The install step regenerates the C ABI helper layer from Valve's
`steam_api.json`, runs SWIG, builds the Python extension, and bundles the
platform-specific Steamworks runtime library into the installed package.

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

## Generation Pipeline

```text
Steamworks SDK metadata
  sdk/public/steam/steam_api.json
  sdk/public/steam/steam_api_flat.h
  read by tools/generate_model.py
        |
        v
shared normalized API model
  generated/steamworks_c_api_model.json
  written by tools/generate_model.py
        |
        v
C ABI + helper shim
  generated/steamworks_c_api.h
  generated/steamworks_c_api.cpp
  generated/steamworks_helpers.h
  generated/steamworks_helpers.cpp
  generated/steamworks.i
  written by tools/generate_core.py
        |
        v
Python / Go / Lua / other bindings
  Python: tools/generate_python.py, then setup.py runs SWIG/build_ext
  Go:     tools/build_go_swig.py orchestrates SWIG and tools/generate_go.py
  Lua:    tools/build_lua_swig.py orchestrates SWIG and tools/generate_lua.py
```

The C ABI is the primary generated product. Language bindings wrap the same
`SWS_*` surface so lifecycle fixes, helper functions, callback IDs, and type
rules are shared.

`tools/generate_model.py` reads the SDK and is the main metadata/classification
step. It pulls in curated helper metadata from `tools/helper_specs.json`
through `tools/steamworks_helpers.py`, callback metadata from
`tools/steamworks_callbacks.py` through `tools/generate_callbacks.py`, and
promoted output helpers from `tools/generate_output_helpers.py`. It records the
generated wrappers, output-helper implementation metadata, SDK feature flags,
supported C ABI methods, and skipped methods in the shared model.

`tools/generate_core.py` then renders the C++ helper shim, C ABI files, and
SWIG interface from the generated model without rereading the SDK metadata.

For Python package builds, `setup.py` runs `tools/generate_model.py`,
`tools/generate_core.py`, `tools/generate_python.py`, and SWIG automatically
before compiling the `steamworks._steamworks` extension. API coverage docs are
generated separately with `tools/generate_api_docs.py`.

## Shared API Model

`tools/generate_model.py` writes a shared model file:

```text
generated/steamworks_c_api_model.json
```

Each entry should include enough information for language backends and docs:

```json
{
  "interface": "Apps",
  "method": "IsSubscribed",
  "raw_c_name": "SWS_SteamAPI_ISteamApps_BIsSubscribed",
  "friendly_name": "IsSubscribed",
  "return_type": "bool",
  "params": [],
  "callback_safe": true,
  "language_support": "scalar_string"
}
```

The model now records skipped methods and reasons, such as pointer output
buffers, unsupported structs, callback function pointers, interface pointers, or
owned result lifetimes.

## Redistribution builds

### Linux wheels for PyPI

PyPI does not accept generic `linux_x86_64` wheels. Build repaired manylinux
wheels using Docker or Podman:

```bash
tools/build_manylinux_wheels.sh --sdk-dir sdk
```

By default this uses `quay.io/pypa/manylinux2014_x86_64` and builds CPython
3.10-3.15 wheels into `wheelhouse/`. Limit the matrix when required:

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
SWIG, install the python version manager:

```powershell
winget install 9NQ7512CXL7T -e --accept-package-agreements --disable-interactivity
```

For each version of Python that is required:

```powershell
py install 3.14
```

To build the wheels for windows:

```powershell
.\tools\build_windows_wheels.ps1 -SdkDir C:\path\to\steamworks\sdk
```

It builds CPython 3.10-3.15 `win_amd64` wheels into `wheelhouse`. Build a smaller
matrix with:

```powershell
.\tools\build_windows_wheels.ps1 `
  -SdkDir C:\path\to\steamworks\sdk `
  -PythonVersions 3.11,3.12
```

It validates each wheel with Twine and checks that the resulting
filename has a `win_amd64` platform tag. Upload with:

```powershell
py -3.12 -m twine upload wheelhouse\*.whl
```

## Licensing

Original SteamworksSwig code is licensed under BSD-3-Clause. Valve's Steamworks
runtime libraries are excluded from that grant and remain governed by Valve's
Steamworks terms. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).


## Other Language Targets

Although this project currently generates Python and experimental Go bindings,
the generated C ABI is intended to be the common foundation for other language
targets such as Lua, Ruby, Zig, Rust FFI, C#, Java, or JavaScript.

Supporting another target requires a separate language-specific build and
package layer. Exception mapping, callback/event delivery, native object
ownership, string and buffer typemaps, and runtime-library loading must be
reviewed for that language. The manual-versus-automatic callback dispatch
restriction must also remain enforced.

The internal C++ helper layer remains an implementation detail for Steamworks
quirks, callback decoding, and APIs that need explicit adapters. Language
bindings should target `generated/steamworks_c_api.h`, not the helper layer.

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

## Runtime Shutdown

Applications should still call the binding shutdown function when they are done
with Steamworks. The shutdown helpers clear wrapper-owned callback/helper state
and then call Valve's `SteamAPI_Shutdown()` / `SteamGameServer_Shutdown()`.

During Linux testing with Steamworks SDK 1.65, a minimal C++ program using only
Valve's SDK reproduced an intermittent segfault inside the Steam client during
`SteamAPI_Shutdown()` after an async lobby query. The repro lives in
`shutdown/` and is intended for reporting/debugging the upstream issue.

Skipping shutdown is not treated as a supported workaround for this project: it
can leave Steam client internals and networking state uncleared. If you hit this
crash, keep calling the shutdown function in normal application code and use the
standalone repro when reporting or isolating the Steam client behavior.

## Python Usage

See [PYTHON.md](PYTHON.md) for the Python grouped API, smoke tests, callback
usage, lobby helpers, and networking examples.

## C ABI Layer

The generator emits `generated/steamworks_c_api.h`,
`generated/steamworks_c_api.cpp`, and `generated/steamworks_c_api_model.json`
as the primary language-neutral ABI foundation. Python and Go both bind through
this layer. The public header avoids Steam C++ types and STL containers;
generated functions use fixed-width C types, `bool`, `const char *`,
`SWS_String` for owned string results, `SWS_StringList` for owned string-list
results, and `SWS_Bytes` / `SWS_BytesList` for binary payload helpers.

Automatically generated C ABI functions are named after Valve's unique flat API
symbols with an `SWS_` prefix, for example
`SWS_SteamAPI_ISteamApps_BIsSubscribed()`. Curated global helpers keep their
helper names with the same prefix, for example `SWS_Steam_Init()`.

This layer currently covers scalar/string-safe JSON methods plus core init,
game-server, lobby, manual-dispatch, callback cleanup, byte-buffer helpers,
string/vector helpers, and selected async helper APIs. Pointer output buffers,
callback function pointers, C++ reference types, interface pointers, and
unsupported SDK structs still need explicit C-safe adapters.

### Helper Specs

A helper is project-owned adapter code around Valve SDK calls, used when the raw
SDK shape needs lifecycle handling, ownership handling, output conversion, or
callback state to be usable from language bindings.

Most C ABI functions are generated directly from Valve's flat API metadata.
Helpers are the exception: they are project-defined adapters for APIs that need
more intent than the SDK headers provide. Examples include lifecycle entry
points, lobby conveniences, callback/manual-dispatch glue, byte buffers, owned
strings, owned string lists, and APIs where the native SDK expects caller-owned
output memory.

These helpers are listed in `tools/helper_specs.json` and loaded by
`tools/steamworks_helpers.py`. Keeping the list as data makes the curated API
surface easier to review while still letting `tools/generate_model.py` record
the matching model entries and `tools/generate_core.py` emit the C declarations
and wrappers. The C++ helper
implementations remain in the templates where behavior is required.

Some helper candidates can be discovered automatically from common SDK
signature patterns, such as string output buffers. Those generated candidates
still need promotion into the helper spec before they become part of the stable
binding surface, because the headers do not always say whether a buffer is text,
binary data, an array, or part of a multi-call ownership protocol.

## API Coverage

Coverage is measured against the interface methods listed in
`sdk/public/steam/steam_api.json`. The generated model records supported
methods plus skipped methods and reasons, such as pointer output buffers,
interface pointers, callback function pointers, and unsupported SDK structs.

Run this after changing the SDK or generator:

```bash
python3 tools/generate_api_docs.py
```

See [docs/API_COVERAGE.md](docs/API_COVERAGE.md) for current counts by
interface, C ABI function source, skipped reason, and representative skipped
methods.


## Regenerating

The generator can be run directly:

```bash
python3 tools/generate_model.py --output generated/steamworks_c_api_model.json
python3 tools/generate_core.py --model generated/steamworks_c_api_model.json --output-dir generated
```

The generated wrapper currently covers methods with SWIG-friendly value and
`const char *` parameters. Pointer/out/ref-heavy APIs, callbacks, and structured
result handling are intentionally skipped until explicit typemaps are added.
