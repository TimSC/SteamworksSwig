"""Check that the installed wheel exposes the invite callbacks without Steam."""

import steamworks
import steamworks._steamworks


def main():
    dispatch = steamworks.manual_dispatch
    lobby = dispatch.callback_id_game_lobby_join_requested()
    presence = dispatch.callback_id_game_rich_presence_join_requested()
    dismissed = dispatch.callback_id_floating_gamepad_text_input_dismissed()
    assert all(callback_id > 0 for callback_id in (lobby, presence, dismissed))
    assert len({lobby, presence, dismissed}) == 3
    assert callable(dispatch.decode_callback_game_lobby_join_requested)
    assert callable(dispatch.decode_callback_game_rich_presence_join_requested)
    assert callable(dispatch.decode_callback_floating_gamepad_text_input_dismissed)
    assert steamworks.GameLobbyJoinRequested(1, 2).lobby_id == 1
    assert steamworks.GameRichPresenceJoinRequested(2, "join-token").connect == "join-token"
    assert steamworks.EResult.LimitExceeded.name == "LimitExceeded"
    assert steamworks.result_name(2**31 - 1) == "Unknown(2147483647)"
    assert steamworks.EFloatingGamepadTextInputMode.SingleLine == 0


if __name__ == "__main__":
    main()
