package main

import (
	"fmt"
	"os"

	"github.com/TimSC/SteamworksSwig/go/steamworks"
)

func yesNo(value bool) string {
	if value {
		return "yes"
	}
	return "no"
}

func main() {
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

	fmt.Println("Hello from Steamworks!")
	fmt.Printf("App ID: %d\n", steamworks.Utils.AppID())
	fmt.Printf("Logged on: %s\n", yesNo(steamworks.User.LoggedOn()))
	fmt.Printf("Persona name: %s\n", steamworks.Friends.PersonaName())
	fmt.Printf("Steam ID: %d\n", steamworks.User.SteamID())
	fmt.Printf("Subscribed to app: %s\n", yesNo(steamworks.Apps.IsSubscribed()))
}
