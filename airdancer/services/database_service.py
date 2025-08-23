"""Enhanced database service with business logic"""

import os
import logging
from typing import List, Optional, Dict

from .interfaces import DatabaseServiceInterface
from ..models.entities import User, Switch, SwitchWithOwner, Owner
from ..models.database import DatabaseManager
from ..exceptions import (
    DatabaseError,
    UserNotFoundError,
    SwitchAlreadyRegisteredError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class DatabaseService(DatabaseServiceInterface):
    """Enhanced database service with business logic and validation"""

    def __init__(self, database_path: str = "airdancer.db"):
        # Convert relative paths to absolute paths relative to current working directory
        if not os.path.isabs(database_path):
            database_path = os.path.abspath(database_path)
        self._db_manager = DatabaseManager(database_path)
        self._user_cache: Dict[
            str, User
        ] = {}  # Simple caching for frequently accessed users

    def add_user(
        self,
        slack_user_id: str,
        username: str,
        is_admin: bool = False,
        botherable: bool = True,
    ) -> bool:
        """Add a new user to the database with validation"""
        # Validate inputs
        if not slack_user_id or not slack_user_id.strip():
            raise ValidationError("slack_user_id", slack_user_id, "cannot be empty")
        if not username or not username.strip():
            raise ValidationError("username", username, "cannot be empty")

        slack_user_id = slack_user_id.strip()
        username = username.strip()

        try:
            result = self._db_manager.add_user(slack_user_id, username, is_admin)
            if result:
                # Clear cache entry if it exists
                self._user_cache.pop(slack_user_id, None)
                logger.info(
                    f"Added user: {username} ({slack_user_id}) admin={is_admin}"
                )
            return result
        except Exception as e:
            logger.error(f"Failed to add user {username} ({slack_user_id}): {e}")
            raise DatabaseError("add_user", str(e))

    def get_user(self, slack_user_id: str) -> User | None:
        """Get user by Slack user ID with caching"""
        if not slack_user_id or not slack_user_id.strip():
            return None

        slack_user_id = slack_user_id.strip()

        # Check cache first
        if slack_user_id in self._user_cache:
            return self._user_cache[slack_user_id]

        try:
            user = self._db_manager.get_user(slack_user_id)
            if user:
                # Cache the result
                self._user_cache[slack_user_id] = user
            return user
        except Exception as e:
            logger.error(f"Failed to get user {slack_user_id}: {e}")
            raise DatabaseError("get_user", str(e))

    def is_admin(self, slack_user_id: str) -> bool:
        """Check if user is admin"""
        return self._db_manager.is_admin(slack_user_id)

    def set_admin(self, slack_user_id: str, is_admin: bool) -> bool:
        """Set admin status for user"""
        result = self._db_manager.set_admin(slack_user_id, is_admin)
        if result:
            # Clear cache entry since user data changed
            self._user_cache.pop(slack_user_id, None)
        return result

    def set_botherable(self, slack_user_id: str, botherable: bool) -> bool:
        """Set botherable status for user"""
        result = self._db_manager.set_botherable(slack_user_id, botherable)
        if result:
            # Clear cache entry since user data changed
            self._user_cache.pop(slack_user_id, None)
        return result

    def register_switch(self, slack_user_id: str, switch_id: str) -> bool:
        """Register a switch to a user with comprehensive validation"""
        # Validate inputs
        if not slack_user_id or not slack_user_id.strip():
            raise ValidationError("slack_user_id", slack_user_id, "cannot be empty")
        if not switch_id or not switch_id.strip():
            raise ValidationError("switch_id", switch_id, "cannot be empty")

        slack_user_id = slack_user_id.strip()
        switch_id = switch_id.strip()

        # Business logic validation
        if self.is_switch_registered(switch_id):
            owner = self.get_switch_owner(switch_id)
            if owner and owner.slack_user_id != slack_user_id:
                raise SwitchAlreadyRegisteredError(switch_id, owner.slack_user_id)

        # Check if user exists
        user = self.get_user(slack_user_id)
        if not user:
            raise UserNotFoundError(slack_user_id)

        try:
            result = self._db_manager.register_switch(slack_user_id, switch_id)
            if result:
                # Clear user cache since switch_id changed
                self._user_cache.pop(slack_user_id, None)
                logger.info(f"Registered switch {switch_id} to user {slack_user_id}")
            return result
        except Exception as e:
            logger.error(
                f"Failed to register switch {switch_id} to user {slack_user_id}: {e}"
            )
            raise DatabaseError("register_switch", str(e))

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

    def clear_user_cache(self, slack_user_id: Optional[str] = None) -> None:
        """Clear user cache for specific user or all users"""
        if slack_user_id:
            self._user_cache.pop(slack_user_id, None)
        else:
            self._user_cache.clear()

    def get_user_with_switch_validation(self, slack_user_id: str) -> User:
        """Get user and validate they have a registered switch"""
        user = self.get_user(slack_user_id)
        if not user:
            raise UserNotFoundError(slack_user_id)

        if not user.switch_id or not user.switch_id.strip():
            raise ValidationError("switch_id", "", "User has no registered switch")

        return user

    def register_switch_for_new_user(
        self, slack_user_id: str, username: str, switch_id: str, is_admin: bool = False
    ) -> bool:
        """Register a switch for a new user (creates user if needed)"""
        # Create user if they don't exist
        if not self.get_user(slack_user_id):
            if not self.add_user(slack_user_id, username, is_admin):
                raise DatabaseError(
                    "register_switch_for_new_user", "Failed to create user"
                )

        # Register the switch
        return self.register_switch(slack_user_id, switch_id)
