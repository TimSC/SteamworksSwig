package main

import (
	"fmt"
	"os"
	"time"

	"github.com/TimSC/SteamworksSwig/go/steamworks"
)

func pumpUntil(predicate func() bool, timeout time.Duration) bool {
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		steamworks.RunCallbacks()
		if predicate() {
			return true
		}
		time.Sleep(50 * time.Millisecond)
	}
	return false
}

func main() {
	if !steamworks.IsSteamRunning() {
		fmt.Fprintln(os.Stderr, "Steam is not running.")
		os.Exit(1)
	}

	if err := steamworks.Init(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	defer steamworks.Shutdown()

	steamworks.Lobby.RequestList()
	if !pumpUntil(steamworks.Lobby.IsListComplete, 10*time.Second) {
		fmt.Fprintln(os.Stderr, "Timed out waiting for lobby list.")
		os.Exit(1)
	}

	if steamworks.Lobby.ListHadIOFailure() {
		fmt.Fprintln(os.Stderr, "Lobby list request failed with an IO failure.")
		os.Exit(1)
	}

	count := steamworks.Lobby.ListResultCount()
	fmt.Printf("Found %d lobbies\n", count)
	for index := 0; index < int(count); index++ {
		lobbyID := steamworks.Lobby.ListLobbyByIndex(index)
		lobbyName := steamworks.Lobby.ListLobbyNameByIndex(index)
		fmt.Printf("%d: %d %s\n", index, lobbyID, lobbyName)
	}
}
