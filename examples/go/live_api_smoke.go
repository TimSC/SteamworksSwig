package main

// Low-impact live Steam API smoke test.
//
// Run from the project root after building the Go wrapper:
//
//   go run examples/go/live_api_smoke.go
//
// The test initializes Steam, calls a curated set of no-argument read-style
// APIs, prints a short result for each call, and shuts Steam down.

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"

	"github.com/TimSC/SteamworksSwig/go/steamworks"
	"github.com/TimSC/SteamworksSwig/go/steamworks/raw"
)

type liveCall struct {
	name string
	fn   func() any
}

type callResult struct {
	Name  string `json:"name"`
	OK    bool   `json:"ok"`
	Value string `json:"value,omitempty"`
	Error string `json:"error,omitempty"`
}

func short(value any) string {
	text := fmt.Sprintf("%#v", value)
	if len(text) > 96 {
		return text[:93] + "..."
	}
	return text
}

func runCall(call liveCall) (value any, err any) {
	defer func() {
		if recovered := recover(); recovered != nil {
			err = recovered
		}
	}()
	return call.fn(), nil
}

func liveCalls() []liveCall {
	return []liveCall{
		{name: "Apps.BIsSubscribed", fn: func() any { return raw.SWS_SteamAPI_ISteamApps_BIsSubscribed() }},
		{name: "Apps.BIsCybercafe", fn: func() any { return raw.SWS_SteamAPI_ISteamApps_BIsCybercafe() }},
		{name: "Apps.BIsLowViolence", fn: func() any { return raw.SWS_SteamAPI_ISteamApps_BIsLowViolence() }},
		{name: "Apps.BIsSubscribedFromFamilySharing", fn: func() any { return raw.SWS_SteamAPI_ISteamApps_BIsSubscribedFromFamilySharing() }},
		{name: "Apps.BIsSubscribedFromFreeWeekend", fn: func() any { return raw.SWS_SteamAPI_ISteamApps_BIsSubscribedFromFreeWeekend() }},
		{name: "Apps.BIsVACBanned", fn: func() any { return raw.SWS_SteamAPI_ISteamApps_BIsVACBanned() }},
		{name: "Apps.GetAppBuildId", fn: func() any { return raw.SWS_SteamAPI_ISteamApps_GetAppBuildId() }},
		{name: "Apps.GetAppOwner", fn: func() any { return raw.SWS_SteamAPI_ISteamApps_GetAppOwner() }},
		{name: "Apps.GetAvailableGameLanguages", fn: func() any { return raw.SWS_SteamAPI_ISteamApps_GetAvailableGameLanguages() }},
		{name: "Apps.GetCurrentGameLanguage", fn: func() any { return raw.SWS_SteamAPI_ISteamApps_GetCurrentGameLanguage() }},
		{name: "Apps.GetDLCCount", fn: func() any { return raw.SWS_SteamAPI_ISteamApps_GetDLCCount() }},

		{name: "Friends.GetClanCount", fn: func() any { return raw.SWS_SteamAPI_ISteamFriends_GetClanCount() }},
		{name: "Friends.GetCoplayFriendCount", fn: func() any { return raw.SWS_SteamAPI_ISteamFriends_GetCoplayFriendCount() }},
		{name: "Friends.GetFriendsGroupCount", fn: func() any { return raw.SWS_SteamAPI_ISteamFriends_GetFriendsGroupCount() }},
		{name: "Friends.GetNumChatsWithUnreadPriorityMessages", fn: func() any { return raw.SWS_SteamAPI_ISteamFriends_GetNumChatsWithUnreadPriorityMessages() }},
		{name: "Friends.GetPersonaName", fn: func() any { return raw.SWS_SteamAPI_ISteamFriends_GetPersonaName() }},
		{name: "Friends.GetPersonaState", fn: func() any { return raw.SWS_SteamAPI_ISteamFriends_GetPersonaState() }},

		{name: "GameServer.GetGameplayStats", fn: func() any { raw.SWS_SteamAPI_ISteamGameServer_GetGameplayStats(); return nil }},
		{name: "GameServer.GetSteamID", fn: func() any { return raw.SWS_SteamAPI_ISteamGameServer_GetSteamID() }},

		{name: "Input.GetSessionInputConfigurationSettings", fn: func() any { return raw.SWS_SteamAPI_ISteamInput_GetSessionInputConfigurationSettings() }},
		{name: "Inventory.GetNumItemsWithPrices", fn: func() any { return raw.SWS_SteamAPI_ISteamInventory_GetNumItemsWithPrices() }},
		{name: "Matchmaking.GetFavoriteGameCount", fn: func() any { return raw.SWS_SteamAPI_ISteamMatchmaking_GetFavoriteGameCount() }},

		{name: "Music.BIsEnabled", fn: func() any { return raw.SWS_SteamAPI_ISteamMusic_BIsEnabled() }},
		{name: "Music.BIsPlaying", fn: func() any { return raw.SWS_SteamAPI_ISteamMusic_BIsPlaying() }},
		{name: "Music.GetPlaybackStatus", fn: func() any { return raw.SWS_SteamAPI_ISteamMusic_GetPlaybackStatus() }},
		{name: "Music.GetVolume", fn: func() any { return raw.SWS_SteamAPI_ISteamMusic_GetVolume() }},

		{name: "NetworkingSockets.GetHostedDedicatedServerPOPID", fn: func() any { return raw.SWS_SteamAPI_ISteamNetworkingSockets_GetHostedDedicatedServerPOPID() }},
		{name: "NetworkingSockets.GetHostedDedicatedServerPort", fn: func() any { return raw.SWS_SteamAPI_ISteamNetworkingSockets_GetHostedDedicatedServerPort() }},
		{name: "NetworkingUtils.GetLocalTimestamp", fn: func() any { return raw.SWS_SteamAPI_ISteamNetworkingUtils_GetLocalTimestamp() }},
		{name: "NetworkingUtils.GetPOPCount", fn: func() any { return raw.SWS_SteamAPI_ISteamNetworkingUtils_GetPOPCount() }},

		{name: "ParentalSettings.BIsParentalLockEnabled", fn: func() any { return raw.SWS_SteamAPI_ISteamParentalSettings_BIsParentalLockEnabled() }},
		{name: "ParentalSettings.BIsParentalLockLocked", fn: func() any { return raw.SWS_SteamAPI_ISteamParentalSettings_BIsParentalLockLocked() }},
		{name: "Parties.GetNumActiveBeacons", fn: func() any { return raw.SWS_SteamAPI_ISteamParties_GetNumActiveBeacons() }},
		{name: "RemotePlay.GetSessionCount", fn: func() any { return raw.SWS_SteamAPI_ISteamRemotePlay_GetSessionCount() }},

		{name: "RemoteStorage.GetCachedUGCCount", fn: func() any { return raw.SWS_SteamAPI_ISteamRemoteStorage_GetCachedUGCCount() }},
		{name: "RemoteStorage.GetFileCount", fn: func() any { return raw.SWS_SteamAPI_ISteamRemoteStorage_GetFileCount() }},
		{name: "RemoteStorage.GetLocalFileChangeCount", fn: func() any { return raw.SWS_SteamAPI_ISteamRemoteStorage_GetLocalFileChangeCount() }},
		{name: "RemoteStorage.IsCloudEnabledForAccount", fn: func() any { return raw.SWS_SteamAPI_ISteamRemoteStorage_IsCloudEnabledForAccount() }},
		{name: "RemoteStorage.IsCloudEnabledForApp", fn: func() any { return raw.SWS_SteamAPI_ISteamRemoteStorage_IsCloudEnabledForApp() }},

		{name: "Screenshots.IsScreenshotsHooked", fn: func() any { return raw.SWS_SteamAPI_ISteamScreenshots_IsScreenshotsHooked() }},
		{name: "UGC.GetNumDownloadedItems", fn: func() any { return raw.SWS_SteamAPI_ISteamUGC_GetNumDownloadedItems() }},

		{name: "User.BIsBehindNAT", fn: func() any { return raw.SWS_SteamAPI_ISteamUser_BIsBehindNAT() }},
		{name: "User.BIsPhoneIdentifying", fn: func() any { return raw.SWS_SteamAPI_ISteamUser_BIsPhoneIdentifying() }},
		{name: "User.BIsPhoneRequiringVerification", fn: func() any { return raw.SWS_SteamAPI_ISteamUser_BIsPhoneRequiringVerification() }},
		{name: "User.BIsPhoneVerified", fn: func() any { return raw.SWS_SteamAPI_ISteamUser_BIsPhoneVerified() }},
		{name: "User.BIsTwoFactorEnabled", fn: func() any { return raw.SWS_SteamAPI_ISteamUser_BIsTwoFactorEnabled() }},
		{name: "User.GetHSteamUser", fn: func() any { return raw.SWS_SteamAPI_ISteamUser_GetHSteamUser() }},
		{name: "User.GetPlayerSteamLevel", fn: func() any { return raw.SWS_SteamAPI_ISteamUser_GetPlayerSteamLevel() }},
		{name: "User.GetSteamID", fn: func() any { return raw.SWS_SteamAPI_ISteamUser_GetSteamID() }},
		{name: "User.GetVoiceOptimalSampleRate", fn: func() any { return raw.SWS_SteamAPI_ISteamUser_GetVoiceOptimalSampleRate() }},

		{name: "UserStats.GetNumAchievements", fn: func() any { return raw.SWS_SteamAPI_ISteamUserStats_GetNumAchievements() }},

		{name: "Utils.GetAppID", fn: func() any { return raw.SWS_SteamAPI_ISteamUtils_GetAppID() }},
		{name: "Utils.GetConnectedUniverse", fn: func() any { return raw.SWS_SteamAPI_ISteamUtils_GetConnectedUniverse() }},
		{name: "Utils.GetCurrentBatteryPower", fn: func() any { return raw.SWS_SteamAPI_ISteamUtils_GetCurrentBatteryPower() }},
		{name: "Utils.GetEnteredGamepadTextLength", fn: func() any { return raw.SWS_SteamAPI_ISteamUtils_GetEnteredGamepadTextLength() }},
		{name: "Utils.GetIPCCallCount", fn: func() any { return raw.SWS_SteamAPI_ISteamUtils_GetIPCCallCount() }},
		{name: "Utils.GetIPCountry", fn: func() any { return raw.SWS_SteamAPI_ISteamUtils_GetIPCountry() }},
		{name: "Utils.GetSecondsSinceAppActive", fn: func() any { return raw.SWS_SteamAPI_ISteamUtils_GetSecondsSinceAppActive() }},
		{name: "Utils.GetSecondsSinceComputerActive", fn: func() any { return raw.SWS_SteamAPI_ISteamUtils_GetSecondsSinceComputerActive() }},
		{name: "Utils.GetServerRealTime", fn: func() any { return raw.SWS_SteamAPI_ISteamUtils_GetServerRealTime() }},
		{name: "Utils.GetSteamHardwareDefaultConfig", fn: func() any { return raw.SWS_SteamAPI_ISteamUtils_GetSteamHardwareDefaultConfig() }},
		{name: "Utils.GetSteamUILanguage", fn: func() any { return raw.SWS_SteamAPI_ISteamUtils_GetSteamUILanguage() }},
		{name: "Utils.IsOverlayEnabled", fn: func() any { return raw.SWS_SteamAPI_ISteamUtils_IsOverlayEnabled() }},
		{name: "Utils.IsRunningOnSteamHardware", fn: func() any { return raw.SWS_SteamAPI_ISteamUtils_IsRunningOnSteamHardware() }},
		{name: "Utils.IsRunningUnderProton", fn: func() any { return raw.SWS_SteamAPI_ISteamUtils_IsRunningUnderProton() }},
		{name: "Utils.IsSteamChinaLauncher", fn: func() any { return raw.SWS_SteamAPI_ISteamUtils_IsSteamChinaLauncher() }},
		{name: "Utils.IsSteamInBigPictureMode", fn: func() any { return raw.SWS_SteamAPI_ISteamUtils_IsSteamInBigPictureMode() }},
		{name: "Utils.IsSteamRunningInVR", fn: func() any { return raw.SWS_SteamAPI_ISteamUtils_IsSteamRunningInVR() }},
		{name: "Utils.IsVRHeadsetStreamingEnabled", fn: func() any { return raw.SWS_SteamAPI_ISteamUtils_IsVRHeadsetStreamingEnabled() }},
	}
}

func main() {
	jsonOutput := flag.Bool("json", false, "emit machine-readable JSON")
	limit := flag.Int("limit", 0, "only run the first N calls")
	flag.Parse()

	if !steamworks.IsSteamRunning() {
		fmt.Fprintln(os.Stderr, "Steam_IsSteamRunning returned false.")
		fmt.Fprintln(os.Stderr, "Start Steam, log in, then run this program again from the project root.")
		os.Exit(1)
	}

	if err := steamworks.Init(); err != nil {
		fmt.Fprintf(os.Stderr, "%s\n", err)
		fmt.Fprintln(os.Stderr, "Make sure Steam is running and steam_appid.txt is in the working directory.")
		os.Exit(1)
	}
	defer steamworks.Shutdown()

	steamworks.RunCallbacks()

	calls := liveCalls()
	if *limit > 0 && *limit < len(calls) {
		calls = calls[:*limit]
	}

	results := make([]callResult, 0, len(calls))
	failed := 0
	for _, call := range calls {
		value, err := runCall(call)
		if err != nil {
			failed++
			results = append(results, callResult{Name: call.name, OK: false, Error: fmt.Sprint(err)})
			if !*jsonOutput {
				fmt.Printf("FAIL %s: %v\n", call.name, err)
			}
			continue
		}
		results = append(results, callResult{Name: call.name, OK: true, Value: fmt.Sprintf("%#v", value)})
		if !*jsonOutput {
			fmt.Printf("OK   %s: %s\n", call.name, short(value))
		}
	}

	if *jsonOutput {
		payload := map[string]any{"total": len(results), "failed": failed, "results": results}
		encoded, err := json.MarshalIndent(payload, "", "  ")
		if err != nil {
			fmt.Fprintf(os.Stderr, "JSON encode failed: %v\n", err)
			os.Exit(1)
		}
		fmt.Println(string(encoded))
	} else {
		fmt.Printf("\nLive smoke complete: %d/%d passed\n", len(results)-failed, len(results))
	}
	if failed > 0 {
		os.Exit(1)
	}
}
