#!/usr/bin/env python3
"""Generate Steamworks helper sources from the shared C ABI model.

Run tools/generate_model.py first after changing the SDK, helper metadata, or
model classification logic.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from generator_io import load_json, render_template, write_text
from generate_callbacks import (
    manual_dispatch_declarations,
    manual_dispatch_definitions,
    manual_dispatch_serializer_forward_declarations,
    manual_dispatch_serializers,
)
from generate_c_abi import write_c_abi_files
from generate_output_helpers import (
    output_helper_declarations_from_model,
    output_helper_definitions_from_model,
)
from steamworks_helpers import C_HELPER_FUNCTIONS, C_MANUAL_FUNCTIONS


DEFAULT_MODEL = Path("generated/steamworks_c_api_model.json")


def declaration(method: dict) -> str:
    params = ", ".join(f"{type_name} {name}" for type_name, name in method["params"])
    return f'{method["return_type"]} {method["wrapper_name"]}( {params} );'


def helper_declaration(item: tuple) -> str:
    return_type, name, params = item
    rendered_params = ", ".join(f"{type_name} {param_name}" for type_name, param_name in params)
    if rendered_params:
        return f"{return_type} {name}( {rendered_params} );"
    return f"{return_type} {name}();"


def helper_declarations(items: list[tuple]) -> str:
    return "\n".join(helper_declaration(item) for item in items)


def manual_helper_declaration_items() -> list[tuple]:
    return [
        item
        for item in C_MANUAL_FUNCTIONS
        if item[1].startswith("Steam_Lobby_")
    ]


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


def generate(model: dict, output_dir: Path) -> None:
    methods = model.get("generated_wrappers", [])
    features = model.get("template_features", {})
    output_dir.mkdir(parents=True, exist_ok=True)

    header = output_dir / "steamworks_helpers.h"
    source = output_dir / "steamworks_helpers.cpp"
    interface = output_dir / "steamworks.i"

    generated_declarations = "\n".join(declaration(method) for method in methods)
    generated_definitions = "\n\n".join(definition(method) for method in methods)

    write_text(
        header,
        render_template(
            "steamworks_helpers.h.in",
            helper_declarations=helper_declarations(manual_helper_declaration_items() + C_HELPER_FUNCTIONS),
            generated_declarations=generated_declarations,
            output_helper_declarations=output_helper_declarations_from_model(model),
            manual_dispatch_declarations=manual_dispatch_declarations(),
        )
        + "\n",
    )

    write_text(
        source,
        render_template(
            "steamworks_helpers.cpp.in",
            generated_definitions=generated_definitions,
            output_helper_definitions=output_helper_definitions_from_model(model),
            manual_dispatch_serializer_forward_declarations=manual_dispatch_serializer_forward_declarations(),
            manual_dispatch_serializers=manual_dispatch_serializers(),
            manual_dispatch_definitions=manual_dispatch_definitions(),
            game_server_item_optional_fields=game_server_item_optional_fields(
                features.get("game_server_item_friend_counts", False)
            ),
            matchmaking_server_friends_helpers=matchmaking_server_friends_helpers(
                features.get("matchmaking_server_friends", False)
            ),
            matchmaking_server_friends_definitions=matchmaking_server_friends_definitions(
                features.get("matchmaking_server_friends", False)
            ),
            matchmaking_server_friends_clear=matchmaking_server_friends_clear(
                features.get("matchmaking_server_friends", False)
            ),
            matchmaking_server_friends_declarations=matchmaking_server_friends_declarations(
                features.get("matchmaking_server_friends", False)
            ),
            connection_realtime_optional_fields=connection_realtime_optional_fields(
                features.get("connection_realtime_max_jitter", False)
            ),
        )
        + "\n",
    )

    write_text(
        interface,
        render_template("steamworks.i.in")
        + "\n",
    )

    write_c_abi_files(model, output_dir)

    print(
        f"Generated helper and C ABI sources for {len(methods)} wrapper functions "
        f"and {len(model.get('methods', []))} C ABI functions in {output_dir}"
    )


def game_server_item_optional_fields(enabled: bool) -> str:
    if not enabled:
        return ""
    return "\n".join(
        [
            '\tresult += "\\tcurrent_friend_count=" + std::to_string( server.m_nCurrentFriendCount );',
            '\tresult += "\\ttotal_friend_count=" + std::to_string( server.m_nTotalFriendCount );',
        ]
    )


def matchmaking_server_friends_declarations(enabled: bool) -> str:
    if not enabled:
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


def matchmaking_server_friends_helpers(enabled: bool) -> str:
    if not enabled:
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


def matchmaking_server_friends_definitions(enabled: bool) -> str:
    if not enabled:
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


def matchmaking_server_friends_clear(enabled: bool) -> str:
    if not enabled:
        return ""
    return "g_matchmakingServerFriendsResponse.Clear();"


def connection_realtime_optional_fields(enabled: bool) -> str:
    if not enabled:
        return ""
    return (
        '\tserialized += "\\tmax_jitter_usec=" '
        "+ std::to_string( status.m_usecMaxJitter );"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=str(DEFAULT_MODEL))
    parser.add_argument("--output-dir", default="generated")
    args = parser.parse_args()

    generate(load_json(Path(args.model)), Path(args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
