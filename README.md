# Airdancer Slack Bot

A Slack bot that enables users to send physical notifications by controlling remote Tasmota switches via MQTT. Users can "bother" others by activating their registered switches.

## Setup

1. Install dependencies: `uv sync`
2. Configure environment variables for Slack tokens and MQTT connection
3. Run: `uv run app.py`

One mechanism for managing environment variables is to put them into a `.env` file, and then reference that in the `uv run` command:

```
uv run --env-file .env app.py
```

## Commands

From any channel, you can run these commands by prefixing them with `/dancer`:

```
/dancer users
```

You can also start a private message with the Airdancer app; in this case, you don't need the `/dancer` prefix to run the commands:

```
users
```

### User Commands

- `register <switch_id>` - Register a Tasmota switch to your account
- `bother [--duration <seconds>] <user_or_group>` - Activate someone's switch (default: 15 seconds)
- `set --bother|--no-bother` - Enable/disable bother notifications for your account
- `users` - List all registered users
- `groups` - List all available groups
- `help` - Show command help

### Admin Commands

**User Management:**
- `user list` - List all users
- `user show <user>` - Show user details
- `user set <user> [--admin|--no-admin] [--bother|--no-bother]` - Configure user settings
- `user register <user> <switch_id>` - Register a switch to a specific user
- `unregister <user>` - Remove a user's switch registration

**Switch Management:**
- `switch list` - List all discovered switches with status
- `switch show <switch_id>` - Show detailed switch information
- `switch on|off|toggle <switch_id>` - Control switch power state

**Group Management:**
- `group list` - List all groups with member counts
- `group show <name>` - Show group members
- `group create <name>` - Create a new group
- `group destroy <name>` - Delete a group
- `group add <name> <user1> [user2...]` - Add users to a group
- `group remove <name> <user1> [user2...]` - Remove users from a group

## Examples

```
/dancer register tasmota_12345
/dancer bother @username
/dancer bother --duration 30 mygroup
/dancer switch toggle tasmota_12345
/dancer group add engineering @alice @bob
```
