"""Database service implementation"""

import os
import logging
from typing import List

from .interfaces import DatabaseServiceInterface
from ..models.entities import User, Switch, SwitchWithOwner, Owner
from ..models.database import DatabaseManager

logger = logging.getLogger(__name__)


class DatabaseService(DatabaseServiceInterface):
    """Service for database operations using the existing DatabaseManager"""

    def __init__(self, database_path: str = "airdancer.db"):
        # Convert relative paths to absolute paths relative to current working directory
        if not os.path.isabs(database_path):
            database_path = os.path.abspath(database_path)
        self._db_manager = DatabaseManager(database_path)

    def add_user(
        self, slack_user_id: str, username: str, is_admin: bool = False
    ) -> bool:
        """Add a new user to the database"""
        return self._db_manager.add_user(slack_user_id, username, is_admin)

    def get_user(self, slack_user_id: str) -> User | None:
        """Get user by Slack user ID"""
        return self._db_manager.get_user(slack_user_id)

    def is_admin(self, slack_user_id: str) -> bool:
        """Check if user is admin"""
        return self._db_manager.is_admin(slack_user_id)

    def set_admin(self, slack_user_id: str, is_admin: bool) -> bool:
        """Set admin status for user"""
        return self._db_manager.set_admin(slack_user_id, is_admin)

    def register_switch(self, slack_user_id: str, switch_id: str) -> bool:
        """Register a switch to a user"""
        return self._db_manager.register_switch(slack_user_id, switch_id)

    def unregister_user(self, slack_user_id: str) -> bool:
        """Remove user from database"""
        return self._db_manager.unregister_user(slack_user_id)

    def is_switch_registered(self, switch_id: str) -> bool:
        """Check if switch is registered to any user"""
        return self._db_manager.is_switch_registered(switch_id)

    def get_switch_owner(self, switch_id: str) -> Owner | None:
        """Get the owner of a switch"""
        return self._db_manager.get_switch_owner(switch_id)

    def add_switch(self, switch_id: str, device_info: str = "") -> bool:
        """Add a switch to the database"""
        return self._db_manager.add_switch(switch_id, device_info)

    def update_switch_status(self, switch_id: str, status: str) -> bool:
        """Update switch online/offline status"""
        return self._db_manager.update_switch_status(switch_id, status)

    def update_switch_power_state(self, switch_id: str, power_state: str) -> bool:
        """Update switch power state"""
        return self._db_manager.update_switch_power_state(switch_id, power_state)

    def get_all_switches(self) -> List[Switch]:
        """Get all switches"""
        return self._db_manager.get_all_switches()

    def get_all_switches_with_owners(self) -> List[SwitchWithOwner]:
        """Get all switches with owner information"""
        return self._db_manager.get_all_switches_with_owners()

    def get_all_users(self) -> List[User]:
        """Get all users"""
        return self._db_manager.get_all_users()

    def create_group(self, group_name: str) -> bool:
        """Create a new group"""
        return self._db_manager.create_group(group_name)

    def delete_group(self, group_name: str) -> bool:
        """Delete a group"""
        return self._db_manager.delete_group(group_name)

    def add_user_to_group(self, group_name: str, slack_user_id: str) -> bool:
        """Add user to group"""
        return self._db_manager.add_user_to_group(group_name, slack_user_id)

    def remove_user_from_group(self, group_name: str, slack_user_id: str) -> bool:
        """Remove user from group"""
        return self._db_manager.remove_user_from_group(group_name, slack_user_id)

    def get_group_members(self, group_name: str) -> List[str]:
        """Get members of a group"""
        return self._db_manager.get_group_members(group_name)

    def get_all_groups(self) -> List[str]:
        """Get all group names"""
        return self._db_manager.get_all_groups()
