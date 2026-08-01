"""Python bindings for the generated Steamworks SWIG wrapper."""

try:
    from .steamworks import *  # noqa: F401,F403
except ImportError as exc:
    raise ImportError(
        "The generated Steamworks extension is not available. "
        "Install this project with `pip install .` from the repository root."
    ) from exc


def _install_constant(name, getter_name):
    getter = globals().get(getter_name)
    if getter is not None:
        globals()[name] = getter()


_install_constant("k_ELobbyTypePrivate", "Steam_LobbyTypePrivate")
_install_constant("k_ELobbyTypeFriendsOnly", "Steam_LobbyTypeFriendsOnly")
_install_constant("k_ELobbyTypePublic", "Steam_LobbyTypePublic")
_install_constant("k_ELobbyTypeInvisible", "Steam_LobbyTypeInvisible")
_install_constant("k_ELobbyTypePrivateUnique", "Steam_LobbyTypePrivateUnique")
_install_constant("k_ELobbyComparisonEqual", "Steam_LobbyComparisonEqual")
_install_constant("k_EPersonaStateOffline", "Steam_PersonaStateOffline")
_install_constant("k_EPersonaStateOnline", "Steam_PersonaStateOnline")
_install_constant("k_EPersonaStateBusy", "Steam_PersonaStateBusy")
_install_constant("k_EPersonaStateAway", "Steam_PersonaStateAway")
_install_constant("k_EPersonaStateSnooze", "Steam_PersonaStateSnooze")
_install_constant("k_EPersonaStateLookingToTrade", "Steam_PersonaStateLookingToTrade")
_install_constant("k_EPersonaStateLookingToPlay", "Steam_PersonaStateLookingToPlay")
_install_constant("k_EPersonaStateInvisible", "Steam_PersonaStateInvisible")
