"""Admin command handlers"""

import logging
from typing import Dict
from .base import BaseCommand, CommandContext
from ..services.interfaces import DatabaseServiceInterface, MQTTServiceInterface

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
        """List all switches"""
        switches = self.database_service.get_all_switches_with_owners()

        if not switches:
            context.respond("No switches have been discovered.")
            return

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

            owner_text = ""
            if switch.owner:
                owner_text = f" - <@{switch.owner.slack_user_id}>"
                if switch.owner.is_admin:
                    owner_text += " 👑"
            else:
                owner_text = " - _Unregistered_"

            switch_list.append(
                f"• `{switch.switch_id}` {status_emoji}{power_emoji}{owner_text}"
            )

        context.respond("*Discovered Switches:*\n" + "\n".join(switch_list))

    def _show_switch(self, switch_id: str, context: CommandContext) -> None:
        """Show detailed switch information"""
        # Implementation would be similar to the current switch show command
        context.respond(
            f"Detailed info for switch `{switch_id}` (implementation needed)"
        )

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

    def can_execute(self, context: CommandContext) -> bool:
        """Only admins can manage users"""
        return self.database_service.is_admin(context.user_id)

    def execute(self, context: CommandContext) -> None:
        """Execute user command"""
        context.respond("User management commands (implementation needed)")


class GroupCommand(BaseCommand):
    """Handle group management commands (admin only)"""

    def __init__(self, database_service: DatabaseServiceInterface):
        self.database_service = database_service

    def can_execute(self, context: CommandContext) -> bool:
        """Only admins can manage groups"""
        return self.database_service.is_admin(context.user_id)

    def execute(self, context: CommandContext) -> None:
        """Execute group command"""
        context.respond("Group management commands (implementation needed)")
