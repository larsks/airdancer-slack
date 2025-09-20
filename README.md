These are the Kubernetes manifests used to deploy the [airdancer-slack] application.

The deployment requires a secret named `airdancer-slack-config` that defines the following keys:

| Key                      | Description                                     |
| ------------------------ | ----------------------------------------------- |
| `DANCER_ADMIN_USER`      | Name of the initial admin user                  |
| `DANCER_MQTT_URL`        | `mqtt://` or `mqtts://` URL for the MQTT server |
| `DANCER_MQTT_USERNAME`   | Username for MQTT server                        |
| `DANCER_MQTT_PASSWORD`   | Password for MQTT server                        |
| `DANCER_SLACK_APP_TOKEN` | Slack app token                                 |
| `DANCER_SLACK_BOT_TOKEN` | Slack bot token                                 |

[airdancer-slack]: https://github.com/larsks/airdancer-slack
