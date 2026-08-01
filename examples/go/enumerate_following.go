package main

import (
	"flag"
	"fmt"
	"os"
	"time"

	"github.com/TimSC/SteamworksSwig/go/steamworks"
)

func waitForAutoAPICall(apiCall uint64, timeout time.Duration) (bool, map[string]string, string) {
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		steamworks.RunCallbacks()
		payload := steamworks.Utils.IsAPICallCompletedString(apiCall)
		if payload != "" {
			return true, steamworks.ParseCallbackPayload(payload), payload
		}
		time.Sleep(50 * time.Millisecond)
	}
	return false, map[string]string{}, ""
}

func waitForManualAPICall(apiCall uint64, timeout time.Duration) (bool, steamworks.Callback) {
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		callback, ok := steamworks.PollCallback()
		if ok && callback.APICallCompleted && callback.CompletedAPICall == steamworks.APICall(apiCall) {
			return true, callback
		}
		time.Sleep(50 * time.Millisecond)
	}
	return false, steamworks.Callback{}
}

func main() {
	dispatch := flag.String("dispatch", "auto", "callback dispatch mode: auto or manual")
	startIndex := flag.Uint("start-index", 0, "following-list start index")
	timeout := flag.Duration("timeout", 10*time.Second, "time to wait for completion")
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
	}

	apiCall := steamworks.Friends.EnumerateFollowingList(*startIndex)
	fmt.Printf("Friends.EnumerateFollowingList call: %d\n", apiCall)
	if apiCall == 0 {
		fmt.Fprintln(os.Stderr, "Friends.EnumerateFollowingList returned an invalid SteamAPICall_t.")
		os.Exit(1)
	}

	if *dispatch == "manual" {
		completed, callback := waitForManualAPICall(apiCall, *timeout)
		if !completed {
			fmt.Fprintln(os.Stderr, "Timed out waiting for Friends.EnumerateFollowingList.")
			os.Exit(1)
		}
		fmt.Println("Completed: yes")
		fmt.Printf("Failed: %t\n", callback.APICallResultFailed)
		fmt.Printf("Callback ID: %d\n", callback.CompletedCallbackID)
		return
	}

	completed, fields, payload := waitForAutoAPICall(apiCall, *timeout)
	if !completed {
		fmt.Fprintln(os.Stderr, "Timed out waiting for Friends.EnumerateFollowingList.")
		os.Exit(1)
	}
	fmt.Println("Completed: yes")
	if failed, ok := fields["failed"]; ok {
		fmt.Printf("Failed: %s\n", failed)
	} else {
		fmt.Println("Failed: unknown")
	}
	if payload != "" {
		fmt.Printf("Completion payload: %s\n", payload)
	}
}
