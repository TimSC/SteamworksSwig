#!/usr/bin/env python3
"""Generate the shared Steamworks C ABI model from SDK metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate_callbacks import manual_dispatch_c_functions
from generate_output_helpers import (
    candidate_from_dict,
    output_helper_functions,
    promoted_candidate_dicts,
)
from generator_io import load_json, write_text
from steamworks_discovery import declared_identifiers, iter_wrappable_methods
from steamworks_helpers import C_HELPER_FUNCTIONS, C_MANUAL_FUNCTIONS
from steamworks_model import c_api_methods, c_api_model, classify_skipped_methods


def has_matchmaking_server_friends(steam_include: Path) -> bool:
    matchmaking = steam_include / "steam" / "isteammatchmaking.h"
    header_text = matchmaking.read_text(encoding="utf-8", errors="replace")
    return (
        "class ISteamMatchmakingServerFriendsResponse" in header_text
        and "ServerFriends( uint32 unIP, uint16 usPort" in header_text
    )


def template_features(steam_include: Path) -> dict:
    matchmaking_types = steam_include / "steam" / "matchmakingtypes.h"
    networking_types = steam_include / "steam" / "steamnetworkingtypes.h"
    return {
        "game_server_item_friend_counts": "m_nCurrentFriendCount"
        in matchmaking_types.read_text(encoding="utf-8", errors="replace"),
        "matchmaking_server_friends": has_matchmaking_server_friends(steam_include),
        "connection_realtime_max_jitter": "m_usecMaxJitter"
        in networking_types.read_text(encoding="utf-8", errors="replace"),
    }


def generate_model(api: dict, steam_include: Path, api_json: Path | None = None) -> dict:
    flat_header = steam_include / "steam" / "steam_api_flat.h"
    flat_header_text = flat_header.read_text(encoding="utf-8", errors="replace")
    flat_identifiers = declared_identifiers(flat_header_text)
    methods = sorted(
        iter_wrappable_methods(api, flat_identifiers),
        key=lambda item: item["wrapper_name"],
    )
    output_helpers = promoted_candidate_dicts(api, flat_identifiers)
    output_helper_candidates = [
        candidate_from_dict(candidate)
        for candidate in output_helpers
    ]
    c_methods = c_api_methods(
        api,
        methods,
        manual_functions=C_MANUAL_FUNCTIONS,
        helper_functions=C_HELPER_FUNCTIONS + output_helper_functions(output_helper_candidates),
        manual_dispatch_functions=manual_dispatch_c_functions(),
    )
    skipped_methods = classify_skipped_methods(api, flat_identifiers, c_methods)
    model = c_api_model(
        api,
        c_methods,
        skipped_methods,
        generated_wrappers=methods,
        output_helpers=output_helpers,
        template_features=template_features(steam_include),
    )
    model["sdk"] = {
        "api_json": str(
            (api_json or steam_include / "steam" / "steam_api.json").resolve()
        ),
        "steam_include": str(steam_include.resolve()),
        "flat_header": str(flat_header.resolve()),
    }
    return model


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-json", default="sdk/public/steam/steam_api.json")
    parser.add_argument("--steam-include")
    parser.add_argument("--output", default="generated/steamworks_c_api_model.json")
    args = parser.parse_args()

    api_json = Path(args.api_json)
    steam_include = Path(args.steam_include) if args.steam_include else api_json.parent.parent
    model = generate_model(load_json(api_json), steam_include, api_json)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_text(output, json.dumps(model, indent=2, sort_keys=True) + "\n")
    print(
        f"Wrote model with {len(model.get('generated_wrappers', []))} wrapper functions "
        f"and {model['summary']['c_abi_functions_total']} C ABI functions to {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
