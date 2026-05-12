#!/usr/bin/env python3
"""Interactive Steam lobby and P2P server demo.

Run this script under two Steam accounts for the same AppID. One account can
create a lobby and host a P2P listen socket; the other can list and join it.
Console input is read on a background thread so the main thread keeps pumping
Steam callbacks.
"""

from __future__ import annotations

import argparse
import queue
import shlex
import sys
import threading
import time
from dataclasses import dataclass, field

import steamworks


DEFAULT_PORT = 0
PUMP_INTERVAL_SECONDS = 0.05


def parse_event(line: str) -> dict[str, str]:
    event: dict[str, str] = {}
    for part in line.split("\t"):
        key, _, value = part.partition("=")
        event[key] = value
    return event


def event_int(event: dict[str, str], key: str) -> int:
    try:
        return int(event.get(key, "0"))
    except ValueError:
        return 0


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on", "joinable"}:
        return True
    if normalized in {"0", "false", "no", "off", "closed"}:
        return False
    raise ValueError(f"expected boolean value, got {value!r}")


def lobby_type_value(name: str) -> int:
    normalized = name.strip().lower()
    if normalized == "private":
        return steamworks.k_ELobbyTypePrivate
    if normalized in {"friends", "friends-only", "friendsonly"}:
        return steamworks.k_ELobbyTypeFriendsOnly
    if normalized == "invisible":
        return steamworks.k_ELobbyTypeInvisible
    if normalized == "private-unique":
        return steamworks.k_ELobbyTypePrivateUnique
    return steamworks.k_ELobbyTypePublic


def lobby_type_name(value: int) -> str:
    names = {
        steamworks.k_ELobbyTypePrivate: "private",
        steamworks.k_ELobbyTypeFriendsOnly: "friends",
        steamworks.k_ELobbyTypePublic: "public",
        steamworks.k_ELobbyTypeInvisible: "invisible",
        steamworks.k_ELobbyTypePrivateUnique: "private-unique",
    }
    return names.get(value, str(value))


def persona_state_name(value: int) -> str:
    names = {
        steamworks.k_EPersonaStateOffline: "offline",
        steamworks.k_EPersonaStateOnline: "online",
        steamworks.k_EPersonaStateBusy: "busy",
        steamworks.k_EPersonaStateAway: "away",
        steamworks.k_EPersonaStateSnooze: "snooze",
        steamworks.k_EPersonaStateLookingToTrade: "looking-to-trade",
        steamworks.k_EPersonaStateLookingToPlay: "looking-to-play",
        steamworks.k_EPersonaStateInvisible: "invisible",
    }
    return names.get(value, str(value))


def enqueue_stdin(lines: queue.Queue[str], stop: threading.Event) -> None:
    while not stop.is_set():
        line = sys.stdin.readline()
        if line == "":
            lines.put("quit")
            return
        lines.put(line.rstrip("\n"))


@dataclass
class DemoState:
    steam_id: int
    virtual_port: int
    listen_socket: int = 0
    current_lobby: int = 0
    lobby_results: list[int] = field(default_factory=list)
    online_friends: list[int] = field(default_factory=list)
    connections: set[int] = field(default_factory=set)
    connection_peers: dict[int, int] = field(default_factory=dict)
    attempted_hosts: set[tuple[int, int]] = field(default_factory=set)
    rich_presence: dict[str, str] = field(default_factory=dict)
    awaiting_list: bool = False
    awaiting_create: bool = False
    awaiting_join: bool = False
    running: bool = True


class Demo:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.state = DemoState(
            steam_id=steamworks.Steam_User_GetSteamID(),
            virtual_port=args.port,
        )

    def print_help(self) -> None:
        print(
            "\n".join(
                [
                    "Commands:",
                    "  host start [port]                   create a P2P listen socket",
                    "  host stop                           close the P2P listen socket",
                    "  lobby host start [port]             host the current lobby and tell members to connect",
                    "  lobby create [name] [public|friends|private] [max]",
                    "                                      create a lobby and advertise this host",
                    "  lobby list                          request and print lobbies",
                    "  lobby join <lobby-id|list-index>    join a lobby and connect to its host",
                    "  lobby invite <friend-index|steamid> invite a friend to the current lobby",
                    "  lobby members                       print current lobby members",
                    "  lobby data <list|get|set|delete>    inspect or edit lobby metadata",
                    "  lobby type <type>                   set lobby type",
                    "  lobby joinable <true|false>         set lobby joinability",
                    "  lobby owner [set <member|steamid>]  show or transfer lobby ownership",
                    "  lobby info                          print current lobby metadata",
                    "  lobby leave                         leave the current lobby",
                    "  friends                             list online friends",
                    "  friend rich <friend-index|steamid>  inspect a friend's rich presence",
                    "  client connect <steamid> [port]     connect directly to a P2P host",
                    "  client send <message>               send to all connected peers",
                    "  client players                      list peers connected to this host/client",
                    "  client detail [connection]          show connection diagnostics",
                    "  client flush [connection]           flush queued outbound messages",
                    "  client name <connection> <name>     name a connection for diagnostics",
                    "  client close                        close all P2P connections",
                    "  presence <text>                     set rich presence status",
                    "  presence auto                       set rich presence from current state",
                    "  presence connect [value]            set rich presence connect string",
                    "  presence-key <key> <value|clear>    set or clear a rich presence key",
                    "  presence show|clear                 show tracked values or clear all",
                    "  status                              print local state",
                    "  help                                show this help",
                    "  quit                                exit",
                ]
            )
        )

    def start_host(self, port: int | None = None) -> bool:
        if port is not None:
            self.state.virtual_port = port
        if self.state.listen_socket:
            print(f"Already hosting on virtual port {self.state.virtual_port}")
            return True

        listen_socket = steamworks.Steam_NetworkingSockets_CreateListenSocketP2PNoOptions(
            self.state.virtual_port
        )
        if not listen_socket:
            print("Failed to create P2P listen socket.")
            return False

        self.state.listen_socket = listen_socket
        print(
            f"Hosting P2P on SteamID {self.state.steam_id}, "
            f"virtual port {self.state.virtual_port}"
        )
        return True

    def stop_host(self) -> None:
        if not self.state.listen_socket:
            print("Host is not running.")
            return

        steamworks.Steam_NetworkingSockets_CloseListenSocket(self.state.listen_socket)
        self.state.listen_socket = 0
        print("Stopped P2P host listen socket.")

    def advertise_lobby_host(self, lobby_id: int) -> None:
        steamworks.Steam_Matchmaking_SetLobbyData(lobby_id, "state", "starting")
        steamworks.Steam_Matchmaking_SetLobbyData(
            lobby_id, "host_steam_id", str(self.state.steam_id)
        )
        steamworks.Steam_Matchmaking_SetLobbyData(
            lobby_id, "virtual_port", str(self.state.virtual_port)
        )
        steamworks.Steam_Matchmaking_SetLobbyData(lobby_id, "state", "playing")
        steamworks.Steam_Matchmaking_SetLobbyMemberData(lobby_id, "role", "host")

    def default_connect_string(self) -> str:
        values = [f"steamid={self.state.steam_id}", f"port={self.state.virtual_port}"]
        if self.state.current_lobby:
            values.append(f"lobby={self.state.current_lobby}")
        return ";".join(values)

    def current_presence_status(self) -> str:
        if self.state.current_lobby and self.state.listen_socket:
            return "Hosting lobby"
        if self.state.current_lobby:
            return "In lobby"
        if self.state.connections:
            return "Connected"
        if self.state.listen_socket:
            return "Hosting"
        return "In menu"

    def set_rich_presence(self, key: str, value: str) -> None:
        if not key:
            print("Rich presence key cannot be empty.")
            return

        updated = steamworks.Steam_Friends_SetRichPresence(key, value)
        if not updated:
            print(f"Failed to set rich presence key '{key}'.")
            return

        if value:
            self.state.rich_presence[key] = value
            print(f"Rich presence {key}={value}")
        else:
            self.state.rich_presence.pop(key, None)
            print(f"Cleared rich presence key '{key}'.")

    def clear_rich_presence(self) -> None:
        steamworks.Steam_Friends_ClearRichPresence()
        self.state.rich_presence.clear()
        print("Cleared rich presence.")

    def show_rich_presence(self) -> None:
        if not self.state.rich_presence:
            print("No tracked rich presence values.")
            return

        print("Tracked rich presence:")
        for key, value in sorted(self.state.rich_presence.items()):
            print(f"  {key}={value}")

    def handle_presence_command(self, parts: list[str]) -> None:
        if len(parts) < 2:
            print("Usage: presence <text>|connect [value]|show|clear")
            return

        subcommand = parts[1].lower()
        if subcommand == "clear":
            self.clear_rich_presence()
            return
        if subcommand == "show":
            self.show_rich_presence()
            return
        if subcommand == "auto":
            self.set_rich_presence("status", self.current_presence_status())
            self.set_rich_presence("connect", self.default_connect_string())
            return
        if subcommand == "connect":
            value = " ".join(parts[2:]) if len(parts) > 2 else self.default_connect_string()
            self.set_rich_presence("connect", value)
            return

        self.set_rich_presence("status", " ".join(parts[1:]))

    def handle_presence_key_command(self, parts: list[str]) -> None:
        if len(parts) < 3:
            print("Usage: presence-key <key> <value|clear>")
            return

        key = parts[1]
        if len(parts) == 3 and parts[2].lower() == "clear":
            self.set_rich_presence(key, "")
            return

        self.set_rich_presence(key, " ".join(parts[2:]))

    def start_lobby_host(self, port: int | None = None) -> None:
        lobby_id = self.state.current_lobby
        if not lobby_id:
            print("Create or join a lobby before running lobby host start.")
            return
        if steamworks.Steam_Matchmaking_GetLobbyOwner(lobby_id) != self.state.steam_id:
            print("Only the lobby owner should run lobby host start.")
            return
        if not self.start_host(port):
            return

        self.advertise_lobby_host(lobby_id)
        print(
            f"Lobby {lobby_id} is now advertising host {self.state.steam_id} "
            f"on virtual port {self.state.virtual_port}."
        )

    def create_lobby(self, parts: list[str]) -> None:
        if self.state.awaiting_create:
            print("Lobby creation is already pending.")
            return

        name = parts[1] if len(parts) > 1 else f"Python Demo {self.state.steam_id}"
        type_name = parts[2] if len(parts) > 2 else "public"
        max_members = int(parts[3]) if len(parts) > 3 else 4

        if not self.start_host(self.state.virtual_port):
            return
        steamworks.Steam_Lobby_Create(lobby_type_value(type_name), max_members)
        self.state.awaiting_create = True
        print(
            f"Creating {lobby_type_name(lobby_type_value(type_name))} lobby "
            f"'{name}' for {max_members} members..."
        )
        self.pending_lobby_name = name
        self.pending_lobby_type = type_name

    def finish_create_if_ready(self) -> None:
        if not self.state.awaiting_create or not steamworks.Steam_Lobby_IsCreateComplete():
            return

        self.state.awaiting_create = False
        if not steamworks.Steam_Lobby_CreateSucceeded():
            result = steamworks.Steam_Lobby_GetCreateResult()
            print(
                "Lobby creation failed "
                f"(io_failure={yes_no(steamworks.Steam_Lobby_CreateHadIOFailure())}, "
                f"result={result})."
            )
            return

        lobby_id = steamworks.Steam_Lobby_GetCreatedLobbyID()
        self.state.current_lobby = lobby_id
        steamworks.Steam_Matchmaking_SetLobbyData(lobby_id, "name", self.pending_lobby_name)
        steamworks.Steam_Matchmaking_SetLobbyData(lobby_id, "demo", "python")
        self.advertise_lobby_host(lobby_id)
        steamworks.Steam_Matchmaking_SetLobbyJoinable(lobby_id, True)
        print(f"Created lobby {lobby_id}. Other clients can run: lobby join {lobby_id}")

    def request_lobbies(self) -> None:
        if self.state.awaiting_list:
            print("Lobby list request is already pending.")
            return
        steamworks.Steam_Matchmaking_AddRequestLobbyListStringFilter(
            "demo", "python", steamworks.k_ELobbyComparisonEqual
        )
        steamworks.Steam_Lobby_RequestList()
        self.state.awaiting_list = True
        print("Requesting lobby list...")

    def finish_list_if_ready(self) -> None:
        if not self.state.awaiting_list or not steamworks.Steam_Lobby_IsListComplete():
            return

        self.state.awaiting_list = False
        self.state.lobby_results.clear()
        if steamworks.Steam_Lobby_ListHadIOFailure():
            print("Lobby list request failed with an IO failure.")
            return

        count = steamworks.Steam_Lobby_GetListResultCount()
        print(f"Found {count} lobby/lobbies")
        for index in range(count):
            lobby_id = steamworks.Steam_Lobby_GetListLobbyByIndex(index)
            self.state.lobby_results.append(lobby_id)
            name = steamworks.Steam_Matchmaking_GetLobbyData(lobby_id, "name") or "(unnamed)"
            host = steamworks.Steam_Matchmaking_GetLobbyData(lobby_id, "host_steam_id")
            port = steamworks.Steam_Matchmaking_GetLobbyData(lobby_id, "virtual_port")
            members = steamworks.Steam_Matchmaking_GetNumLobbyMembers(lobby_id)
            limit = steamworks.Steam_Matchmaking_GetLobbyMemberLimit(lobby_id)
            print(f"  [{index}] {lobby_id} {name} host={host} port={port} {members}/{limit}")

    def join_lobby(self, parts: list[str]) -> None:
        if len(parts) < 2:
            print("Usage: lobby join <lobby-id|list-index>")
            return
        if self.state.awaiting_join:
            print("Lobby join is already pending.")
            return

        value = int(parts[1])
        lobby_id = value
        if 0 <= value < len(self.state.lobby_results):
            lobby_id = self.state.lobby_results[value]

        steamworks.Steam_Lobby_Join(lobby_id)
        self.state.awaiting_join = True
        print(f"Joining lobby {lobby_id}...")

    def finish_join_if_ready(self) -> None:
        if not self.state.awaiting_join or not steamworks.Steam_Lobby_IsJoinComplete():
            return

        self.state.awaiting_join = False
        if not steamworks.Steam_Lobby_JoinSucceeded():
            print(
                "Lobby join failed "
                f"(io_failure={yes_no(steamworks.Steam_Lobby_JoinHadIOFailure())}, "
                f"response={steamworks.Steam_Lobby_GetJoinResponse()})."
            )
            return

        lobby_id = steamworks.Steam_Lobby_GetJoinedLobbyID()
        self.state.current_lobby = lobby_id
        steamworks.Steam_Matchmaking_SetLobbyMemberData(lobby_id, "role", "client")
        print(f"Joined lobby {lobby_id}")

        host = steamworks.Steam_Matchmaking_GetLobbyData(lobby_id, "host_steam_id")
        port = steamworks.Steam_Matchmaking_GetLobbyData(lobby_id, "virtual_port")
        if not host:
            print("Lobby has no host_steam_id metadata. Use client connect <steamid> manually.")
            return
        try:
            host_steam_id = int(host)
            host_port = int(port or self.state.virtual_port)
        except ValueError:
            print("Lobby host metadata is not numeric. Use client connect <steamid> manually.")
            return
        if host_steam_id == self.state.steam_id:
            print("This lobby advertises the local account as host.")
            return
        self.connect_to_peer(host_steam_id, host_port)

    def connect_to_peer(self, peer: int, port: int | None = None) -> None:
        remote_port = self.state.virtual_port if port is None else port
        connection = steamworks.Steam_NetworkingSockets_ConnectP2PSteamIDNoOptions(
            peer, remote_port
        )
        if not connection:
            print(f"Failed to start P2P connection to {peer}:{remote_port}")
            return
        self.state.attempted_hosts.add((peer, remote_port))
        print(f"Connecting to {peer} on virtual port {remote_port}, connection {connection}")

    def poll_lobby_host(self) -> None:
        lobby_id = self.state.current_lobby
        if not lobby_id or self.state.listen_socket:
            return

        state = steamworks.Steam_Matchmaking_GetLobbyData(lobby_id, "state")
        if state not in {"starting", "playing"}:
            return

        host = steamworks.Steam_Matchmaking_GetLobbyData(lobby_id, "host_steam_id")
        if not host:
            return

        try:
            host_steam_id = int(host)
        except ValueError:
            return
        if host_steam_id == self.state.steam_id:
            return

        try:
            port = int(
                steamworks.Steam_Matchmaking_GetLobbyData(lobby_id, "virtual_port")
                or self.state.virtual_port
            )
        except ValueError:
            return
        target = (host_steam_id, port)
        if target in self.state.attempted_hosts:
            return

        print(f"Lobby {lobby_id} is {state}; connecting to host {host_steam_id}:{port}")
        self.connect_to_peer(host_steam_id, port)

    def poll_network_events(self) -> None:
        connecting = steamworks.Steam_NetworkingConnectionState_Connecting()
        connected = steamworks.Steam_NetworkingConnectionState_Connected()
        closed = steamworks.Steam_NetworkingConnectionState_ClosedByPeer()
        problem = steamworks.Steam_NetworkingConnectionState_ProblemDetectedLocally()

        for line in steamworks.Steam_NetworkingSockets_PollConnectionStatusChangedStrings(32):
            event = parse_event(line)
            connection = event_int(event, "connection")
            listen_socket = event_int(event, "listen_socket")
            state = event_int(event, "state")
            old_state = event_int(event, "old_state")
            remote = event_int(event, "remote_steam_id")
            description = event.get("description", "")
            end_debug = event.get("end_debug", "")

            print(f"event conn={connection} remote={remote} {old_state}->{state} {description}")
            if end_debug:
                print(f"  end: {end_debug}")
            if remote:
                self.state.connection_peers[connection] = remote

            if state == connecting and listen_socket:
                result = steamworks.Steam_NetworkingSockets_AcceptConnection(connection)
                print(f"  accepted connection {connection}: {result}")
            elif state == connected:
                self.state.connections.add(connection)
            elif state in (closed, problem):
                self.state.connections.discard(connection)
                self.state.connection_peers.pop(connection, None)
                steamworks.Steam_NetworkingSockets_CloseConnection(
                    connection,
                    steamworks.Steam_NetConnectionEnd_AppGeneric(),
                    "closed",
                    False,
                )

    def poll_messages(self) -> None:
        for connection in list(self.state.connections):
            messages = steamworks.Steam_NetworkingSockets_ReceiveMessagesOnConnectionStrings(
                connection, 32
            )
            for payload in messages:
                print(f"recv {connection}: {payload}")

    def send_message(self, message: str) -> None:
        if not self.state.connections:
            print("No connected peers.")
            return
        for connection in list(self.state.connections):
            result = steamworks.Steam_NetworkingSockets_SendMessageToConnectionString(
                connection,
                message,
                steamworks.Steam_NetworkingSend_Reliable(),
            )
            print(f"send {connection}: {result}")

    def print_members(self) -> None:
        lobby_id = self.state.current_lobby
        if not lobby_id:
            print("Not in a lobby.")
            return
        count = steamworks.Steam_Matchmaking_GetNumLobbyMembers(lobby_id)
        print(f"Lobby {lobby_id} members:")
        for index in range(count):
            member = steamworks.Steam_Matchmaking_GetLobbyMemberByIndex(lobby_id, index)
            role = steamworks.Steam_Matchmaking_GetLobbyMemberData(lobby_id, member, "role")
            print(f"  {member} role={role}")

    def print_players(self) -> None:
        if not self.state.connections:
            print("No connected players.")
            return

        print("Connected players:")
        for index, connection in enumerate(sorted(self.state.connections)):
            steam_id = self.state.connection_peers.get(connection, 0)
            if steam_id:
                name = steamworks.Steam_Friends_GetFriendPersonaName(steam_id) or "(unknown)"
                print(f"  [{index}] conn={connection} steam_id={steam_id} name={name}")
            else:
                print(f"  [{index}] conn={connection} steam_id=(unknown)")

    def target_connections(self, parts: list[str], start_index: int) -> list[int]:
        if len(parts) <= start_index:
            return sorted(self.state.connections)
        return [int(parts[start_index])]

    def print_connection_details(self, parts: list[str]) -> None:
        connections = self.target_connections(parts, 2)
        if not connections:
            print("No connected peers.")
            return

        for connection in connections:
            peer = self.state.connection_peers.get(connection, 0)
            name = steamworks.Steam_NetworkingSockets_GetConnectionNameString(connection)
            detail = steamworks.Steam_NetworkingSockets_GetDetailedConnectionStatusString(connection)
            print(f"Connection {connection} peer={peer} name={name or '(unnamed)'}")
            print(detail or "  (no detail)")

    def flush_connections(self, parts: list[str]) -> None:
        connections = self.target_connections(parts, 2)
        if not connections:
            print("No connected peers.")
            return

        for connection in connections:
            result = steamworks.Steam_NetworkingSockets_FlushMessagesOnConnection(connection)
            print(f"flush {connection}: {result}")

    def name_connection(self, parts: list[str]) -> None:
        if len(parts) < 4:
            print("Usage: client name <connection> <name>")
            return
        connection = int(parts[2])
        name = " ".join(parts[3:])
        steamworks.Steam_NetworkingSockets_SetConnectionName(connection, name)
        print(f"Named connection {connection}: {name}")

    def list_online_friends(self) -> None:
        self.state.online_friends.clear()
        count = steamworks.Steam_Friends_GetFriendCount(steamworks.Steam_FriendFlagImmediate())
        print("Online friends:")
        for index in range(count):
            friend_id = steamworks.Steam_Friends_GetFriendByIndex(
                index, steamworks.Steam_FriendFlagImmediate()
            )
            state = steamworks.Steam_Friends_GetFriendPersonaState(friend_id)
            if state == steamworks.k_EPersonaStateOffline:
                continue

            display_index = len(self.state.online_friends)
            self.state.online_friends.append(friend_id)
            name = steamworks.Steam_Friends_GetFriendPersonaName(friend_id) or "(unknown)"
            in_game = yes_no(steamworks.Steam_Friends_IsFriendInCurrentGame(friend_id))
            steamworks.Steam_Friends_RequestFriendRichPresence(friend_id)
            status = steamworks.Steam_Friends_GetFriendRichPresence(friend_id, "status")
            connect = steamworks.Steam_Friends_GetFriendRichPresence(friend_id, "connect")
            print(
                f"  [{display_index}] {name} {friend_id} "
                f"state={persona_state_name(state)} in_current_game={in_game}"
            )
            if status:
                print(f"      status={status}")
            if connect:
                print(f"      connect={connect}")

        if not self.state.online_friends:
            print("  (none)")

    def invite_friend(self, parts: list[str]) -> None:
        lobby_id = self.state.current_lobby
        if not lobby_id:
            print("Create or join a lobby before inviting friends.")
            return
        if len(parts) < 2:
            print("Usage: lobby invite <friend-index|steamid>")
            return

        value = int(parts[1])
        friend_id = value
        if 0 <= value < len(self.state.online_friends):
            friend_id = self.state.online_friends[value]

        name = steamworks.Steam_Friends_GetFriendPersonaName(friend_id) or str(friend_id)
        invited = steamworks.Steam_Matchmaking_InviteUserToLobby(lobby_id, friend_id)
        if invited:
            print(f"Invited {name} ({friend_id}) to lobby {lobby_id}.")
        else:
            print(f"Failed to invite {name} ({friend_id}) to lobby {lobby_id}.")

    def resolve_friend_id(self, value: str) -> int:
        numeric = int(value)
        if 0 <= numeric < len(self.state.online_friends):
            return self.state.online_friends[numeric]
        return numeric

    def resolve_lobby_member_id(self, value: str) -> int:
        numeric = int(value)
        lobby_id = self.state.current_lobby
        if lobby_id and 0 <= numeric < steamworks.Steam_Matchmaking_GetNumLobbyMembers(lobby_id):
            return steamworks.Steam_Matchmaking_GetLobbyMemberByIndex(lobby_id, numeric)
        return numeric

    def print_friend_rich_presence(self, parts: list[str]) -> None:
        if len(parts) < 3 or parts[1].lower() != "rich":
            print("Usage: friend rich <friend-index|steamid>")
            return

        friend_id = self.resolve_friend_id(parts[2])
        name = steamworks.Steam_Friends_GetFriendPersonaName(friend_id) or "(unknown)"
        steamworks.Steam_Friends_RequestFriendRichPresence(friend_id)
        count = steamworks.Steam_Friends_GetFriendRichPresenceKeyCount(friend_id)
        print(f"Rich presence for {name} ({friend_id}):")
        if count <= 0:
            print("  (none)")
            return
        for index in range(count):
            key = steamworks.Steam_Friends_GetFriendRichPresenceKeyByIndex(friend_id, index)
            print(f"  {key}={steamworks.Steam_Friends_GetFriendRichPresence(friend_id, key)}")

    def print_lobby(self) -> None:
        lobby_id = self.state.current_lobby
        if not lobby_id:
            print("Not in a lobby.")
            return
        keys = ["name", "demo", "state", "host_steam_id", "virtual_port"]
        print(f"Lobby {lobby_id}:")
        for key in keys:
            print(f"  {key}={steamworks.Steam_Matchmaking_GetLobbyData(lobby_id, key)}")

    def handle_lobby_data_command(self, parts: list[str]) -> None:
        lobby_id = self.state.current_lobby
        if not lobby_id:
            print("Not in a lobby.")
            return
        if len(parts) < 3:
            print("Usage: lobby data <list|get|set|delete>")
            return

        action = parts[2].lower()
        if action == "list":
            entries = steamworks.Steam_Lobby_GetDataEntries(lobby_id)
            if not entries:
                print("No lobby metadata.")
                return
            print(f"Lobby {lobby_id} metadata:")
            for entry in entries:
                print(f"  {entry}")
        elif action == "get":
            if len(parts) < 4:
                print("Usage: lobby data get <key>")
                return
            print(f"{parts[3]}={steamworks.Steam_Matchmaking_GetLobbyData(lobby_id, parts[3])}")
        elif action == "set":
            if len(parts) < 5:
                print("Usage: lobby data set <key> <value>")
                return
            value = " ".join(parts[4:])
            updated = steamworks.Steam_Matchmaking_SetLobbyData(lobby_id, parts[3], value)
            print(f"Set {parts[3]}={value}: {yes_no(updated)}")
        elif action in {"delete", "del", "clear"}:
            if len(parts) < 4:
                print("Usage: lobby data delete <key>")
                return
            deleted = steamworks.Steam_Matchmaking_DeleteLobbyData(lobby_id, parts[3])
            print(f"Deleted {parts[3]}: {yes_no(deleted)}")
        else:
            print(f"Unknown lobby data command: {action}")

    def set_lobby_type(self, parts: list[str]) -> None:
        lobby_id = self.state.current_lobby
        if not lobby_id:
            print("Not in a lobby.")
            return
        if len(parts) < 3:
            print("Usage: lobby type <public|friends|private|invisible>")
            return
        updated = steamworks.Steam_Matchmaking_SetLobbyType(lobby_id, lobby_type_value(parts[2]))
        print(f"Set lobby type to {parts[2]}: {yes_no(updated)}")

    def set_lobby_joinable(self, parts: list[str]) -> None:
        lobby_id = self.state.current_lobby
        if not lobby_id:
            print("Not in a lobby.")
            return
        if len(parts) < 3:
            print("Usage: lobby joinable <true|false>")
            return
        joinable = parse_bool(parts[2])
        updated = steamworks.Steam_Matchmaking_SetLobbyJoinable(lobby_id, joinable)
        print(f"Set lobby joinable={yes_no(joinable)}: {yes_no(updated)}")

    def handle_lobby_owner_command(self, parts: list[str]) -> None:
        lobby_id = self.state.current_lobby
        if not lobby_id:
            print("Not in a lobby.")
            return

        owner = steamworks.Steam_Matchmaking_GetLobbyOwner(lobby_id)
        if len(parts) == 2:
            name = steamworks.Steam_Friends_GetFriendPersonaName(owner) or "(unknown)"
            print(f"Lobby owner: {owner} {name}")
            return
        if len(parts) >= 4 and parts[2].lower() == "set":
            new_owner = self.resolve_lobby_member_id(parts[3])
            updated = steamworks.Steam_Matchmaking_SetLobbyOwner(lobby_id, new_owner)
            print(f"Set lobby owner to {new_owner}: {yes_no(updated)}")
            return
        print("Usage: lobby owner [set <member-index|steamid>]")

    def close_connections(self) -> None:
        for connection in list(self.state.connections):
            steamworks.Steam_NetworkingSockets_CloseConnection(
                connection,
                steamworks.Steam_NetConnectionEnd_AppGeneric(),
                "closed by demo",
                False,
            )
        self.state.connections.clear()
        self.state.connection_peers.clear()
        if self.state.listen_socket:
            self.stop_host()
        print("Closed P2P connections and listen socket.")

    def status(self) -> None:
        print(f"SteamID: {self.state.steam_id}")
        print(f"AppID: {steamworks.Steam_Utils_GetAppID()}")
        print(f"Lobby: {self.state.current_lobby or '(none)'}")
        print(f"Hosting: {yes_no(bool(self.state.listen_socket))}")
        print(f"Virtual port: {self.state.virtual_port}")
        print(f"Connections: {sorted(self.state.connections)}")
        print(f"Peers: {self.state.connection_peers}")
        print(f"Rich presence: {self.state.rich_presence}")

    def leave_lobby(self) -> None:
        if self.state.current_lobby:
            steamworks.Steam_Matchmaking_LeaveLobby(self.state.current_lobby)
            print(f"Left lobby {self.state.current_lobby}")
            self.state.current_lobby = 0
        else:
            print("Not in a lobby.")

    def handle_lobby_command(self, parts: list[str]) -> None:
        if len(parts) < 2:
            print("Usage: lobby <create|list|join|host start|invite|members|data|type|joinable|owner|info|leave>")
            return

        subcommand = parts[1].lower()
        subparts = parts[1:]
        if subcommand == "create":
            self.create_lobby(subparts)
        elif subcommand == "list":
            self.request_lobbies()
        elif subcommand == "join":
            self.join_lobby(subparts)
        elif subcommand == "host" and len(parts) > 2 and parts[2].lower() == "start":
            self.start_lobby_host(int(parts[3]) if len(parts) > 3 else None)
        elif subcommand == "invite":
            self.invite_friend(subparts)
        elif subcommand == "members":
            self.print_members()
        elif subcommand == "data":
            self.handle_lobby_data_command(parts)
        elif subcommand == "type":
            self.set_lobby_type(parts)
        elif subcommand == "joinable":
            self.set_lobby_joinable(parts)
        elif subcommand == "owner":
            self.handle_lobby_owner_command(parts)
        elif subcommand in {"info", "show"}:
            self.print_lobby()
        elif subcommand == "leave":
            self.leave_lobby()
        else:
            print(f"Unknown lobby command: {' '.join(parts[1:])}. Type help.")

    def handle_client_command(self, parts: list[str], line: str) -> None:
        if len(parts) < 2:
            print("Usage: client <connect|send|players|detail|flush|name|close>")
            return

        subcommand = parts[1].lower()
        if subcommand == "connect":
            if len(parts) < 3:
                print("Usage: client connect <steamid> [port]")
            else:
                self.connect_to_peer(int(parts[2]), int(parts[3]) if len(parts) > 3 else None)
        elif subcommand == "send":
            split_line = line.split(None, 2)
            self.send_message(split_line[2] if len(split_line) > 2 else "")
        elif subcommand == "players":
            self.print_players()
        elif subcommand == "detail":
            self.print_connection_details(parts)
        elif subcommand == "flush":
            self.flush_connections(parts)
        elif subcommand == "name":
            self.name_connection(parts)
        elif subcommand == "close":
            self.close_connections()
        else:
            print(f"Unknown client command: {' '.join(parts[1:])}. Type help.")

    def handle_host_command(self, parts: list[str]) -> None:
        if len(parts) < 2:
            print("Usage: host <start|stop>")
            return

        subcommand = parts[1].lower()
        if subcommand == "start":
            self.start_host(int(parts[2]) if len(parts) > 2 else None)
        elif subcommand == "stop":
            self.stop_host()
        else:
            print(f"Unknown host command: {' '.join(parts[1:])}. Type help.")

    def handle_command(self, line: str) -> None:
        try:
            parts = shlex.split(line)
        except ValueError as exc:
            print(f"Could not parse command: {exc}")
            return
        if not parts:
            return

        command = parts[0].lower()
        try:
            if command == "help":
                self.print_help()
            elif command == "lobby":
                self.handle_lobby_command(parts)
            elif command == "client":
                self.handle_client_command(parts, line)
            elif command == "host":
                self.handle_host_command(parts)
            elif command in {"friends", "online"}:
                self.list_online_friends()
            elif command == "friend":
                self.print_friend_rich_presence(parts)
            elif command == "presence":
                self.handle_presence_command(parts)
            elif command in {"presence-key", "presence_key"}:
                self.handle_presence_key_command(parts)
            elif command == "status":
                self.status()
            elif command in {"quit", "exit"}:
                self.state.running = False
            else:
                print(f"Unknown command: {command}. Type help.")
        except (ValueError, OverflowError) as exc:
            print(f"Invalid command argument: {exc}")

    def run(self) -> None:
        lines: queue.Queue[str] = queue.Queue()
        stop = threading.Event()
        thread = threading.Thread(target=enqueue_stdin, args=(lines, stop), daemon=True)
        thread.start()

        self.print_help()
        self.status()
        print("Enter a command:")

        try:
            while self.state.running:
                steamworks.Steam_RunCallbacks()
                self.finish_create_if_ready()
                self.finish_list_if_ready()
                self.finish_join_if_ready()
                self.poll_lobby_host()
                self.poll_network_events()
                self.poll_messages()

                while True:
                    try:
                        line = lines.get_nowait()
                    except queue.Empty:
                        break
                    self.handle_command(line)

                time.sleep(PUMP_INTERVAL_SECONDS)
        finally:
            stop.set()
            if self.state.current_lobby:
                steamworks.Steam_Matchmaking_LeaveLobby(self.state.current_lobby)
            self.close_connections()


def init_steam() -> bool:
    missing = [
        name
        for name in ["Steam_Lobby_Create", "Steam_Lobby_IsCreateComplete"]
        if not hasattr(steamworks, name)
    ]
    if missing:
        print(
            "The installed steamworks module does not expose the new lobby-create "
            f"helpers: {', '.join(missing)}. Reinstall with `pip install .`.",
            file=sys.stderr,
        )
        return False

    if not steamworks.Steam_IsSteamRunning():
        print("Steam is not running.", file=sys.stderr)
        return False

    result = steamworks.Steam_InitEx()
    if result != 0:
        print(
            f"Steam_InitEx failed ({result}): {steamworks.Steam_GetLastInitError()}",
            file=sys.stderr,
        )
        return False

    steamworks.Steam_NetworkingUtils_InitRelayNetworkAccess()
    steamworks.Steam_NetworkingSockets_EnableConnectionStatusCallbacks()
    steamworks.Steam_NetworkingSockets_ClearConnectionStatusChangedEvents()
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="P2P virtual port")
    args = parser.parse_args()

    if not init_steam():
        return 1

    try:
        Demo(args).run()
    finally:
        steamworks.Steam_Shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
