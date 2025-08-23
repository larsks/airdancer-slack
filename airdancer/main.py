"""Main application using the new architecture"""

import os
import logging
import re

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .config import AppConfig
from .services import DatabaseService, MQTTService
from .handlers import CommandContext, UserCommandHandler, AdminCommandHandler
from .commands.router import CommandRouter
from .error_handler import ErrorHandler

# Configure logging
logging.basicConfig(level=logging.DEBUG if os.environ.get("DEBUG") else logging.INFO)
logger = logging.getLogger(__name__)


class AirdancerApp:
    """Main Airdancer application with dependency injection"""

    def __init__(self, config: AppConfig):
        self.config = config

        # Initialize services
        logger.info("🚀 Initializing Airdancer Slack App")
        self.database_service = DatabaseService(config.database_path)
        logger.info("📄 Database service initialized")

        self.mqtt_service = MQTTService(self.database_service, config.mqtt)
        logger.info("📡 MQTT service initialized")

        # Initialize Slack app
        self.slack_app = App(token=config.slack.bot_token)
        logger.info("💬 Slack app initialized")

        # Initialize command handlers
        self.user_handler = UserCommandHandler(self.database_service, self.mqtt_service)
        self.admin_handler = AdminCommandHandler(
            self.database_service, self.mqtt_service
        )

        # Initialize command router
        self.command_router = CommandRouter(self.user_handler, self.admin_handler)
        logger.info("⚙️  Command handlers and router configured")

        # Set up commands and events
        self._setup_commands()
        self._setup_events()

        # Set up initial admin user if specified
        if config.admin_user:
            logger.info(f"👑 Admin user configured: {config.admin_user}")
        else:
            logger.warning("⚠️  No admin user configured")

    def _setup_commands(self):
        """Set up Slack command handlers"""

        @self.slack_app.command("/dancer")
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
            context = CommandContext(
                user_id=user_id, args=args[1:], respond=respond, client=client
            )

            # Ensure user exists in database and route command
            self._process_command(user_id, cmd, context, client)

        @self.slack_app.command("/bother")
        def handle_bother_command(ack, respond, command, client):
            ack()

            user_id = command["user_id"]
            text = command["text"].strip()
            args = text.split() if text else []

            # Create context for bother command
            context = CommandContext(
                user_id=user_id, args=args, respond=respond, client=client
            )

            # Ensure user exists in database and route to bother command
            self._process_command(user_id, "bother", context, client)

    def _setup_events(self):
        """Set up Slack event handlers"""

        @self.slack_app.event("message")
        def handle_message_events(body, say, client):
            # Only handle direct messages (not channel messages)
            event = body["event"]

            # Skip bot messages and messages that aren't direct messages
            if event.get("bot_id") or event.get("channel_type") != "im":
                return

            user_id = event["user"]
            text = event.get("text", "").strip()

            if not text:
                say("Please send a command. Type `help` for available commands.")
                return

            args = text.split()
            cmd = args[0].lower()

            # Create response function that uses say
            def respond(message):
                say(message)

            context = CommandContext(
                user_id=user_id, args=args[1:], respond=respond, client=client
            )

            # Ensure user exists in database and route command
            self._process_command(user_id, cmd, context, client)

        # Handle toggle button actions
        @self.slack_app.action(re.compile(r"toggle_switch_.*"))
        def handle_toggle_switch(ack, body, client):
            ack()

            user_id = body["user"]["id"]
            action = body["actions"][0]
            switch_id = action["value"]

            logger.info(f"Toggle button pressed by {user_id} for switch {switch_id}")

            # Check if user is admin (only admins can toggle switches)
            if not self.database_service.is_admin(user_id):
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
            success = self.mqtt_service.switch_toggle(switch_id)

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

        # Handle bother button actions
        @self.slack_app.action("bother_user")
        def handle_bother_user(ack, body, client):
            ack()

            user_id = body["user"]["id"]
            action = body["actions"][0]
            target_user_id = action["value"]

            logger.info(f"Bother button pressed by {user_id} for user {target_user_id}")

            # Create a respond function that posts ephemeral messages
            def respond(message):
                try:
                    client.chat_postEphemeral(
                        channel=body["channel"]["id"],
                        user=user_id,
                        text=message,
                    )
                except Exception as e:
                    logger.error(f"Error sending ephemeral response: {e}")

            # Create context for bother command
            context = CommandContext(
                user_id=user_id,
                args=[f"<@{target_user_id}>"],
                respond=respond,
                client=client,
            )

            # Process the bother command
            self._process_command(user_id, "bother", context, client)

    def _ensure_admin_user(self, user_id: str, username: str) -> None:
        """Check if this user should be made admin based on config"""
        if not self.config.admin_user:
            return

        # Check if this user matches the admin identifier (by username or user ID)
        username_match = self.config.admin_user == username
        user_id_match = self.config.admin_user == user_id

        if username_match or user_id_match:
            user = self.database_service.get_user(user_id)
            if not user:
                self.database_service.add_user(user_id, username, True)
                logger.info(f"✅ Created admin user: {username} ({user_id})")
            elif not user.is_admin:
                self.database_service.set_admin(user_id, True)
                logger.info(f"✅ Granted admin privileges to: {username} ({user_id})")

    def _process_command(
        self, user_id: str, cmd: str, context: CommandContext, client
    ) -> None:
        """Process a command with user setup and routing"""
        try:
            # Ensure user exists in database
            user_info = client.users_info(user=user_id)
            username = user_info["user"]["name"]
            if not self.database_service.get_user(user_id):
                self.database_service.add_user(user_id, username)

            # Check if this user should be made admin
            self._ensure_admin_user(user_id, username)

            # Route command through the centralized router
            self.command_router.route_command(cmd, context)

        except Exception as e:
            logger.error(f"Error processing command '{cmd}' for user {user_id}: {e}")
            ErrorHandler.handle_command_error(e, context)

    def _handle_help(self, context: CommandContext) -> None:
        """Legacy help handler for backward compatibility with tests"""
        # Delegate to the command router
        self.command_router._handle_help(context)

    def start(self):
        """Start the application"""
        logger.info("🎯 Starting Airdancer application")
        self.mqtt_service.start()
        logger.info("🔗 Starting Slack socket mode handler...")
        SocketModeHandler(self.slack_app, self.config.slack.app_token).start()


def create_app() -> AirdancerApp:
    """Create and configure the application with dependency injection"""
    config = AppConfig()
    return AirdancerApp(config)


def main():
    """Application entry point"""
    try:
        app = create_app()
        logger.info("✨ Starting Airdancer Slack App")
        app.start()
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise


if __name__ == "__main__":
    main()
