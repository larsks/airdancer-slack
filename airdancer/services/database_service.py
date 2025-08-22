"""Database service implementation"""

import logging
from typing import List
from datetime import datetime

from .interfaces import DatabaseServiceInterface
from ..models.entities import User, Switch, SwitchWithOwner, Owner
from ..models.database import DatabaseManager

logger = logging.getLogger(__name__)


class DatabaseService(DatabaseServiceInterface):
    """Service for database operations using the existing DatabaseManager"""

    def __init__(self, database_path: str = "airdancer.db"):
        self._db_manager = DatabaseManager(database_path)

    def add_user(
        self, slack_user_id: str, username: str, is_admin: bool = False
    ) -> bool:
        """Add a new user to the database"""
        return self._db_manager.add_user(slack_user_id, username, is_admin)

    def get_user(self, slack_user_id: str) -> User | None:
        """Get user by Slack user ID"""
        user_dict = self._db_manager.get_user(slack_user_id)
        if user_dict:
            return User(
                slack_user_id=user_dict["slack_user_id"],
                username=user_dict["username"],
                is_admin=user_dict["is_admin"],
                switch_id=user_dict["switch_id"],
                created_at=datetime.fromisoformat(user_dict["created_at"]),
            )
        return None

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
        owner_dict = self._db_manager.get_switch_owner(switch_id)
        if owner_dict:
            return Owner(
                slack_user_id=owner_dict["slack_user_id"],
                username=owner_dict["username"],
                is_admin=owner_dict["is_admin"],
            )
        return None

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
        switches_dict = self._db_manager.get_all_switches()
        return [
            Switch(
                switch_id=switch["switch_id"],
                status=switch["status"],
                power_state=switch["power_state"],
                last_seen=datetime.fromisoformat(switch["last_seen"]),
                device_info=switch["device_info"],
            )
            for switch in switches_dict
        ]

    def get_all_switches_with_owners(self) -> List[SwitchWithOwner]:
        """Get all switches with owner information"""
        switches_dict = self._db_manager.get_all_switches_with_owners()
        result = []

        for switch in switches_dict:
            owner = None
            if switch["owner"]:
                owner = Owner(
                    slack_user_id=switch["owner"]["slack_user_id"],
                    username=switch["owner"]["username"],
                    is_admin=switch["owner"]["is_admin"],
                )

            result.append(
                SwitchWithOwner(
                    switch_id=switch["switch_id"],
                    status=switch["status"],
                    power_state=switch["power_state"],
                    last_seen=datetime.fromisoformat(switch["last_seen"]),
                    device_info=switch["device_info"],
                    owner=owner,
                )
            )

        return result

    def get_all_users(self) -> List[User]:
        """Get all users"""
        users_dict = self._db_manager.get_all_users()
        return [
            User(
                slack_user_id=user["slack_user_id"],
                username=user["username"],
                is_admin=user["is_admin"],
                switch_id=user["switch_id"],
                created_at=datetime.fromisoformat(user["created_at"]),
            )
            for user in users_dict
        ]

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
