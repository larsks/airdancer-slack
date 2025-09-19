---
title: "Airdancer: The wacky waving notification system"
---

## Connecting to WiFi

When you first plug in your Airdancer switch, it will create a WiFi network named `airdancer-<something>-<something>`. Connect to this network, then point your browser at <http://192.168.4.1>. This will allow you to enter credentials for your WiFi network:

![Tasmota wifi configuration screen](/img/wifi-config.png)

Once you have saved your credentials, the switch will restart and register with the Airdancer server.

### Moving to another Wifi network

If you need to move the switch to another WiFi network, hold down the physical button on the switch for at least 40 seconds. When the blue LED lights up, the device has successfully reset and will once again present the `airdancer-<something>-<something>` network. At this point you can enter credentials for the new network by following the earlier instructions.

## Slack commands

### The bother command

To bother somebody:

```
/bother @username
```

This will (a) activate the recipients Airdancer for 15 seconds, and (b) send them a private message that says, "you have been bothered by @yourname". You can adjust the duration for which the Airdancer runs using the `--duration` (`-d`) flag:

```
/bother -d 5 @username
```

You can bother a group of people by using a group name instead of a user name:

```
/bother <groupname>
```

See below for how to get a list of groups.

### The dancer command

All other commands are accessed via the `/dancer` command:

```
/dancer users
/dancer set --no-bother
```

The following commands are available:

- `register <switch_id>` -- Register a switch to your account. If you have a [Tasmota] switch that has not been registered to someone else, you can register it to yourself. The `<switch_id>` value is the `topic` value shown in the MQTT configuration screen.
- `unregister` -- Unregister your switch. It will no longer be assigned to you and can them be registered to someone else.
- `bother [--duration <seconds>] <user_or_group>` -- Activate someone's switch; this is the same as the `/bother` command.
- `set --bother|--no-bother` -- Enable/disable bother notifications.
- `users [--box] [--short]` -- List all users. Use `--box` to get plain-text table, and `--short` to get even simpler plain-text output.
- `groups` - List all groups.

You can start a private chat with the Airdancer app; in this case, you don't need to use the `/dancer` command; you can just send the commands as regular messages.

## For more information

You can find more information, project source code, etc, in our GitHub repository, <https://github.com/larsks/airdancer-slack>.
