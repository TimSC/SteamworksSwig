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
		{name: "Apps.BIsSubscribed", fn: func() any { return steamworks.Apps.IsSubscribed() }},
		{name: "Apps.BIsCybercafe", fn: func() any { return steamworks.Apps.IsCybercafe() }},
		{name: "Apps.BIsLowViolence", fn: func() any { return steamworks.Apps.IsLowViolence() }},
		{name: "Apps.BIsSubscribedFromFamilySharing", fn: func() any { return steamworks.Apps.IsSubscribedFromFamilySharing() }},
		{name: "Apps.BIsSubscribedFromFreeWeekend", fn: func() any { return steamworks.Apps.IsSubscribedFromFreeWeekend() }},
		{name: "Apps.BIsVACBanned", fn: func() any { return steamworks.Apps.IsVACBanned() }},
		{name: "Apps.GetAppBuildId", fn: func() any { return steamworks.Apps.GetAppBuildId() }},
		{name: "Apps.GetAppOwner", fn: func() any { return steamworks.Apps.GetAppOwner() }},
		{name: "Apps.GetAvailableGameLanguages", fn: func() any { return steamworks.Apps.GetAvailableGameLanguages() }},
		{name: "Apps.GetCurrentGameLanguage", fn: func() any { return steamworks.Apps.GetCurrentGameLanguage() }},
		{name: "Apps.GetDLCCount", fn: func() any { return steamworks.Apps.GetDLCCount() }},

		{name: "Friends.GetClanCount", fn: func() any { return steamworks.Friends.GetClanCount() }},
		{name: "Friends.GetCoplayFriendCount", fn: func() any { return steamworks.Friends.GetCoplayFriendCount() }},
		{name: "Friends.GetFriendsGroupCount", fn: func() any { return steamworks.Friends.GetFriendsGroupCount() }},
		{name: "Friends.GetNumChatsWithUnreadPriorityMessages", fn: func() any { return steamworks.Friends.GetNumChatsWithUnreadPriorityMessages() }},
		{name: "Friends.GetPersonaName", fn: func() any { return steamworks.Friends.GetPersonaName() }},
		{name: "Friends.GetPersonaState", fn: func() any { return steamworks.Friends.GetPersonaState() }},

		{name: "GameServer.GetGameplayStats", fn: func() any { steamworks.GameServer.GetGameplayStats(); return nil }},
		{name: "GameServer.GetSteamID", fn: func() any { return steamworks.GameServer.GetSteamID() }},

		{name: "Input.GetSessionInputConfigurationSettings", fn: func() any { return steamworks.Input.GetSessionInputConfigurationSettings() }},
		{name: "Inventory.GetNumItemsWithPrices", fn: func() any { return steamworks.Inventory.GetNumItemsWithPrices() }},
		{name: "Matchmaking.GetFavoriteGameCount", fn: func() any { return steamworks.Matchmaking.GetFavoriteGameCount() }},

		{name: "Music.BIsEnabled", fn: func() any { return steamworks.Music.IsEnabled() }},
		{name: "Music.BIsPlaying", fn: func() any { return steamworks.Music.IsPlaying() }},
		{name: "Music.GetPlaybackStatus", fn: func() any { return steamworks.Music.GetPlaybackStatus() }},
		{name: "Music.GetVolume", fn: func() any { return steamworks.Music.GetVolume() }},

		{name: "NetworkingSockets.GetHostedDedicatedServerPOPID", fn: func() any { return steamworks.NetworkingSockets.GetHostedDedicatedServerPOPID() }},
		{name: "NetworkingSockets.GetHostedDedicatedServerPort", fn: func() any { return steamworks.NetworkingSockets.GetHostedDedicatedServerPort() }},
		{name: "NetworkingUtils.GetLocalTimestamp", fn: func() any { return steamworks.NetworkingUtils.GetLocalTimestamp() }},
		{name: "NetworkingUtils.GetPOPCount", fn: func() any { return steamworks.NetworkingUtils.GetPOPCount() }},

		{name: "ParentalSettings.BIsParentalLockEnabled", fn: func() any { return steamworks.ParentalSettings.IsParentalLockEnabled() }},
		{name: "ParentalSettings.BIsParentalLockLocked", fn: func() any { return steamworks.ParentalSettings.IsParentalLockLocked() }},
		{name: "Parties.GetNumActiveBeacons", fn: func() any { return steamworks.Parties.GetNumActiveBeacons() }},
		{name: "RemotePlay.GetSessionCount", fn: func() any { return steamworks.RemotePlay.GetSessionCount() }},

		{name: "RemoteStorage.GetCachedUGCCount", fn: func() any { return steamworks.RemoteStorage.GetCachedUGCCount() }},
		{name: "RemoteStorage.GetFileCount", fn: func() any { return steamworks.RemoteStorage.GetFileCount() }},
		{name: "RemoteStorage.GetLocalFileChangeCount", fn: func() any { return steamworks.RemoteStorage.GetLocalFileChangeCount() }},
		{name: "RemoteStorage.IsCloudEnabledForAccount", fn: func() any { return steamworks.RemoteStorage.IsCloudEnabledForAccount() }},
		{name: "RemoteStorage.IsCloudEnabledForApp", fn: func() any { return steamworks.RemoteStorage.IsCloudEnabledForApp() }},

		{name: "Screenshots.IsScreenshotsHooked", fn: func() any { return steamworks.Screenshots.IsScreenshotsHooked() }},
		{name: "UGC.GetNumDownloadedItems", fn: func() any { return steamworks.UGC.GetNumDownloadedItems() }},

		{name: "User.BIsBehindNAT", fn: func() any { return steamworks.User.IsBehindNAT() }},
		{name: "User.BIsPhoneIdentifying", fn: func() any { return steamworks.User.IsPhoneIdentifying() }},
		{name: "User.BIsPhoneRequiringVerification", fn: func() any { return steamworks.User.IsPhoneRequiringVerification() }},
		{name: "User.BIsPhoneVerified", fn: func() any { return steamworks.User.IsPhoneVerified() }},
		{name: "User.BIsTwoFactorEnabled", fn: func() any { return steamworks.User.IsTwoFactorEnabled() }},
		{name: "User.GetHSteamUser", fn: func() any { return steamworks.User.GetHSteamUser() }},
		{name: "User.GetPlayerSteamLevel", fn: func() any { return steamworks.User.GetPlayerSteamLevel() }},
		{name: "User.GetSteamID", fn: func() any { return steamworks.User.GetSteamID() }},
		{name: "User.GetVoiceOptimalSampleRate", fn: func() any { return steamworks.User.GetVoiceOptimalSampleRate() }},

		{name: "UserStats.GetNumAchievements", fn: func() any { return steamworks.UserStats.GetNumAchievements() }},

		{name: "Utils.GetAppID", fn: func() any { return steamworks.Utils.GetAppID() }},
		{name: "Utils.GetConnectedUniverse", fn: func() any { return steamworks.Utils.GetConnectedUniverse() }},
		{name: "Utils.GetCurrentBatteryPower", fn: func() any { return steamworks.Utils.GetCurrentBatteryPower() }},
		{name: "Utils.GetEnteredGamepadTextLength", fn: func() any { return steamworks.Utils.GetEnteredGamepadTextLength() }},
		{name: "Utils.GetIPCCallCount", fn: func() any { return steamworks.Utils.GetIPCCallCount() }},
		{name: "Utils.GetIPCountry", fn: func() any { return steamworks.Utils.GetIPCountry() }},
		{name: "Utils.GetSecondsSinceAppActive", fn: func() any { return steamworks.Utils.GetSecondsSinceAppActive() }},
		{name: "Utils.GetSecondsSinceComputerActive", fn: func() any { return steamworks.Utils.GetSecondsSinceComputerActive() }},
		{name: "Utils.GetServerRealTime", fn: func() any { return steamworks.Utils.GetServerRealTime() }},
		{name: "Utils.GetSteamHardwareDefaultConfig", fn: func() any { return steamworks.Utils.GetSteamHardwareDefaultConfig() }},
		{name: "Utils.GetSteamUILanguage", fn: func() any { return steamworks.Utils.GetSteamUILanguage() }},
		{name: "Utils.IsOverlayEnabled", fn: func() any { return steamworks.Utils.IsOverlayEnabled() }},
		{name: "Utils.IsRunningOnSteamHardware", fn: func() any { return steamworks.Utils.IsRunningOnSteamHardware() }},
		{name: "Utils.IsRunningUnderProton", fn: func() any { return steamworks.Utils.IsRunningUnderProton() }},
		{name: "Utils.IsSteamChinaLauncher", fn: func() any { return steamworks.Utils.IsSteamChinaLauncher() }},
		{name: "Utils.IsSteamInBigPictureMode", fn: func() any { return steamworks.Utils.IsSteamInBigPictureMode() }},
		{name: "Utils.IsSteamRunningInVR", fn: func() any { return steamworks.Utils.IsSteamRunningInVR() }},
		{name: "Utils.IsVRHeadsetStreamingEnabled", fn: func() any { return steamworks.Utils.IsVRHeadsetStreamingEnabled() }},
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
