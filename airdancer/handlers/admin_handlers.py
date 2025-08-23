"""Admin command handlers"""

import logging
from typing import Dict
from .base import BaseCommand, CommandContext
from ..services.interfaces import DatabaseServiceInterface, MQTTServiceInterface
from ..utils.parsers import create_admin_user_set_parser

logger = logging.getLogger(__name__)


class AdminCommandHandler:
    """Handler for admin commands"""

    def __init__(
        self,
        database_service: DatabaseServiceInterface,
        mqtt_service: MQTTServiceInterface,
    ):
        self.database_service = database_service
        self.mqtt_service = mqtt_service
        self.commands: Dict[str, BaseCommand] = {
            "unregister": UnregisterCommand(database_service),
            "switch": SwitchCommand(database_service, mqtt_service),
            "user": UserCommand(database_service),
            "group": GroupCommand(database_service),
        }

    def handle_command(self, command: str, context: CommandContext) -> None:
        """Handle an admin command"""
        if command in self.commands:
            cmd_handler = self.commands[command]
            if cmd_handler.can_execute(context):
                cmd_handler.execute(context)
            else:
                context.respond("Only administrators can use this command.")
        else:
            context.respond(f"Unknown admin command: {command}")


class UnregisterCommand(BaseCommand):
    """Handle user unregistration (admin only)"""

    def __init__(self, database_service: DatabaseServiceInterface):
        self.database_service = database_service

    def can_execute(self, context: CommandContext) -> bool:
        """Only admins can unregister users"""
        return self.database_service.is_admin(context.user_id)

    def execute(self, context: CommandContext) -> None:
        """Execute unregister command"""
        if len(context.args) != 1:
            context.respond("Usage: `unregister <user>`")
            return

        # This is simplified - in real implementation, you'd resolve user identifier
        target_user = context.args[0]

        if self.database_service.unregister_user(target_user):
            context.respond("Successfully unregistered user.")
        else:
            context.respond("Failed to unregister user or user not found.")


class SwitchCommand(BaseCommand):
    """Handle switch management commands (admin only)"""

    def __init__(
        self,
        database_service: DatabaseServiceInterface,
        mqtt_service: MQTTServiceInterface,
    ):
        self.database_service = database_service
        self.mqtt_service = mqtt_service

    def can_execute(self, context: CommandContext) -> bool:
        """Only admins can manage switches"""
        return self.database_service.is_admin(context.user_id)

    def execute(self, context: CommandContext) -> None:
        """Execute switch command"""
        if not context.args:
            context.respond("Usage: `switch [list|show|on|off|toggle] [switch_id]`")
            return

        cmd = context.args[0].lower()

        if cmd == "list":
            self._list_switches(context)
        elif cmd == "show" and len(context.args) >= 2:
            self._show_switch(context.args[1], context)
        elif cmd in ["on", "off", "toggle"] and len(context.args) >= 2:
            self._control_switch(cmd, context.args[1], context)
        else:
            context.respond("Usage: `switch [list|show|on|off|toggle] [switch_id]`")

    def _list_switches(self, context: CommandContext) -> None:
        """List all switches with interactive blocks and toggle buttons"""
        switches = self.database_service.get_all_switches_with_owners()

        if not switches:
            context.respond("No switches have been discovered.")
            return

        # Create Block Kit layout for switch list
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🔌 Discovered Switches"},
            }
        ]

        for switch in switches:
            status_emoji = "🟢" if switch.status == "online" else "🔴"
            status_text = "Online" if switch.status == "online" else "Offline"

            power_emoji = ""
            power_text = ""
            if switch.power_state == "ON":
                power_emoji = "⚡"
                power_text = "On"
            elif switch.power_state == "OFF":
                power_emoji = "⭕"
                power_text = "Off"
            elif switch.power_state == "unknown":
                power_emoji = "❓"
                power_text = "Unknown"

            # Format last seen date nicely
            try:
                from datetime import datetime

                last_seen = datetime.fromisoformat(str(switch.last_seen))
                last_seen_text = last_seen.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                last_seen_text = str(switch.last_seen)

            # Get switch owner information
            if switch.owner:
                owner_text = f"<@{switch.owner.slack_user_id}>"
                if switch.owner.is_admin:
                    owner_text += " 👑"
            else:
                owner_text = "_Unregistered_"

            # Add section block for each switch with toggle button
            switch_block = {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Switch ID:*\n`{switch.switch_id}`",
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
                    "action_id": f"toggle_switch_{switch.switch_id}",
                    "value": switch.switch_id,
                },
            }

            blocks.append(switch_block)

            # Add divider between switches (except for the last one)
            if switch != switches[-1]:
                blocks.append({"type": "divider"})

        # Try different approaches for sending blocks
        try:
            # Method 1: Direct blocks parameter (for slash commands)
            context.respond(blocks=blocks)
        except TypeError:
            try:
                # Method 2: Dictionary with blocks (for some response types)
                context.respond({"text": "Discovered Switches", "blocks": blocks})
            except Exception:
                # Method 3: Fallback to text format
                logger.info("Blocks not supported, using text fallback")
                switch_list = []
                for switch in switches:
                    status_emoji = "🟢" if switch.status == "online" else "🔴"
                    power_emoji = ""
                    if switch.power_state == "ON":
                        power_emoji = " ⚡"
                    elif switch.power_state == "OFF":
                        power_emoji = " ⭕"
                    elif switch.power_state == "unknown":
                        power_emoji = " ❓"

                    # Get owner info for text fallback
                    owner_text = ""
                    if switch.owner:
                        owner_text = f" - <@{switch.owner.slack_user_id}>"
                        if switch.owner.is_admin:
                            owner_text += " 👑"
                    else:
                        owner_text = " - _Unregistered_"

                    switch_list.append(
                        f"• `{switch.switch_id}` {status_emoji}{power_emoji}{owner_text} (last seen: {switch.last_seen})"
                    )
                context.respond("*Discovered Switches:*\n" + "\n".join(switch_list))
        except Exception as e:
            logger.warning(f"Failed to send blocks: {e}")
            # Final fallback to text format
            switch_list = []
            for switch in switches:
                status_emoji = "🟢" if switch.status == "online" else "🔴"
                power_emoji = ""
                if switch.power_state == "ON":
                    power_emoji = " ⚡"
                elif switch.power_state == "OFF":
                    power_emoji = " ⭕"
                elif switch.power_state == "unknown":
                    power_emoji = " ❓"

                # Get owner info for final fallback
                owner_text = ""
                if switch.owner:
                    owner_text = f" - <@{switch.owner.slack_user_id}>"
                    if switch.owner.is_admin:
                        owner_text += " 👑"
                else:
                    owner_text = " - _Unregistered_"

                switch_list.append(
                    f"• `{switch.switch_id}` {status_emoji}{power_emoji}{owner_text} (last seen: {switch.last_seen})"
                )
            context.respond("*Discovered Switches:*\n" + "\n".join(switch_list))

    def _show_switch(self, switch_id: str, context: CommandContext) -> None:
        """Show detailed switch information"""
        switches = self.database_service.get_all_switches_with_owners()
        switch = next((s for s in switches if s.switch_id == switch_id), None)

        if not switch:
            context.respond(f"Switch `{switch_id}` not found.")
            return

        status_emoji = "🟢" if switch.status == "online" else "🔴"
        power_emoji = ""
        if switch.power_state == "ON":
            power_emoji = " ⚡"
        elif switch.power_state == "OFF":
            power_emoji = " ⭕"
        elif switch.power_state == "unknown":
            power_emoji = " ❓"

        owner_text = "None"
        if switch.owner:
            owner_text = f"<@{switch.owner.slack_user_id}>"
            if switch.owner.is_admin:
                owner_text += " 👑"

        context.respond(f"""*Switch Details:*
• ID: `{switch.switch_id}`
• Status: {status_emoji} {switch.status.title()}{power_emoji}
• Power: {switch.power_state}
• Owner: {owner_text}
• Last Seen: {switch.last_seen}
• Device Info: {switch.device_info or "None"}""")

    def _control_switch(
        self, action: str, switch_id: str, context: CommandContext
    ) -> None:
        """Control a switch"""
        success = False
        if action == "on":
            success = self.mqtt_service.switch_on(switch_id)
        elif action == "off":
            success = self.mqtt_service.switch_off(switch_id)
        elif action == "toggle":
            success = self.mqtt_service.switch_toggle(switch_id)

        if success:
            context.respond(f"Successfully {action} switch `{switch_id}`.")
        else:
            context.respond(f"Failed to {action} switch `{switch_id}`.")


class UserCommand(BaseCommand):
    """Handle user management commands (admin only)"""

    def __init__(self, database_service: DatabaseServiceInterface):
        self.database_service = database_service
        self.set_parser = create_admin_user_set_parser()

    def can_execute(self, context: CommandContext) -> bool:
        """Only admins can manage users"""
        return self.database_service.is_admin(context.user_id)

    def execute(self, context: CommandContext) -> None:
        """Execute user command"""
        if not context.args:
            context.respond("Usage: `user [list|show|set|register] ...`")
            return

        cmd = context.args[0].lower()

        if cmd == "list":
            self._list_users(context)
        elif cmd == "show" and len(context.args) >= 2:
            self._show_user(context.args[1], context)
        elif cmd == "set" and len(context.args) >= 2:
            self._set_user(context.args[1:], context)
        elif cmd == "register" and len(context.args) >= 3:
            self._register_user(context.args[1], context.args[2], context)
        else:
            context.respond(
                "Usage: `user [list|show <user>|set <user> [--admin|--no-admin] [--bother|--no-bother]|register <user> <switch>]`"
            )

    def _list_users(self, context: CommandContext) -> None:
        """List all users"""
        users = self.database_service.get_all_users()
        if not users:
            context.respond("No users found.")
            return

        user_list = []
        for user in users:
            admin_badge = " 👑" if user.is_admin else ""
            switch_info = (
                f" (switch: `{user.switch_id}`)"
                if user.switch_id and user.switch_id.strip()
                else ""
            )
            user_list.append(f"• <@{user.slack_user_id}>{admin_badge}{switch_info}")

        context.respond("*All Users:*\n" + "\n".join(user_list))

    def _show_user(self, target_user: str, context: CommandContext) -> None:
        """Show detailed user information"""
        target_user_id = self._resolve_user_identifier(target_user, context)

        if not target_user_id:
            context.respond(f"Could not find user {target_user}")
            return

        user = self.database_service.get_user(target_user_id)

        if not user:
            context.respond(f"User <@{target_user_id}> not found.")
            return

        admin_status = "Yes 👑" if user.is_admin else "No"
        botherable_status = "Yes" if user.botherable else "No"
        switch_status = (
            user.switch_id if user.switch_id and user.switch_id.strip() else "None"
        )

        context.respond(f"""*User Details:*
• User: <@{user.slack_user_id}>
• Admin: {admin_status}
• Botherable: {botherable_status}
• Switch: `{switch_status}`
• Created: {user.created_at}""")

    def _set_user(self, args: list, context: CommandContext) -> None:
        """Set user properties using argparse"""
        try:
            parsed_args = self.set_parser.parse_args(args)
        except Exception as e:
            error_msg = str(e)
            context.respond(f"Error parsing arguments: {error_msg}")
            return

        target_user_id = self._resolve_user_identifier(parsed_args.user, context)
        if not target_user_id:
            context.respond(f"Could not find user {parsed_args.user}")
            return

        # Track what changes were made for response message
        changes = []

        # Handle admin setting
        if parsed_args.admin:
            if self.database_service.set_admin(target_user_id, True):
                changes.append("granted admin privileges")
            else:
                context.respond("Failed to grant admin privileges.")
                return
        elif parsed_args.no_admin:
            if self.database_service.set_admin(target_user_id, False):
                changes.append("revoked admin privileges")
            else:
                context.respond("Failed to revoke admin privileges.")
                return

        # Handle bother setting
        if parsed_args.bother:
            if self.database_service.set_botherable(target_user_id, True):
                changes.append("enabled bother notifications")
            else:
                context.respond("Failed to enable bother notifications.")
                return
        elif parsed_args.no_bother:
            if self.database_service.set_botherable(target_user_id, False):
                changes.append("disabled bother notifications")
            else:
                context.respond("Failed to disable bother notifications.")
                return

        # Send success message
        if changes:
            change_text = " and ".join(changes)
            context.respond(f"Successfully {change_text} for <@{target_user_id}>.")
        else:
            context.respond(
                "No changes specified. Use --admin/--no-admin or --bother/--no-bother."
            )

    def _register_user(
        self, user_str: str, switch_id: str, context: CommandContext
    ) -> None:
        """Register a switch to a specific user (admin only)"""
        from ..utils.formatters import clean_switch_id

        target_user_id = self._resolve_user_identifier(user_str, context)
        if not target_user_id:
            context.respond(f"Could not find user {user_str}")
            return

        switch_id = clean_switch_id(switch_id)

        try:
            if self.database_service.register_switch(target_user_id, switch_id):
                context.respond(
                    f"Successfully registered switch `{switch_id}` to <@{target_user_id}>."
                )
            else:
                context.respond(
                    "Failed to register switch. Make sure the user has an account."
                )
        except Exception as e:
            # Use the ErrorHandler for exceptions from the enhanced database service
            from ..error_handler import ErrorHandler

            ErrorHandler.handle_command_error(e, context)

    def _resolve_user_identifier(
        self, user_str: str, context: CommandContext
    ) -> str | None:
        """Resolve a user identifier to a Slack user ID"""
        return _resolve_user_identifier(user_str, context, self.database_service)


class GroupCommand(BaseCommand):
    """Handle group management commands (admin only)"""

    def __init__(self, database_service: DatabaseServiceInterface):
        self.database_service = database_service

    def can_execute(self, context: CommandContext) -> bool:
        """Only admins can manage groups"""
        return self.database_service.is_admin(context.user_id)

    def execute(self, context: CommandContext) -> None:
        """Execute group command"""
        if not context.args:
            context.respond("Usage: `group [list|show|create|destroy|add|remove] ...`")
            return

        cmd = context.args[0].lower()

        if cmd == "list":
            self._list_groups(context)
        elif cmd == "show" and len(context.args) >= 2:
            self._show_group(context.args[1], context)
        elif cmd == "create" and len(context.args) >= 2:
            self._create_group(context.args[1], context)
        elif cmd == "destroy" and len(context.args) >= 2:
            self._destroy_group(context.args[1], context)
        elif cmd == "add" and len(context.args) >= 3:
            self._add_users_to_group(context.args[1], context.args[2:], context)
        elif cmd == "remove" and len(context.args) >= 3:
            self._remove_users_from_group(context.args[1], context.args[2:], context)
        else:
            context.respond(
                "Usage: `group [list|show <name>|create <name>|destroy <name>|add <name> <user> ...|remove <name> <user> ...]`"
            )

    def _list_groups(self, context: CommandContext) -> None:
        """List all groups"""
        groups = self.database_service.get_all_groups()
        if not groups:
            context.respond("No groups found.")
            return

        group_list = []
        for group in groups:
            member_count = len(self.database_service.get_group_members(group))
            group_list.append(f"• `{group}` ({member_count} members)")

        context.respond("*All Groups:*\n" + "\n".join(group_list))

    def _show_group(self, group_name: str, context: CommandContext) -> None:
        """Show group members"""
        members = self.database_service.get_group_members(group_name)

        if not members:
            if group_name.lower() == "all":
                context.respond(
                    f"Group `{group_name}` has no members (no users have registered switches)."
                )
            else:
                context.respond(f"Group `{group_name}` not found or has no members.")
            return

        member_list = [f"• <@{member_id}>" for member_id in members]
        if group_name.lower() == "all":
            context.respond(
                f"*Members of group `{group_name}` (all users with registered switches):*\n"
                + "\n".join(member_list)
            )
        else:
            context.respond(
                f"*Members of group `{group_name}`:*\n" + "\n".join(member_list)
            )

    def _create_group(self, group_name: str, context: CommandContext) -> None:
        """Create a new group"""
        if self.database_service.create_group(group_name):
            context.respond(f"Created group `{group_name}`.")
        else:
            context.respond(
                f"Failed to create group `{group_name}`. It may already exist."
            )

    def _destroy_group(self, group_name: str, context: CommandContext) -> None:
        """Destroy a group"""
        if group_name.lower() == "all":
            context.respond("Cannot destroy the special `all` group.")
            return

        if self.database_service.delete_group(group_name):
            context.respond(f"Destroyed group `{group_name}`.")
        else:
            context.respond(
                f"Failed to destroy group `{group_name}`. It may not exist."
            )

    def _add_users_to_group(
        self, group_name: str, users: list, context: CommandContext
    ) -> None:
        """Add users to a group"""
        if group_name.lower() == "all":
            context.respond("Cannot add users to the special `all` group.")
            return

        added_count = 0
        for user_str in users:
            user_id = self._resolve_user_identifier(user_str, context)
            if user_id and self.database_service.add_user_to_group(group_name, user_id):
                added_count += 1

        context.respond(f"Added {added_count} user(s) to group `{group_name}`.")

    def _remove_users_from_group(
        self, group_name: str, users: list, context: CommandContext
    ) -> None:
        """Remove users from a group"""
        if group_name.lower() == "all":
            context.respond("Cannot remove users from the special `all` group.")
            return

        removed_count = 0
        for user_str in users:
            user_id = self._resolve_user_identifier(user_str, context)
            if user_id and self.database_service.remove_user_from_group(
                group_name, user_id
            ):
                removed_count += 1

        context.respond(f"Removed {removed_count} user(s) from group `{group_name}`.")

    def _resolve_user_identifier(
        self, user_str: str, context: CommandContext
    ) -> str | None:
        """Resolve a user identifier to a Slack user ID"""
        return _resolve_user_identifier(user_str, context, self.database_service)


def _resolve_user_identifier(
    user_str: str, context: CommandContext, database_service: DatabaseServiceInterface
) -> str | None:
    """Shared helper function to resolve user identifiers"""
    # Handle direct user ID format <@U12345>
    if user_str.startswith("<@") and user_str.endswith(">"):
        user_id = user_str[2:-1]
        try:
            response = context.client.users_info(user=user_id)
            if response["ok"]:
                # Add to database if they don't exist
                if not database_service.get_user(user_id):
                    username = response["user"].get("name", user_id)
                    database_service.add_user(user_id, username)
                return user_id
        except Exception:
            return None

    # Handle username format @username or username
    username = user_str[1:] if user_str.startswith("@") else user_str

    # First check if we already have this user in our database
    all_users = database_service.get_all_users()
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
                    if not database_service.get_user(user_id):
                        database_service.add_user(user_id, username)
                    return user_id
    except Exception as e:
        logger.warning(f"Error looking up user '{username}' via API: {e}")

    return None
