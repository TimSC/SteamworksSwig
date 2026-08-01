-- Exercise a low-impact Friends async API call from Lua.
--
-- This intentionally uses Friends.EnumerateFollowingList because it returns a
-- SteamAPICall_t without changing account, app, lobby, or file state. It is
-- useful for checking callback pumping and shutdown behavior.

local steamworks = require("steamworks")

local function parse_args(args)
    local options = {
        dispatch = "auto",
        start_index = 0,
        timeout = 10,
        skip_shutdown = false,
    }
    local index = 1
    while index <= #args do
        local arg_value = args[index]
        if arg_value == "--start-index" then
            index = index + 1
            options.start_index = tonumber(args[index])
            if options.start_index == nil then
                io.stderr:write("--start-index expects a number\n")
                os.exit(2)
            end
        elseif arg_value == "--dispatch" then
            index = index + 1
            options.dispatch = args[index]
            if options.dispatch ~= "auto" and options.dispatch ~= "manual" then
                io.stderr:write("--dispatch expects auto or manual\n")
                os.exit(2)
            end
        elseif string.sub(arg_value, 1, 11) == "--dispatch=" then
            options.dispatch = string.sub(arg_value, 12)
            if options.dispatch ~= "auto" and options.dispatch ~= "manual" then
                io.stderr:write("--dispatch expects auto or manual\n")
                os.exit(2)
            end
        elseif string.sub(arg_value, 1, 14) == "--start-index=" then
            options.start_index = tonumber(string.sub(arg_value, 15))
            if options.start_index == nil then
                io.stderr:write("--start-index expects a number\n")
                os.exit(2)
            end
        elseif arg_value == "--timeout" then
            index = index + 1
            options.timeout = tonumber(args[index])
            if options.timeout == nil then
                io.stderr:write("--timeout expects a number\n")
                os.exit(2)
            end
        elseif string.sub(arg_value, 1, 10) == "--timeout=" then
            options.timeout = tonumber(string.sub(arg_value, 11))
            if options.timeout == nil then
                io.stderr:write("--timeout expects a number\n")
                os.exit(2)
            end
        elseif arg_value == "--skip-shutdown" then
            options.skip_shutdown = true
        else
            io.stderr:write("Unknown argument: " .. arg_value .. "\n")
            os.exit(2)
        end
        index = index + 1
    end
    return options
end

local function sleep_briefly()
    local deadline = os.clock() + 0.05
    while os.clock() < deadline do
    end
end

local function parse_payload(data)
    local fields = {}
    if data == nil then
        return fields
    end
    for part in string.gmatch(data, "[^\t]+") do
        local key, value = string.match(part, "^([^=]+)=(.*)$")
        if key ~= nil then
            fields[key] = value
        end
    end
    return fields
end

local function wait_for_api_call(api_call, timeout_seconds)
    local deadline = os.clock() + timeout_seconds
    while os.clock() < deadline do
        steamworks.run_callbacks()
        local payload = steamworks.utils.is_api_call_completed_string(api_call)
        if payload ~= nil and payload ~= "" then
            return true, parse_payload(payload), payload
        end
        sleep_briefly()
    end
    return false, {}, ""
end

local function wait_for_manual_api_call(api_call, timeout_seconds)
    local deadline = os.clock() + timeout_seconds
    while os.clock() < deadline do
        local callback = steamworks.poll_callback()
        if callback ~= nil
            and callback.api_call_completed
            and callback.completed_api_call == api_call
        then
            return true, callback
        end
        sleep_briefly()
    end
    return false, nil
end

local options = parse_args(arg)

if not steamworks.is_steam_running() then
    io.stderr:write("Steam is not running.\n")
    os.exit(1)
end

local ok, message = steamworks.init()
if not ok then
    io.stderr:write(message .. "\n")
    os.exit(1)
end

local success = false

if options.dispatch == "manual" then
    steamworks.manual_dispatch_init()
end

local api_call = steamworks.friends.enumerate_following_list(options.start_index)
print(string.format("Friends.EnumerateFollowingList call: %s", tostring(api_call)))

if api_call == nil or api_call == 0 then
    io.stderr:write("Friends.EnumerateFollowingList returned an invalid SteamAPICall_t.\n")
elseif options.dispatch == "manual" then
    local completed, callback = wait_for_manual_api_call(api_call, options.timeout)
    if not completed then
        io.stderr:write("Timed out waiting for Friends.EnumerateFollowingList.\n")
    else
        print("Completed: yes")
        print(string.format("Callback ID: %s", tostring(callback.completed_callback_id)))
        print(string.format("Failed: %s", tostring(callback.api_call_result_failed)))
        success = true
    end
else
    local completed, fields, payload = wait_for_api_call(api_call, options.timeout)
    if not completed then
        io.stderr:write("Timed out waiting for Friends.EnumerateFollowingList.\n")
    else
        print("Completed: yes")
        print(string.format("Failed: %s", tostring(fields.failed or "unknown")))
        if payload ~= "" then
            print("Completion payload: " .. payload)
        end
        success = true
    end
end

if not options.skip_shutdown then
    if options.dispatch == "manual" then
        steamworks.shutdown_manual_dispatch()
    else
        steamworks.shutdown()
    end
end

if not success then
    os.exit(1)
end
