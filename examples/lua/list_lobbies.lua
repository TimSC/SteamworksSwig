-- Query Steam lobbies using the generated Lua lobby call-result helper.

local steamworks = require("steamworks")

local function parse_args(args)
    local options = {
        max_results = 10,
        timeout = 10,
        skip_shutdown = false,
    }
    local index = 1
    while index <= #args do
        local arg_value = args[index]
        if arg_value == "--max-results" then
            index = index + 1
            options.max_results = tonumber(args[index])
            if options.max_results == nil then
                io.stderr:write("--max-results expects a number\n")
                os.exit(2)
            end
        elseif string.sub(arg_value, 1, 14) == "--max-results=" then
            options.max_results = tonumber(string.sub(arg_value, 15))
            if options.max_results == nil then
                io.stderr:write("--max-results expects a number\n")
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

local function pump_until(predicate, timeout_seconds)
    local deadline = os.time() + timeout_seconds
    while os.time() < deadline do
        steamworks.run_callbacks()
        if predicate() then
            return true
        end
        sleep_briefly()
    end
    return false
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

steamworks.matchmaking.add_request_lobby_list_result_count_filter(options.max_results)
steamworks.lobby.request_list()
if not pump_until(steamworks.lobby.is_list_complete, options.timeout) then
    io.stderr:write("Timed out waiting for lobby list.\n")
elseif steamworks.lobby.list_had_io_failure() then
    io.stderr:write("Lobby list request failed with an IO failure.\n")
else
    local count = math.floor(steamworks.lobby.list_result_count())
    print(string.format("Found %d lobbies", count))
    for index = 0, count - 1 do
        local lobby_id = steamworks.lobby.list_lobby_by_index(index)
        local lobby_name = steamworks.lobby.list_lobby_name_by_index(index)
        local members = steamworks.matchmaking.get_num_lobby_members(lobby_id)
        local member_limit = steamworks.matchmaking.get_lobby_member_limit(lobby_id)
        local owner_id = steamworks.matchmaking.get_lobby_owner(lobby_id)
        print(string.format(
            "%d: %s name=%q members=%s/%s owner=%s",
            index,
            tostring(lobby_id),
            lobby_name,
            tostring(members),
            tostring(member_limit),
            tostring(owner_id)
        ))
    end
    success = true
end

if not options.skip_shutdown then
    steamworks.shutdown()
end

if not success then
    os.exit(1)
end
