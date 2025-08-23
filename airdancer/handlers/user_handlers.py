"""User command handlers"""

import logging
from typing import Dict
from .base import BaseCommand, CommandContext
from ..services.interfaces import DatabaseServiceInterface, MQTTServiceInterface
from ..utils.parsers import create_bother_parser, create_user_set_parser
from ..utils.formatters import clean_switch_id
# Error handling will be done on a case-by-case basis

logger = logging.getLogger(__name__)


class UserCommandHandler:
    """Handler for user commands"""

    def __init__(
        self,
        database_service: DatabaseServiceInterface,
        mqtt_service: MQTTServiceInterface,
    ):
        self.database_service = database_service
        self.mqtt_service = mqtt_service
        self.commands: Dict[str, BaseCommand] = {
            "register": RegisterCommand(database_service),
            "bother": BotherCommand(database_service, mqtt_service),
            "users": ListUsersCommand(database_service),
            "groups": ListGroupsCommand(database_service),
            "set": UserSetCommand(database_service),
        }

    def handle_command(self, command: str, context: CommandContext) -> None:
        """Handle a user command"""
        if command in self.commands:
            cmd_handler = self.commands[command]
            if cmd_handler.can_execute(context):
                cmd_handler.execute(context)
            else:
                context.respond(f"Cannot execute command: {command}")
        else:
            context.respond(f"Unknown command: {command}")


class RegisterCommand(BaseCommand):
    """Handle user registration of switches"""

    def __init__(self, database_service: DatabaseServiceInterface):
        self.database_service = database_service

    def can_execute(self, context: CommandContext) -> bool:
        """Check if register command can be executed"""
        return len(context.args) >= 1

    def execute(self, context: CommandContext) -> None:
        """Execute register command"""
        if len(context.args) != 1:
            context.respond("Usage: `register <switch>`")
            return

        switch_id = clean_switch_id(context.args[0])

        try:
            if self.database_service.register_switch(context.user_id, switch_id):
                context.respond(
                    f"Successfully registered switch `{switch_id}` to your account."
                )
            else:
                context.respond(
                    "Failed to register switch. Make sure you have an account."
                )
        except Exception as e:
            # Use the ErrorHandler for exceptions from the enhanced database service
            from ..error_handler import ErrorHandler

            ErrorHandler.handle_command_error(e, context)


class BotherCommand(BaseCommand):
    """Handle bother command with argparse"""

    def __init__(
        self,
        database_service: DatabaseServiceInterface,
        mqtt_service: MQTTServiceInterface,
    ):
        self.database_service = database_service
        self.mqtt_service = mqtt_service
        self.parser = create_bother_parser()

    def can_execute(self, context: CommandContext) -> bool:
        """Check if bother command can be executed"""
        return len(context.args) >= 1

    def execute(self, context: CommandContext) -> None:
        """Execute bother command"""
        try:
            parsed_args = self.parser.parse_args(context.args)
        except Exception as e:
            error_msg = str(e)
            context.respond(f"Error parsing arguments: {error_msg}")
            return

        duration = parsed_args.duration
        target = parsed_args.target

        # Validate duration
        if duration <= 0:
            context.respond("Duration must be a positive number.")
            return

        # Check if target is a group
        available_groups = self.database_service.get_all_groups()
        if target.lower() in [g.lower() for g in available_groups]:
            self._bother_group(target, duration, context)
        else:
            self._bother_user(target, duration, context)

    def _bother_group(
        self, group_name: str, duration: int, context: CommandContext
    ) -> None:
        """Bother all members of a group"""
        members = self.database_service.get_group_members(group_name)
        if not members:
            if group_name.lower() == "all":
                context.respond(
                    f"Group `{group_name}` has no members (no users have registered switches)."
                )
            else:
                context.respond(f"Group `{group_name}` has no members.")
            return

        bothered_count = 0
        for member_id in members:
            if self._bother_user_by_id(member_id, duration):
                bothered_count += 1

        context.respond(
            f"Bothered {bothered_count} members of group `{group_name}` for {duration} seconds."
        )

    def _bother_user(self, target: str, duration: int, context: CommandContext) -> None:
        """Bother a specific user"""
        # Resolve user identifier (handle @username, username, or <@U123>)
        user_id = self._resolve_user_identifier(target, context)
        if not user_id:
            context.respond(f"Could not find user: {target}")
            return

        if self._bother_user_by_id(user_id, duration):
            context.respond(f"Successfully bothered user for {duration} seconds.")
        else:
            context.respond(
                "Failed to bother user. They may not have a registered switch."
            )

    def _bother_user_by_id(self, user_id: str, duration: int) -> bool:
        """Bother user by their ID"""
        user = self.database_service.get_user(user_id)
        if not user or not user.switch_id or not user.switch_id.strip():
            return False

        # Check if user is botherable
        if not user.botherable:
            return False

        return self.mqtt_service.bother_switch(user.switch_id, duration)

    def _resolve_user_identifier(
        self, user_str: str, context: CommandContext
    ) -> str | None:
        """Resolve a user identifier to a Slack user ID"""
        # Handle direct user ID format <@U12345>
        if user_str.startswith("<@") and user_str.endswith(">"):
            user_id = user_str[2:-1]
            try:
                context.client.users_info(user=user_id)
                return user_id
            except Exception:
                return None

        # Handle plain user ID format (U12345)
        if user_str.startswith("U") and len(user_str) == 9:
            try:
                context.client.users_info(user=user_str)
                return user_str
            except Exception:
                return None

        # Handle username format @username or username
        username = user_str[1:] if user_str.startswith("@") else user_str

        # First check if we already have this user in our database
        all_users = self.database_service.get_all_users()
        for user in all_users:
            if user.username == username:
                return user.slack_user_id

        # If not in database, try to look up by username using Slack API
        try:
            response = context.client.users_list()
            if response["ok"]:
                for user in response["members"]:
                    if user.get("name") == username and not user.get("deleted", False):
                        user_id = user["id"]
                        # Add to database for future lookups
                        if not self.database_service.get_user(user_id):
                            self.database_service.add_user(user_id, username)
                        return user_id
        except Exception as e:
            logger.warning(f"Error looking up user '{username}' via API: {e}")

        return None


class ListUsersCommand(BaseCommand):
    """List registered users"""

    def __init__(self, database_service: DatabaseServiceInterface):
        self.database_service = database_service

    def can_execute(self, context: CommandContext) -> bool:
        """Anyone can list users"""
        return True

    def execute(self, context: CommandContext) -> None:
        """List users with registered switches"""
        users = self.database_service.get_all_users()
        registered_users = [u for u in users if u.switch_id and u.switch_id.strip()]

        if not registered_users:
            context.respond("No users are currently registered with switches.")
            return

        user_list = []
        for user in registered_users:
            admin_badge = " 👑" if user.is_admin else ""
            user_list.append(
                f"• <@{user.slack_user_id}> (switch: `{user.switch_id}`){admin_badge}"
            )

        context.respond("*Registered Users:*\n" + "\n".join(user_list))


class ListGroupsCommand(BaseCommand):
    """List available groups"""

    def __init__(self, database_service: DatabaseServiceInterface):
        self.database_service = database_service

    def can_execute(self, context: CommandContext) -> bool:
        """Anyone can list groups"""
        return True

    def execute(self, context: CommandContext) -> None:
        """List all groups"""
        groups = self.database_service.get_all_groups()

        if not groups:
            context.respond("No groups have been created.")
            return

        group_list = []
        for group in groups:
            member_count = len(self.database_service.get_group_members(group))
            group_list.append(f"• `{group}` ({member_count} members)")

        context.respond("*Available Groups:*\n" + "\n".join(group_list))


class UserSetCommand(BaseCommand):
    """Handle user set command for configuring user settings"""

    def __init__(self, database_service: DatabaseServiceInterface):
        self.database_service = database_service
        self.parser = create_user_set_parser()

    def can_execute(self, context: CommandContext) -> bool:
        """Any user can modify their own settings"""
        return True

    def execute(self, context: CommandContext) -> None:
        """Execute user set command"""
        try:
            parsed_args = self.parser.parse_args(context.args)
        except Exception as e:
            error_msg = str(e)
            context.respond(f"Error parsing arguments: {error_msg}")
            return

        # Determine the new botherable setting
        botherable = parsed_args.bother

        # Update the user's botherable setting
        if self.database_service.set_botherable(context.user_id, botherable):
            status = "enabled" if botherable else "disabled"
            context.respond(
                f"Successfully {status} bother notifications for your account."
            )
        else:
            context.respond(
                "Failed to update settings. You may need to register first."
            )
