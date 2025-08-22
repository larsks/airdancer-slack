import os
import json
import logging
import re
from datetime import datetime
from typing import TypedDict
from urllib.parse import urlparse

import paho.mqtt.client as mqtt
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from pony.orm import (
    Database,
    Required,
    Optional,
    Set as PonySet,
    db_session,
)

logging.basicConfig(level=logging.DEBUG if os.environ.get("DEBUG") else logging.INFO)
logger = logging.getLogger(__name__)


# Type definitions for database objects
class UserDict(TypedDict):
    slack_user_id: str
    username: str
    is_admin: bool
    switch_id: str
    created_at: str


class SwitchDict(TypedDict):
    switch_id: str
    status: str
    power_state: str
    last_seen: str
    device_info: str


class OwnerDict(TypedDict):
    slack_user_id: str
    username: str
    is_admin: bool


class SwitchWithOwnerDict(TypedDict):
    switch_id: str
    status: str
    power_state: str
    last_seen: str
    device_info: str
    owner: OwnerDict | None


# Initialize PonyORM database
db = Database()


class User(db.Entity):
    slack_user_id = Required(str, unique=True)
    username = Required(str)
    is_admin = Required(bool, default=False)
    switch_id = Optional(str)
    created_at = Required(datetime, default=datetime.now)
    groups = PonySet("GroupMember")


class Switch(db.Entity):
    switch_id = Required(str, unique=True)
    status = Required(str, default="offline")
    power_state = Required(str, default="unknown")
    last_seen = Required(datetime, default=datetime.now)
    device_info = Optional(str)


class Group(db.Entity):
    group_name = Required(str, unique=True)
    created_at = Required(datetime, default=datetime.now)
    members = PonySet("GroupMember")


class GroupMember(db.Entity):
    group = Required(Group)
    user = Required(User)


class DatabaseManager:
    def __init__(self, db_path: str = "airdancer.db"):
        db.bind("sqlite", db_path)
        db.generate_mapping(create_tables=True)

    @db_session
    def add_user(
        self, slack_user_id: str, username: str, is_admin: bool = False
    ) -> bool:
        try:
            user = User.get(slack_user_id=slack_user_id)
            if user:
                user.username = username
                user.is_admin = is_admin
            else:
                User(slack_user_id=slack_user_id, username=username, is_admin=is_admin)
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False

    @db_session
    def get_user(self, slack_user_id: str) -> UserDict | None:
        user = User.get(slack_user_id=slack_user_id)
        if user:
            return {
                "slack_user_id": user.slack_user_id,
                "username": user.username,
                "is_admin": user.is_admin,
                "switch_id": user.switch_id,
                "created_at": user.created_at.isoformat(),
            }
        return None

    def is_admin(self, slack_user_id: str) -> bool:
        user = self.get_user(slack_user_id)
        return bool(user and user["is_admin"])

    @db_session
    def set_admin(self, slack_user_id: str, is_admin: bool) -> bool:
        try:
            user = User.get(slack_user_id=slack_user_id)
            if user:
                user.is_admin = is_admin
                return True
            return False
        except Exception as e:
            logger.error(f"Error setting admin status: {e}")
            return False

    @db_session
    def register_switch(self, slack_user_id: str, switch_id: str) -> bool:
        try:
            user = User.get(slack_user_id=slack_user_id)
            if user:
                user.switch_id = switch_id
                return True
            return False
        except Exception as e:
            logger.error(f"Error registering switch: {e}")
            return False

    @db_session
    def unregister_user(self, slack_user_id: str) -> bool:
        try:
            user = User.get(slack_user_id=slack_user_id)
            if user:
                user.delete()
                return True
            return False
        except Exception as e:
            logger.error(f"Error unregistering user: {e}")
            return False

    @db_session
    def add_switch(self, switch_id: str, device_info: str = "") -> bool:
        try:
            switch = Switch.get(switch_id=switch_id)
            if switch:
                switch.status = "online"
                switch.device_info = device_info
                switch.last_seen = datetime.now()
            else:
                Switch(switch_id=switch_id, status="online", device_info=device_info)
            return True
        except Exception as e:
            logger.error(f"Error adding switch: {e}")
            return False

    @db_session
    def update_switch_status(self, switch_id: str, status: str) -> bool:
        try:
            switch = Switch.get(switch_id=switch_id)
            if switch:
                switch.status = status
                switch.last_seen = datetime.now()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating switch status: {e}")
            return False

    @db_session
    def update_switch_power_state(self, switch_id: str, power_state: str) -> bool:
        try:
            switch = Switch.get(switch_id=switch_id)
            if switch:
                switch.power_state = power_state
                switch.last_seen = datetime.now()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating switch power state: {e}")
            return False

    @db_session
    def get_all_switches(self) -> list[SwitchDict]:
        switches = list(Switch.select())
        return [
            {
                "switch_id": switch.switch_id,
                "status": switch.status,
                "power_state": switch.power_state,
                "last_seen": switch.last_seen.isoformat(),
                "device_info": switch.device_info,
            }
            for switch in switches
        ]

    @db_session
    def get_all_switches_with_owners(self) -> list[SwitchWithOwnerDict]:
        """Get all switches with their owner information using a join"""
        # Get all switches with left join to users
        query = """
        SELECT s.switch_id, s.status, s.power_state, s.last_seen, s.device_info,
               u.slack_user_id, u.username, u.is_admin
        FROM switch s
        LEFT JOIN user u ON s.switch_id = u.switch_id
        ORDER BY s.switch_id
        """

        results = []
        for row in db.execute(query):
            switch_data = {
                "switch_id": row[0],
                "status": row[1],
                "power_state": row[2],
                "last_seen": row[3],
                "device_info": row[4],
                "owner": None,
            }

            # If there's an owner (user data is not null)
            if row[5]:  # slack_user_id is not None
                switch_data["owner"] = {
                    "slack_user_id": row[5],
                    "username": row[6],
                    "is_admin": bool(row[7]),
                }

            results.append(switch_data)

        return results

    @db_session
    def get_all_users(self) -> list[UserDict]:
        users = list(User.select())
        return [
            {
                "slack_user_id": user.slack_user_id,
                "username": user.username,
                "is_admin": user.is_admin,
                "switch_id": user.switch_id,
                "created_at": user.created_at.isoformat(),
            }
            for user in users
        ]

    @db_session
    def create_group(self, group_name: str) -> bool:
        try:
            if not Group.get(group_name=group_name):
                Group(group_name=group_name)
                return True
            return False
        except Exception as e:
            logger.error(f"Error creating group: {e}")
            return False

    @db_session
    def delete_group(self, group_name: str) -> bool:
        try:
            group = Group.get(group_name=group_name)
            if group:
                group.delete()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting group: {e}")
            return False

    @db_session
    def add_user_to_group(self, group_name: str, slack_user_id: str) -> bool:
        try:
            group = Group.get(group_name=group_name)
            user = User.get(slack_user_id=slack_user_id)
            if group and user:
                # Check if membership already exists
                existing = GroupMember.get(group=group, user=user)
                if not existing:
                    GroupMember(group=group, user=user)
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding user to group: {e}")
            return False

    @db_session
    def remove_user_from_group(self, group_name: str, slack_user_id: str) -> bool:
        try:
            group = Group.get(group_name=group_name)
            user = User.get(slack_user_id=slack_user_id)
            if group and user:
                membership = GroupMember.get(group=group, user=user)
                if membership:
                    membership.delete()
                    return True
            return False
        except Exception as e:
            logger.error(f"Error removing user from group: {e}")
            return False

    def get_group_members(self, group_name: str) -> list[str]:
        # Handle special 'all' group
        if group_name.lower() == "all":
            return [
                user["slack_user_id"]
                for user in self.get_all_users()
                if user["switch_id"] and user["switch_id"].strip()
            ]

        with db_session:
            group = Group.get(group_name=group_name)
            if group:
                return [member.user.slack_user_id for member in group.members]
            return []

    @db_session
    def get_all_groups(self) -> list[str]:
        groups = [group.group_name for group in list(Group.select())]

        # Always include the special 'all' group
        if "all" not in [g.lower() for g in groups]:
            groups.append("all")

        return groups

    @db_session
    def get_switch_owner(self, switch_id: str) -> OwnerDict | None:
        """Get the user who owns the specified switch"""
        user = User.get(switch_id=switch_id)
        if user:
            return {
                "slack_user_id": user.slack_user_id,
                "username": user.username,
                "is_admin": user.is_admin,
            }
        return None


class MQTTManager:
    def __init__(self, database: DatabaseManager):
        self.database = database
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.discovered_switches: set[str] = set()

        # MQTT configuration from environment variables
        self.mqtt_host = "localhost"
        self.mqtt_port = 1883
        self.mqtt_username = None
        self.mqtt_password = None
        self.use_tls = False

        # Parse DANCER_MQTT_URL if provided
        mqtt_url = os.environ.get("DANCER_MQTT_URL")
        if mqtt_url:
            parsed = urlparse(mqtt_url)
            self.mqtt_host = parsed.hostname or "localhost"

            # Set default port and TLS based on scheme
            if parsed.port:
                self.mqtt_port = parsed.port
            elif parsed.scheme == "mqtts":
                self.mqtt_port = 8883
                self.use_tls = True
            else:
                self.mqtt_port = 1883
                self.use_tls = False

            # Enable TLS for mqtts:// even if port is explicitly specified
            if parsed.scheme == "mqtts":
                self.use_tls = True

            if parsed.username:
                self.mqtt_username = parsed.username
            if parsed.password:
                self.mqtt_password = parsed.password

        # Override with separate username/password if provided
        if os.environ.get("DANCER_MQTT_USERNAME"):
            self.mqtt_username = os.environ.get("DANCER_MQTT_USERNAME")
        if os.environ.get("DANCER_MQTT_PASSWORD"):
            self.mqtt_password = os.environ.get("DANCER_MQTT_PASSWORD")

        if self.mqtt_username:
            self.client.username_pw_set(self.mqtt_username, self.mqtt_password)

        if self.use_tls:
            self.client.tls_set()

    def start(self):
        protocol = "mqtts" if self.use_tls else "mqtt"
        logger.info(
            f"Attempting to connect to MQTT broker at {protocol}://{self.mqtt_host}:{self.mqtt_port}"
        )
        if self.use_tls:
            logger.info("Using TLS/SSL encryption")
        if self.mqtt_username:
            logger.info(
                f"Using MQTT authentication with username: {self.mqtt_username}"
            )
        try:
            self.client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.client.loop_start()
            logger.info(
                f"Successfully connected to MQTT broker at {protocol}://{self.mqtt_host}:{self.mqtt_port}"
            )
        except Exception as e:
            logger.error(
                f"Failed to connect to MQTT broker at {protocol}://{self.mqtt_host}:{self.mqtt_port}: {e}"
            )

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            logger.info("MQTT client successfully connected to broker")
            logger.info("Subscribing to Tasmota discovery topic: tasmota/discovery/#")
            client.subscribe("tasmota/discovery/#")
            logger.info(
                "Subscribing to switch LWT (Last Will and Testament) topics: tele/+/LWT"
            )
            client.subscribe("tele/+/LWT")
            logger.info("Subscribing to switch power state topics: stat/+/POWER")
            client.subscribe("stat/+/POWER")
            logger.info("MQTT subscriptions completed, ready to discover switches")

            # Query power state for any switches with unknown state
            self.query_unknown_power_states()
        else:
            logger.error(f"MQTT connection failed with reason code: {reason_code}")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode()

            if topic.startswith("tasmota/discovery/"):
                self.handle_discovery(payload)
            elif topic.endswith("/LWT"):
                switch_id = topic.split("/")[1]
                status = "online" if payload == "Online" else "offline"
                self.database.update_switch_status(switch_id, status)
                logger.info(f"Switch {switch_id} is now {status}")
            elif topic.startswith("stat/") and topic.endswith("/POWER"):
                switch_id = topic.split("/")[1]
                power_state = payload.upper()  # Should be "ON" or "OFF"
                self.database.update_switch_power_state(switch_id, power_state)
                logger.info(f"Switch {switch_id} power state: {power_state}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def handle_discovery(self, payload: str):
        try:
            logger.debug(f"Processing discovery message: {payload}")
            data = json.loads(payload)
            switch_id = data.get("t")
            if switch_id and switch_id not in self.discovered_switches:
                self.discovered_switches.add(switch_id)
                device_info = {
                    "ip": data.get("ip"),
                    "hostname": data.get("hn"),
                    "mac": data.get("mac"),
                    "model": data.get("md"),
                    "software": data.get("sw"),
                }
                self.database.add_switch(switch_id, json.dumps(device_info))
                logger.info(f"🔌 Discovered new Tasmota switch: {switch_id}")
                logger.info(f"   └─ IP: {device_info.get('ip', 'unknown')}")
                logger.info(f"   └─ Model: {device_info.get('model', 'unknown')}")
                logger.info(f"   └─ Hostname: {device_info.get('hostname', 'unknown')}")
                logger.info(f"   └─ MAC: {device_info.get('mac', 'unknown')}")
                logger.info(f"   └─ Software: {device_info.get('software', 'unknown')}")

                # Query power state for newly discovered switch
                logger.info(f"   └─ Querying power state for {switch_id}")
                self.query_power_state(switch_id)
            elif switch_id:
                logger.debug(f"Switch {switch_id} already discovered, ignoring")
        except Exception as e:
            logger.error(f"Error handling discovery message: {e}")
            logger.error(f"Problematic payload: {payload}")

    def send_command(self, switch_id: str, command: str, value: str = ""):
        topic = f"cmnd/{switch_id}/{command}"
        try:
            self.client.publish(topic, value)
            logger.info(
                f"Sent command {command} with value '{value}' to switch {switch_id}"
            )
            return True
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return False

    def bother_switch(self, switch_id: str, duration: int = 15000):
        # Use TimedPower1 to turn on for specified duration
        return self.send_command(
            switch_id, "TimedPower1", str(duration * 1000)
        )  # Convert to milliseconds

    def switch_on(self, switch_id: str) -> bool:
        """Turn switch on"""
        return self.send_command(switch_id, "Power1", "ON")

    def switch_off(self, switch_id: str) -> bool:
        """Turn switch off"""
        return self.send_command(switch_id, "Power1", "OFF")

    def switch_toggle(self, switch_id: str) -> bool:
        """Toggle switch state"""
        return self.send_command(switch_id, "Power1", "TOGGLE")

    def query_power_state(self, switch_id: str) -> bool:
        """Query current power state of switch"""
        return self.send_command(switch_id, "Power", "")

    def query_unknown_power_states(self):
        """Query power state for all switches with unknown power state"""
        switches = self.database.get_all_switches()
        unknown_switches = [s for s in switches if s["power_state"] == "unknown"]

        if unknown_switches:
            logger.info(
                f"Querying power state for {len(unknown_switches)} switches with unknown state"
            )
            for switch in unknown_switches:
                switch_id = switch["switch_id"]
                logger.info(f"   └─ Querying power state for {switch_id}")
                self.query_power_state(switch_id)


class AirdancerApp:
    def __init__(self):
        logger.info("🚀 Initializing Airdancer Slack App")
        self.database = DatabaseManager()
        logger.info("📄 Database initialized")
        self.mqtt_manager = MQTTManager(self.database)
        logger.info("📡 MQTT manager initialized")
        self.app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
        logger.info("💬 Slack app initialized")
        self.setup_commands()
        logger.info("⚙️  Slash commands configured")

        # Set up initial admin user if specified
        self.initial_admin_identifier = os.environ.get("DANCER_ADMIN_USER")
        if self.initial_admin_identifier:
            logger.info(f"👑 Admin user configured: {self.initial_admin_identifier}")
        else:
            logger.warning("⚠️  No admin user configured (DANCER_ADMIN_USER not set)")

    def ensure_admin_user(self, user_id: str, username: str) -> None:
        """Check if this user should be made admin based on DANCER_ADMIN_USER setting"""
        if not self.initial_admin_identifier:
            return

        logger.debug(
            f"Checking admin status for user_id='{user_id}', username='{username}'"
        )
        logger.debug(f"DANCER_ADMIN_USER is set to: '{self.initial_admin_identifier}'")

        # Check if this user matches the admin identifier (by username or user ID)
        username_match = self.initial_admin_identifier == username
        user_id_match = self.initial_admin_identifier == user_id

        logger.debug(
            f"Username match: {username_match}, User ID match: {user_id_match}"
        )

        if username_match or user_id_match:
            # Get or create user and ensure they have admin privileges
            user = self.database.get_user(user_id)
            if not user:
                self.database.add_user(user_id, username, True)
                logger.info(f"✅ Created admin user: {username} ({user_id})")
            elif not user["is_admin"]:
                self.database.set_admin(user_id, True)
                logger.info(f"✅ Granted admin privileges to: {username} ({user_id})")
            else:
                logger.debug(
                    f"User {username} ({user_id}) already has admin privileges"
                )

    def setup_commands(self):
        @self.app.command("/dancer")
        def handle_dancer_command(ack, respond, command, client):
            ack()

            user_id = command["user_id"]
            text = command["text"].strip()
            args = text.split() if text else []

            if not args:
                respond(
                    "Please specify a command. Use `/dancer help` for available commands."
                )
                return

            cmd = args[0].lower()

            # Ensure user exists in database
            try:
                user_info = client.users_info(user=user_id)
                username = user_info["user"]["name"]
                if not self.database.get_user(user_id):
                    self.database.add_user(user_id, username)

                # Check if this user should be made admin
                self.ensure_admin_user(user_id, username)
            except Exception as e:
                logger.error(f"Error getting user info: {e}")
                username = "Unknown"

            if cmd == "help":
                self.handle_help(respond, user_id)
            elif cmd == "register":
                self.handle_register(respond, user_id, args[1:], client)
            elif cmd == "unregister":
                self.handle_unregister(respond, user_id, args[1:], client)
            elif cmd == "bother":
                self.handle_bother(respond, user_id, args[1:], client)
            elif cmd == "users":
                self.handle_list_users(respond, user_id)
            elif cmd == "groups":
                self.handle_list_groups(respond, user_id)
            elif cmd == "switch":
                self.handle_switch_commands(respond, user_id, args[1:])
            elif cmd == "user":
                self.handle_user_commands(respond, user_id, args[1:], client)
            elif cmd == "group":
                self.handle_group_commands(respond, user_id, args[1:], client)
            else:
                respond(
                    f"Unknown command: {cmd}. Use `/dancer help` for available commands."
                )

        # Handle direct messages and app mentions
        @self.app.message("")
        def handle_message(message, say, client):
            # Skip if it's a bot message, empty, or other subtypes we don't handle
            subtype = message.get("subtype")
            if subtype in ["bot_message", "message_changed", "message_deleted"]:
                return

            # Only respond to direct messages or app mentions
            channel_type = message.get("channel_type")
            text = message.get("text", "").strip()
            user_id = message.get("user")

            # Skip if no user or empty text
            if not user_id or not text:
                return

            # Only respond to DMs or app mentions
            is_dm = channel_type == "im"

            # For DMs, no need to check or remove mentions
            if is_dm:
                # In DMs, process the text as-is
                pass
            else:
                # In channels, check for app mentions and remove only the bot mention
                mentions = re.findall(r"<@[UW][A-Z0-9]+>", text)
                is_mention = len(mentions) > 0

                if not is_mention:
                    return

                # Try to get the bot's user ID to remove only the bot mention
                try:
                    auth_response = client.auth_test()
                    bot_user_id = auth_response["user_id"]
                    bot_mention = f"<@{bot_user_id}>"
                    if bot_mention in text:
                        text = text.replace(bot_mention, "").strip()
                except Exception:
                    # Fallback: remove the first mention (likely the bot)
                    if mentions:
                        text = text.replace(mentions[0], "").strip()

            # Parse the command
            self.handle_dm_command(text, user_id, say, client)

        # Handle other message events gracefully
        @self.app.event("message")
        def handle_message_events(body, logger):
            # This catches any message events not handled by the specific message handler above
            event = body.get("event", {})
            subtype = event.get("subtype")
            if subtype:
                logger.debug(f"Ignoring message event with subtype: {subtype}")
            # No response needed - just prevent "unhandled request" warnings

        # Handle toggle button actions
        @self.app.action(re.compile(r"toggle_switch_.*"))
        def handle_toggle_switch(ack, body, client):
            ack()

            user_id = body["user"]["id"]
            action = body["actions"][0]
            switch_id = action["value"]

            logger.info(f"Toggle button pressed by {user_id} for switch {switch_id}")

            # Check if user is admin (only admins can toggle switches)
            if not self.database.is_admin(user_id):
                try:
                    client.chat_postEphemeral(
                        channel=body["channel"]["id"],
                        user=user_id,
                        text="❌ Only administrators can toggle switches.",
                    )
                except Exception as e:
                    logger.error(f"Error sending ephemeral message: {e}")
                return

            # Send toggle command
            success = self.mqtt_manager.send_command(switch_id, "Power", "toggle")

            # Send response
            try:
                if success:
                    client.chat_postEphemeral(
                        channel=body["channel"]["id"],
                        user=user_id,
                        text=f"✅ Toggle command sent to switch `{switch_id}`",
                    )
                else:
                    client.chat_postEphemeral(
                        channel=body["channel"]["id"],
                        user=user_id,
                        text=f"❌ Failed to send toggle command to switch `{switch_id}`",
                    )
            except Exception as e:
                logger.error(f"Error sending toggle response: {e}")

    def handle_dm_command(self, text: str, user_id: str, say, client):
        """Handle direct message commands"""
        args = text.split() if text else []

        if not args:
            say("Please specify a command. Use `help` for available commands.")
            return

        cmd = args[0].lower()

        # Create a response function that uses say instead of respond
        def dm_respond(message):
            say(message)

        # Ensure user exists in database
        try:
            user_info = client.users_info(user=user_id)
            username = user_info["user"]["name"]
            if not self.database.get_user(user_id):
                self.database.add_user(user_id, username)

            # Check if this user should be made admin
            self.ensure_admin_user(user_id, username)
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            username = "Unknown"

        # Route to existing command handlers
        if cmd == "help":
            self.handle_help(dm_respond, user_id)
        elif cmd == "register":
            self.handle_register(dm_respond, user_id, args[1:], client)
        elif cmd == "unregister":
            self.handle_unregister(dm_respond, user_id, args[1:], client)
        elif cmd == "bother":
            self.handle_bother(dm_respond, user_id, args[1:], client)
        elif cmd == "users":
            self.handle_list_users(dm_respond, user_id)
        elif cmd == "groups":
            self.handle_list_groups(dm_respond, user_id)
        elif cmd == "switch":
            self.handle_switch_commands(dm_respond, user_id, args[1:])
        elif cmd == "user":
            self.handle_user_commands(dm_respond, user_id, args[1:], client)
        elif cmd == "group":
            self.handle_group_commands(dm_respond, user_id, args[1:], client)
        else:
            dm_respond(f"Unknown command: {cmd}. Use `help` for available commands.")

    def handle_help(self, respond, user_id):
        is_admin = self.database.is_admin(user_id)

        help_text = """
*User Commands:*
• `register <switch>` - register a Tasmota switch to your user
• `bother [--duration <n>] (<user>|<group>)` - activate switch for user or group (default 15 seconds)
• `users` - list registered users
• `groups` - list available groups
• Use `all` to bother all users with registered switches

*Note:* Commands work via `/dancer` slash commands or direct messages to this bot.
"""

        if is_admin:
            help_text += """
*Admin Commands:*
• `register <switch> <user>` - register switch to specific user
• `unregister <user>` - remove switch registration for user
• `switch list` - list discovered switches
• `switch on <switch>` - turn switch on
• `switch off <switch>` - turn switch off
• `switch toggle <switch>` - toggle switch state
• `user list` - list all users
• `user show <user>` - show details for user
• `user set <user> [+admin|-admin]` - grant/revoke admin privileges
• `group list` - list all groups
• `group show <name>` - show group members
• `group create <name>` - create new group
• `group destroy <name>` - delete group
• `group add <name> <user> [<user> ...]` - add users to group
• `group remove <name> <user> [<user> ...]` - remove users from group
"""

        respond(help_text)

    def handle_register(self, respond, user_id, args, client):
        if len(args) == 1:
            # User registering themselves
            switch_id = self.clean_switch_id(args[0])
            if self.database.register_switch(user_id, switch_id):
                respond(
                    f"Successfully registered switch `{switch_id}` to your account."
                )
            else:
                respond("Failed to register switch. Make sure you have an account.")
        elif len(args) == 2 and self.database.is_admin(user_id):
            # Admin registering switch to another user
            switch_id, target_user = args
            switch_id = self.clean_switch_id(switch_id)
            target_user_id = self.resolve_user_identifier(target_user, client)

            if not target_user_id:
                respond(f"Could not find user {target_user}")
                return

            # Ensure target user exists in database
            try:
                user_info = client.users_info(user=target_user_id)
                username = user_info["user"]["name"]
                if not self.database.get_user(target_user_id):
                    self.database.add_user(target_user_id, username)
            except Exception:
                respond(f"Could not find user {target_user}")
                return

            if self.database.register_switch(target_user_id, switch_id):
                respond(
                    f"Successfully registered switch `{switch_id}` to <@{target_user_id}>."
                )
            else:
                respond("Failed to register switch.")
        else:
            respond(
                "Usage: `/dancer register <switch>` or `/dancer register <switch> <user>` (admin only)"
            )

    def handle_unregister(self, respond, user_id, args, client):
        if not self.database.is_admin(user_id):
            respond("Only administrators can unregister users.")
            return

        if len(args) != 1:
            respond("Usage: `/dancer unregister <user>`")
            return

        target_user = args[0]
        target_user_id = self.resolve_user_identifier(target_user, client)

        if not target_user_id:
            respond(f"Could not find user {target_user}")
            return

        if self.database.unregister_user(target_user_id):
            respond(f"Successfully unregistered <@{target_user_id}>.")
        else:
            respond("Failed to unregister user or user not found.")

    def handle_bother(self, respond, user_id, args, client):
        duration = 15  # default duration in seconds
        target = None

        # Parse arguments
        i = 0
        while i < len(args):
            if args[i] == "--duration" and i + 1 < len(args):
                try:
                    duration = int(args[i + 1])
                    i += 2
                except ValueError:
                    respond("Invalid duration value.")
                    return
            else:
                target = args[i]
                break

        if not target:
            respond("Usage: `/dancer bother [--duration <n>] (<user>|<group>)`")
            return

        # First check if target is a group name
        available_groups = self.database.get_all_groups()
        if target.lower() in [g.lower() for g in available_groups]:
            # Group target
            members = self.database.get_group_members(target)
            if not members:
                if target.lower() == "all":
                    respond(
                        f"Group `{target}` has no members (no users have registered switches)."
                    )
                else:
                    respond(f"Group `{target}` has no members.")
                return

            bothered_count = 0
            for member_id in members:
                if self.bother_user(member_id, duration):
                    bothered_count += 1

            respond(
                f"Bothered {bothered_count} members of group `{target}` for {duration} seconds."
            )
        else:
            # User target
            target_user_id = self.resolve_user_identifier(target, client)

            if not target_user_id:
                respond(f"Could not find user or group `{target}`")
                return

            if self.bother_user(target_user_id, duration):
                respond(
                    f"Successfully bothered <@{target_user_id}> for {duration} seconds."
                )
            else:
                respond(
                    f"Failed to bother <@{target_user_id}>. They may not have a registered switch."
                )

    def bother_user(self, user_id: str, duration: int) -> bool:
        user = self.database.get_user(user_id)
        if not user or not user["switch_id"] or not user["switch_id"].strip():
            return False

        return self.mqtt_manager.bother_switch(user["switch_id"], duration)

    def handle_list_users(self, respond, user_id):
        users = self.database.get_all_users()
        registered_users = [
            u for u in users if u["switch_id"] and u["switch_id"].strip()
        ]

        if not registered_users:
            respond("No users are currently registered with switches.")
            return

        user_list = []
        for user in registered_users:
            admin_badge = " 👑" if user["is_admin"] else ""
            user_list.append(
                f"• <@{user['slack_user_id']}> (switch: `{user['switch_id']}`){admin_badge}"
            )

        respond("*Registered Users:*\n" + "\n".join(user_list))

    def handle_list_groups(self, respond, user_id):
        groups = self.database.get_all_groups()

        if not groups:
            respond("No groups have been created.")
            return

        group_list = []
        for group in groups:
            member_count = len(self.database.get_group_members(group))
            group_list.append(f"• `{group}` ({member_count} members)")

        respond("*Available Groups:*\n" + "\n".join(group_list))

    def handle_switch_commands(self, respond, user_id, args):
        if not self.database.is_admin(user_id):
            respond("Only administrators can manage switches.")
            return

        if not args:
            respond("Usage: `/dancer switch [list|on|off|toggle] [switch_id]`")
            return

        cmd = args[0].lower()

        if cmd == "list":
            switches = self.database.get_all_switches_with_owners()

            if not switches:
                respond("No switches have been discovered.")
                return

            # Create Block Kit layout for switch list
            blocks = [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "🔌 Discovered Switches"},
                }
            ]

            for switch in switches:
                status_emoji = "🟢" if switch["status"] == "online" else "🔴"
                status_text = "Online" if switch["status"] == "online" else "Offline"

                power_emoji = ""
                power_text = ""
                if switch["power_state"] == "ON":
                    power_emoji = "⚡"
                    power_text = "On"
                elif switch["power_state"] == "OFF":
                    power_emoji = "⭕"
                    power_text = "Off"
                elif switch["power_state"] == "unknown":
                    power_emoji = "❓"
                    power_text = "Unknown"

                # Format last seen date nicely
                try:
                    last_seen = datetime.fromisoformat(switch["last_seen"])
                    last_seen_text = last_seen.strftime("%Y-%m-%d %H:%M")
                except (ValueError, TypeError):
                    last_seen_text = switch["last_seen"]

                # Get switch owner information (now included in switch data)
                owner = switch.get("owner")
                if owner:
                    owner_text = f"<@{owner['slack_user_id']}>"
                    if owner["is_admin"]:
                        owner_text += " 👑"
                else:
                    owner_text = "_Unregistered_"

                # Add section block for each switch with toggle button
                switch_block = {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Switch ID:*\n`{switch['switch_id']}`",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Status:*\n{status_emoji} {status_text}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Power:*\n{power_emoji} {power_text}",
                        },
                        {"type": "mrkdwn", "text": f"*Owner:*\n{owner_text}"},
                        {"type": "mrkdwn", "text": f"*Last Seen:*\n{last_seen_text}"},
                    ],
                    "accessory": {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Toggle"},
                        "style": "primary",
                        "action_id": f"toggle_switch_{switch['switch_id']}",
                        "value": switch["switch_id"],
                    },
                }

                blocks.append(switch_block)

                # Add divider between switches (except for the last one)
                if switch != switches[-1]:
                    blocks.append({"type": "divider"})

            # Try different approaches for sending blocks
            try:
                # Method 1: Direct blocks parameter (for slash commands)
                respond(blocks=blocks)
            except TypeError:
                try:
                    # Method 2: Dictionary with blocks (for some response types)
                    respond({"text": "Discovered Switches", "blocks": blocks})
                except Exception:
                    # Method 3: Fallback to text format
                    logger.info("Blocks not supported, using text fallback")
                    switch_list = []
                    for switch in switches:
                        status_emoji = "🟢" if switch["status"] == "online" else "🔴"
                        power_emoji = ""
                        if switch["power_state"] == "ON":
                            power_emoji = " ⚡"
                        elif switch["power_state"] == "OFF":
                            power_emoji = " ⭕"
                        elif switch["power_state"] == "unknown":
                            power_emoji = " ❓"

                        # Get owner info for text fallback (now included in switch data)
                        owner = switch.get("owner")
                        owner_text = (
                            f" - <@{owner['slack_user_id']}>"
                            if owner
                            else " - _Unregistered_"
                        )
                        if owner and owner["is_admin"]:
                            owner_text += " 👑"

                        switch_list.append(
                            f"• `{switch['switch_id']}` {status_emoji}{power_emoji}{owner_text} (last seen: {switch['last_seen']})"
                        )
                    respond("*Discovered Switches:*\n" + "\n".join(switch_list))
            except Exception as e:
                logger.warning(f"Failed to send blocks: {e}")
                # Final fallback to text format
                switch_list = []
                for switch in switches:
                    status_emoji = "🟢" if switch["status"] == "online" else "🔴"
                    power_emoji = ""
                    if switch["power_state"] == "ON":
                        power_emoji = " ⚡"
                    elif switch["power_state"] == "OFF":
                        power_emoji = " ⭕"
                    elif switch["power_state"] == "unknown":
                        power_emoji = " ❓"

                    # Get owner info for final fallback (now included in switch data)
                    owner = switch.get("owner")
                    owner_text = (
                        f" - <@{owner['slack_user_id']}>"
                        if owner
                        else " - _Unregistered_"
                    )
                    if owner and owner["is_admin"]:
                        owner_text += " 👑"

                    switch_list.append(
                        f"• `{switch['switch_id']}` {status_emoji}{power_emoji}{owner_text} (last seen: {switch['last_seen']})"
                    )
                respond("*Discovered Switches:*\n" + "\n".join(switch_list))

        elif cmd in ["on", "off", "toggle"]:
            if len(args) < 2:
                respond(f"Usage: `/dancer switch {cmd} <switch_id>`")
                return

            switch_id = self.clean_switch_id(args[1])

            # Check if switch exists in database
            switches = self.database.get_all_switches()
            switch_ids = [s["switch_id"] for s in switches]

            if switch_id not in switch_ids:
                respond(
                    f"Switch `{switch_id}` not found. Use `/dancer switch list` to see available switches."
                )
                return

            # Execute the command
            success = False
            if cmd == "on":
                success = self.mqtt_manager.switch_on(switch_id)
                action = "turned on"
            elif cmd == "off":
                success = self.mqtt_manager.switch_off(switch_id)
                action = "turned off"
            elif cmd == "toggle":
                success = self.mqtt_manager.switch_toggle(switch_id)
                action = "toggled"

            if success:
                respond(f"Successfully {action} switch `{switch_id}`.")
            else:
                respond(f"Failed to {cmd} switch `{switch_id}`. Check MQTT connection.")

        else:
            respond("Usage: `/dancer switch [list|on|off|toggle] [switch_id]`")

    def handle_user_commands(self, respond, user_id, args, client):
        logger.info(f"🔍 handle_user_commands called: user_id={user_id}, args={args}")
        if not self.database.is_admin(user_id):
            logger.info(f"🔍 User {user_id} is not admin, denying access")
            respond("Only administrators can manage users.")
            return

        if not args:
            logger.info("🔍 No args provided to user command")
            respond("Usage: `/dancer user [list|show|set] ...`")
            return

        cmd = args[0].lower()
        logger.info(f"🔍 User command: {cmd}")

        if cmd == "list":
            users = self.database.get_all_users()
            if not users:
                respond("No users found.")
                return

            user_list = []
            for user in users:
                admin_badge = " 👑" if user["is_admin"] else ""
                switch_info = (
                    f" (switch: `{user['switch_id']}`)"
                    if user["switch_id"] and user["switch_id"].strip()
                    else ""
                )
                user_list.append(
                    f"• <@{user['slack_user_id']}>{admin_badge}{switch_info}"
                )

            respond("*All Users:*\n" + "\n".join(user_list))

        elif cmd == "show" and len(args) >= 2:
            target_user = args[1]
            logger.info(
                f"🔍 User show command: target_user='{target_user}', args={args}"
            )
            target_user_id = self.resolve_user_identifier(target_user, client)
            logger.info(f"🔍 Resolved target_user_id='{target_user_id}'")

            if not target_user_id:
                respond(f"Could not find user {target_user}")
                return

            user = self.database.get_user(target_user_id)
            logger.debug(f"Database lookup result: {user}")

            if not user:
                respond(f"User <@{target_user_id}> not found.")
                return

            admin_status = "Yes 👑" if user["is_admin"] else "No"
            switch_status = (
                user["switch_id"]
                if user["switch_id"] and user["switch_id"].strip()
                else "None"
            )

            respond(f"""*User Details:*
• User: <@{user["slack_user_id"]}>
• Admin: {admin_status}
• Switch: `{switch_status}`
• Created: {user["created_at"]}""")

        elif cmd == "set" and len(args) >= 3:
            target_user = args[1]
            action = args[2]
            target_user_id = self.resolve_user_identifier(target_user, client)

            if not target_user_id:
                respond(f"Could not find user {target_user}")
                return

            if action == "+admin":
                if self.database.set_admin(target_user_id, True):
                    respond(f"Granted admin privileges to <@{target_user_id}>.")
                else:
                    respond("Failed to grant admin privileges.")
            elif action == "-admin":
                if self.database.set_admin(target_user_id, False):
                    respond(f"Revoked admin privileges from <@{target_user_id}>.")
                else:
                    respond("Failed to revoke admin privileges.")
            else:
                respond("Usage: `/dancer user set <user> [+admin|-admin]`")
        else:
            respond(
                "Usage: `/dancer user [list|show <user>|set <user> [+admin|-admin]]`"
            )

    def handle_group_commands(self, respond, user_id, args, client):
        if not self.database.is_admin(user_id):
            respond("Only administrators can manage groups.")
            return

        if not args:
            respond("Usage: `/dancer group [list|show|create|destroy|add|remove] ...`")
            return

        cmd = args[0].lower()

        if cmd == "list":
            groups = self.database.get_all_groups()
            if not groups:
                respond("No groups found.")
                return

            group_list = []
            for group in groups:
                member_count = len(self.database.get_group_members(group))
                group_list.append(f"• `{group}` ({member_count} members)")

            respond("*All Groups:*\n" + "\n".join(group_list))

        elif cmd == "show" and len(args) >= 2:
            group_name = args[1]
            members = self.database.get_group_members(group_name)

            if not members:
                if group_name.lower() == "all":
                    respond(
                        f"Group `{group_name}` has no members (no users have registered switches)."
                    )
                else:
                    respond(f"Group `{group_name}` not found or has no members.")
                return

            member_list = [f"• <@{member_id}>" for member_id in members]
            if group_name.lower() == "all":
                respond(
                    f"*Members of group `{group_name}` (all users with registered switches):*\n"
                    + "\n".join(member_list)
                )
            else:
                respond(
                    f"*Members of group `{group_name}`:*\n" + "\n".join(member_list)
                )

        elif cmd == "create" and len(args) >= 2:
            group_name = args[1]
            if group_name.lower() == "all":
                respond("Cannot create group `all` - it's a special built-in group.")
                return
            if self.database.create_group(group_name):
                respond(f"Created group `{group_name}`.")
            else:
                respond(f"Failed to create group `{group_name}`. It may already exist.")

        elif cmd == "destroy" and len(args) >= 2:
            group_name = args[1]
            if group_name.lower() == "all":
                respond("Cannot destroy group `all` - it's a special built-in group.")
                return
            if self.database.delete_group(group_name):
                respond(f"Destroyed group `{group_name}`.")
            else:
                respond(f"Failed to destroy group `{group_name}`.")

        elif cmd == "add" and len(args) >= 3:
            group_name = args[1]
            if group_name.lower() == "all":
                respond(
                    "Cannot add users to group `all` - it automatically includes all users with registered switches."
                )
                return
            users_to_add = args[2:]

            added_count = 0
            for user_mention in users_to_add:
                user_id_to_add = self.resolve_user_identifier(user_mention, client)

                if not user_id_to_add:
                    continue

                # Ensure user exists in database
                try:
                    user_info = client.users_info(user=user_id_to_add)
                    username = user_info["user"]["name"]
                    if not self.database.get_user(user_id_to_add):
                        self.database.add_user(user_id_to_add, username)
                except Exception:
                    continue

                if self.database.add_user_to_group(group_name, user_id_to_add):
                    added_count += 1

            respond(f"Added {added_count} user(s) to group `{group_name}`.")

        elif cmd == "remove" and len(args) >= 3:
            group_name = args[1]
            if group_name.lower() == "all":
                respond(
                    "Cannot remove users from group `all` - it automatically includes all users with registered switches."
                )
                return
            users_to_remove = args[2:]

            removed_count = 0
            for user_mention in users_to_remove:
                user_id_to_remove = self.resolve_user_identifier(user_mention, client)
                if user_id_to_remove and self.database.remove_user_from_group(
                    group_name, user_id_to_remove
                ):
                    removed_count += 1

            respond(f"Removed {removed_count} user(s) from group `{group_name}`.")

        else:
            respond(
                "Usage: `/dancer group [list|show <name>|create <name>|destroy <name>|add <name> <user> ...|remove <name> <user> ...]`"
            )

    def parse_user_mention(self, user_str: str) -> str:
        # Handle both @username and <@U1234567890> formats
        if user_str.startswith("<@") and user_str.endswith(">"):
            return user_str[2:-1]
        elif user_str.startswith("@"):
            return user_str[1:]
        else:
            return user_str

    def clean_switch_id(self, switch_str: str) -> str:
        # Remove formatting characters commonly used in Slack messages
        # Strip backticks, quotes, and whitespace
        cleaned = switch_str.strip()
        if cleaned.startswith("`") and cleaned.endswith("`"):
            cleaned = cleaned[1:-1]
        if cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1]
        if cleaned.startswith("'") and cleaned.endswith("'"):
            cleaned = cleaned[1:-1]
        return cleaned.strip()

    def resolve_user_identifier(self, user_str: str, client) -> str | None:
        """
        Resolve a user identifier (mention, username, or user ID) to a Slack user ID
        Returns None if user cannot be found
        """
        logger.info(f"🔍 Resolving user identifier: '{user_str}'")

        # Handle direct user ID format <@U12345>
        if user_str.startswith("<@") and user_str.endswith(">"):
            user_id = user_str[2:-1]
            logger.info(f"🔍 Detected user mention format, extracted ID: {user_id}")
            try:
                client.users_info(user=user_id)
                logger.info(f"🔍 User ID {user_id} validated via API")
                return user_id
            except Exception as e:
                logger.info(f"🔍 User ID {user_id} validation failed: {e}")
                return None

        # Handle username format @username or username
        username = user_str[1:] if user_str.startswith("@") else user_str
        logger.info(f"🔍 Extracted username: '{username}'")

        # First check if we already have this user in our database
        all_users = self.database.get_all_users()
        for user in all_users:
            if user["username"] == username:
                return user["slack_user_id"]

        # If not in database, try to look up by username using Slack API
        # Note: This is less efficient but necessary for DM commands
        try:
            # Try to get user by username - this requires users.list API call
            # which may be rate limited but is necessary for username resolution
            response = client.users_list()
            if response["ok"]:
                for user in response["members"]:
                    if user.get("name") == username and not user.get("deleted", False):
                        user_id = user["id"]
                        # Add to database for future lookups
                        if not self.database.get_user(user_id):
                            self.database.add_user(user_id, username)
                        return user_id
        except Exception as e:
            logger.warning(f"Error looking up user '{username}' via API: {e}")

        logger.warning(
            f"Could not resolve username '{username}' to user ID. User may not exist in workspace."
        )
        return None

    def start(self):
        logger.info("🎯 Starting Airdancer application")
        self.mqtt_manager.start()
        logger.info("🔗 Starting Slack socket mode handler...")
        SocketModeHandler(self.app, os.environ["SLACK_APP_TOKEN"]).start()


# Initialize and start the application
airdancer_app = AirdancerApp()

if __name__ == "__main__":
    logger.info("✨ Starting Airdancer Slack App")
    airdancer_app.start()
