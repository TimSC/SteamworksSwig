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


SUPPORTED_POINTER_TYPES = {"const char *"}
FLAT_TYPEDEFS = {
    "uint64_steamid": "unsigned long long",
    "uint64_gameid": "unsigned long long",
}
GLOBAL_DECLARATIONS = [
    "bool Steam_Init();",
    "int Steam_InitEx();",
    "int Steam_InitFlat();",
    "void Steam_Shutdown();",
    "void Steam_RunCallbacks();",
    "bool Steam_IsSteamRunning();",
    "bool Steam_RestartAppIfNecessary( AppId_t appID );",
    "void Steam_ReleaseCurrentThreadMemory();",
    "void Steam_WriteMiniDump( uint32 structuredExceptionCode, uint32 buildID );",
    "const char * Steam_GetSteamInstallPath();",
    "void Steam_SetTryCatchCallbacks( bool enabled );",
    "void Steam_SetMiniDumpComment( const char * message );",
    "void Steam_ManualDispatch_Init();",
    "void Steam_ManualDispatch_RunFrame( HSteamPipe pipe );",
    "void Steam_ManualDispatch_FreeLastCallback( HSteamPipe pipe );",
    "HSteamPipe Steam_GetHSteamPipe();",
    "HSteamUser Steam_GetHSteamUser();",
    "int Steam_GetLastInitResult();",
    "const char * Steam_GetLastInitError();",
    "bool Steam_GameServer_Init( uint32 ip, uint16 gamePort, uint16 queryPort, int serverMode, const char * versionString );",
    "int Steam_GameServer_InitEx( uint32 ip, uint16 gamePort, uint16 queryPort, int serverMode, const char * versionString );",
    "void Steam_GameServer_Shutdown();",
    "void Steam_GameServer_RunCallbacks();",
    "void Steam_GameServer_ReleaseCurrentThreadMemory();",
    "bool Steam_GameServer_GlobalBSecure();",
    "uint64 Steam_GameServer_GlobalGetSteamID();",
    "HSteamPipe Steam_GameServer_GetHSteamPipe();",
    "HSteamUser Steam_GameServer_GetHSteamUser();",
    "int Steam_GameServer_GetLastInitResult();",
    "const char * Steam_GameServer_GetLastInitError();",
    "int Steam_ServerModeInvalid();",
    "int Steam_ServerModeNoAuthentication();",
    "int Steam_ServerModeAuthentication();",
    "int Steam_ServerModeAuthenticationAndSecure();",
    "uint16 Steam_GameServer_QueryPortShared();",
    "HSteamListenSocket Steam_NetworkingSockets_CreateListenSocketP2PNoOptions( int localVirtualPort );",
    "HSteamNetConnection Steam_NetworkingSockets_ConnectP2PSteamIDNoOptions( uint64_steamid steamID, int remoteVirtualPort );",
    "void Steam_NetworkingSockets_EnableConnectionStatusCallbacks();",
    "void Steam_NetworkingSockets_ClearConnectionStatusChangedEvents();",
    "std::vector<std::string> Steam_NetworkingSockets_PollConnectionStatusChangedStrings( int maxEvents );",
    "int Steam_NetworkingSockets_SendMessageToConnectionString( HSteamNetConnection connection, const std::string & data, int sendFlags );",
    "std::vector<std::string> Steam_NetworkingSockets_ReceiveMessagesOnConnectionStrings( HSteamNetConnection connection, int maxMessages );",
    "std::vector<std::string> Steam_NetworkingSockets_ReceiveMessagesOnPollGroupStrings( HSteamNetPollGroup pollGroup, int maxMessages );",
    "std::string Steam_NetworkingSockets_GetConnectionNameString( HSteamNetConnection connection );",
    "std::string Steam_NetworkingSockets_GetDetailedConnectionStatusString( HSteamNetConnection connection );",
    "HSteamListenSocket Steam_GameServerNetworkingSockets_CreateListenSocketP2PNoOptions( int localVirtualPort );",
    "HSteamNetPollGroup Steam_GameServerNetworkingSockets_CreatePollGroup();",
    "bool Steam_GameServerNetworkingSockets_DestroyPollGroup( HSteamNetPollGroup pollGroup );",
    "int Steam_GameServerNetworkingSockets_AcceptConnection( HSteamNetConnection connection );",
    "bool Steam_GameServerNetworkingSockets_CloseConnection( HSteamNetConnection connection, int reason, const char * debugMessage, bool enableLinger );",
    "bool Steam_GameServerNetworkingSockets_CloseListenSocket( HSteamListenSocket listenSocket );",
    "bool Steam_GameServerNetworkingSockets_SetConnectionPollGroup( HSteamNetConnection connection, HSteamNetPollGroup pollGroup );",
    "int Steam_GameServerNetworkingSockets_SendMessageToConnectionString( HSteamNetConnection connection, const std::string & data, int sendFlags );",
    "std::vector<std::string> Steam_GameServerNetworkingSockets_ReceiveMessagesOnConnectionStrings( HSteamNetConnection connection, int maxMessages );",
    "std::vector<std::string> Steam_GameServerNetworkingSockets_ReceiveMessagesOnPollGroupStrings( HSteamNetPollGroup pollGroup, int maxMessages );",
    "int Steam_NetworkingSend_Unreliable();",
    "int Steam_NetworkingSend_UnreliableNoDelay();",
    "int Steam_NetworkingSend_Reliable();",
    "int Steam_NetworkingSend_ReliableNoNagle();",
    "int Steam_NetworkingConnectionState_None();",
    "int Steam_NetworkingConnectionState_Connecting();",
    "int Steam_NetworkingConnectionState_FindingRoute();",
    "int Steam_NetworkingConnectionState_Connected();",
    "int Steam_NetworkingConnectionState_ClosedByPeer();",
    "int Steam_NetworkingConnectionState_ProblemDetectedLocally();",
    "int Steam_NetConnectionEnd_AppGeneric();",
    "int Steam_NetConnectionEnd_AppExceptionGeneric();",
    "SteamAPICall_t Steam_Lobby_RequestList();",
    "bool Steam_Lobby_IsListPending();",
    "bool Steam_Lobby_IsListComplete();",
    "bool Steam_Lobby_ListHadIOFailure();",
    "uint32 Steam_Lobby_GetListResultCount();",
    "uint64_steamid Steam_Lobby_GetListLobbyByIndex( int index );",
    "std::string Steam_Lobby_GetListLobbyNameByIndex( int index );",
    "std::vector<std::string> Steam_Lobby_GetDataEntries( uint64_steamid lobbyID );",
    "SteamAPICall_t Steam_Lobby_Create( int lobbyType, int maxMembers );",
    "bool Steam_Lobby_IsCreatePending();",
    "bool Steam_Lobby_IsCreateComplete();",
    "bool Steam_Lobby_CreateHadIOFailure();",
    "uint64_steamid Steam_Lobby_GetCreatedLobbyID();",
    "int Steam_Lobby_GetCreateResult();",
    "bool Steam_Lobby_CreateSucceeded();",
    "SteamAPICall_t Steam_Lobby_Join( uint64_steamid lobbyID );",
    "bool Steam_Lobby_IsJoinPending();",
    "bool Steam_Lobby_IsJoinComplete();",
    "bool Steam_Lobby_JoinHadIOFailure();",
    "uint64_steamid Steam_Lobby_GetJoinedLobbyID();",
    "uint32 Steam_Lobby_GetJoinResponse();",
    "bool Steam_Lobby_JoinSucceeded();",
    "int Steam_Lobby_ChatRoomEnterResponseSuccess();",
    "int Steam_FriendFlagImmediate();",
    "int Steam_FriendFlagOnGameServer();",
    "int Steam_FriendFlagAll();",
    "int Steam_Friends_GetFriendCountImmediate();",
    "uint64_steamid Steam_Friends_GetFriendByIndexImmediate( int index );",
    "bool Steam_Friends_GetFriendGamePlayedInfo( uint64_steamid friendID );",
    "uint64_gameid Steam_Friends_GetFriendGameID( uint64_steamid friendID );",
    "AppId_t Steam_Friends_GetFriendGameAppID( uint64_steamid friendID );",
    "uint32 Steam_Friends_GetFriendGameIP( uint64_steamid friendID );",
    "uint16 Steam_Friends_GetFriendGamePort( uint64_steamid friendID );",
    "uint16 Steam_Friends_GetFriendGameQueryPort( uint64_steamid friendID );",
    "uint64_steamid Steam_Friends_GetFriendGameLobbyID( uint64_steamid friendID );",
    "bool Steam_Friends_IsFriendInCurrentGame( uint64_steamid friendID );",
]
GLOBAL_DEFINITIONS = r'''namespace
{
SteamErrMsg g_lastInitError = { 0 };
int g_lastInitResult = 0;
SteamErrMsg g_lastGameServerInitError = { 0 };
int g_lastGameServerInitResult = 0;

class LobbyAsyncState
{
public:
	SteamAPICall_t RequestList()
	{
		m_listPending = false;
		m_listComplete = false;
		m_listIOFailure = false;
		m_lobbyCount = 0;

		ISteamMatchmaking *matchmaking = SteamMatchmaking();
		if ( !matchmaking )
		{
			m_listComplete = true;
			m_listIOFailure = true;
			return k_uAPICallInvalid;
		}

		SteamAPICall_t call = matchmaking->RequestLobbyList();
		if ( call == k_uAPICallInvalid )
		{
			m_listComplete = true;
			m_listIOFailure = true;
			return call;
		}

		m_listPending = true;
		m_listCallResult.Set( call, this, &LobbyAsyncState::OnLobbyMatchList );
		return call;
	}

	SteamAPICall_t Join( uint64_steamid lobbyID )
	{
		m_joinPending = false;
		m_joinComplete = false;
		m_joinIOFailure = false;
		m_joinedLobbyID = 0;
		m_joinResponse = 0;

		ISteamMatchmaking *matchmaking = SteamMatchmaking();
		if ( !matchmaking )
		{
			m_joinComplete = true;
			m_joinIOFailure = true;
			return k_uAPICallInvalid;
		}

		SteamAPICall_t call = matchmaking->JoinLobby( CSteamID( lobbyID ) );
		if ( call == k_uAPICallInvalid )
		{
			m_joinComplete = true;
			m_joinIOFailure = true;
			return call;
		}

		m_joinPending = true;
		m_joinCallResult.Set( call, this, &LobbyAsyncState::OnLobbyEnter );
		return call;
	}

	SteamAPICall_t Create( int lobbyType, int maxMembers )
	{
		m_createPending = false;
		m_createComplete = false;
		m_createIOFailure = false;
		m_createdLobbyID = 0;
		m_createResult = k_EResultNone;

		ISteamMatchmaking *matchmaking = SteamMatchmaking();
		if ( !matchmaking )
		{
			m_createComplete = true;
			m_createIOFailure = true;
			return k_uAPICallInvalid;
		}

		SteamAPICall_t call = matchmaking->CreateLobby( static_cast<ELobbyType>( lobbyType ), maxMembers );
		if ( call == k_uAPICallInvalid )
		{
			m_createComplete = true;
			m_createIOFailure = true;
			return call;
		}

		m_createPending = true;
		m_createCallResult.Set( call, this, &LobbyAsyncState::OnLobbyCreated );
		return call;
	}

	bool IsListPending() const { return m_listPending; }
	bool IsListComplete() const { return m_listComplete; }
	bool ListHadIOFailure() const { return m_listIOFailure; }
	uint32 GetLobbyCount() const { return m_lobbyCount; }
	bool IsCreatePending() const { return m_createPending; }
	bool IsCreateComplete() const { return m_createComplete; }
	bool CreateHadIOFailure() const { return m_createIOFailure; }
	uint64_steamid GetCreatedLobbyID() const { return m_createdLobbyID; }
	int GetCreateResult() const { return static_cast<int>( m_createResult ); }
	bool IsJoinPending() const { return m_joinPending; }
	bool IsJoinComplete() const { return m_joinComplete; }
	bool JoinHadIOFailure() const { return m_joinIOFailure; }
	uint64_steamid GetJoinedLobbyID() const { return m_joinedLobbyID; }
	uint32 GetJoinResponse() const { return m_joinResponse; }

private:
	void OnLobbyMatchList( LobbyMatchList_t *result, bool ioFailure )
	{
		m_listPending = false;
		m_listComplete = true;
		m_listIOFailure = ioFailure;
		m_lobbyCount = result ? result->m_nLobbiesMatching : 0;
	}

	void OnLobbyEnter( LobbyEnter_t *result, bool ioFailure )
	{
		m_joinPending = false;
		m_joinComplete = true;
		m_joinIOFailure = ioFailure;
		m_joinedLobbyID = result ? result->m_ulSteamIDLobby : 0;
		m_joinResponse = result ? result->m_EChatRoomEnterResponse : 0;
	}

	void OnLobbyCreated( LobbyCreated_t *result, bool ioFailure )
	{
		m_createPending = false;
		m_createComplete = true;
		m_createIOFailure = ioFailure;
		m_createResult = result ? result->m_eResult : k_EResultFail;
		m_createdLobbyID = result ? result->m_ulSteamIDLobby : 0;
	}

	CCallResult<LobbyAsyncState, LobbyMatchList_t> m_listCallResult;
	CCallResult<LobbyAsyncState, LobbyEnter_t> m_joinCallResult;
	CCallResult<LobbyAsyncState, LobbyCreated_t> m_createCallResult;
	bool m_listPending = false;
	bool m_listComplete = false;
	bool m_listIOFailure = false;
	uint32 m_lobbyCount = 0;
	bool m_createPending = false;
	bool m_createComplete = false;
	bool m_createIOFailure = false;
	uint64_steamid m_createdLobbyID = 0;
	EResult m_createResult = k_EResultNone;
	bool m_joinPending = false;
	bool m_joinComplete = false;
	bool m_joinIOFailure = false;
	uint64_steamid m_joinedLobbyID = 0;
	uint32 m_joinResponse = 0;
};

LobbyAsyncState g_lobbyAsyncState;

class NetworkingStatusChangedQueue
{
public:
	void Register()
	{
		m_callback.Register( this, &NetworkingStatusChangedQueue::OnStatusChanged );
	}

	void Clear()
	{
		m_events.clear();
	}

	std::vector<std::string> PopEvents( int maxEvents )
	{
		std::vector<std::string> result;
		if ( maxEvents <= 0 )
		{
			return result;
		}

		const size_t count = std::min( static_cast<size_t>( maxEvents ), m_events.size() );
		result.reserve( count );
		for ( size_t index = 0; index < count; ++index )
		{
			result.push_back( m_events[index] );
		}
		m_events.erase( m_events.begin(), m_events.begin() + static_cast<std::vector<std::string>::difference_type>( count ) );
		return result;
	}

private:
	void OnStatusChanged( SteamNetConnectionStatusChangedCallback_t *callback )
	{
		if ( !callback )
		{
			return;
		}

		const SteamNetConnectionInfo_t &info = callback->m_info;
		std::string event;
		event.reserve( 512 );
		event += "connection=" + std::to_string( static_cast<uint32>( callback->m_hConn ) );
		event += "\tlisten_socket=" + std::to_string( static_cast<uint32>( info.m_hListenSocket ) );
		event += "\tremote_steam_id=" + std::to_string( info.m_identityRemote.GetSteamID64() );
		event += "\told_state=" + std::to_string( static_cast<int>( callback->m_eOldState ) );
		event += "\tstate=" + std::to_string( static_cast<int>( info.m_eState ) );
		event += "\tend_reason=" + std::to_string( info.m_eEndReason );
		event += "\tflags=" + std::to_string( info.m_nFlags );
		event += "\tdescription=" + std::string( info.m_szConnectionDescription );
		event += "\tend_debug=" + std::string( info.m_szEndDebug );
		m_events.push_back( event );
	}

	CCallbackManual<NetworkingStatusChangedQueue, SteamNetConnectionStatusChangedCallback_t> m_callback;
	std::vector<std::string> m_events;
};

NetworkingStatusChangedQueue g_networkingStatusChangedQueue;

std::vector<std::string> ReceiveMessagesOnConnectionStrings( ISteamNetworkingSockets *sockets, HSteamNetConnection connection, int maxMessages )
{
	std::vector<std::string> result;
	if ( !sockets || maxMessages <= 0 )
	{
		return result;
	}

	std::vector<SteamNetworkingMessage_t *> messages( static_cast<size_t>( maxMessages ), nullptr );
	const int count = sockets->ReceiveMessagesOnConnection( connection, messages.data(), maxMessages );
	if ( count <= 0 )
	{
		return result;
	}

	result.reserve( static_cast<size_t>( count ) );
	for ( int index = 0; index < count; ++index )
	{
		SteamNetworkingMessage_t *message = messages[static_cast<size_t>( index )];
		if ( message )
		{
			result.emplace_back( static_cast<const char *>( message->m_pData ), static_cast<size_t>( message->m_cbSize ) );
			message->Release();
		}
	}
	return result;
}

std::vector<std::string> ReceiveMessagesOnPollGroupStrings( ISteamNetworkingSockets *sockets, HSteamNetPollGroup pollGroup, int maxMessages )
{
	std::vector<std::string> result;
	if ( !sockets || maxMessages <= 0 )
	{
		return result;
	}

	std::vector<SteamNetworkingMessage_t *> messages( static_cast<size_t>( maxMessages ), nullptr );
	const int count = sockets->ReceiveMessagesOnPollGroup( pollGroup, messages.data(), maxMessages );
	if ( count <= 0 )
	{
		return result;
	}

	result.reserve( static_cast<size_t>( count ) );
	for ( int index = 0; index < count; ++index )
	{
		SteamNetworkingMessage_t *message = messages[static_cast<size_t>( index )];
		if ( message )
		{
			result.emplace_back( static_cast<const char *>( message->m_pData ), static_cast<size_t>( message->m_cbSize ) );
			message->Release();
		}
	}
	return result;
}

bool GetFriendGameInfo( uint64_steamid friendID, FriendGameInfo_t *info )
{
	ISteamFriends *friends = SteamFriends();
	if ( !friends || !info )
	{
		return false;
	}
	return friends->GetFriendGamePlayed( CSteamID( friendID ), info );
}
}

bool Steam_Init()
{
	return SteamAPI_Init();
}

int Steam_InitEx()
{
	g_lastInitError[0] = '\0';
	g_lastInitResult = static_cast<int>( SteamAPI_InitEx( &g_lastInitError ) );
	return g_lastInitResult;
}

int Steam_InitFlat()
{
	g_lastInitError[0] = '\0';
	g_lastInitResult = static_cast<int>( SteamAPI_InitFlat( &g_lastInitError ) );
	return g_lastInitResult;
}

void Steam_Shutdown()
{
	SteamAPI_Shutdown();
}

void Steam_RunCallbacks()
{
	SteamAPI_RunCallbacks();
}

bool Steam_IsSteamRunning()
{
	return SteamAPI_IsSteamRunning();
}

bool Steam_RestartAppIfNecessary( AppId_t appID )
{
	return SteamAPI_RestartAppIfNecessary( appID );
}

void Steam_ReleaseCurrentThreadMemory()
{
	SteamAPI_ReleaseCurrentThreadMemory();
}

void Steam_WriteMiniDump( uint32 structuredExceptionCode, uint32 buildID )
{
	SteamAPI_WriteMiniDump( structuredExceptionCode, nullptr, buildID );
}

const char * Steam_GetSteamInstallPath()
{
	return SteamAPI_GetSteamInstallPath();
}

void Steam_SetTryCatchCallbacks( bool enabled )
{
	SteamAPI_SetTryCatchCallbacks( enabled );
}

void Steam_SetMiniDumpComment( const char * message )
{
	SteamAPI_SetMiniDumpComment( message );
}

void Steam_ManualDispatch_Init()
{
	SteamAPI_ManualDispatch_Init();
}

void Steam_ManualDispatch_RunFrame( HSteamPipe pipe )
{
	SteamAPI_ManualDispatch_RunFrame( pipe );
}

void Steam_ManualDispatch_FreeLastCallback( HSteamPipe pipe )
{
	SteamAPI_ManualDispatch_FreeLastCallback( pipe );
}

HSteamPipe Steam_GetHSteamPipe()
{
	return SteamAPI_GetHSteamPipe();
}

HSteamUser Steam_GetHSteamUser()
{
	return SteamAPI_GetHSteamUser();
}

int Steam_GetLastInitResult()
{
	return g_lastInitResult;
}

const char * Steam_GetLastInitError()
{
	return g_lastInitError;
}

bool Steam_GameServer_Init( uint32 ip, uint16 gamePort, uint16 queryPort, int serverMode, const char * versionString )
{
	return SteamGameServer_Init( ip, gamePort, queryPort, static_cast<EServerMode>( serverMode ), versionString );
}

int Steam_GameServer_InitEx( uint32 ip, uint16 gamePort, uint16 queryPort, int serverMode, const char * versionString )
{
	g_lastGameServerInitError[0] = '\0';
	g_lastGameServerInitResult = static_cast<int>(
		SteamGameServer_InitEx( ip, gamePort, queryPort, static_cast<EServerMode>( serverMode ), versionString, &g_lastGameServerInitError )
	);
	return g_lastGameServerInitResult;
}

void Steam_GameServer_Shutdown()
{
	SteamGameServer_Shutdown();
}

void Steam_GameServer_RunCallbacks()
{
	SteamGameServer_RunCallbacks();
}

void Steam_GameServer_ReleaseCurrentThreadMemory()
{
	SteamGameServer_ReleaseCurrentThreadMemory();
}

bool Steam_GameServer_GlobalBSecure()
{
	return SteamGameServer_BSecure();
}

uint64 Steam_GameServer_GlobalGetSteamID()
{
	return SteamGameServer_GetSteamID();
}

HSteamPipe Steam_GameServer_GetHSteamPipe()
{
	return SteamGameServer_GetHSteamPipe();
}

HSteamUser Steam_GameServer_GetHSteamUser()
{
	return SteamGameServer_GetHSteamUser();
}

int Steam_GameServer_GetLastInitResult()
{
	return g_lastGameServerInitResult;
}

const char * Steam_GameServer_GetLastInitError()
{
	return g_lastGameServerInitError;
}

int Steam_ServerModeInvalid()
{
	return static_cast<int>( eServerModeInvalid );
}

int Steam_ServerModeNoAuthentication()
{
	return static_cast<int>( eServerModeNoAuthentication );
}

int Steam_ServerModeAuthentication()
{
	return static_cast<int>( eServerModeAuthentication );
}

int Steam_ServerModeAuthenticationAndSecure()
{
	return static_cast<int>( eServerModeAuthenticationAndSecure );
}

uint16 Steam_GameServer_QueryPortShared()
{
	return STEAMGAMESERVER_QUERY_PORT_SHARED;
}

HSteamListenSocket Steam_NetworkingSockets_CreateListenSocketP2PNoOptions( int localVirtualPort )
{
	g_networkingStatusChangedQueue.Register();
	auto *sockets = SteamAPI_SteamNetworkingSockets_SteamAPI();
	return sockets ? sockets->CreateListenSocketP2P( localVirtualPort, 0, nullptr ) : HSteamListenSocket{};
}

HSteamNetConnection Steam_NetworkingSockets_ConnectP2PSteamIDNoOptions( uint64_steamid steamID, int remoteVirtualPort )
{
	g_networkingStatusChangedQueue.Register();
	auto *sockets = SteamAPI_SteamNetworkingSockets_SteamAPI();
	if ( !sockets )
	{
		return HSteamNetConnection{};
	}

	SteamNetworkingIdentity identity;
	identity.SetSteamID64( steamID );
	return sockets->ConnectP2P( identity, remoteVirtualPort, 0, nullptr );
}

void Steam_NetworkingSockets_EnableConnectionStatusCallbacks()
{
	g_networkingStatusChangedQueue.Register();
}

void Steam_NetworkingSockets_ClearConnectionStatusChangedEvents()
{
	g_networkingStatusChangedQueue.Clear();
}

std::vector<std::string> Steam_NetworkingSockets_PollConnectionStatusChangedStrings( int maxEvents )
{
	return g_networkingStatusChangedQueue.PopEvents( maxEvents );
}

int Steam_NetworkingSockets_SendMessageToConnectionString( HSteamNetConnection connection, const std::string & data, int sendFlags )
{
	auto *sockets = SteamAPI_SteamNetworkingSockets_SteamAPI();
	if ( !sockets )
	{
		return k_EResultInvalidState;
	}
	return static_cast<int>( sockets->SendMessageToConnection( connection, data.data(), static_cast<uint32>( data.size() ), sendFlags, nullptr ) );
}

std::vector<std::string> Steam_NetworkingSockets_ReceiveMessagesOnConnectionStrings( HSteamNetConnection connection, int maxMessages )
{
	return ReceiveMessagesOnConnectionStrings( SteamAPI_SteamNetworkingSockets_SteamAPI(), connection, maxMessages );
}

std::vector<std::string> Steam_NetworkingSockets_ReceiveMessagesOnPollGroupStrings( HSteamNetPollGroup pollGroup, int maxMessages )
{
	return ReceiveMessagesOnPollGroupStrings( SteamAPI_SteamNetworkingSockets_SteamAPI(), pollGroup, maxMessages );
}

std::string Steam_NetworkingSockets_GetConnectionNameString( HSteamNetConnection connection )
{
	auto *sockets = SteamAPI_SteamNetworkingSockets_SteamAPI();
	if ( !sockets )
	{
		return {};
	}

	char buffer[256] = { 0 };
	return sockets->GetConnectionName( connection, buffer, sizeof( buffer ) ) ? std::string( buffer ) : std::string();
}

std::string Steam_NetworkingSockets_GetDetailedConnectionStatusString( HSteamNetConnection connection )
{
	auto *sockets = SteamAPI_SteamNetworkingSockets_SteamAPI();
	if ( !sockets )
	{
		return {};
	}

	char buffer[4096] = { 0 };
	const int result = sockets->GetDetailedConnectionStatus( connection, buffer, sizeof( buffer ) );
	return result >= 0 ? std::string( buffer ) : std::string();
}

HSteamListenSocket Steam_GameServerNetworkingSockets_CreateListenSocketP2PNoOptions( int localVirtualPort )
{
	auto *sockets = SteamAPI_SteamGameServerNetworkingSockets_SteamAPI();
	return sockets ? sockets->CreateListenSocketP2P( localVirtualPort, 0, nullptr ) : HSteamListenSocket{};
}

HSteamNetPollGroup Steam_GameServerNetworkingSockets_CreatePollGroup()
{
	auto *sockets = SteamAPI_SteamGameServerNetworkingSockets_SteamAPI();
	return sockets ? sockets->CreatePollGroup() : HSteamNetPollGroup{};
}

bool Steam_GameServerNetworkingSockets_DestroyPollGroup( HSteamNetPollGroup pollGroup )
{
	auto *sockets = SteamAPI_SteamGameServerNetworkingSockets_SteamAPI();
	return sockets ? sockets->DestroyPollGroup( pollGroup ) : false;
}

int Steam_GameServerNetworkingSockets_AcceptConnection( HSteamNetConnection connection )
{
	auto *sockets = SteamAPI_SteamGameServerNetworkingSockets_SteamAPI();
	return sockets ? static_cast<int>( sockets->AcceptConnection( connection ) ) : k_EResultInvalidState;
}

bool Steam_GameServerNetworkingSockets_CloseConnection( HSteamNetConnection connection, int reason, const char * debugMessage, bool enableLinger )
{
	auto *sockets = SteamAPI_SteamGameServerNetworkingSockets_SteamAPI();
	return sockets ? sockets->CloseConnection( connection, reason, debugMessage, enableLinger ) : false;
}

bool Steam_GameServerNetworkingSockets_CloseListenSocket( HSteamListenSocket listenSocket )
{
	auto *sockets = SteamAPI_SteamGameServerNetworkingSockets_SteamAPI();
	return sockets ? sockets->CloseListenSocket( listenSocket ) : false;
}

bool Steam_GameServerNetworkingSockets_SetConnectionPollGroup( HSteamNetConnection connection, HSteamNetPollGroup pollGroup )
{
	auto *sockets = SteamAPI_SteamGameServerNetworkingSockets_SteamAPI();
	return sockets ? sockets->SetConnectionPollGroup( connection, pollGroup ) : false;
}

int Steam_GameServerNetworkingSockets_SendMessageToConnectionString( HSteamNetConnection connection, const std::string & data, int sendFlags )
{
	auto *sockets = SteamAPI_SteamGameServerNetworkingSockets_SteamAPI();
	if ( !sockets )
	{
		return k_EResultInvalidState;
	}
	return static_cast<int>( sockets->SendMessageToConnection( connection, data.data(), static_cast<uint32>( data.size() ), sendFlags, nullptr ) );
}

std::vector<std::string> Steam_GameServerNetworkingSockets_ReceiveMessagesOnConnectionStrings( HSteamNetConnection connection, int maxMessages )
{
	return ReceiveMessagesOnConnectionStrings( SteamAPI_SteamGameServerNetworkingSockets_SteamAPI(), connection, maxMessages );
}

std::vector<std::string> Steam_GameServerNetworkingSockets_ReceiveMessagesOnPollGroupStrings( HSteamNetPollGroup pollGroup, int maxMessages )
{
	return ReceiveMessagesOnPollGroupStrings( SteamAPI_SteamGameServerNetworkingSockets_SteamAPI(), pollGroup, maxMessages );
}

int Steam_NetworkingSend_Unreliable()
{
	return k_nSteamNetworkingSend_Unreliable;
}

int Steam_NetworkingSend_UnreliableNoDelay()
{
	return k_nSteamNetworkingSend_UnreliableNoDelay;
}

int Steam_NetworkingSend_Reliable()
{
	return k_nSteamNetworkingSend_Reliable;
}

int Steam_NetworkingSend_ReliableNoNagle()
{
	return k_nSteamNetworkingSend_ReliableNoNagle;
}

int Steam_NetworkingConnectionState_None()
{
	return k_ESteamNetworkingConnectionState_None;
}

int Steam_NetworkingConnectionState_Connecting()
{
	return k_ESteamNetworkingConnectionState_Connecting;
}

int Steam_NetworkingConnectionState_FindingRoute()
{
	return k_ESteamNetworkingConnectionState_FindingRoute;
}

int Steam_NetworkingConnectionState_Connected()
{
	return k_ESteamNetworkingConnectionState_Connected;
}

int Steam_NetworkingConnectionState_ClosedByPeer()
{
	return k_ESteamNetworkingConnectionState_ClosedByPeer;
}

int Steam_NetworkingConnectionState_ProblemDetectedLocally()
{
	return k_ESteamNetworkingConnectionState_ProblemDetectedLocally;
}

int Steam_NetConnectionEnd_AppGeneric()
{
	return k_ESteamNetConnectionEnd_App_Generic;
}

int Steam_NetConnectionEnd_AppExceptionGeneric()
{
	return k_ESteamNetConnectionEnd_AppException_Generic;
}

SteamAPICall_t Steam_Lobby_RequestList()
{
	return g_lobbyAsyncState.RequestList();
}

bool Steam_Lobby_IsListPending()
{
	return g_lobbyAsyncState.IsListPending();
}

bool Steam_Lobby_IsListComplete()
{
	return g_lobbyAsyncState.IsListComplete();
}

bool Steam_Lobby_ListHadIOFailure()
{
	return g_lobbyAsyncState.ListHadIOFailure();
}

uint32 Steam_Lobby_GetListResultCount()
{
	return g_lobbyAsyncState.GetLobbyCount();
}

uint64_steamid Steam_Lobby_GetListLobbyByIndex( int index )
{
	if ( index < 0 || static_cast<uint32>( index ) >= g_lobbyAsyncState.GetLobbyCount() )
	{
		return 0;
	}
	ISteamMatchmaking *matchmaking = SteamMatchmaking();
	return matchmaking ? matchmaking->GetLobbyByIndex( index ).ConvertToUint64() : 0;
}

std::string Steam_Lobby_GetListLobbyNameByIndex( int index )
{
	const uint64_steamid lobbyID = Steam_Lobby_GetListLobbyByIndex( index );
	if ( lobbyID == 0 )
	{
		return {};
	}
	ISteamMatchmaking *matchmaking = SteamMatchmaking();
	if ( !matchmaking )
	{
		return {};
	}
	const char *name = matchmaking->GetLobbyData( CSteamID( lobbyID ), "name" );
	return name ? std::string( name ) : std::string();
}

std::vector<std::string> Steam_Lobby_GetDataEntries( uint64_steamid lobbyID )
{
	std::vector<std::string> result;
	ISteamMatchmaking *matchmaking = SteamMatchmaking();
	if ( !matchmaking || lobbyID == 0 )
	{
		return result;
	}

	const int count = matchmaking->GetLobbyDataCount( CSteamID( lobbyID ) );
	result.reserve( static_cast<size_t>( std::max( count, 0 ) ) );
	for ( int index = 0; index < count; ++index )
	{
		char key[256] = { 0 };
		char value[4096] = { 0 };
		if ( matchmaking->GetLobbyDataByIndex( CSteamID( lobbyID ), index, key, sizeof( key ), value, sizeof( value ) ) )
		{
			result.emplace_back( std::string( key ) + "=" + std::string( value ) );
		}
	}
	return result;
}

SteamAPICall_t Steam_Lobby_Create( int lobbyType, int maxMembers )
{
	return g_lobbyAsyncState.Create( lobbyType, maxMembers );
}

bool Steam_Lobby_IsCreatePending()
{
	return g_lobbyAsyncState.IsCreatePending();
}

bool Steam_Lobby_IsCreateComplete()
{
	return g_lobbyAsyncState.IsCreateComplete();
}

bool Steam_Lobby_CreateHadIOFailure()
{
	return g_lobbyAsyncState.CreateHadIOFailure();
}

uint64_steamid Steam_Lobby_GetCreatedLobbyID()
{
	return g_lobbyAsyncState.GetCreatedLobbyID();
}

int Steam_Lobby_GetCreateResult()
{
	return g_lobbyAsyncState.GetCreateResult();
}

bool Steam_Lobby_CreateSucceeded()
{
	return g_lobbyAsyncState.IsCreateComplete()
		&& !g_lobbyAsyncState.CreateHadIOFailure()
		&& g_lobbyAsyncState.GetCreateResult() == k_EResultOK;
}

SteamAPICall_t Steam_Lobby_Join( uint64_steamid lobbyID )
{
	return g_lobbyAsyncState.Join( lobbyID );
}

bool Steam_Lobby_IsJoinPending()
{
	return g_lobbyAsyncState.IsJoinPending();
}

bool Steam_Lobby_IsJoinComplete()
{
	return g_lobbyAsyncState.IsJoinComplete();
}

bool Steam_Lobby_JoinHadIOFailure()
{
	return g_lobbyAsyncState.JoinHadIOFailure();
}

uint64_steamid Steam_Lobby_GetJoinedLobbyID()
{
	return g_lobbyAsyncState.GetJoinedLobbyID();
}

uint32 Steam_Lobby_GetJoinResponse()
{
	return g_lobbyAsyncState.GetJoinResponse();
}

bool Steam_Lobby_JoinSucceeded()
{
	return g_lobbyAsyncState.IsJoinComplete()
		&& !g_lobbyAsyncState.JoinHadIOFailure()
		&& g_lobbyAsyncState.GetJoinResponse() == k_EChatRoomEnterResponseSuccess;
}

int Steam_Lobby_ChatRoomEnterResponseSuccess()
{
	return k_EChatRoomEnterResponseSuccess;
}

int Steam_FriendFlagImmediate()
{
	return k_EFriendFlagImmediate;
}

int Steam_FriendFlagOnGameServer()
{
	return k_EFriendFlagOnGameServer;
}

int Steam_FriendFlagAll()
{
	return k_EFriendFlagAll;
}

int Steam_Friends_GetFriendCountImmediate()
{
	ISteamFriends *friends = SteamFriends();
	return friends ? friends->GetFriendCount( k_EFriendFlagImmediate ) : 0;
}

uint64_steamid Steam_Friends_GetFriendByIndexImmediate( int index )
{
	ISteamFriends *friends = SteamFriends();
	if ( !friends || index < 0 )
	{
		return 0;
	}
	return friends->GetFriendByIndex( index, k_EFriendFlagImmediate ).ConvertToUint64();
}

bool Steam_Friends_GetFriendGamePlayedInfo( uint64_steamid friendID )
{
	FriendGameInfo_t info{};
	return GetFriendGameInfo( friendID, &info );
}

uint64_gameid Steam_Friends_GetFriendGameID( uint64_steamid friendID )
{
	FriendGameInfo_t info{};
	return GetFriendGameInfo( friendID, &info ) ? info.m_gameID.ToUint64() : 0;
}

AppId_t Steam_Friends_GetFriendGameAppID( uint64_steamid friendID )
{
	FriendGameInfo_t info{};
	return GetFriendGameInfo( friendID, &info ) ? static_cast<AppId_t>( info.m_gameID.AppID() ) : k_uAppIdInvalid;
}

uint32 Steam_Friends_GetFriendGameIP( uint64_steamid friendID )
{
	FriendGameInfo_t info{};
	return GetFriendGameInfo( friendID, &info ) ? info.m_unGameIP : 0;
}

uint16 Steam_Friends_GetFriendGamePort( uint64_steamid friendID )
{
	FriendGameInfo_t info{};
	return GetFriendGameInfo( friendID, &info ) ? info.m_usGamePort : 0;
}

uint16 Steam_Friends_GetFriendGameQueryPort( uint64_steamid friendID )
{
	FriendGameInfo_t info{};
	return GetFriendGameInfo( friendID, &info ) ? info.m_usQueryPort : 0;
}

uint64_steamid Steam_Friends_GetFriendGameLobbyID( uint64_steamid friendID )
{
	FriendGameInfo_t info{};
	return GetFriendGameInfo( friendID, &info ) ? info.m_steamIDLobby.ConvertToUint64() : 0;
}

bool Steam_Friends_IsFriendInCurrentGame( uint64_steamid friendID )
{
	ISteamUtils *utils = SteamUtils();
	if ( !utils )
	{
		return false;
	}

	const AppId_t friendAppID = Steam_Friends_GetFriendGameAppID( friendID );
	return friendAppID != k_uAppIdInvalid && friendAppID == utils->GetAppID();
}'''
CPP_KEYWORDS = {
    "alignas",
    "alignof",
    "and",
    "and_eq",
    "asm",
    "auto",
    "bitand",
    "bitor",
    "bool",
    "break",
    "case",
    "catch",
    "char",
    "class",
    "compl",
    "const",
    "constexpr",
    "continue",
    "decltype",
    "default",
    "delete",
    "do",
    "double",
    "dynamic_cast",
    "else",
    "enum",
    "explicit",
    "export",
    "extern",
    "false",
    "float",
    "for",
    "friend",
    "goto",
    "if",
    "inline",
    "int",
    "long",
    "mutable",
    "namespace",
    "new",
    "noexcept",
    "not",
    "not_eq",
    "nullptr",
    "operator",
    "or",
    "or_eq",
    "private",
    "protected",
    "public",
    "register",
    "reinterpret_cast",
    "return",
    "short",
    "signed",
    "sizeof",
    "static",
    "static_assert",
    "static_cast",
    "struct",
    "switch",
    "template",
    "this",
    "thread_local",
    "throw",
    "true",
    "try",
    "typedef",
    "typeid",
    "typename",
    "union",
    "unsigned",
    "using",
    "virtual",
    "void",
    "volatile",
    "wchar_t",
    "while",
    "xor",
    "xor_eq",
}


def normalize_type(type_name: str) -> str:
    return " ".join(type_name.replace(" *", "*").replace("*", " *").split())


def swig_safe_type(type_name: str) -> str | None:
    type_name = normalize_type(type_name)
    if "&" in type_name or "[" in type_name or "]" in type_name:
        return None
    if "*" in type_name and type_name not in SUPPORTED_POINTER_TYPES:
        return None
    if type_name.startswith("ISteam"):
        return None
    return type_name


def safe_name(name: str, fallback: str) -> str:
    name = name or fallback
    if name in CPP_KEYWORDS:
        return f"{name}_"
    return name


def flat_type(entry: dict, key: str) -> str | None:
    value = entry.get(f"{key}_flat", entry.get(key))
    if not value:
        return None
    return swig_safe_type(value)


def wrapper_name(classname: str, methodname: str) -> str:
    if classname.startswith("ISteam"):
        classname = classname[len("ISteam") :]
    return f"Steam_{classname}_{methodname}"


def iter_wrappable_methods(api: dict):
    for interface in api.get("interfaces", []):
        accessors = interface.get("accessors") or []
        if not accessors:
            continue

        accessor = accessors[0].get("name_flat")
        classname = interface.get("classname")
        if not accessor or not classname:
            continue

        for method in interface.get("methods", []):
            methodname = method.get("methodname")
            flat_name = method.get("methodname_flat")
            return_type = flat_type(method, "returntype")
            if not methodname or not flat_name or return_type is None:
                continue

            params = []
            for index, param in enumerate(method.get("params", [])):
                param_type = flat_type(param, "paramtype")
                if param_type is None:
                    break
                param_name = safe_name(param.get("paramname", ""), f"arg{index}")
                params.append((param_type, param_name))
            else:
                yield {
                    "classname": classname,
                    "accessor": accessor,
                    "methodname": methodname,
                    "flat_name": flat_name,
                    "return_type": return_type,
                    "params": params,
                    "wrapper_name": wrapper_name(classname, methodname),
                }


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


def generate(api: dict, output_dir: Path) -> None:
    methods = sorted(iter_wrappable_methods(api), key=lambda item: item["wrapper_name"])
    output_dir.mkdir(parents=True, exist_ok=True)

    header = output_dir / "steamworks_swig_shim.h"
    source = output_dir / "steamworks_swig_shim.cpp"
    interface = output_dir / "steamworks.i"

    header.write_text(
        "\n".join(
            [
                "#pragma once",
                "",
                "#include <algorithm>",
                "#include <string>",
                "#include <vector>",
                "",
                '#include "steam/steam_api_flat.h"',
                '#include "steam/steam_gameserver.h"',
                "",
                *GLOBAL_DECLARATIONS,
                "",
                *[declaration(method) for method in methods],
                "",
            ]
        ),
        encoding="utf-8",
    )

    source.write_text(
        "\n\n".join(
            [
                '#include "steamworks_swig_shim.h"\n\n' + GLOBAL_DEFINITIONS,
                *[definition(method) for method in methods],
                "",
            ]
        ),
        encoding="utf-8",
    )

    interface.write_text(
        "\n".join(
            [
                "%module steamworks",
                "",
                "%{",
                '#include "steamworks_swig_shim.h"',
                "%}",
                "",
                "%include <std_string.i>",
                "%include <std_vector.i>",
                "%template(StringVector) std::vector<std::string>;",
                "",
                *swig_type_declarations(api, methods),
                "",
                '%include "steamworks_swig_shim.h"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"Generated {len(methods)} wrapper functions in {output_dir}")


def swig_type_declarations(api: dict, methods: list[dict]) -> list[str]:
    lines = [
        "/* SWIG-only type declarations. The compiled extension uses Valve's real headers. */",
    ]

    for item in api.get("typedefs", []):
        alias = item.get("typedef")
        target = item.get("type")
        if not alias or not target:
            continue
        target = normalize_type(target)
        if "*" in target or "[" in target or "]" in target or "(" in target:
            continue
        lines.append(f"typedef {target} {alias};")

    for alias, target in FLAT_TYPEDEFS.items():
        lines.append(f"typedef {target} {alias};")

    lines.append("")

    used_types = {method["return_type"] for method in methods}
    for method in methods:
        used_types.update(type_name for type_name, _ in method["params"])

    for item in api.get("enums", []):
        enum_name = item.get("enumname")
        if not enum_name or enum_name not in used_types:
            continue
        values = [
            value["name"]
            for value in item.get("values", [])
            if value.get("name") and value["name"].replace("_", "").isalnum()
        ]
        if not values:
            continue
        lines.append(f"enum {enum_name} {{")
        for value in values:
            lines.append(f"\t{value},")
        lines.append("};")

    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-json", default="sdk/public/steam/steam_api.json")
    parser.add_argument("--output-dir", default="generated")
    args = parser.parse_args()

    api = json.loads(Path(args.api_json).read_text(encoding="utf-8"))
    generate(api, Path(args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
