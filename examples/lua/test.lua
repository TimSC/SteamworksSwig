local steamworks = require("steamworks")

local function yes_no(value)
    if value then
        return "yes"
    end
    return "no"
end

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

print("Hello from Steamworks!")
print(string.format("App ID: %s", steamworks.utils.get_app_id()))
print(string.format("Logged on: %s", yes_no(steamworks.user.logged_on())))
print(string.format("Persona name: %s", steamworks.friends.get_persona_name()))
print(string.format("Steam ID: %s", steamworks.user.get_steam_id()))
print(string.format("Subscribed to app: %s", yes_no(steamworks.apps.is_subscribed())))

steamworks.shutdown()
