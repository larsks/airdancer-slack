"""Centralized command routing logic"""

import logging
from typing import Callable
from ..handlers.base import CommandContext
from ..handlers.user_handlers import UserCommandHandler
from ..handlers.admin_handlers import AdminCommandHandler
from ..error_handler import ErrorHandler

logger = logging.getLogger(__name__)


class CommandRouter:
    """Centralized command routing with error handling"""

    def __init__(
        self,
        user_handler: UserCommandHandler,
        admin_handler: AdminCommandHandler,
    ):
        self.user_handler = user_handler
        self.admin_handler = admin_handler
        # Access database service for admin checks
        self.database_service = user_handler.database_service
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Set up command routing table"""
        self._routes: dict[str, Callable[[CommandContext], None]] = {
            # Help command
            "help": self._handle_help,
            # User commands
            "register": lambda ctx: self.user_handler.handle_command("register", ctx),
            "bother": lambda ctx: self.user_handler.handle_command("bother", ctx),
            "users": lambda ctx: self.user_handler.handle_command("users", ctx),
            "groups": lambda ctx: self.user_handler.handle_command("groups", ctx),
            "set": lambda ctx: self.user_handler.handle_command("set", ctx),
            # Admin commands
            "unregister": lambda ctx: self.admin_handler.handle_command(
                "unregister", ctx
            ),
            "switch": lambda ctx: self.admin_handler.handle_command("switch", ctx),
            "user": lambda ctx: self.admin_handler.handle_command("user", ctx),
            "group": lambda ctx: self.admin_handler.handle_command("group", ctx),
        }

    def route_command(self, cmd: str, context: CommandContext) -> None:
        """Route a command to the appropriate handler with error handling"""
        try:
            handler = self._routes.get(cmd.lower())
            if handler:
                logger.info(f"Routing command '{cmd}' for user {context.user_id}")
                handler(context)
            else:
                self._handle_unknown_command(cmd, context)
        except Exception as e:
            logger.error(
                f"Error routing command '{cmd}' for user {context.user_id}: {e}"
            )
            ErrorHandler.handle_command_error(e, context)

    def _handle_help(self, context: CommandContext) -> None:
        """Handle help command"""
        try:
            help_text = self._get_help_text(context)
            context.respond(help_text)
        except Exception as e:
            ErrorHandler.handle_command_error(e, context)

    def _handle_unknown_command(self, cmd: str, context: CommandContext) -> None:
        """Handle unknown commands"""
        available_commands = ", ".join(sorted(self._routes.keys()))
        context.respond(
            f"❌ Unknown command: `{cmd}`\\n"
            f"Available commands: {available_commands}\\n"
            f"Use `help` for detailed information."
        )

    def _get_help_text(self, context: CommandContext) -> str:
        """Generate help text for available commands based on user privileges"""
        is_admin = self.database_service.is_admin(context.user_id)

        help_text = """
*Available Commands:*

*User Commands:*
• `register <switch_id>` - Register a switch to your account
• `bother [--duration <seconds>] <user_or_group>` - Activate someone's switch
• `set --bother|--no-bother` - Enable/disable bother notifications
• `users` [--box] [--brief] - List all registered users
• `groups` - List all available groups

For more information, visit https://airdancer.oddbit.com
"""

        if is_admin:
            help_text += """

*Admin Commands:*
• `unregister <user>` - Remove a user's switch registration
• `switch list` - List all switches and their status
• `switch show <switch_id>` - Show details for a specific switch
• `switch on <switch_id>` - Turn on a switch
• `switch off <switch_id>` - Turn off a switch
• `switch toggle <switch_id>` - Toggle a switch
• `user list` - List all users (admin view)
• `user show <user>` - Show user details
• `user set <user> [--admin|--no-admin] [--bother|--no-bother]` - Configure user settings
• `user register <user> <switch_id>` - Register a switch to a specific user
• `group list` - List all groups with member counts
• `group create <name>` - Create a new group
• `group destroy <name>` - Delete a group
• `group add <name> <user1> [user2...]` - Add users to a group
• `group remove <name> <user1> [user2...]` - Remove users from a group"""

        help_text += """

*Examples:*
• `/dancer register tasmota_12345`
• `/dancer bother @username`
• `/dancer bother --duration 30 mygroup`"""

        if is_admin:
            help_text += """
• `/dancer switch toggle tasmota_12345`

*Note:* Admin commands require administrator privileges."""

        return help_text.strip()

    def get_available_commands(self) -> list[str]:
        """Get list of available commands"""
        return list(self._routes.keys())

    def is_admin_command(self, cmd: str) -> bool:
        """Check if a command requires admin privileges"""
        admin_commands = {"unregister", "switch", "user", "group"}
        return cmd.lower() in admin_commands
