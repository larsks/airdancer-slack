# Airdancer Slack Bot

A Slack bot that enables users to send physical notifications by controlling remote [Tasmota] switches via MQTT. Users can "bother" others by activating their registered switches.

[tasmota]: https://tasmota.github.io/docs/

## Setup

1. Install dependencies: `uv sync`
2. Configure environment variables for Slack tokens and MQTT connection
3. Run: `uv run app.py`

One mechanism for managing environment variables is to put them into a `.env` file, and then reference that in the `uv run` command:

```
uv run --env-file .env app.py
```

### Required environment variables

Variables required to register a Slack application:

- `DANCER_SLACK_BOT_TOKEN`
- `DANCER_SLACK_APP_TOKEN`

Identify the initial admin user:

- `DANCER_ADMIN_USER`

Configure access to mqtt service:

- `DANCER_MQTT_URL` -- `mqtt://` or `mqtts://` url of the MQTT server
- `DANCER_MQTT_USERNAME`
- `DANCER_MQTT_PASSWORD`

## Documentation

See <https://airdancer.oddbit.com> for additional documentation.
