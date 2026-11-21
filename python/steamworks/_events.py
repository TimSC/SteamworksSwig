"""Python types and decoders for the native helper's callback payloads."""

from __future__ import annotations

import re
from typing import NamedTuple


_ESCAPES = {"t": "\t", "n": "\n", "r": "\r", "\\": "\\"}


def parse_callback_payload(payload: str) -> dict[str, str]:
    """Decode the shim's tab-separated, escaped key/value fields."""
    fields = {}
    for field in payload.split("\t"):
        key, separator, value = field.partition("=")
        if separator:
            fields[key] = re.sub(r"\\([tnr\\])", lambda match: _ESCAPES[match[1]], value)
    return fields


class ConnectionRealTimeStatus(NamedTuple):
    result: int
    state: int
    ping_ms: int
    pending_reliable_bytes: int
    pending_unreliable_bytes: int
    unacknowledged_reliable_bytes: int
    queue_time_usec: int


class ConnectionStatusChanged(NamedTuple):
    connection: int
    listen_socket: int
    old_state: int
    new_state: int
    end_reason: int
    debug_text: str


def connection_real_time_status(payload: str) -> ConnectionRealTimeStatus | None:
    if not payload:
        return None
    fields = parse_callback_payload(payload)
    return ConnectionRealTimeStatus(*(int(fields[key]) for key in (
        "result", "state", "ping", "pending_reliable", "pending_unreliable",
        "sent_unacked_reliable", "queue_time_usec",
    )))


def connection_status_changed(payload: str) -> ConnectionStatusChanged:
    fields = parse_callback_payload(payload)
    return ConnectionStatusChanged(
        int(fields["connection"]), int(fields["listen_socket"]),
        int(fields["old_state"]), int(fields["state"]),
        int(fields["end_reason"]), fields["end_debug"],
    )


class LobbyDataUpdate(NamedTuple):
    lobby_id: int
    member_id: int
    success: bool


def lobby_data_update(payload: str) -> LobbyDataUpdate:
    fields = parse_callback_payload(payload)
    return LobbyDataUpdate(int(fields["lobby"]), int(fields["member"]), fields["success"] == "1")


class GameLobbyJoinRequested(NamedTuple):
    lobby_id: int
    friend_id: int


def game_lobby_join_requested(payload: str) -> GameLobbyJoinRequested:
    fields = parse_callback_payload(payload)
    return GameLobbyJoinRequested(int(fields["lobby"]), int(fields["friend"]))


class GameRichPresenceJoinRequested(NamedTuple):
    friend_id: int
    connect: str


def game_rich_presence_join_requested(payload: str) -> GameRichPresenceJoinRequested:
    fields = parse_callback_payload(payload)
    return GameRichPresenceJoinRequested(int(fields["friend"]), fields["connect"])


class FloatingGamepadTextInputDismissed(NamedTuple):
    """The floating keyboard closed. SDL provides any text and key events."""


def floating_gamepad_text_input_dismissed(_payload: str) -> FloatingGamepadTextInputDismissed:
    return FloatingGamepadTextInputDismissed()
