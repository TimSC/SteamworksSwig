"""Python bindings for the generated Steamworks SWIG wrapper."""

from __future__ import annotations

try:
    from . import steamworks as _raw
except ImportError as exc:
    raise ImportError(
        "The generated Steamworks extension is not available. "
        "Install this project with `pip install .` from the repository root."
    ) from exc

try:
    from .grouped import *  # noqa: F401,F403
except ImportError:
    pass


def _install_constant(name, getter_name):
    getter = getattr(_raw, getter_name, None)
    if getter is not None:
        globals()[name] = getter()


_install_constant("k_ELobbyTypePrivate", "SWS_Steam_LobbyTypePrivate")
_install_constant("k_ELobbyTypeFriendsOnly", "SWS_Steam_LobbyTypeFriendsOnly")
_install_constant("k_ELobbyTypePublic", "SWS_Steam_LobbyTypePublic")
_install_constant("k_ELobbyTypeInvisible", "SWS_Steam_LobbyTypeInvisible")
_install_constant("k_ELobbyTypePrivateUnique", "SWS_Steam_LobbyTypePrivateUnique")
_install_constant("k_ELobbyComparisonEqual", "SWS_Steam_LobbyComparisonEqual")
_install_constant("k_EPersonaStateOffline", "SWS_Steam_PersonaStateOffline")
_install_constant("k_EPersonaStateOnline", "SWS_Steam_PersonaStateOnline")
_install_constant("k_EPersonaStateBusy", "SWS_Steam_PersonaStateBusy")
_install_constant("k_EPersonaStateAway", "SWS_Steam_PersonaStateAway")
_install_constant("k_EPersonaStateSnooze", "SWS_Steam_PersonaStateSnooze")
_install_constant("k_EPersonaStateLookingToTrade", "SWS_Steam_PersonaStateLookingToTrade")
_install_constant("k_EPersonaStateLookingToPlay", "SWS_Steam_PersonaStateLookingToPlay")
_install_constant("k_EPersonaStateInvisible", "SWS_Steam_PersonaStateInvisible")


def parse_callback_payload(data: str) -> dict[str, str]:
    payload: dict[str, str] = {}
    if not data:
        return payload
    for field in data.split("\t"):
        key, separator, value = field.partition("=")
        if not separator or not key:
            continue
        payload[key] = _unescape_callback_payload_value(value)
    return payload


def _unescape_callback_payload_value(value: str) -> str:
    if "\\" not in value:
        return value

    result = []
    escaped = False
    for ch in value:
        if escaped:
            if ch == "t":
                result.append("\t")
            elif ch == "n":
                result.append("\n")
            elif ch == "r":
                result.append("\r")
            elif ch == "\\":
                result.append("\\")
            else:
                result.append("\\")
                result.append(ch)
            escaped = False
            continue

        if ch == "\\":
            escaped = True
            continue
        result.append(ch)

    if escaped:
        result.append("\\")
    return "".join(result)
