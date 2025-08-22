"""Service interfaces for dependency injection"""

from abc import ABC, abstractmethod
from typing import List
from ..models.entities import User, Switch, SwitchWithOwner, Owner


class DatabaseServiceInterface(ABC):
    """Interface for database operations"""

    @abstractmethod
    def add_user(
        self, slack_user_id: str, username: str, is_admin: bool = False
    ) -> bool:
        """Add a new user to the database"""
        pass

    @abstractmethod
    def get_user(self, slack_user_id: str) -> User | None:
        """Get user by Slack user ID"""
        pass

    @abstractmethod
    def is_admin(self, slack_user_id: str) -> bool:
        """Check if user is admin"""
        pass

    @abstractmethod
    def set_admin(self, slack_user_id: str, is_admin: bool) -> bool:
        """Set admin status for user"""
        pass

    @abstractmethod
    def register_switch(self, slack_user_id: str, switch_id: str) -> bool:
        """Register a switch to a user"""
        pass

    @abstractmethod
    def unregister_user(self, slack_user_id: str) -> bool:
        """Remove user from database"""
        pass

    @abstractmethod
    def is_switch_registered(self, switch_id: str) -> bool:
        """Check if switch is registered to any user"""
        pass

    @abstractmethod
    def get_switch_owner(self, switch_id: str) -> Owner | None:
        """Get the owner of a switch"""
        pass

    @abstractmethod
    def add_switch(self, switch_id: str, device_info: str = "") -> bool:
        """Add a switch to the database"""
        pass

    @abstractmethod
    def update_switch_status(self, switch_id: str, status: str) -> bool:
        """Update switch online/offline status"""
        pass

    @abstractmethod
    def update_switch_power_state(self, switch_id: str, power_state: str) -> bool:
        """Update switch power state"""
        pass

    @abstractmethod
    def get_all_switches(self) -> List[Switch]:
        """Get all switches"""
        pass

    @abstractmethod
    def get_all_switches_with_owners(self) -> List[SwitchWithOwner]:
        """Get all switches with owner information"""
        pass

    @abstractmethod
    def get_all_users(self) -> List[User]:
        """Get all users"""
        pass

    @abstractmethod
    def create_group(self, group_name: str) -> bool:
        """Create a new group"""
        pass

    @abstractmethod
    def delete_group(self, group_name: str) -> bool:
        """Delete a group"""
        pass

    @abstractmethod
    def add_user_to_group(self, group_name: str, slack_user_id: str) -> bool:
        """Add user to group"""
        pass

    @abstractmethod
    def remove_user_from_group(self, group_name: str, slack_user_id: str) -> bool:
        """Remove user from group"""
        pass

    @abstractmethod
    def get_group_members(self, group_name: str) -> List[str]:
        """Get members of a group"""
        pass

    @abstractmethod
    def get_all_groups(self) -> List[str]:
        """Get all group names"""
        pass


class MQTTServiceInterface(ABC):
    """Interface for MQTT operations"""

    @abstractmethod
    def start(self) -> None:
        """Start the MQTT client"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop the MQTT client"""
        pass

    @abstractmethod
    def send_command(self, switch_id: str, command: str, value: str = "") -> bool:
        """Send a command to a switch"""
        pass

    @abstractmethod
    def bother_switch(self, switch_id: str, duration: int = 15) -> bool:
        """Activate switch for specified duration"""
        pass

    @abstractmethod
    def switch_on(self, switch_id: str) -> bool:
        """Turn switch on"""
        pass

    @abstractmethod
    def switch_off(self, switch_id: str) -> bool:
        """Turn switch off"""
        pass

    @abstractmethod
    def switch_toggle(self, switch_id: str) -> bool:
        """Toggle switch state"""
        pass

    @abstractmethod
    def query_power_state(self, switch_id: str) -> bool:
        """Query current power state of switch"""
        pass
