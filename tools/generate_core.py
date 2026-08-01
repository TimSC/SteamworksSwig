#!/usr/bin/env python3
"""Generate Steamworks helper sources and the shared C ABI model from steam_api.json.

This intentionally starts with the subset that maps cleanly to scripting
languages: interface methods with a known flat accessor and value-like
parameters. Pointer/out/ref APIs, callbacks, structs, and raw interface-returning
functions are skipped until they have explicit helper coverage.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generator_io import load_json, render_template, write_text
from generate_callbacks import (
    manual_dispatch_c_functions,
    manual_dispatch_declarations,
    manual_dispatch_definitions,
    manual_dispatch_serializer_forward_declarations,
    manual_dispatch_serializers,
)
from generate_c_abi import write_c_abi_files
from steamworks_helpers import C_HELPER_FUNCTIONS, C_MANUAL_FUNCTIONS
from steamworks_discovery import declared_identifiers, iter_wrappable_methods
from steamworks_model import (
    c_api_methods,
    c_api_model,
    classify_skipped_methods,
)


def declaration(method: dict) -> str:
    params = ", ".join(f"{type_name} {name}" for type_name, name in method["params"])
    return f'{method["return_type"]} {method["wrapper_name"]}( {params} );'


def definition(method: dict) -> str:
    params = ", ".join(f"{type_name} {name}" for type_name, name in method["params"])
    args = ", ".join(["self"] + [name for _, name in method["params"]])
    lines = [
        f'{method["return_type"]} {method["wrapper_name"]}( {params} )',
        "{",
        f'\tauto *self = {method["accessor"]}();',
        "\tif ( !self )",
        "\t{",
    ]
    if method["return_type"] == "void":
        lines.append("\t\treturn;")
    else:
        lines.append("\t\treturn {};")
    lines.extend(
        [
            "\t}",
        ]
    )
    if method["return_type"] == "void":
        lines.append(f'\t{method["flat_name"]}( {args} );')
    else:
        lines.append(f'\treturn {method["flat_name"]}( {args} );')
    lines.append("}")
    return "\n".join(lines)


def generate(api: dict, output_dir: Path, steam_include: Path) -> None:
    flat_header = steam_include / "steam" / "steam_api_flat.h"
    flat_header_text = flat_header.read_text(encoding="utf-8", errors="replace")
    flat_identifiers = declared_identifiers(flat_header_text)
    methods = sorted(
        iter_wrappable_methods(api, flat_identifiers),
        key=lambda item: item["wrapper_name"],
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    header = output_dir / "steamworks_helpers.h"
    source = output_dir / "steamworks_helpers.cpp"
    interface = output_dir / "steamworks.i"
    c_model = output_dir / "steamworks_c_api_model.json"

    generated_declarations = "\n".join(declaration(method) for method in methods)
    generated_definitions = "\n\n".join(definition(method) for method in methods)
    c_methods = c_api_methods(
        api,
        methods,
        manual_functions=C_MANUAL_FUNCTIONS,
        helper_functions=C_HELPER_FUNCTIONS,
        manual_dispatch_functions=manual_dispatch_c_functions(),
    )
    skipped_methods = classify_skipped_methods(api, flat_identifiers, c_methods)
    model = c_api_model(api, c_methods, skipped_methods)

    write_text(
        header,
        render_template(
            "steamworks_helpers.h.in",
            generated_declarations=generated_declarations,
            manual_dispatch_declarations=manual_dispatch_declarations(),
            matchmaking_server_friends_declarations=matchmaking_server_friends_declarations(
                steam_include
            ),
        )
        + "\n",
    )

    write_text(
        source,
        render_template(
            "steamworks_helpers.cpp.in",
            generated_definitions=generated_definitions,
            manual_dispatch_serializer_forward_declarations=manual_dispatch_serializer_forward_declarations(),
            manual_dispatch_serializers=manual_dispatch_serializers(),
            manual_dispatch_definitions=manual_dispatch_definitions(),
            game_server_item_optional_fields=game_server_item_optional_fields(
                steam_include
            ),
            matchmaking_server_friends_helpers=matchmaking_server_friends_helpers(
                steam_include
            ),
            matchmaking_server_friends_definitions=matchmaking_server_friends_definitions(
                steam_include
            ),
            matchmaking_server_friends_clear=matchmaking_server_friends_clear(
                steam_include
            ),
            matchmaking_server_friends_declarations=matchmaking_server_friends_declarations(
                steam_include
            ),
            connection_realtime_optional_fields=connection_realtime_optional_fields(
                steam_include
            ),
        )
        + "\n",
    )

    write_text(
        interface,
        render_template("steamworks.i.in")
        + "\n",
    )

    write_text(
        c_model,
        json.dumps(model, indent=2, sort_keys=True) + "\n",
    )
    write_c_abi_files(model, output_dir)

    print(
        f"Generated {len(methods)} wrapper functions and {len(c_methods)} C ABI functions in {output_dir} "
        f"using {flat_header}"
    )


def game_server_item_optional_fields(steam_include: Path) -> str:
    matchmaking_types = steam_include / "steam" / "matchmakingtypes.h"
    header_text = matchmaking_types.read_text(encoding="utf-8", errors="replace")
    if "m_nCurrentFriendCount" not in header_text:
        return ""
    return "\n".join(
        [
            '\tresult += "\\tcurrent_friend_count=" + std::to_string( server.m_nCurrentFriendCount );',
            '\tresult += "\\ttotal_friend_count=" + std::to_string( server.m_nTotalFriendCount );',
        ]
    )


def has_server_friends(steam_include: Path) -> bool:
    matchmaking = steam_include / "steam" / "isteammatchmaking.h"
    header_text = matchmaking.read_text(encoding="utf-8", errors="replace")
    return (
        "class ISteamMatchmakingServerFriendsResponse" in header_text
        and "ServerFriends( uint32 unIP, uint16 usPort" in header_text
    )


def matchmaking_server_friends_declarations(steam_include: Path) -> str:
    if not has_server_friends(steam_include):
        return ""
    return "\n".join(
        [
            "HServerQuery Steam_MatchmakingServers_ServerFriends( uint32 ip, uint16 port );",
            "bool Steam_MatchmakingServers_IsServerFriendsPending();",
            "bool Steam_MatchmakingServers_IsServerFriendsComplete();",
            "bool Steam_MatchmakingServers_ServerFriendsFailed();",
            "bool Steam_MatchmakingServers_ServerFriendsSucceeded();",
            "std::vector<std::string> Steam_MatchmakingServers_GetServerFriends();",
            "void Steam_MatchmakingServers_ClearServerFriendsResult();",
        ]
    )


def matchmaking_server_friends_helpers(steam_include: Path) -> str:
    if not has_server_friends(steam_include):
        return ""
    return r'''
class MatchmakingServerFriendsResponse : public ISteamMatchmakingServerFriendsResponse
{
public:
	HServerQuery ServerFriends( uint32 ip, uint16 port )
	{
		Clear();

		ISteamMatchmakingServers *servers = SteamMatchmakingServers();
		if ( !servers )
		{
			m_complete = true;
			m_failed = true;
			return HSERVERQUERY_INVALID;
		}

		m_query = servers->ServerFriends( ip, port, this );
		if ( m_query == HSERVERQUERY_INVALID )
		{
			m_complete = true;
			m_failed = true;
			return m_query;
		}

		m_pending = true;
		return m_query;
	}

	void AddFriendToList( CSteamID steamID, const char *pchName, bool bCurrentlyConnected ) override
	{
		std::string friendInfo;
		friendInfo.reserve( 256 );
		friendInfo += "steam_id=" + std::to_string( steamID.ConvertToUint64() );
		friendInfo += "\tname=" + EscapeEventField( pchName ? pchName : "" );
		friendInfo += "\tcurrently_connected=" + std::to_string( bCurrentlyConnected ? 1 : 0 );
		m_friends.push_back( friendInfo );
	}

	void FriendsFailedToRespond() override
	{
		m_pending = false;
		m_complete = true;
		m_failed = true;
	}

	void FriendsRefreshComplete() override
	{
		m_pending = false;
		m_complete = true;
		m_failed = false;
	}

	bool IsPending() const { return m_pending; }
	bool IsComplete() const { return m_complete; }
	bool Failed() const { return m_complete && m_failed; }
	bool Succeeded() const { return m_complete && !m_failed; }
	std::vector<std::string> GetFriends() const { return m_friends; }

	void Clear()
	{
		CancelPendingQuery();
		m_query = HSERVERQUERY_INVALID;
		m_pending = false;
		m_complete = false;
		m_failed = false;
		m_friends.clear();
	}

private:
	void CancelPendingQuery()
	{
		if ( !m_pending || m_query == HSERVERQUERY_INVALID )
		{
			return;
		}

		ISteamMatchmakingServers *servers = SteamMatchmakingServers();
		if ( servers )
		{
			servers->CancelServerQuery( m_query );
		}
	}

	HServerQuery m_query = HSERVERQUERY_INVALID;
	bool m_pending = false;
	bool m_complete = false;
	bool m_failed = false;
	std::vector<std::string> m_friends;
};

MatchmakingServerFriendsResponse g_matchmakingServerFriendsResponse;
'''.strip()


def matchmaking_server_friends_definitions(steam_include: Path) -> str:
    if not has_server_friends(steam_include):
        return ""
    return r'''
HServerQuery Steam_MatchmakingServers_ServerFriends( uint32 ip, uint16 port )
{
	return g_matchmakingServerFriendsResponse.ServerFriends( ip, port );
}

bool Steam_MatchmakingServers_IsServerFriendsPending()
{
	return g_matchmakingServerFriendsResponse.IsPending();
}

bool Steam_MatchmakingServers_IsServerFriendsComplete()
{
	return g_matchmakingServerFriendsResponse.IsComplete();
}

bool Steam_MatchmakingServers_ServerFriendsFailed()
{
	return g_matchmakingServerFriendsResponse.Failed();
}

bool Steam_MatchmakingServers_ServerFriendsSucceeded()
{
	return g_matchmakingServerFriendsResponse.Succeeded();
}

std::vector<std::string> Steam_MatchmakingServers_GetServerFriends()
{
	return g_matchmakingServerFriendsResponse.GetFriends();
}

void Steam_MatchmakingServers_ClearServerFriendsResult()
{
	g_matchmakingServerFriendsResponse.Clear();
}
'''.strip()


def matchmaking_server_friends_clear(steam_include: Path) -> str:
    if not has_server_friends(steam_include):
        return ""
    return "g_matchmakingServerFriendsResponse.Clear();"


def connection_realtime_optional_fields(steam_include: Path) -> str:
    networking_types = steam_include / "steam" / "steamnetworkingtypes.h"
    header_text = networking_types.read_text(encoding="utf-8", errors="replace")
    if "m_usecMaxJitter" not in header_text:
        return ""
    return (
        '\tserialized += "\\tmax_jitter_usec=" '
        "+ std::to_string( status.m_usecMaxJitter );"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-json", default="sdk/public/steam/steam_api.json")
    parser.add_argument("--steam-include")
    parser.add_argument("--output-dir", default="generated")
    args = parser.parse_args()

    api_json = Path(args.api_json)
    steam_include = (
        Path(args.steam_include)
        if args.steam_include
        else api_json.parent.parent
    )
    api = load_json(api_json)
    generate(api, Path(args.output_dir), steam_include)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
