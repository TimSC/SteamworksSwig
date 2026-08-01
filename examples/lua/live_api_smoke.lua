-- Low-impact live Steam API smoke test.
--
-- Run from the project root after building the Lua wrapper:
--
--   LUA_PATH="./lua/?.lua;;" LUA_CPATH="./lua/?.so;;" lua examples/lua/live_api_smoke.lua
--
-- The test initializes Steam, calls a curated set of no-argument read-style
-- APIs, prints a short result for each call, and shuts Steam down.

local steamworks = require("steamworks")

local function parse_args(args)
    local options = {
        json = false,
        limit = nil,
    }
    local index = 1
    while index <= #args do
        local arg = args[index]
        if arg == "--json" then
            options.json = true
        elseif arg == "--limit" then
            index = index + 1
            options.limit = tonumber(args[index])
            if options.limit == nil then
                io.stderr:write("--limit expects a number\n")
                os.exit(2)
            end
        elseif string.sub(arg, 1, 8) == "--limit=" then
            options.limit = tonumber(string.sub(arg, 9))
            if options.limit == nil then
                io.stderr:write("--limit expects a number\n")
                os.exit(2)
            end
        else
            io.stderr:write("Unknown argument: " .. arg .. "\n")
            os.exit(2)
        end
        index = index + 1
    end
    return options
end

local function short(value)
    local text
    if value == nil then
        text = "nil"
    elseif type(value) == "string" then
        text = string.format("%q", value)
    else
        text = tostring(value)
    end
    if #text > 96 then
        return string.sub(text, 1, 93) .. "..."
    end
    return text
end

local function json_escape(value)
    return string.format("%q", tostring(value))
end

local function print_json(results, failed)
    print("{")
    print(string.format('  "total": %d,', #results))
    print(string.format('  "failed": %d,', failed))
    print('  "results": [')
    for index, result in ipairs(results) do
        local suffix = index == #results and "" or ","
        if result.ok then
            print(string.format(
                '    {"name": %s, "ok": true, "value": %s}%s',
                json_escape(result.name),
                json_escape(result.value),
                suffix
            ))
        else
            print(string.format(
                '    {"name": %s, "ok": false, "error": %s}%s',
                json_escape(result.name),
                json_escape(result.error),
                suffix
            ))
        end
    end
    print("  ]")
    print("}")
end

local calls = {
    {name = "Apps.BIsSubscribed", fn = function() return steamworks.apps.is_subscribed() end},
    {name = "Apps.BIsCybercafe", fn = function() return steamworks.apps.is_cybercafe() end},
    {name = "Apps.BIsLowViolence", fn = function() return steamworks.apps.is_low_violence() end},
    {name = "Apps.BIsSubscribedFromFamilySharing", fn = function() return steamworks.apps.is_subscribed_from_family_sharing() end},
    {name = "Apps.BIsSubscribedFromFreeWeekend", fn = function() return steamworks.apps.is_subscribed_from_free_weekend() end},
    {name = "Apps.BIsVACBanned", fn = function() return steamworks.apps.is_vac_banned() end},
    {name = "Apps.GetAppBuildId", fn = function() return steamworks.apps.get_app_build_id() end},
    {name = "Apps.GetAppOwner", fn = function() return steamworks.apps.get_app_owner() end},
    {name = "Apps.GetAvailableGameLanguages", fn = function() return steamworks.apps.get_available_game_languages() end},
    {name = "Apps.GetCurrentGameLanguage", fn = function() return steamworks.apps.get_current_game_language() end},
    {name = "Apps.GetDLCCount", fn = function() return steamworks.apps.get_dlc_count() end},

    {name = "Friends.GetClanCount", fn = function() return steamworks.friends.get_clan_count() end},
    {name = "Friends.GetCoplayFriendCount", fn = function() return steamworks.friends.get_coplay_friend_count() end},
    {name = "Friends.GetFriendsGroupCount", fn = function() return steamworks.friends.get_friends_group_count() end},
    {name = "Friends.GetNumChatsWithUnreadPriorityMessages", fn = function() return steamworks.friends.get_num_chats_with_unread_priority_messages() end},
    {name = "Friends.GetPersonaName", fn = function() return steamworks.friends.get_persona_name() end},
    {name = "Friends.GetPersonaState", fn = function() return steamworks.friends.get_persona_state() end},

    {name = "GameServer.GetGameplayStats", fn = function() return steamworks.game_server.get_gameplay_stats() end},
    {name = "GameServer.GetSteamID", fn = function() return steamworks.game_server.get_steam_id() end},

    {name = "Input.GetSessionInputConfigurationSettings", fn = function() return steamworks.input.get_session_input_configuration_settings() end},
    {name = "Inventory.GetNumItemsWithPrices", fn = function() return steamworks.inventory.get_num_items_with_prices() end},
    {name = "Matchmaking.GetFavoriteGameCount", fn = function() return steamworks.matchmaking.get_favorite_game_count() end},

    {name = "Music.BIsEnabled", fn = function() return steamworks.music.is_enabled() end},
    {name = "Music.BIsPlaying", fn = function() return steamworks.music.is_playing() end},
    {name = "Music.GetPlaybackStatus", fn = function() return steamworks.music.get_playback_status() end},
    {name = "Music.GetVolume", fn = function() return steamworks.music.get_volume() end},

    {name = "NetworkingSockets.GetHostedDedicatedServerPOPID", fn = function() return steamworks.networking_sockets.get_hosted_dedicated_server_popid() end},
    {name = "NetworkingSockets.GetHostedDedicatedServerPort", fn = function() return steamworks.networking_sockets.get_hosted_dedicated_server_port() end},
    {name = "NetworkingUtils.GetLocalTimestamp", fn = function() return steamworks.networking_utils.get_local_timestamp() end},
    {name = "NetworkingUtils.GetPOPCount", fn = function() return steamworks.networking_utils.get_pop_count() end},

    {name = "ParentalSettings.BIsParentalLockEnabled", fn = function() return steamworks.parental_settings.is_parental_lock_enabled() end},
    {name = "ParentalSettings.BIsParentalLockLocked", fn = function() return steamworks.parental_settings.is_parental_lock_locked() end},
    {name = "Parties.GetNumActiveBeacons", fn = function() return steamworks.parties.get_num_active_beacons() end},
    {name = "RemotePlay.GetSessionCount", fn = function() return steamworks.remote_play.get_session_count() end},

    {name = "RemoteStorage.GetCachedUGCCount", fn = function() return steamworks.remote_storage.get_cached_ugc_count() end},
    {name = "RemoteStorage.GetFileCount", fn = function() return steamworks.remote_storage.get_file_count() end},
    {name = "RemoteStorage.GetLocalFileChangeCount", fn = function() return steamworks.remote_storage.get_local_file_change_count() end},
    {name = "RemoteStorage.IsCloudEnabledForAccount", fn = function() return steamworks.remote_storage.is_cloud_enabled_for_account() end},
    {name = "RemoteStorage.IsCloudEnabledForApp", fn = function() return steamworks.remote_storage.is_cloud_enabled_for_app() end},

    {name = "Screenshots.IsScreenshotsHooked", fn = function() return steamworks.screenshots.is_screenshots_hooked() end},
    {name = "UGC.GetNumDownloadedItems", fn = function() return steamworks.ugc.get_num_downloaded_items() end},

    {name = "User.BIsBehindNAT", fn = function() return steamworks.user.is_behind_nat() end},
    {name = "User.BIsPhoneIdentifying", fn = function() return steamworks.user.is_phone_identifying() end},
    {name = "User.BIsPhoneRequiringVerification", fn = function() return steamworks.user.is_phone_requiring_verification() end},
    {name = "User.BIsPhoneVerified", fn = function() return steamworks.user.is_phone_verified() end},
    {name = "User.BIsTwoFactorEnabled", fn = function() return steamworks.user.is_two_factor_enabled() end},
    {name = "User.GetHSteamUser", fn = function() return steamworks.user.get_h_steam_user() end},
    {name = "User.GetPlayerSteamLevel", fn = function() return steamworks.user.get_player_steam_level() end},
    {name = "User.GetSteamID", fn = function() return steamworks.user.get_steam_id() end},
    {name = "User.GetVoiceOptimalSampleRate", fn = function() return steamworks.user.get_voice_optimal_sample_rate() end},

    {name = "UserStats.GetNumAchievements", fn = function() return steamworks.user_stats.get_num_achievements() end},

    {name = "Utils.GetAppID", fn = function() return steamworks.utils.get_app_id() end},
    {name = "Utils.GetConnectedUniverse", fn = function() return steamworks.utils.get_connected_universe() end},
    {name = "Utils.GetCurrentBatteryPower", fn = function() return steamworks.utils.get_current_battery_power() end},
    {name = "Utils.GetEnteredGamepadTextLength", fn = function() return steamworks.utils.get_entered_gamepad_text_length() end},
    {name = "Utils.GetIPCCallCount", fn = function() return steamworks.utils.get_ipc_call_count() end},
    {name = "Utils.GetIPCountry", fn = function() return steamworks.utils.get_ip_country() end},
    {name = "Utils.GetSecondsSinceAppActive", fn = function() return steamworks.utils.get_seconds_since_app_active() end},
    {name = "Utils.GetSecondsSinceComputerActive", fn = function() return steamworks.utils.get_seconds_since_computer_active() end},
    {name = "Utils.GetServerRealTime", fn = function() return steamworks.utils.get_server_real_time() end},
    {name = "Utils.GetSteamHardwareDefaultConfig", fn = function() return steamworks.utils.get_steam_hardware_default_config() end},
    {name = "Utils.GetSteamUILanguage", fn = function() return steamworks.utils.get_steam_ui_language() end},
    {name = "Utils.IsOverlayEnabled", fn = function() return steamworks.utils.is_overlay_enabled() end},
    {name = "Utils.IsRunningOnSteamHardware", fn = function() return steamworks.utils.is_running_on_steam_hardware() end},
    {name = "Utils.IsRunningUnderProton", fn = function() return steamworks.utils.is_running_under_proton() end},
    {name = "Utils.IsSteamChinaLauncher", fn = function() return steamworks.utils.is_steam_china_launcher() end},
    {name = "Utils.IsSteamInBigPictureMode", fn = function() return steamworks.utils.is_steam_in_big_picture_mode() end},
    {name = "Utils.IsSteamRunningInVR", fn = function() return steamworks.utils.is_steam_running_in_vr() end},
    {name = "Utils.IsVRHeadsetStreamingEnabled", fn = function() return steamworks.utils.is_vr_headset_streaming_enabled() end},
}

local options = parse_args(arg)

if not steamworks.is_steam_running() then
    io.stderr:write("Steam_IsSteamRunning returned false.\n")
    io.stderr:write("Start Steam, log in, then run this program again from the project root.\n")
    os.exit(1)
end

local ok, message = steamworks.init()
if not ok then
    io.stderr:write(message .. "\n")
    io.stderr:write("Make sure Steam is running and steam_appid.txt is in the working directory.\n")
    os.exit(1)
end

steamworks.run_callbacks()

local results = {}
local failed = 0
local limit = options.limit or #calls
if limit > #calls then
    limit = #calls
end

for index = 1, limit do
    local call = calls[index]
    local call_ok, value = pcall(call.fn)
    if call_ok then
        table.insert(results, {name = call.name, ok = true, value = short(value)})
        if not options.json then
            print(string.format("OK   %s: %s", call.name, short(value)))
        end
    else
        failed = failed + 1
        table.insert(results, {name = call.name, ok = false, error = tostring(value)})
        if not options.json then
            print(string.format("FAIL %s: %s", call.name, tostring(value)))
        end
    end
end

steamworks.shutdown()

if options.json then
    print_json(results, failed)
else
    print(string.format("\nLive smoke complete: %d/%d passed", #results - failed, #results))
end

if failed > 0 then
    os.exit(1)
end
