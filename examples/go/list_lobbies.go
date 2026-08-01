package main

import (
	"flag"
	"fmt"
	"os"
	"strconv"
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

func pumpManualLobbyList(apiCall uint64, timeout time.Duration) (bool, bool, map[string]string) {
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		callback, ok := steamworks.PollCallback()
		if ok &&
			callback.APICallCompleted &&
			callback.CompletedAPICall == steamworks.APICall(apiCall) &&
			callback.CompletedCallbackID == steamworks.CallbackIDLobbyMatchList() {
			payload := steamworks.ManualDispatch.DecodeAPICallResultLobbyMatchList()
			return true, callback.APICallResultFailed, steamworks.ParseCallbackPayload(payload)
		}
		time.Sleep(50 * time.Millisecond)
	}
	return false, false, map[string]string{}
}

func printLobbies(count int, useAutoHelpers bool) {
	fmt.Printf("Found %d lobbies\n", count)
	for index := 0; index < count; index++ {
		var lobbyID uint64
		var lobbyName string
		if useAutoHelpers {
			lobbyID = steamworks.Lobby.GetListLobbyByIndex(index)
			lobbyName = steamworks.Lobby.GetListLobbyNameByIndex(index)
		} else {
			lobbyID = steamworks.Matchmaking.GetLobbyByIndex(index)
			lobbyName = steamworks.Matchmaking.GetLobbyData(lobbyID, "name")
		}
		members := steamworks.Matchmaking.GetNumLobbyMembers(lobbyID)
		memberLimit := steamworks.Matchmaking.GetLobbyMemberLimit(lobbyID)
		ownerID := steamworks.Matchmaking.GetLobbyOwner(lobbyID)
		fmt.Printf("%d: %d name=%q members=%d/%d owner=%d\n", index, lobbyID, lobbyName, members, memberLimit, ownerID)
	}
}

func main() {
	dispatch := flag.String("dispatch", "auto", "callback dispatch mode: auto or manual")
	maxResults := flag.Int("max-results", 10, "maximum lobby results to request")
	timeout := flag.Duration("timeout", 10*time.Second, "time to wait for the lobby query")
	flag.Parse()
	if *dispatch != "auto" && *dispatch != "manual" {
		fmt.Fprintln(os.Stderr, "--dispatch expects auto or manual")
		os.Exit(2)
	}

	if !steamworks.IsSteamRunning() {
		fmt.Fprintln(os.Stderr, "Steam is not running.")
		os.Exit(1)
	}

	if err := steamworks.Init(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	defer func() {
		if *dispatch == "manual" {
			steamworks.ShutdownManualDispatch()
		} else {
			steamworks.Shutdown()
		}
	}()

	if *dispatch == "manual" {
		steamworks.ManualDispatchInit()
		steamworks.Matchmaking.AddRequestLobbyListResultCountFilter(*maxResults)
		apiCall := steamworks.Matchmaking.RequestLobbyList()
		completed, failed, fields := pumpManualLobbyList(apiCall, *timeout)
		if !completed {
			fmt.Fprintln(os.Stderr, "Timed out waiting for lobby list.")
			os.Exit(1)
		}
		if failed {
			fmt.Fprintln(os.Stderr, "Lobby list request failed with an IO failure.")
			os.Exit(1)
		}
		count, _ := strconv.Atoi(fields["lobbies_matching"])
		printLobbies(count, false)
	} else {
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
		printLobbies(int(steamworks.Lobby.GetListResultCount()), true)
	}
}
