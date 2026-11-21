"""Request-scoped lobby results and typed client callbacks."""

from __future__ import annotations

from typing import NamedTuple

from . import _events
from . import grouped as _api


def result_name(result: int) -> str:
    """Return the SDK EResult member name, or a numeric label for newer values."""
    try:
        return _api.EResult(result).name
    except ValueError:
        return f"Unknown({result})"


class LobbyRequestResult(NamedTuple):
    status: str
    io_failure: bool | None = None
    lobby_id: int | None = None
    result_code: int | None = None
    join_response: int | None = None
    lobby_ids: tuple[int, ...] = ()


class LobbyRequest:
    """An outstanding Steam lobby call. poll() retains its terminal result."""

    def __init__(self, handle: int, operation: str):
        self.handle = handle
        self.operation = operation
        self._result = None if handle else LobbyRequestResult("rejected")

    def poll(self) -> LobbyRequestResult | None:
        return self._result


class ClientCallbacks:
    """Pump the client pipe in manual mode and dispatch registered Python handlers."""

    def __init__(self):
        self._pipe = _api.h_steam_pipe()
        if not self._pipe:
            raise RuntimeError("Initialize the Steamworks client before creating ClientCallbacks")
        self._require_manual(allow_uninitialized=True)
        _api.manual_dispatch.init()
        self._require_manual()
        dispatch = _api.manual_dispatch
        self._events = {
            _events.ConnectionStatusChanged: (
                dispatch.callback_id_steam_net_connection_status_changed,
                dispatch.decode_callback_steam_net_connection_status_changed,
                _events.connection_status_changed,
            ),
            _events.LobbyDataUpdate: (
                dispatch.callback_id_lobby_data_update,
                dispatch.decode_callback_lobby_data_update, _events.lobby_data_update,
            ),
            _events.GameLobbyJoinRequested: (
                dispatch.callback_id_game_lobby_join_requested,
                dispatch.decode_callback_game_lobby_join_requested, _events.game_lobby_join_requested,
            ),
            _events.GameRichPresenceJoinRequested: (
                dispatch.callback_id_game_rich_presence_join_requested,
                dispatch.decode_callback_game_rich_presence_join_requested,
                _events.game_rich_presence_join_requested,
            ),
            _events.FloatingGamepadTextInputDismissed: (
                dispatch.callback_id_floating_gamepad_text_input_dismissed,
                dispatch.decode_callback_floating_gamepad_text_input_dismissed,
                _events.floating_gamepad_text_input_dismissed,
            ),
        }
        self._result_decoders = {
            "create": (dispatch.callback_id_lobby_created(), dispatch.decode_api_call_result_lobby_created),
            "join": (dispatch.callback_id_lobby_enter(), dispatch.decode_api_call_result_lobby_enter),
            "list": (dispatch.callback_id_lobby_match_list(), dispatch.decode_api_call_result_lobby_match_list),
        }
        self._handlers = {}
        self._requests = {}
        self._list_handle = None
        self._pumping = False

    def _require_manual(self, *, allow_uninitialized=False):
        mode = _api.callback_dispatch_mode()
        if mode != _api.callback_dispatch_mode_manual() and not (
            allow_uninitialized and mode == _api.callback_dispatch_mode_uninitialized()
        ):
            raise RuntimeError("ClientCallbacks requires manual Steam callback dispatch")

    def _require_pipe(self):
        if _api.h_steam_pipe() != self._pipe:
            raise RuntimeError("The Steamworks client pipe is no longer active")
        self._require_manual()

    def register(self, event_type, handler):
        """Register a typed event handler and return a function that removes it."""
        callback_id, read, decode = self._events[event_type]
        handlers = self._handlers.setdefault(callback_id(), (read, decode, {}))[2]
        token = object()
        handlers[token] = handler

        def unregister():
            handlers.pop(token, None)

        return unregister

    def create_lobby(self, lobby_type: int, max_members: int) -> LobbyRequest:
        self._require_pipe()
        return self._track("create", _api.matchmaking.create_lobby(lobby_type, max_members))

    def join_lobby(self, lobby_id: int) -> LobbyRequest:
        self._require_pipe()
        return self._track("join", _api.matchmaking.join_lobby(lobby_id))

    def request_lobby_list(self) -> LobbyRequest:
        self._require_pipe()
        handle = _api.matchmaking.request_lobby_list()
        if handle:
            if self._list_handle is not None:
                previous = self._requests.pop(self._list_handle)
                previous._result = LobbyRequestResult("superseded")
            self._list_handle = handle
        return self._track("list", handle)

    def _track(self, operation, handle):
        request = LobbyRequest(handle, operation)
        if handle:
            self._requests[handle] = request
        return request

    def _complete_request(self, dispatch):
        handle = dispatch.completed_api_call()
        request = self._requests.get(handle)
        if request is None:
            return
        callback_id, read = self._result_decoders[request.operation]
        if dispatch.completed_callback_id() != callback_id:
            return
        del self._requests[handle]
        if self._list_handle == handle:
            self._list_handle = None

        ok = dispatch.api_call_result(self._pipe, handle, dispatch.completed_callback_size(), callback_id)
        failed = dispatch.api_call_result_failed()
        fields = _events.parse_callback_payload(read()) if ok else {}
        if not fields:
            request._result = LobbyRequestResult("unavailable", io_failure=failed)
        elif request.operation == "create":
            request._result = LobbyRequestResult(
                "complete", failed, lobby_id=int(fields["lobby"]), result_code=int(fields["result"])
            )
        elif request.operation == "join":
            request._result = LobbyRequestResult(
                "complete", failed, lobby_id=int(fields["lobby"]), join_response=int(fields["response"])
            )
        else:
            lobby_ids = () if failed else tuple(
                _api.matchmaking.lobby_by_index(index)
                for index in range(int(fields["lobbies_matching"]))
            )
            request._result = LobbyRequestResult("complete", failed, lobby_ids=lobby_ids)

    def pump(self):
        """Run one client frame and deliver callbacks on the calling thread."""
        self._require_pipe()
        if self._pumping:
            raise RuntimeError("ClientCallbacks.pump() cannot be called recursively")
        self._pumping = True
        dispatch = _api.manual_dispatch
        try:
            dispatch.run_frame(self._pipe)
            while dispatch.next_callback(self._pipe):
                event = None
                handlers = ()
                try:
                    if dispatch.callback_is_api_call_completed():
                        self._complete_request(dispatch)
                    else:
                        entry = self._handlers.get(dispatch.callback_id())
                        if entry and entry[2]:
                            read, decode, registered = entry
                            payload = read()
                            if payload:
                                event = decode(payload)
                                handlers = tuple(registered.values())
                finally:
                    dispatch.free_last_callback(self._pipe)
                for handler in handlers:
                    handler(event)
        finally:
            self._pumping = False
