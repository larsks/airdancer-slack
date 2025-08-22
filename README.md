This app allows slack users to send physical notifications to other users by activating remote switches running the Tasmota firmware. These switches can be controlled using an MQTT API.

## MQTT API

Each switch can be addressed by sending messages to topic `cmnd/<switch>/<command>`, where `<switch>` is a unique identifier for the switch.

We will make use of the following commands:

- `Power` -- turn the switch on and off. The message should be `ON`, `OFF`, or `TOGGLE`. If the message is empty, the response will contain the current power state.
- `TimedPower1` -- turn the switch on for a specific duration. The message is the duration in milliseconds.

Each command sent to a remote switch will result in a message from the switch to the topic `stat/<switch>/RESULT`, containing a JSON document showing the change.

Changes in power state will also generate a message to `stat/<switch>/POWER`, where the message will be `ON` or `OFF`.

### Discovery

We can automatically discover switches by listening to the `tasmota/discovery/#` topic. Messages on this topic are a JSON document; we are interested in the `t` key which contains the switch id. An example discovery message:

```
{"ip":"10.42.0.214","dn":"Tasmota","fn":["Tasmota",null,null,null,null,null,null,null],"hn":"tasmota-28D42B-5163","mac":"483FDA28D42B","md":"Sonoff Basic","ty":0,"if":0,"cam":0,"ofln":"Offline","onln":"Online","state":["OFF","ON","TOGGLE","HOLD"],"sw":"15.0.1.3","t":"tasmota_28D42B","ft":"%prefix%/%topic%/","tp":["cmnd","stat","tele"],"rl":[1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],"swc":[-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1],"swn":[null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null],"btn":[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],"so":{"4":0,"11":0,"13":0,"17":0,"20":0,"30":0,"68":0,"73":0,"82":0,"114":0,"117":0},"lk":0,"lt_st":0,"bat":0,"dslp":0,"sho":[],"sht":[],"ver":1}
```

If we saw the above message, we would discover a switch with the identifier `tasmota_28D42B`.

We also want to monitor the topic `tele/<switch>/LWT`; the message `Offline` means that a switch is no longer available, while `Online` means that a switch has come online.

## Commands

## User commands

These commands can be executed by any authorized user.

- `/dancer register <switch>` -- register Tasmota switch `<switch>` to current user
- `/dancer bother [--duration <n>] (<user>|<group>)` -- activate switch for user or group (for `<n>` seconds, default 15)
- `/dancer users` -- list registered users
- `/dancer groups` -- list registered users

### Admin commands

These commands require administrative privileges.

- `/dancer register <switch> <user>` -- register Tasmota switch `<switch>` to `<user>`
- `/dancer unregister <user>` -- remove switch registration for `<user>`
- `/dancer switch list` -- list discovered switches
- `/dancer user list` -- list known users
- `/dancer user show <user>` -- show details for `<user>`
- `/dancer user set <user> [+admin|-admin]` -- grant or revoke admin privileges for `<user>`
- `/dancer group list` -- list groups
- `/dancer group show <name>` -- show members of group `<name>`
- `/dancer group create <name>` -- create group named `<name>`
- `/dancer group destroy <name>` -- destroy group named `<name>`
- `/dancer group add <name> <user> [<user> [...]]` -- add users to group `<name>`
- `/dancer group remove <name> <user> [<user> [...]]` -- remove users from group `<name>`
