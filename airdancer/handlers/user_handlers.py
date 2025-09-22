"""User command handlers"""

import logging
from .base import BaseCommand, CommandContext
from ..services.interfaces import DatabaseServiceInterface, MQTTServiceInterface
from ..utils.parsers import (
    create_bother_parser,
    create_user_set_parser,
    create_users_list_parser,
    create_register_parser,
    create_groups_parser,
    HelpRequestedException,
)
from ..utils.formatters import clean_switch_id
from ..utils.user_resolvers import resolve_user_identifier
from ..utils.slack_blocks import (
    send_blocks_response,
    create_header_block,
    create_divider_block,
    create_section_block,
    create_button_accessory,
)
from ..utils.table_formatters import (
    process_user_data,
    format_users_plain_table,
    format_users_box_table,
)
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
        self.commands: dict[str, BaseCommand] = {
            "register": RegisterCommand(database_service),
            "unregister": UnregisterCommand(database_service),
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
        self.parser = create_register_parser()

    def can_execute(self, context: CommandContext) -> bool:
        """Check if register command can be executed"""
        return True

    def execute(self, context: CommandContext) -> None:
        """Execute register command"""
        try:
            parsed_args = self.parser.parse_args(context.args)
        except HelpRequestedException as e:
            context.respond(e.help_text)
            return
        except Exception as e:
            error_msg = str(e)
            context.respond(f"Error parsing arguments: {error_msg}")
            return

        switch_id = clean_switch_id(parsed_args.switch_id)

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


class UnregisterCommand(BaseCommand):
    """Handle user unregistration of their own switch"""

    def __init__(self, database_service: DatabaseServiceInterface):
        self.database_service = database_service

    def can_execute(self, context: CommandContext) -> bool:
        """Check if unregister command can be executed"""
        return True

    def execute(self, context: CommandContext) -> None:
        """Execute unregister command"""
        if context.args:
            context.respond(
                "The `unregister` command takes no arguments. Use `/dancer unregister` to remove your switch registration."
            )
            return

        # Check if user has a registered switch
        user = self.database_service.get_user(context.user_id)
        if not user or not user.switch_id or not user.switch_id.strip():
            context.respond("❌ You don't have a switch registered.")
            return

        # Unregister the user's switch
        if self.database_service.unregister_user(context.user_id):
            context.respond("✅ Successfully removed your switch registration.")
        else:
            context.respond(
                "❌ Failed to remove your switch registration. Please try again."
            )


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
        except HelpRequestedException as e:
            context.respond(e.help_text)
            return
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
            if self._bother_user_by_id(member_id, duration, context):
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

        if self._bother_user_by_id(user_id, duration, context):
            context.respond(f"Successfully bothered user for {duration} seconds.")
        else:
            context.respond(
                "Failed to bother user. They may not have a registered switch."
            )

    def _bother_user_by_id(
        self, user_id: str, duration: int, context: CommandContext
    ) -> bool:
        """Bother user by their ID"""
        user = self.database_service.get_user(user_id)
        if not user or not user.switch_id or not user.switch_id.strip():
            return False

        # Check if user is botherable
        if not user.botherable:
            return False

        # Send the bother command to the switch
        success = self.mqtt_service.bother_switch(user.switch_id, duration)

        if success:
            # Send a message to the target user informing them they've been bothered
            # Skip notification if user is bothering themselves
            if user_id != context.user_id:
                self._send_bother_notification(user_id, context)

        return success

    def _send_bother_notification(
        self, target_user_id: str, context: CommandContext
    ) -> None:
        """Send a notification to the target user that they've been bothered"""
        try:
            # Get the username of the person who initiated the bother command
            botherer_info = context.client.users_info(user=context.user_id)
            botherer_username = botherer_info["user"]["name"]

            # Open a direct message conversation with the target user
            dm_response = context.client.conversations_open(users=target_user_id)
            if dm_response["ok"]:
                channel_id = dm_response["channel"]["id"]

                # Send the bother notification message
                context.client.chat_postMessage(
                    channel=channel_id,
                    text=f"You have been bothered by @{botherer_username}",
                )
                logger.info(
                    f"Sent bother notification to user {target_user_id} from {botherer_username}"
                )
            else:
                logger.error(
                    f"Failed to open DM conversation with user {target_user_id}: {dm_response.get('error', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(
                f"Failed to send bother notification to user {target_user_id}: {e}"
            )

    def _resolve_user_identifier(
        self, user_str: str, context: CommandContext
    ) -> str | None:
        """Resolve a user identifier to a Slack user ID"""
        return resolve_user_identifier(user_str, context, self.database_service)


class ListUsersCommand(BaseCommand):
    """List registered users"""

    def __init__(self, database_service: DatabaseServiceInterface):
        self.database_service = database_service
        self.parser = create_users_list_parser()

    def can_execute(self, context: CommandContext) -> bool:
        """Anyone can list users"""
        return True

    def execute(self, context: CommandContext) -> None:
        """List users with different output formats based on arguments"""
        # Parse arguments for verbose and box flags
        try:
            parsed_args = self.parser.parse_args(context.args)
        except HelpRequestedException as e:
            context.respond(e.help_text)
            return
        except Exception as e:
            context.respond(f"Error parsing arguments: {str(e)}")
            return

        users = self.database_service.get_all_users()

        # Filter for users with registered switches
        users_with_switches = [
            user for user in users if user.switch_id and user.switch_id.strip()
        ]

        if not users_with_switches:
            context.respond("No users with registered switches found.")
            return

        # Get switch status information
        all_switches = self.database_service.get_all_switches()
        switch_status_map = {switch.switch_id: switch.status for switch in all_switches}

        if parsed_args.short:
            self._list_users_concise(users_with_switches, switch_status_map, context)
        elif parsed_args.box:
            self._list_users_box(users_with_switches, switch_status_map, context)
        else:
            self._list_users_verbose(users_with_switches, switch_status_map, context)

    def _list_users_verbose(
        self, users, switch_status_map, context: CommandContext
    ) -> None:
        """List users with interactive blocks and buttons (original format)"""
        blocks = [create_header_block("👥 User Directory"), create_divider_block()]

        for user in users:
            # Determine botherable status
            botherable_status = (
                "✅ Botherable" if user.botherable else "🚫 Not botherable"
            )

            # Admin badge
            admin_badge = " 👑" if user.is_admin else ""

            # Get switch status for button logic
            switch_status = switch_status_map.get(user.switch_id, "offline")

            # Create user section text (switch status now shown via button)
            user_text = f"*<@{user.slack_user_id}>*{admin_badge}\n{botherable_status}"

            # Add bother button if user is botherable
            accessory = None
            if user.botherable:
                if switch_status == "online":
                    accessory = create_button_accessory(
                        "🔔 Bother", "bother_user", user.slack_user_id, "primary"
                    )
                else:
                    # Show disabled button when switch is offline
                    accessory = create_button_accessory(
                        "🔴 Offline", "disabled", "disabled", "danger"
                    )

            user_section = create_section_block(user_text, accessory=accessory)
            blocks.append(user_section)
            blocks.append(create_divider_block())

        # Remove the last divider
        if blocks and blocks[-1]["type"] == "divider":
            blocks.pop()

        # Create fallback text generator
        def generate_fallback_text():
            user_lines = []
            for user in users:
                botherable_status = (
                    "✅ Botherable" if user.botherable else "🚫 Not botherable"
                )
                admin_badge = " 👑" if user.is_admin else ""
                user_lines.append(
                    f"• <@{user.slack_user_id}>{admin_badge} - {botherable_status}"
                )
            return "*👥 User Directory*\n" + "\n".join(user_lines)

        send_blocks_response(
            blocks, context.respond, "👥 User Directory", generate_fallback_text
        )

    def _list_users_concise(
        self, users, switch_status_map, context: CommandContext
    ) -> None:
        """List users in a concise plain-text table format"""
        # Use shared data processing logic
        rows = process_user_data(users, switch_status_map)
        table_output = format_users_plain_table(rows)
        context.respond(table_output)

    def _list_users_box(
        self, users, switch_status_map, context: CommandContext
    ) -> None:
        """List users in a box table format using Unicode box drawing characters"""
        # Use shared data processing logic
        rows = process_user_data(users, switch_status_map)
        table_output = format_users_box_table(rows)
        context.respond(table_output)


class ListGroupsCommand(BaseCommand):
    """List available groups"""

    def __init__(self, database_service: DatabaseServiceInterface):
        self.database_service = database_service
        self.parser = create_groups_parser()

    def can_execute(self, context: CommandContext) -> bool:
        """Anyone can list groups"""
        return True

    def execute(self, context: CommandContext) -> None:
        """List all groups"""
        try:
            self.parser.parse_args(context.args)
        except HelpRequestedException as e:
            context.respond(e.help_text)
            return
        except Exception as e:
            error_msg = str(e)
            context.respond(f"Error parsing arguments: {error_msg}")
            return

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
        except HelpRequestedException as e:
            context.respond(e.help_text)
            return
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
