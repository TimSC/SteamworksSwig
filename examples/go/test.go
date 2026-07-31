package main

import (
	"fmt"
	"os"

	steamworks "../../go/steamworks"
)

func yesNo(value bool) string {
	if value {
		return "yes"
	}
	return "no"
}

func main() {
	if !steamworks.SWS_Steam_IsSteamRunning() {
		fmt.Fprintln(os.Stderr, "Steam_IsSteamRunning returned false.")
		fmt.Fprintln(os.Stderr, "Start Steam, log in, then run this program again from the project root.")
		os.Exit(1)
	}

	initResult := steamworks.SWS_Steam_InitEx()
	if initResult != 0 {
		fmt.Fprintf(os.Stderr, "Steam_InitEx failed (%d): %s\n", initResult, steamworks.SWS_Steam_GetLastInitError())
		fmt.Fprintln(os.Stderr, "Make sure Steam is running and steam_appid.txt is in the working directory.")
		os.Exit(1)
	}
	defer steamworks.SWS_Steam_Shutdown()

	steamworks.SWS_Steam_RunCallbacks()

	fmt.Println("Hello from Steamworks!")
	fmt.Printf("App ID: %d\n", steamworks.SWS_SteamAPI_ISteamUtils_GetAppID())
	fmt.Printf("Logged on: %s\n", yesNo(steamworks.SWS_SteamAPI_ISteamUser_BLoggedOn()))
	fmt.Printf("Persona name: %s\n", steamworks.SWS_SteamAPI_ISteamFriends_GetPersonaName())
	fmt.Printf("Steam ID: %d\n", steamworks.SWS_SteamAPI_ISteamUser_GetSteamID())
	fmt.Printf("Subscribed to app: %s\n", yesNo(steamworks.SWS_SteamAPI_ISteamApps_BIsSubscribed()))
}

