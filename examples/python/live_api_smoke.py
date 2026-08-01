#!/usr/bin/env python3
"""Low-impact live Steam API smoke test.

Run from the project root after `pip install .`.

The test initializes Steam, calls generated no-argument read-style SDK APIs,
prints a short result for each call, and shuts Steam down. It intentionally
skips mutating calls, parameterized calls, and async SteamAPICall_t request
starters.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SAFE_NAME_PREFIXES = ("BIs", "Is", "Get", "Has")
SKIP_NAME_PREFIXES = (
    "GetAPICall",
    "GetAuthSessionTicket",
    "GetEncryptedAppTicket",
    "GetNext",
)
SKIP_HELPER_RETURN_TYPES = {"SteamAPICall_t"}


def load_model(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} not found. Run from the project root after generating sources."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def live_smoke_calls(model: dict) -> list[dict]:
    calls = []
    for method in model.get("methods", []):
        name = method.get("friendly_name") or ""
        if method.get("source") != "sdk":
            continue
        if method.get("params"):
            continue
        if not name.startswith(SAFE_NAME_PREFIXES):
            continue
        if name.startswith(SKIP_NAME_PREFIXES):
            continue
        if method.get("helper_return_type") in SKIP_HELPER_RETURN_TYPES:
            continue
        calls.append(
            {
                "interface": method.get("interface") or "Global/static",
                "name": name,
                "raw": method["raw_c_name"],
            }
        )
    return sorted(calls, key=lambda call: (call["interface"], call["name"], call["raw"]))


def short(value) -> str:
    text = repr(value)
    if len(text) > 96:
        return text[:93] + "..."
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default="generated/steamworks_c_api_model.json",
        help="Path to generated C ABI model",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--limit", type=int, help="Only run the first N selected calls")
    args = parser.parse_args()

    try:
        import steamworks
        from steamworks import steamworks as raw
    except ImportError as exc:
        print(f"Failed to import steamworks wrapper: {exc}", file=sys.stderr)
        print("Install it first with `pip install .` from this directory.", file=sys.stderr)
        return 1

    if not steamworks.is_steam_running():
        print("steamworks.is_steam_running() returned false.", file=sys.stderr)
        print("Start Steam, log in, then run this program again from the project root.", file=sys.stderr)
        return 1

    calls = live_smoke_calls(load_model(Path(args.model)))
    if args.limit is not None:
        calls = calls[: args.limit]

    init_result = steamworks.init_ex()
    if init_result != 0:
        print(f"steamworks.init_ex() failed ({init_result}): {steamworks.last_init_error()}", file=sys.stderr)
        print("Make sure Steam is running and steam_appid.txt is in the working directory.", file=sys.stderr)
        return 1

    results = []
    try:
        steamworks.run_callbacks()
        for call in calls:
            label = f"{call['interface']}.{call['name']}"
            func = getattr(raw, call["raw"], None)
            if func is None:
                results.append({**call, "ok": False, "error": "missing raw function"})
                if not args.json:
                    print(f"MISS {label}: {call['raw']}")
                continue

            try:
                value = func()
            except Exception as exc:
                results.append({**call, "ok": False, "error": repr(exc)})
                if not args.json:
                    print(f"FAIL {label}: {exc!r}")
            else:
                results.append({**call, "ok": True, "value": repr(value)})
                if not args.json:
                    print(f"OK   {label}: {short(value)}")
    finally:
        steamworks.shutdown()

    failed = [item for item in results if not item["ok"]]
    if args.json:
        print(json.dumps({"total": len(results), "failed": len(failed), "results": results}, indent=2))
    else:
        print(f"\nLive smoke complete: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
