"""Manual-dispatch callback metadata used by the Steamworks generators."""

from __future__ import annotations

MANUAL_DISPATCH_CALLBACKS = [
    {
        "name": "LowBatteryPower",
        "type": "LowBatteryPower_t",
        "reserve": 64,
        "fields": [
            ("minutes_battery_left", "std::to_string( callback.m_nMinutesBatteryLeft )"),
        ],
    },
    {
        "name": "SteamShutdown",
        "type": "SteamShutdown_t",
        "reserve": 32,
        "fields": [
            ("shutdown", 'std::string( "1" )'),
        ],
    },
    {
        "name": "SteamServersConnected",
        "type": "SteamServersConnected_t",
        "reserve": 32,
        "fields": [
            ("connected", 'std::string( "1" )'),
        ],
    },
    {
        "name": "SteamServerConnectFailure",
        "type": "SteamServerConnectFailure_t",
        "reserve": 96,
        "fields": [
            ("result", "std::to_string( static_cast<int>( callback.m_eResult ) )"),
            ("still_retrying", "std::to_string( callback.m_bStillRetrying ? 1 : 0 )"),
        ],
    },
    {
        "name": "SteamServersDisconnected",
        "type": "SteamServersDisconnected_t",
        "reserve": 64,
        "fields": [
            ("result", "std::to_string( static_cast<int>( callback.m_eResult ) )"),
        ],
    },
    {
        "name": "IPCFailure",
        "type": "IPCFailure_t",
        "reserve": 64,
        "fields": [
            ("failure_type", "std::to_string( callback.m_eFailureType )"),
        ],
    },
    {
        "name": "LicensesUpdated",
        "type": "LicensesUpdated_t",
        "reserve": 32,
        "fields": [
            ("updated", 'std::string( "1" )'),
        ],
    },
    {
        "name": "ValidateAuthTicketResponse",
        "type": "ValidateAuthTicketResponse_t",
        "reserve": 160,
        "fields": [
            ("steam_id", "std::to_string( callback.m_SteamID.ConvertToUint64() )"),
            ("auth_session_response", "std::to_string( static_cast<int>( callback.m_eAuthSessionResponse ) )"),
            ("owner_steam_id", "std::to_string( callback.m_OwnerSteamID.ConvertToUint64() )"),
        ],
    },
    {
        "name": "MicroTxnAuthorizationResponse",
        "type": "MicroTxnAuthorizationResponse_t",
        "reserve": 128,
        "fields": [
            ("app_id", "std::to_string( callback.m_unAppID )"),
            ("order_id", "std::to_string( callback.m_ulOrderID )"),
            ("authorized", "std::to_string( callback.m_bAuthorized ? 1 : 0 )"),
        ],
    },
    {
        "name": "ClientGameServerDeny",
        "type": "ClientGameServerDeny_t",
        "reserve": 160,
        "fields": [
            ("app_id", "std::to_string( callback.m_uAppID )"),
            ("game_server_ip", "std::to_string( callback.m_unGameServerIP )"),
            ("game_server_port", "std::to_string( callback.m_usGameServerPort )"),
            ("secure", "std::to_string( callback.m_bSecure ? 1 : 0 )"),
            ("reason", "std::to_string( callback.m_uReason )"),
        ],
    },
    {
        "name": "EncryptedAppTicketResponse",
        "type": "EncryptedAppTicketResponse_t",
        "reserve": 64,
        "fields": [
            ("result", "std::to_string( static_cast<int>( callback.m_eResult ) )"),
        ],
    },
    {
        "name": "GetAuthSessionTicketResponse",
        "type": "GetAuthSessionTicketResponse_t",
        "reserve": 96,
        "fields": [
            ("auth_ticket", "std::to_string( callback.m_hAuthTicket )"),
            ("result", "std::to_string( static_cast<int>( callback.m_eResult ) )"),
        ],
    },
    {
        "name": "GameWebCallback",
        "type": "GameWebCallback_t",
        "reserve": 320,
        "fields": [
            ("url", "EscapeEventField( callback.m_szURL )"),
        ],
    },
    {
        "name": "DlcInstalled",
        "type": "DlcInstalled_t",
        "reserve": 64,
        "fields": [
            ("app_id", "std::to_string( callback.m_nAppID )"),
        ],
    },
    {
        "name": "NewUrlLaunchParameters",
        "type": "NewUrlLaunchParameters_t",
        "reserve": 32,
        "fields": [
            ("new_url_launch_parameters", 'std::string( "1" )'),
        ],
    },
    {
        "name": "FavoritesListChanged",
        "type": "FavoritesListChanged_t",
        "reserve": 192,
        "fields": [
            ("ip", "std::to_string( callback.m_nIP )"),
            ("query_port", "std::to_string( callback.m_nQueryPort )"),
            ("connection_port", "std::to_string( callback.m_nConnPort )"),
            ("app_id", "std::to_string( callback.m_nAppID )"),
            ("flags", "std::to_string( callback.m_nFlags )"),
            ("add", "std::to_string( callback.m_bAdd ? 1 : 0 )"),
            ("account_id", "std::to_string( callback.m_unAccountId )"),
        ],
    },
    {
        "name": "LobbyInvite",
        "type": "LobbyInvite_t",
        "reserve": 160,
        "fields": [
            ("user", "std::to_string( callback.m_ulSteamIDUser )"),
            ("lobby", "std::to_string( callback.m_ulSteamIDLobby )"),
            ("game_id", "std::to_string( callback.m_ulGameID )"),
        ],
    },
    {
        "name": "SteamNetConnectionStatusChanged",
        "type": "SteamNetConnectionStatusChangedCallback_t",
        "reserve": 1152,
        "fields": [
            ("connection", "std::to_string( static_cast<uint32>( callback.m_hConn ) )"),
            ("old_state", "std::to_string( static_cast<int>( callback.m_eOldState ) )"),
        ],
        "append": ["SerializeConnectionInfo( callback.m_info )"],
    },
    {
        "name": "LobbyEnter",
        "type": "LobbyEnter_t",
        "reserve": 160,
        "fields": [
            ("lobby", "std::to_string( callback.m_ulSteamIDLobby )"),
            ("chat_permissions", "std::to_string( callback.m_rgfChatPermissions )"),
            ("locked", "std::to_string( callback.m_bLocked ? 1 : 0 )"),
            ("response", "std::to_string( callback.m_EChatRoomEnterResponse )"),
        ],
    },
    {
        "name": "LobbyDataUpdate",
        "type": "LobbyDataUpdate_t",
        "reserve": 128,
        "fields": [
            ("lobby", "std::to_string( callback.m_ulSteamIDLobby )"),
            ("member", "std::to_string( callback.m_ulSteamIDMember )"),
            ("success", "std::to_string( callback.m_bSuccess ? 1 : 0 )"),
        ],
    },
    {
        "name": "LobbyChatUpdate",
        "type": "LobbyChatUpdate_t",
        "reserve": 192,
        "fields": [
            ("lobby", "std::to_string( callback.m_ulSteamIDLobby )"),
            ("user_changed", "std::to_string( callback.m_ulSteamIDUserChanged )"),
            ("making_change", "std::to_string( callback.m_ulSteamIDMakingChange )"),
            ("state_change", "std::to_string( callback.m_rgfChatMemberStateChange )"),
        ],
    },
    {
        "name": "LobbyChatMsg",
        "type": "LobbyChatMsg_t",
        "reserve": 160,
        "fields": [
            ("lobby", "std::to_string( callback.m_ulSteamIDLobby )"),
            ("user", "std::to_string( callback.m_ulSteamIDUser )"),
            ("type", "std::to_string( callback.m_eChatEntryType )"),
            ("chat_id", "std::to_string( callback.m_iChatID )"),
        ],
    },
    {
        "name": "LobbyGameCreated",
        "type": "LobbyGameCreated_t",
        "reserve": 160,
        "fields": [
            ("lobby", "std::to_string( callback.m_ulSteamIDLobby )"),
            ("game_server", "std::to_string( callback.m_ulSteamIDGameServer )"),
            ("ip", "std::to_string( callback.m_unIP )"),
            ("port", "std::to_string( callback.m_usPort )"),
        ],
    },
    {
        "name": "LobbyKicked",
        "type": "LobbyKicked_t",
        "reserve": 128,
        "fields": [
            ("lobby", "std::to_string( callback.m_ulSteamIDLobby )"),
            ("admin", "std::to_string( callback.m_ulSteamIDAdmin )"),
            ("kicked_due_to_disconnect", "std::to_string( callback.m_bKickedDueToDisconnect ? 1 : 0 )"),
        ],
    },
    {
        "name": "GameServerChangeRequested",
        "type": "GameServerChangeRequested_t",
        "reserve": 160,
        "fields": [
            ("server", "EscapeEventField( callback.m_rgchServer )"),
            ("password", "EscapeEventField( callback.m_rgchPassword )"),
        ],
    },
    {
        "name": "GameOverlayActivated",
        "type": "GameOverlayActivated_t",
        "reserve": 128,
        "fields": [
            ("active", "std::to_string( callback.m_bActive ? 1 : 0 )"),
            ("user_initiated", "std::to_string( callback.m_bUserInitiated ? 1 : 0 )"),
            ("app_id", "std::to_string( callback.m_nAppID )"),
            ("overlay_pid", "std::to_string( callback.m_dwOverlayPID )"),
        ],
    },
    {
        "name": "GameLobbyJoinRequested",
        "type": "GameLobbyJoinRequested_t",
        "reserve": 128,
        "fields": [
            ("lobby", "std::to_string( callback.m_steamIDLobby.ConvertToUint64() )"),
            ("friend", "std::to_string( callback.m_steamIDFriend.ConvertToUint64() )"),
        ],
    },
    {
        "name": "AvatarImageLoaded",
        "type": "AvatarImageLoaded_t",
        "reserve": 128,
        "fields": [
            ("steam_id", "std::to_string( callback.m_steamID.ConvertToUint64() )"),
            ("image", "std::to_string( callback.m_iImage )"),
            ("wide", "std::to_string( callback.m_iWide )"),
            ("tall", "std::to_string( callback.m_iTall )"),
        ],
    },
    {
        "name": "FriendRichPresenceUpdate",
        "type": "FriendRichPresenceUpdate_t",
        "reserve": 96,
        "fields": [
            ("friend", "std::to_string( callback.m_steamIDFriend.ConvertToUint64() )"),
            ("app_id", "std::to_string( callback.m_nAppID )"),
        ],
    },
    {
        "name": "GameRichPresenceJoinRequested",
        "type": "GameRichPresenceJoinRequested_t",
        "reserve": 384,
        "fields": [
            ("friend", "std::to_string( callback.m_steamIDFriend.ConvertToUint64() )"),
            ("connect", "EscapeEventField( callback.m_rgchConnect )"),
        ],
    },
    {
        "name": "PersonaStateChange",
        "type": "PersonaStateChange_t",
        "reserve": 96,
        "fields": [
            ("steam_id", "std::to_string( callback.m_ulSteamID )"),
            ("change_flags", "std::to_string( callback.m_nChangeFlags )"),
        ],
    },
    {
        "name": "P2PSessionRequest",
        "type": "P2PSessionRequest_t",
        "reserve": 64,
        "fields": [
            ("remote_steam_id", "std::to_string( callback.m_steamIDRemote.ConvertToUint64() )"),
        ],
    },
    {
        "name": "P2PSessionConnectFail",
        "type": "P2PSessionConnectFail_t",
        "reserve": 96,
        "fields": [
            ("remote_steam_id", "std::to_string( callback.m_steamIDRemote.ConvertToUint64() )"),
            ("error", "std::to_string( callback.m_eP2PSessionError )"),
        ],
    },
    {
        "name": "SocketStatusCallback",
        "type": "SocketStatusCallback_t",
        "reserve": 160,
        "fields": [
            ("socket", "std::to_string( callback.m_hSocket )"),
            ("listen_socket", "std::to_string( callback.m_hListenSocket )"),
            ("remote_steam_id", "std::to_string( callback.m_steamIDRemote.ConvertToUint64() )"),
            ("state", "std::to_string( callback.m_eSNetSocketState )"),
        ],
    },
    {
        "name": "SteamNetAuthenticationStatus",
        "type": "SteamNetAuthenticationStatus_t",
        "reserve": 320,
        "fields": [
            ("availability", "std::to_string( static_cast<int>( callback.m_eAvail ) )"),
            ("debug", "EscapeEventField( callback.m_debugMsg )"),
        ],
    },
    {
        "name": "SteamRelayNetworkStatus",
        "type": "SteamRelayNetworkStatus_t",
        "reserve": 448,
        "fields": [
            ("availability", "std::to_string( static_cast<int>( callback.m_eAvail ) )"),
            ("ping_measurement_in_progress", "std::to_string( callback.m_bPingMeasurementInProgress )"),
            ("network_config_availability", "std::to_string( static_cast<int>( callback.m_eAvailNetworkConfig ) )"),
            ("any_relay_availability", "std::to_string( static_cast<int>( callback.m_eAvailAnyRelay ) )"),
            ("debug", "EscapeEventField( callback.m_debugMsg )"),
        ],
    },
    {
        "name": "SteamNetworkingMessagesSessionRequest",
        "type": "SteamNetworkingMessagesSessionRequest_t",
        "reserve": 192,
        "append": ["SerializeNetworkingIdentity( callback.m_identityRemote )"],
    },
    {
        "name": "SteamNetworkingMessagesSessionFailed",
        "type": "SteamNetworkingMessagesSessionFailed_t",
        "reserve": 1024,
        "append": ["SerializeConnectionInfo( callback.m_info )"],
    },
    {
        "name": "SteamNetworkingFakeIPResult",
        "type": "SteamNetworkingFakeIPResult_t",
        "reserve": 512,
        "fields": [
            ("result", "std::to_string( static_cast<int>( callback.m_eResult ) )"),
        ],
        "append": [
            "SerializeNetworkingIdentity( callback.m_identity )",
            'std::string( "ip=" ) + std::to_string( callback.m_unIP )',
            'std::string( "port0=" ) + std::to_string( callback.m_unPorts[0] )',
            'std::string( "port1=" ) + std::to_string( callback.m_unPorts[1] )',
            'std::string( "port2=" ) + std::to_string( callback.m_unPorts[2] )',
            'std::string( "port3=" ) + std::to_string( callback.m_unPorts[3] )',
            'std::string( "port4=" ) + std::to_string( callback.m_unPorts[4] )',
            'std::string( "port5=" ) + std::to_string( callback.m_unPorts[5] )',
            'std::string( "port6=" ) + std::to_string( callback.m_unPorts[6] )',
            'std::string( "port7=" ) + std::to_string( callback.m_unPorts[7] )',
        ],
    },
]

MANUAL_DISPATCH_API_CALL_RESULTS = [
    {
        "name": "LobbyMatchList",
        "type": "LobbyMatchList_t",
        "reserve": 48,
        "fields": [
            ("lobbies_matching", "std::to_string( callback.m_nLobbiesMatching )"),
        ],
    },
    {
        "name": "LobbyEnter",
        "type": "LobbyEnter_t",
    },
    {
        "name": "LobbyCreated",
        "type": "LobbyCreated_t",
        "reserve": 96,
        "fields": [
            ("result", "std::to_string( static_cast<int>( callback.m_eResult ) )"),
            ("lobby", "std::to_string( callback.m_ulSteamIDLobby )"),
        ],
    },
]
