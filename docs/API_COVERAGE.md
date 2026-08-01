# API Coverage

This file is generated from `generated/steamworks_c_api_model.json`.
Regenerate it after changing the SDK, C ABI generator, or curated helper list.

## Summary

- SDK interface methods supported by the generated C ABI: 600 of 921 (65.1%)
- SDK interface methods currently skipped: 321
- Total C ABI functions, including manual helpers: 881

## C ABI Function Sources

| Source | Functions |
| --- | ---: |
| Curated C-safe helpers | 138 |
| Manual lifecycle/global helpers | 44 |
| Manual-dispatch callback helpers | 99 |
| SDK methods | 600 |

## Language Support Buckets

| Bucket | Functions |
| --- | ---: |
| `bytes_or_bytes_list` | 15 |
| `scalar` | 803 |
| `scalar_string` | 55 |
| `string_list` | 8 |

## Interface Coverage

| Steamworks group | SDK methods | C ABI methods | Coverage | Curated/helper funcs |
| --- | ---: | ---: | ---: | ---: |
| `Apps` | 35 | 26 | 74.3% | 0 |
| `Client` | 33 | 0 | 0.0% | 0 |
| `Controller` | 34 | 26 | 76.5% | 0 |
| `Friends` | 78 | 72 | 92.3% | 10 |
| `GameServer` | 41 | 35 | 85.4% | 15 |
| `GameServerStats` | 10 | 7 | 70.0% | 0 |
| `HTMLSurface` | 37 | 30 | 81.1% | 0 |
| `HTTP` | 25 | 15 | 60.0% | 3 |
| `Input` | 48 | 38 | 79.2% | 0 |
| `Inventory` | 38 | 15 | 39.5% | 0 |
| `Matchmaking` | 38 | 33 | 86.8% | 0 |
| `MatchmakingPingResponse` | 2 | 0 | 0.0% | 0 |
| `MatchmakingPlayersResponse` | 3 | 0 | 0.0% | 0 |
| `MatchmakingRulesResponse` | 3 | 0 | 0.0% | 0 |
| `MatchmakingServerFriendsResponse` | 3 | 0 | 0.0% | 0 |
| `MatchmakingServerListResponse` | 3 | 0 | 0.0% | 0 |
| `MatchmakingServers` | 18 | 1 | 5.6% | 14 |
| `Music` | 9 | 9 | 100.0% | 0 |
| `Networking` | 22 | 9 | 40.9% | 0 |
| `NetworkingFakeUDPPort` | 4 | 0 | 0.0% | 0 |
| `NetworkingMessages` | 6 | 0 | 0.0% | 5 |
| `NetworkingSockets` | 47 | 15 | 31.9% | 23 |
| `NetworkingUtils` | 41 | 14 | 34.1% | 0 |
| `ParentalSettings` | 6 | 6 | 100.0% | 0 |
| `Parties` | 12 | 7 | 58.3% | 0 |
| `RemotePlay` | 20 | 17 | 85.0% | 0 |
| `RemoteStorage` | 59 | 43 | 72.9% | 5 |
| `Screenshots` | 9 | 8 | 88.9% | 0 |
| `Timeline` | 18 | 18 | 100.0% | 0 |
| `UGC` | 99 | 74 | 74.7% | 0 |
| `User` | 33 | 24 | 72.7% | 5 |
| `UserStats` | 44 | 24 | 54.5% | 0 |
| `Utils` | 39 | 32 | 82.1% | 0 |
| `Video` | 4 | 2 | 50.0% | 0 |

## Skipped Reasons

| Reason | Methods |
| --- | ---: |
| `interface_pointer` | 12 |
| `no_flat_accessor` | 51 |
| `pointer_output_or_unsupported_pointer` | 205 |
| `reference_type` | 20 |
| `unsupported_c_type` | 33 |

## Skipped Examples

### `interface_pointer`

| Interface | Method | Detail |
| --- | --- | --- |
| `HTMLSurface` | `KeyChar` | `eHTMLKeyModifiers: ISteamHTMLSurface::EHTMLKeyModifiers` |
| `HTMLSurface` | `KeyDown` | `eHTMLKeyModifiers: ISteamHTMLSurface::EHTMLKeyModifiers` |
| `HTMLSurface` | `KeyUp` | `eHTMLKeyModifiers: ISteamHTMLSurface::EHTMLKeyModifiers` |
| `HTMLSurface` | `MouseDoubleClick` | `eMouseButton: ISteamHTMLSurface::EHTMLMouseButton` |
| `HTMLSurface` | `MouseDown` | `eMouseButton: ISteamHTMLSurface::EHTMLMouseButton` |

### `no_flat_accessor`

| Interface | Method | Detail |
| --- | --- | --- |
| `Client` | `BReleaseSteamPipe` | `bool` |
| `Client` | `BShutdownIfAllPipesClosed` | `bool` |
| `Client` | `ConnectToGlobalUser` | `HSteamUser` |
| `Client` | `CreateLocalUser` | `HSteamUser` |
| `Client` | `CreateSteamPipe` | `HSteamPipe` |

### `pointer_output_or_unsupported_pointer`

| Interface | Method | Detail |
| --- | --- | --- |
| `Apps` | `BGetDLCDataByIndex` | `pAppID: AppId_t *` |
| `Apps` | `BIsTimedTrial` | `punSecondsAllowed: uint32 *` |
| `Apps` | `GetAppInstallDir` | `pchFolder: char *` |
| `Apps` | `GetBetaInfo` | `punFlags: uint32 *` |
| `Apps` | `GetCurrentBetaName` | `pchName: char *` |

### `reference_type`

| Interface | Method | Detail |
| --- | --- | --- |
| `NetworkingMessages` | `AcceptSessionWithUser` | `identityRemote: const SteamNetworkingIdentity &` |
| `NetworkingMessages` | `CloseChannelWithUser` | `identityRemote: const SteamNetworkingIdentity &` |
| `NetworkingMessages` | `CloseSessionWithUser` | `identityRemote: const SteamNetworkingIdentity &` |
| `NetworkingMessages` | `GetSessionConnectionInfo` | `identityRemote: const SteamNetworkingIdentity &` |
| `NetworkingMessages` | `SendMessageToUser` | `identityRemote: const SteamNetworkingIdentity &` |

### `unsupported_c_type`

| Interface | Method | Detail |
| --- | --- | --- |
| `Controller` | `GetAnalogActionData` | `return InputAnalogActionData_t` |
| `Controller` | `GetDigitalActionData` | `return InputDigitalActionData_t` |
| `Controller` | `GetMotionData` | `return InputMotionData_t` |
| `GameServer` | `GetPublicIP` | `return SteamIPAddress_t` |
| `Input` | `EnableActionEventCallbacks` | `pCallback: SteamInputActionEventCallbackPointer` |
