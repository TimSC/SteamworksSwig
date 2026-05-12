# Interactive Demo

`interactive.py` is an interactive lobby/P2P demo that keeps Steam callbacks
running while a background thread waits for console commands.

```bash
python3 interactive.py
```

## Host

Start or stop a standalone P2P listen socket:

```text
host start
host stop
```

## Lobby And Hosting

On one Steam account, create and host a lobby:

```text
lobby create TestLobby public 4
```

If players are already in a lobby and the lobby owner wants to begin hosting
later, run:

```text
lobby host start
```

On another Steam account for the same AppID, list and join it:

```text
lobby list
lobby join 0
client send hello
```

The lobby stores `host_steam_id` and `virtual_port` metadata. Joining a lobby
automatically opens a Steam Networking Sockets P2P connection to the advertised
host.

Useful lobby inspection and configuration commands:

```text
lobby data list
lobby data get map
lobby data set map arena01
lobby data delete map
lobby type friends
lobby joinable true
lobby owner
lobby owner set 1
```

## Players

On the host, list connected P2P players:

```text
client players
```

This reports actual `ISteamNetworkingSockets` peers, not just lobby members.
Connection diagnostics are also available:

```text
client detail
client detail 123
client name 123 host-peer
client flush
client flush 123
```

## Friends And Invites

To invite a friend from the lobby owner/client:

```text
friends
lobby invite 0
```

`friends` lists online friends with indexes. `lobby invite` accepts either a
listed friend index or a SteamID64.

Inspect a friend's rich presence:

```text
friend rich 0
friend rich 7656119...
```

## Rich Presence

Rich presence can be advertised independently of lobby/server state:

```text
presence "In menu"
presence-key mode browsing
presence connect
presence auto
presence show
presence clear
```

The `presence connect` command uses the current SteamID, virtual port, and lobby
ID when available. You can also pass an explicit connect string:

```text
presence connect "steamid=7656119...;port=0"
```
