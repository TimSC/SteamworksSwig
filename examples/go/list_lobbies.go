package main

import (
	"flag"
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
	maxResults := flag.Int("max-results", 10, "maximum lobby results to request")
	timeout := flag.Duration("timeout", 10*time.Second, "time to wait for the lobby query")
	flag.Parse()

	if !steamworks.IsSteamRunning() {
		fmt.Fprintln(os.Stderr, "Steam is not running.")
		os.Exit(1)
	}

	if err := steamworks.Init(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	defer steamworks.Shutdown()

	steamworks.Matchmaking.AddRequestLobbyListResultCountFilter(*maxResults)
	steamworks.Lobby.RequestList()
	if !pumpUntil(steamworks.Lobby.IsListComplete, *timeout) {
		fmt.Fprintln(os.Stderr, "Timed out waiting for lobby list.")
		os.Exit(1)
	}

	if steamworks.Lobby.ListHadIOFailure() {
		fmt.Fprintln(os.Stderr, "Lobby list request failed with an IO failure.")
		os.Exit(1)
	}

	count := steamworks.Lobby.GetListResultCount()
	fmt.Printf("Found %d lobbies\n", count)
	for index := 0; index < int(count); index++ {
		lobbyID := steamworks.Lobby.GetListLobbyByIndex(index)
		lobbyName := steamworks.Lobby.GetListLobbyNameByIndex(index)
		members := steamworks.Matchmaking.GetNumLobbyMembers(lobbyID)
		memberLimit := steamworks.Matchmaking.GetLobbyMemberLimit(lobbyID)
		ownerID := steamworks.Matchmaking.GetLobbyOwner(lobbyID)
		fmt.Printf("%d: %d name=%q members=%d/%d owner=%d\n", index, lobbyID, lobbyName, members, memberLimit, ownerID)
	}
}
