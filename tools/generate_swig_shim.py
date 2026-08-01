#!/usr/bin/env python3
"""Generate a small SWIG-facing Steamworks shim from steam_api.json.

This intentionally starts with the subset that maps cleanly to scripting
languages: interface methods with a known flat accessor and value-like
parameters. Pointer/out/ref APIs, callbacks, structs, and raw interface-returning
functions are skipped until they have explicit typemaps.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate_c_abi import write_c_abi_files
from steamworks_model import (
    c_api_methods,
    c_api_model,
    classify_skipped_methods,
    declared_identifiers,
    interface_accessor,
    iter_wrappable_methods,
)

TEMPLATE_DIR = Path(__file__).with_name("templates")

C_MANUAL_FUNCTIONS = [
    ("bool", "Steam_Init", []),
    ("int", "Steam_InitEx", []),
    ("int", "Steam_InitFlat", []),
    ("void", "Steam_Shutdown", []),
    ("void", "Steam_ClearHelperState", []),
    ("void", "Steam_RunCallbacks", []),
    ("int", "Steam_GetCallbackDispatchMode", []),
    ("int", "Steam_CallbackDispatchModeUninitialized", []),
    ("int", "Steam_CallbackDispatchModeAutomatic", []),
    ("int", "Steam_CallbackDispatchModeManual", []),
    ("bool", "Steam_IsSteamRunning", []),
    ("bool", "Steam_RestartAppIfNecessary", [("AppId_t", "appID")]),
    ("void", "Steam_ReleaseCurrentThreadMemory", []),
    ("const char *", "Steam_GetSteamInstallPath", []),
    ("void", "Steam_SetTryCatchCallbacks", [("bool", "enabled")]),
    ("void", "Steam_SetMiniDumpComment", [("const char *", "message")]),
    ("HSteamPipe", "Steam_GetHSteamPipe", []),
    ("HSteamUser", "Steam_GetHSteamUser", []),
    ("int", "Steam_GetLastInitResult", []),
    ("const char *", "Steam_GetLastInitError", []),
    (
        "bool",
        "Steam_GameServer_Init",
        [
            ("uint32", "ip"),
            ("uint16", "gamePort"),
            ("uint16", "queryPort"),
            ("int", "serverMode"),
            ("const char *", "versionString"),
        ],
    ),
    (
        "int",
        "Steam_GameServer_InitEx",
        [
            ("uint32", "ip"),
            ("uint16", "gamePort"),
            ("uint16", "queryPort"),
            ("int", "serverMode"),
            ("const char *", "versionString"),
        ],
    ),
    ("void", "Steam_GameServer_Shutdown", []),
    ("void", "Steam_GameServer_RunCallbacks", []),
    ("void", "Steam_GameServer_ReleaseCurrentThreadMemory", []),
    ("bool", "Steam_GameServer_GlobalBSecure", []),
    ("uint64", "Steam_GameServer_GlobalGetSteamID", []),
    ("HSteamPipe", "Steam_GameServer_GetHSteamPipe", []),
    ("HSteamUser", "Steam_GameServer_GetHSteamUser", []),
    ("int", "Steam_GameServer_GetLastInitResult", []),
    ("const char *", "Steam_GameServer_GetLastInitError", []),
    ("int", "Steam_ServerModeInvalid", []),
    ("int", "Steam_ServerModeNoAuthentication", []),
    ("int", "Steam_ServerModeAuthentication", []),
    ("int", "Steam_ServerModeAuthenticationAndSecure", []),
    ("uint16", "Steam_GameServer_QueryPortShared", []),
    ("SteamAPICall_t", "Steam_Lobby_RequestList", []),
    ("bool", "Steam_Lobby_IsListPending", []),
    ("bool", "Steam_Lobby_IsListComplete", []),
    ("bool", "Steam_Lobby_ListHadIOFailure", []),
    ("uint32", "Steam_Lobby_GetListResultCount", []),
    ("uint64_steamid", "Steam_Lobby_GetListLobbyByIndex", [("int", "index")]),
    ("std::string", "Steam_Lobby_GetListLobbyNameByIndex", [("int", "index")]),
    ("void", "Steam_Lobby_ClearAsyncState", []),
]

C_HELPER_FUNCTIONS = [
    ("SteamworksBytes", "Steam_User_GetLastAuthSessionTicketBytes", []),
    ("HAuthTicket", "Steam_User_GetAuthSessionTicketBytes", [("int", "maxTicketSize")]),
    ("int", "Steam_User_BeginAuthSessionBytes", [("const char *", "data"), ("size_t", "dataSize"), ("uint64_steamid", "steamID")]),
    ("SteamAPICall_t", "Steam_User_RequestEncryptedAppTicketBytes", [("const char *", "data"), ("size_t", "dataSize")]),
    ("SteamworksBytes", "Steam_User_GetEncryptedAppTicketBytes", [("int", "maxTicketSize")]),
    ("SteamworksBytes", "Steam_GameServer_GetLastAuthSessionTicketBytes", []),
    ("HAuthTicket", "Steam_GameServer_GetAuthSessionTicketBytes", [("int", "maxTicketSize")]),
    ("int", "Steam_GameServer_BeginAuthSessionBytes", [("const char *", "data"), ("size_t", "dataSize"), ("uint64_steamid", "steamID")]),
    ("HSteamListenSocket", "Steam_NetworkingSockets_CreateListenSocketIPStringNoOptions", [("const char *", "address")]),
    ("HSteamNetConnection", "Steam_NetworkingSockets_ConnectByIPAddressStringNoOptions", [("const char *", "address")]),
    ("HSteamListenSocket", "Steam_NetworkingSockets_CreateListenSocketP2PNoOptions", [("int", "localVirtualPort")]),
    ("HSteamNetConnection", "Steam_NetworkingSockets_ConnectP2PSteamIDNoOptions", [("uint64_steamid", "steamID"), ("int", "remoteVirtualPort")]),
    ("void", "Steam_NetworkingSockets_EnableConnectionStatusCallbacks", []),
    ("void", "Steam_NetworkingSockets_ClearConnectionStatusChangedEvents", []),
    ("std::vector<std::string>", "Steam_NetworkingSockets_PollConnectionStatusChangedStrings", [("int", "maxEvents")]),
    ("int", "Steam_NetworkingSockets_SendMessageToConnectionString", [("HSteamNetConnection", "connection"), ("const char *", "data"), ("int", "sendFlags")]),
    ("int", "Steam_NetworkingSockets_SendMessageToConnectionBytes", [("HSteamNetConnection", "connection"), ("const char *", "data"), ("size_t", "dataSize"), ("int", "sendFlags")]),
    ("std::vector<std::string>", "Steam_NetworkingSockets_ReceiveMessagesOnConnectionStrings", [("HSteamNetConnection", "connection"), ("int", "maxMessages")]),
    ("SteamworksBytesVector", "Steam_NetworkingSockets_ReceiveMessagesOnConnectionBytes", [("HSteamNetConnection", "connection"), ("int", "maxMessages")]),
    ("std::vector<std::string>", "Steam_NetworkingSockets_ReceiveMessagesOnPollGroupStrings", [("HSteamNetPollGroup", "pollGroup"), ("int", "maxMessages")]),
    ("SteamworksBytesVector", "Steam_NetworkingSockets_ReceiveMessagesOnPollGroupBytes", [("HSteamNetPollGroup", "pollGroup"), ("int", "maxMessages")]),
    ("std::string", "Steam_NetworkingSockets_GetConnectionNameString", [("HSteamNetConnection", "connection")]),
    ("std::string", "Steam_NetworkingSockets_GetConnectionInfoString", [("HSteamNetConnection", "connection")]),
    ("std::string", "Steam_NetworkingSockets_GetConnectionRealTimeStatusString", [("HSteamNetConnection", "connection")]),
    ("std::string", "Steam_NetworkingSockets_GetDetailedConnectionStatusString", [("HSteamNetConnection", "connection")]),
    ("std::string", "Steam_NetworkingSockets_GetListenSocketAddressString", [("HSteamListenSocket", "listenSocket")]),
    ("std::string", "Steam_NetworkingSockets_GetIdentityString", []),
    ("std::string", "Steam_NetworkingSockets_GetAuthenticationStatusString", []),
    ("std::string", "Steam_NetworkingSockets_GetFakeIPString", [("int", "firstPortIndex")]),
    ("HSteamListenSocket", "Steam_NetworkingSockets_CreateListenSocketP2PFakeIPNoOptions", [("int", "fakePortIndex")]),
    ("std::string", "Steam_NetworkingSockets_GetRemoteFakeIPForConnectionString", [("HSteamNetConnection", "connection")]),
    ("HSteamListenSocket", "Steam_GameServerNetworkingSockets_CreateListenSocketP2PNoOptions", [("int", "localVirtualPort")]),
    ("HSteamNetPollGroup", "Steam_GameServerNetworkingSockets_CreatePollGroup", []),
    ("bool", "Steam_GameServerNetworkingSockets_DestroyPollGroup", [("HSteamNetPollGroup", "pollGroup")]),
    ("int", "Steam_GameServerNetworkingSockets_AcceptConnection", [("HSteamNetConnection", "connection")]),
    ("bool", "Steam_GameServerNetworkingSockets_CloseConnection", [("HSteamNetConnection", "connection"), ("int", "reason"), ("const char *", "debugMessage"), ("bool", "enableLinger")]),
    ("bool", "Steam_GameServerNetworkingSockets_CloseListenSocket", [("HSteamListenSocket", "listenSocket")]),
    ("bool", "Steam_GameServerNetworkingSockets_SetConnectionPollGroup", [("HSteamNetConnection", "connection"), ("HSteamNetPollGroup", "pollGroup")]),
    ("int", "Steam_GameServerNetworkingSockets_SendMessageToConnectionString", [("HSteamNetConnection", "connection"), ("const char *", "data"), ("int", "sendFlags")]),
    ("int", "Steam_GameServerNetworkingSockets_SendMessageToConnectionBytes", [("HSteamNetConnection", "connection"), ("const char *", "data"), ("size_t", "dataSize"), ("int", "sendFlags")]),
    ("std::vector<std::string>", "Steam_GameServerNetworkingSockets_ReceiveMessagesOnConnectionStrings", [("HSteamNetConnection", "connection"), ("int", "maxMessages")]),
    ("SteamworksBytesVector", "Steam_GameServerNetworkingSockets_ReceiveMessagesOnConnectionBytes", [("HSteamNetConnection", "connection"), ("int", "maxMessages")]),
    ("std::vector<std::string>", "Steam_GameServerNetworkingSockets_ReceiveMessagesOnPollGroupStrings", [("HSteamNetPollGroup", "pollGroup"), ("int", "maxMessages")]),
    ("SteamworksBytesVector", "Steam_GameServerNetworkingSockets_ReceiveMessagesOnPollGroupBytes", [("HSteamNetPollGroup", "pollGroup"), ("int", "maxMessages")]),
    ("int", "Steam_NetworkingMessages_SendMessageToSteamIDBytes", [("uint64_steamid", "steamID"), ("const char *", "data"), ("size_t", "dataSize"), ("int", "sendFlags"), ("int", "remoteChannel")]),
    ("SteamworksBytesVector", "Steam_NetworkingMessages_ReceiveMessagesOnChannelBytes", [("int", "localChannel"), ("int", "maxMessages")]),
    ("bool", "Steam_NetworkingMessages_AcceptSessionWithSteamID", [("uint64_steamid", "steamID")]),
    ("bool", "Steam_NetworkingMessages_CloseSessionWithSteamID", [("uint64_steamid", "steamID")]),
    ("bool", "Steam_NetworkingMessages_CloseChannelWithSteamID", [("uint64_steamid", "steamID"), ("int", "localChannel")]),
    ("int", "Steam_GameServerNetworkingMessages_SendMessageToSteamIDBytes", [("uint64_steamid", "steamID"), ("const char *", "data"), ("size_t", "dataSize"), ("int", "sendFlags"), ("int", "remoteChannel")]),
    ("SteamworksBytesVector", "Steam_GameServerNetworkingMessages_ReceiveMessagesOnChannelBytes", [("int", "localChannel"), ("int", "maxMessages")]),
    ("bool", "Steam_GameServerNetworkingMessages_AcceptSessionWithSteamID", [("uint64_steamid", "steamID")]),
    ("bool", "Steam_GameServerNetworkingMessages_CloseSessionWithSteamID", [("uint64_steamid", "steamID")]),
    ("bool", "Steam_GameServerNetworkingMessages_CloseChannelWithSteamID", [("uint64_steamid", "steamID"), ("int", "localChannel")]),
    ("bool", "Steam_RemoteStorage_FileWriteBytes", [("const char *", "filename"), ("const char *", "data"), ("size_t", "dataSize")]),
    ("SteamworksBytes", "Steam_RemoteStorage_FileReadBytes", [("const char *", "filename"), ("int32", "dataSize")]),
    ("SteamAPICall_t", "Steam_RemoteStorage_FileWriteAsyncBytes", [("const char *", "filename"), ("const char *", "data"), ("size_t", "dataSize")]),
    ("SteamworksBytes", "Steam_RemoteStorage_FileReadAsyncCompleteBytes", [("SteamAPICall_t", "readCall"), ("uint32", "dataSize")]),
    ("bool", "Steam_RemoteStorage_FileWriteStreamWriteChunkBytes", [("UGCFileWriteStreamHandle_t", "writeHandle"), ("const char *", "data"), ("size_t", "dataSize")]),
    ("bool", "Steam_HTTP_SetHTTPRequestRawPostBodyBytes", [("HTTPRequestHandle", "request"), ("const char *", "contentType"), ("const char *", "data"), ("size_t", "dataSize")]),
    ("SteamworksBytes", "Steam_HTTP_GetHTTPResponseBodyDataBytes", [("HTTPRequestHandle", "request"), ("uint32", "dataSize")]),
    ("SteamworksBytes", "Steam_HTTP_GetHTTPStreamingResponseBodyDataBytes", [("HTTPRequestHandle", "request"), ("uint32", "offset"), ("uint32", "dataSize")]),
    ("bool", "Steam_GameServerHTTP_SetHTTPRequestRawPostBodyBytes", [("HTTPRequestHandle", "request"), ("const char *", "contentType"), ("const char *", "data"), ("size_t", "dataSize")]),
    ("SteamworksBytes", "Steam_GameServerHTTP_GetHTTPResponseBodyDataBytes", [("HTTPRequestHandle", "request"), ("uint32", "dataSize")]),
    ("SteamworksBytes", "Steam_GameServerHTTP_GetHTTPStreamingResponseBodyDataBytes", [("HTTPRequestHandle", "request"), ("uint32", "offset"), ("uint32", "dataSize")]),
    ("int", "Steam_NetworkingSend_Unreliable", []),
    ("int", "Steam_NetworkingSend_UnreliableNoDelay", []),
    ("int", "Steam_NetworkingSend_Reliable", []),
    ("int", "Steam_NetworkingSend_ReliableNoNagle", []),
    ("int", "Steam_NetworkingConnectionState_None", []),
    ("int", "Steam_NetworkingConnectionState_Connecting", []),
    ("int", "Steam_NetworkingConnectionState_FindingRoute", []),
    ("int", "Steam_NetworkingConnectionState_Connected", []),
    ("int", "Steam_NetworkingConnectionState_ClosedByPeer", []),
    ("int", "Steam_NetworkingConnectionState_ProblemDetectedLocally", []),
    ("int", "Steam_NetConnectionEnd_AppGeneric", []),
    ("int", "Steam_NetConnectionEnd_AppExceptionGeneric", []),
    ("std::vector<std::string>", "Steam_Lobby_GetDataEntries", [("uint64_steamid", "lobbyID")]),
    ("SteamAPICall_t", "Steam_Lobby_Create", [("int", "lobbyType"), ("int", "maxMembers")]),
    ("bool", "Steam_Lobby_IsCreatePending", []),
    ("bool", "Steam_Lobby_IsCreateComplete", []),
    ("bool", "Steam_Lobby_CreateHadIOFailure", []),
    ("uint64_steamid", "Steam_Lobby_GetCreatedLobbyID", []),
    ("int", "Steam_Lobby_GetCreateResult", []),
    ("bool", "Steam_Lobby_CreateSucceeded", []),
    ("SteamAPICall_t", "Steam_Lobby_Join", [("uint64_steamid", "lobbyID")]),
    ("bool", "Steam_Lobby_IsJoinPending", []),
    ("bool", "Steam_Lobby_IsJoinComplete", []),
    ("bool", "Steam_Lobby_JoinHadIOFailure", []),
    ("uint64_steamid", "Steam_Lobby_GetJoinedLobbyID", []),
    ("uint32", "Steam_Lobby_GetJoinResponse", []),
    ("bool", "Steam_Lobby_JoinSucceeded", []),
    ("int", "Steam_Lobby_ChatRoomEnterResponseSuccess", []),
    ("void", "Steam_Lobby_EnableChatCallbacks", []),
    ("void", "Steam_Lobby_ClearChatMessages", []),
    ("bool", "Steam_Lobby_SendChatMessage", [("uint64_steamid", "lobbyID"), ("const char *", "message")]),
    ("std::vector<std::string>", "Steam_Lobby_PollChatMessages", [("int", "maxMessages")]),
    ("HServerQuery", "Steam_MatchmakingServers_PingServer", [("uint32", "ip"), ("uint16", "port")]),
    ("bool", "Steam_MatchmakingServers_IsPingPending", []),
    ("bool", "Steam_MatchmakingServers_IsPingComplete", []),
    ("bool", "Steam_MatchmakingServers_PingFailed", []),
    ("bool", "Steam_MatchmakingServers_PingSucceeded", []),
    ("std::string", "Steam_MatchmakingServers_GetPingServer", []),
    ("void", "Steam_MatchmakingServers_ClearPingResult", []),
    ("HServerQuery", "Steam_MatchmakingServers_ServerFriends", [("uint32", "ip"), ("uint16", "port")]),
    ("bool", "Steam_MatchmakingServers_IsServerFriendsPending", []),
    ("bool", "Steam_MatchmakingServers_IsServerFriendsComplete", []),
    ("bool", "Steam_MatchmakingServers_ServerFriendsFailed", []),
    ("bool", "Steam_MatchmakingServers_ServerFriendsSucceeded", []),
    ("std::vector<std::string>", "Steam_MatchmakingServers_GetServerFriends", []),
    ("void", "Steam_MatchmakingServers_ClearServerFriendsResult", []),
    ("int", "Steam_FriendFlagImmediate", []),
    ("int", "Steam_FriendFlagOnGameServer", []),
    ("int", "Steam_FriendFlagAll", []),
    ("int", "Steam_LobbyTypePrivate", []),
    ("int", "Steam_LobbyTypeFriendsOnly", []),
    ("int", "Steam_LobbyTypePublic", []),
    ("int", "Steam_LobbyTypeInvisible", []),
    ("int", "Steam_LobbyTypePrivateUnique", []),
    ("int", "Steam_LobbyComparisonEqual", []),
    ("int", "Steam_PersonaStateOffline", []),
    ("int", "Steam_PersonaStateOnline", []),
    ("int", "Steam_PersonaStateBusy", []),
    ("int", "Steam_PersonaStateAway", []),
    ("int", "Steam_PersonaStateSnooze", []),
    ("int", "Steam_PersonaStateLookingToTrade", []),
    ("int", "Steam_PersonaStateLookingToPlay", []),
    ("int", "Steam_PersonaStateInvisible", []),
    ("int", "Steam_Friends_GetFriendCountImmediate", []),
    ("uint64_steamid", "Steam_Friends_GetFriendByIndexImmediate", [("int", "index")]),
    ("bool", "Steam_Friends_GetFriendGamePlayedInfo", [("uint64_steamid", "friendID")]),
    ("uint64_gameid", "Steam_Friends_GetFriendGameID", [("uint64_steamid", "friendID")]),
    ("AppId_t", "Steam_Friends_GetFriendGameAppID", [("uint64_steamid", "friendID")]),
    ("uint32", "Steam_Friends_GetFriendGameIP", [("uint64_steamid", "friendID")]),
    ("uint16", "Steam_Friends_GetFriendGamePort", [("uint64_steamid", "friendID")]),
    ("uint16", "Steam_Friends_GetFriendGameQueryPort", [("uint64_steamid", "friendID")]),
    ("uint64_steamid", "Steam_Friends_GetFriendGameLobbyID", [("uint64_steamid", "friendID")]),
    ("bool", "Steam_Friends_IsFriendInCurrentGame", [("uint64_steamid", "friendID")]),
]

MANUAL_DISPATCH_FUNCTIONS = [
    ("void", "Steam_ManualDispatch_Init", []),
    ("void", "Steam_ManualDispatch_RunFrame", [("HSteamPipe", "pipe")]),
    ("bool", "Steam_ManualDispatch_GetNextCallback", [("HSteamPipe", "pipe")]),
    ("HSteamUser", "Steam_ManualDispatch_GetCallbackSteamUser", []),
    ("int", "Steam_ManualDispatch_GetCallbackID", []),
    ("std::string", "Steam_ManualDispatch_GetCallbackData", []),
    ("int", "Steam_ManualDispatch_GetCallbackSize", []),
    ("bool", "Steam_ManualDispatch_CallbackIsAPICallCompleted", []),
    ("SteamAPICall_t", "Steam_ManualDispatch_GetCompletedAPICall", []),
    ("int", "Steam_ManualDispatch_GetCompletedCallbackID", []),
    ("uint32", "Steam_ManualDispatch_GetCompletedCallbackSize", []),
    (
        "bool",
        "Steam_ManualDispatch_GetAPICallResult",
        [
            ("HSteamPipe", "pipe"),
            ("SteamAPICall_t", "apiCall"),
            ("int", "callbackSize"),
            ("int", "callbackID"),
        ],
    ),
    ("std::string", "Steam_ManualDispatch_GetAPICallResultData", []),
    ("bool", "Steam_ManualDispatch_GetAPICallResultFailed", []),
    ("int", "Steam_ManualDispatch_CallbackIDSteamAPICallCompleted", []),
    ("void", "Steam_ManualDispatch_FreeLastCallback", [("HSteamPipe", "pipe")]),
]


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


def manual_dispatch_entries() -> list[dict]:
    entries = []
    seen_types = set()
    for item in MANUAL_DISPATCH_CALLBACKS + MANUAL_DISPATCH_API_CALL_RESULTS:
        if item["type"] in seen_types:
            continue
        entries.append(item)
        seen_types.add(item["type"])
    return entries


def manual_dispatch_c_functions() -> list[tuple]:
    items = list(MANUAL_DISPATCH_FUNCTIONS)
    items.extend(
        ("int", f'Steam_ManualDispatch_CallbackID{item["name"]}', [])
        for item in manual_dispatch_entries()
    )
    items.extend(
        ("std::string", f'Steam_ManualDispatch_DecodeCallback{item["name"]}', [])
        for item in MANUAL_DISPATCH_CALLBACKS
    )
    items.extend(
        ("std::string", f'Steam_ManualDispatch_DecodeAPICallResult{item["name"]}', [])
        for item in MANUAL_DISPATCH_API_CALL_RESULTS
    )
    return items


def manual_dispatch_declarations() -> str:
    lines = ["int Steam_ManualDispatch_CallbackIDSteamAPICallCompleted();"]
    for item in manual_dispatch_entries():
        lines.append(f'int Steam_ManualDispatch_CallbackID{item["name"]}();')
    for item in MANUAL_DISPATCH_CALLBACKS:
        lines.append(f'std::string Steam_ManualDispatch_DecodeCallback{item["name"]}();')
    for item in MANUAL_DISPATCH_API_CALL_RESULTS:
        lines.append(f'std::string Steam_ManualDispatch_DecodeAPICallResult{item["name"]}();')
    return "\n".join(lines)


def serializer_name(item: dict) -> str:
    return f'Serialize{item["name"]}'


def manual_dispatch_serializer_forward_declarations() -> str:
    return "\n".join(
        f'std::string {serializer_name(item)}( const {item["type"]} &callback );'
        for item in manual_dispatch_entries()
    )


def serialize_field_lines(item: dict) -> list[str]:
    fields = item.get("fields", [])
    append = item.get("append", [])
    lines: list[str] = []
    first = True
    for key, expr in fields:
        prefix = "" if first else "\\t"
        lines.append(f'\tresult += "{prefix}{key}=" + {expr};')
        first = False
    for expr in append:
        if first:
            lines.append(f"\tresult += {expr};")
        else:
            lines.append(f'\tresult += "\\t" + {expr};')
        first = False
    if first:
        lines.append('\treturn {};')
    else:
        lines.append("\treturn result;")
    return lines


def manual_dispatch_serializer(item: dict) -> str:
    reserve = item.get("reserve", 128)
    lines = [
        f'std::string {serializer_name(item)}( const {item["type"]} &callback )',
        "{",
        "\tstd::string result;",
        f"\tresult.reserve( {reserve} );",
    ]
    lines.extend(serialize_field_lines(item))
    lines.append("}")
    return "\n".join(lines)


def manual_dispatch_serializers() -> str:
    return "\n\n".join(manual_dispatch_serializer(item) for item in manual_dispatch_entries())


def manual_dispatch_callback_id_definition(item: dict) -> str:
    return "\n".join(
        [
            f'int Steam_ManualDispatch_CallbackID{item["name"]}()',
            "{",
            f'\treturn {item["type"]}::k_iCallback;',
            "}",
        ]
    )


def manual_dispatch_decode_callback_definition(item: dict) -> str:
    return "\n".join(
        [
            f'std::string Steam_ManualDispatch_DecodeCallback{item["name"]}()',
            "{",
            f'\tRequireCallbackDispatchMode( k_CallbackDispatchModeManual, "Steam_ManualDispatch_DecodeCallback{item["name"]}" );',
            f'\t{item["type"]} callback = {{}};',
            "\tif ( !CopyCurrentManualDispatchCallback( &callback ) )",
            "\t{",
            "\t\treturn {};",
            "\t}",
            f"\treturn {serializer_name(item)}( callback );",
            "}",
        ]
    )


def manual_dispatch_decode_api_call_result_definition(item: dict) -> str:
    return "\n".join(
        [
            f'std::string Steam_ManualDispatch_DecodeAPICallResult{item["name"]}()',
            "{",
            f'\tRequireCallbackDispatchMode( k_CallbackDispatchModeManual, "Steam_ManualDispatch_DecodeAPICallResult{item["name"]}" );',
            f'\tif ( g_manualDispatchAPICallResultCallbackID != {item["type"]}::k_iCallback )',
            "\t{",
            "\t\treturn {};",
            "\t}",
            "",
            f'\t{item["type"]} callback = {{}};',
            "\tif ( !CopyCallbackPayload( g_manualDispatchAPICallResultData, &callback ) )",
            "\t{",
            "\t\treturn {};",
            "\t}",
            f"\treturn {serializer_name(item)}( callback );",
            "}",
        ]
    )


def manual_dispatch_definitions() -> str:
    blocks = [
        "\n".join(
            [
                "int Steam_ManualDispatch_CallbackIDSteamAPICallCompleted()",
                "{",
                "\treturn SteamAPICallCompleted_t::k_iCallback;",
                "}",
            ]
        )
    ]
    blocks.extend(manual_dispatch_callback_id_definition(item) for item in manual_dispatch_entries())
    blocks.extend(manual_dispatch_decode_callback_definition(item) for item in MANUAL_DISPATCH_CALLBACKS)
    blocks.extend(
        manual_dispatch_decode_api_call_result_definition(item)
        for item in MANUAL_DISPATCH_API_CALL_RESULTS
    )
    return "\n\n".join(blocks)


def render_template(template_name: str, **values: str) -> str:
    rendered = (TEMPLATE_DIR / template_name).read_text(encoding="utf-8")
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{ {key} }}}}", value)
    return rendered


def generate(api: dict, output_dir: Path, steam_include: Path) -> None:
    flat_header = steam_include / "steam" / "steam_api_flat.h"
    flat_header_text = flat_header.read_text(encoding="utf-8", errors="replace")
    flat_identifiers = declared_identifiers(flat_header_text)
    methods = sorted(
        iter_wrappable_methods(api, flat_identifiers),
        key=lambda item: item["wrapper_name"],
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    header = output_dir / "steamworks_swig_shim.h"
    source = output_dir / "steamworks_swig_shim.cpp"
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
    skipped_methods = classify_skipped_methods(api, flat_identifiers, c_methods, interface_accessor)
    model = c_api_model(api, c_methods, skipped_methods)

    header.write_text(
        render_template(
            "steamworks_swig_shim.h.in",
            generated_declarations=generated_declarations,
            manual_dispatch_declarations=manual_dispatch_declarations(),
            matchmaking_server_friends_declarations=matchmaking_server_friends_declarations(
                steam_include
            ),
        )
        + "\n",
        encoding="utf-8",
    )

    source.write_text(
        render_template(
            "steamworks_swig_shim.cpp.in",
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
        encoding="utf-8",
    )

    interface.write_text(
        render_template("steamworks.i.in")
        + "\n",
        encoding="utf-8",
    )

    c_model.write_text(
        json.dumps(model, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
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
    api = json.loads(api_json.read_text(encoding="utf-8"))
    generate(api, Path(args.output_dir), steam_include)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
