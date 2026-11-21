#!/usr/bin/env python3
"""Low-impact live Steam API smoke test.

Run from the project root after `pip install .`.

The test initializes Steam, calls generated no-argument read-style SDK APIs,
prints a short result for each call, and shuts Steam down. Use --async to
include a bounded lobby search, lobby metadata refresh, and following-list check.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
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


class SkipCheck(Exception):
    """The current Steam account or app has no data for this check."""


def run_checks(checks, *, async_checks: bool, json_output: bool) -> list[dict]:
    results = []
    for interface, name, check in checks:
        result = {"interface": interface, "name": name, "async": async_checks}
        try:
            value = check()
        except SkipCheck as exc:
            result.update(ok=None, skipped=str(exc))
            status, detail = "SKIP", str(exc)
        except Exception as exc:
            result.update(ok=False, error=str(exc))
            status, detail = "FAIL", str(exc)
        else:
            result.update(ok=True, value=value)
            status, detail = "OK", short(value)
        if not json_output:
            print(f"{status:4} {interface}.{name}: {detail}")
        results.append(result)
    return results


def parameterized_checks(steamworks):
    def app_installation():
        app_id = steamworks.utils.app_id()
        if not app_id:
            raise RuntimeError("Steam returned no configured App ID")
        directory = steamworks.apps.app_install_dir_string(app_id)
        depots = steamworks.apps.installed_depots_list(app_id)
        if not directory and not depots:
            raise SkipCheck("No local installation data for the configured app")
        if not directory:
            raise RuntimeError("Steam returned installed depots without an install directory")
        if any(not int(depot) for depot in depots):
            raise RuntimeError("Steam returned an invalid depot ID")
        return {"app_id": app_id, "depot_count": len(depots)}

    def first_achievement():
        if not steamworks.user_stats.num_achievements():
            raise SkipCheck("The configured app reports no achievements")
        if not steamworks.user_stats.achievement_name(0):
            raise RuntimeError("Steam returned an empty name for the first achievement")
        return {"name_present": True}

    def first_friend():
        count = steamworks.friends.friend_count_immediate()
        if not count:
            raise SkipCheck("The account reports no friends")
        if count < 0 or not steamworks.friends.friend_by_index_immediate(0):
            raise RuntimeError("Steam could not resolve the first friend")
        return {"friend_id_present": True}

    return [
        ("Apps", "ConfiguredAppInstallation", app_installation),
        ("UserStats", "FirstAchievement", first_achievement),
        ("Friends", "FirstFriend", first_friend),
    ]


def pump_until(callbacks, ready, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        callbacks.pump()
        if ready():
            return True
        time.sleep(0.05)
    return False


def run_async_checks(steamworks, callbacks, *, json_output: bool) -> list[dict]:
    from enumerate_following import wait_for_manual_api_call

    matchmaking = steamworks.matchmaking
    lobby_ids = ()

    def request_lobby_list():
        nonlocal lobby_ids
        matchmaking.add_request_lobby_list_result_count_filter(10)
        request = callbacks.request_lobby_list()
        if not pump_until(callbacks, lambda: request.poll() is not None, 25):
            raise TimeoutError("Lobby list did not complete within 25 seconds")
        result = request.poll()
        if result.status != "complete" or result.io_failure:
            raise RuntimeError(f"Lobby list failed: {result.status}, I/O failure={result.io_failure}")
        if any(not lobby_id for lobby_id in result.lobby_ids):
            raise RuntimeError("Steam returned an invalid lobby ID")
        lobby_ids = result.lobby_ids
        return {"lobby_count": len(lobby_ids)}

    def request_lobby_metadata():
        if not lobby_ids:
            raise SkipCheck("No lobby available from the search")
        lobby_id = lobby_ids[0]
        update = None

        def on_update(event):
            nonlocal update
            if event.lobby_id == lobby_id and event.member_id == lobby_id:
                update = event

        unregister = callbacks.register(steamworks.LobbyDataUpdate, on_update)
        try:
            if not matchmaking.request_lobby_data(lobby_id):
                raise RuntimeError("Steam rejected the lobby metadata request")
            if not pump_until(callbacks, lambda: update is not None, 10):
                raise TimeoutError("Lobby metadata did not arrive within 10 seconds")
            if not update.success:
                raise SkipCheck("The lobby is no longer available")
            return {"metadata_count": matchmaking.lobby_data_count(lobby_id)}
        finally:
            unregister()

    def enumerate_following_list():
        handle = steamworks.friends.enumerate_following_list(0)
        if not handle:
            raise RuntimeError("Steam returned no following-list request handle")
        completed, fields = wait_for_manual_api_call(handle, 10)
        if not completed:
            raise TimeoutError("Following-list request did not complete within 10 seconds")
        if fields.get("failed") != "false":
            raise RuntimeError(f"Following-list request completion failed: {fields}")
        return {"completed": True}

    return run_checks([
        ("Matchmaking", "RequestLobbyList", request_lobby_list),
        ("Matchmaking", "RequestLobbyData", request_lobby_metadata),
        ("Friends", "EnumerateFollowingList", enumerate_following_list),
    ], async_checks=True, json_output=json_output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default="generated/steamworks_c_api_model.json",
        help="Path to generated C ABI model",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--limit", type=int, help="Only run the first N selected calls")
    parser.add_argument(
        "--async", dest="include_async", action="store_true",
        help="Also run the read-only lobby search, lobby metadata, and following-list requests",
    )
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
    checks = parameterized_checks(steamworks)
    if args.limit is not None:
        if args.limit < 0:
            parser.error("--limit must be nonnegative")
        checks = checks[:max(0, args.limit - len(calls))]
        calls = calls[:args.limit]

    init_result = steamworks.init_ex()
    if init_result != 0:
        print(f"steamworks.init_ex() failed ({init_result}): {steamworks.last_init_error()}", file=sys.stderr)
        print("Make sure Steam is running and steam_appid.txt is in the working directory.", file=sys.stderr)
        return 1

    results = []
    try:
        callbacks = steamworks.ClientCallbacks() if args.include_async else None
        if callbacks is None:
            steamworks.run_callbacks()
        else:
            callbacks.pump()
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
        results.extend(run_checks(checks, async_checks=False, json_output=args.json))
        if callbacks is not None:
            results.extend(run_async_checks(steamworks, callbacks, json_output=args.json))
    finally:
        steamworks.shutdown()

    failed = sum(item["ok"] is False for item in results)
    skipped = sum(item["ok"] is None for item in results)
    if args.json:
        print(json.dumps({"total": len(results), "failed": failed, "skipped": skipped, "results": results}, indent=2))
    else:
        print(f"\nLive smoke complete: {len(results) - failed - skipped} passed, {failed} failed, {skipped} skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
