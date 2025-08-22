import json
import logging
from datetime import datetime
from typing import TypedDict

from pony.orm import (
    Database,
    Required,
    Optional,
    Set as PonySet,
    db_session,
)

logger = logging.getLogger(__name__)


# Type definitions for database objects
class UserDict(TypedDict):
    slack_user_id: str
    username: str
    is_admin: bool
    switch_id: str
    created_at: str


class SwitchDict(TypedDict):
    switch_id: str
    status: str
    power_state: str
    last_seen: str
    device_info: str


class OwnerDict(TypedDict):
    slack_user_id: str
    username: str
    is_admin: bool


class SwitchWithOwnerDict(TypedDict):
    switch_id: str
    status: str
    power_state: str
    last_seen: str
    device_info: str
    owner: OwnerDict | None


# Initialize PonyORM database
db = Database()


class User(db.Entity):
    slack_user_id = Required(str, unique=True)
    username = Required(str)
    is_admin = Required(bool, default=False)
    switch_id = Optional(str)
    created_at = Required(datetime, default=datetime.now)
    groups = PonySet("GroupMember")


class Switch(db.Entity):
    switch_id = Required(str, unique=True)
    status = Required(str, default="offline")
    power_state = Required(str, default="unknown")
    last_seen = Required(datetime, default=datetime.now)
    device_info = Optional(str)


class Group(db.Entity):
    group_name = Required(str, unique=True)
    created_at = Required(datetime, default=datetime.now)
    members = PonySet("GroupMember")


class GroupMember(db.Entity):
    group = Required(Group)
    user = Required(User)


class DatabaseManager:
    def __init__(self, db_path: str = "airdancer.db"):
        db.bind("sqlite", db_path)
        db.generate_mapping(create_tables=True)

    @db_session
    def add_user(
        self, slack_user_id: str, username: str, is_admin: bool = False
    ) -> bool:
        try:
            user = User.get(slack_user_id=slack_user_id)
            if user:
                user.username = username
                user.is_admin = is_admin
            else:
                User(slack_user_id=slack_user_id, username=username, is_admin=is_admin)
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False

    @db_session
    def get_user(self, slack_user_id: str) -> UserDict | None:
        user = User.get(slack_user_id=slack_user_id)
        if user:
            return {
                "slack_user_id": user.slack_user_id,
                "username": user.username,
                "is_admin": user.is_admin,
                "switch_id": user.switch_id,
                "created_at": user.created_at.isoformat(),
            }
        return None

    def is_admin(self, slack_user_id: str) -> bool:
        user = self.get_user(slack_user_id)
        return bool(user and user["is_admin"])

    @db_session
    def set_admin(self, slack_user_id: str, is_admin: bool) -> bool:
        try:
            user = User.get(slack_user_id=slack_user_id)
            if user:
                user.is_admin = is_admin
                return True
            return False
        except Exception as e:
            logger.error(f"Error setting admin status: {e}")
            return False

    @db_session
    def register_switch(self, slack_user_id: str, switch_id: str) -> bool:
        try:
            user = User.get(slack_user_id=slack_user_id)
            if user:
                user.switch_id = switch_id
                return True
            return False
        except Exception as e:
            logger.error(f"Error registering switch: {e}")
            return False

    @db_session
    def unregister_user(self, slack_user_id: str) -> bool:
        try:
            user = User.get(slack_user_id=slack_user_id)
            if user:
                user.delete()
                return True
            return False
        except Exception as e:
            logger.error(f"Error unregistering user: {e}")
            return False

    @db_session
    def add_switch(self, switch_id: str, device_info: str = "") -> bool:
        try:
            switch = Switch.get(switch_id=switch_id)
            if switch:
                switch.status = "online"
                switch.device_info = device_info
                switch.last_seen = datetime.now()
            else:
                Switch(switch_id=switch_id, status="online", device_info=device_info)
            return True
        except Exception as e:
            logger.error(f"Error adding switch: {e}")
            return False

    @db_session
    def update_switch_status(self, switch_id: str, status: str) -> bool:
        try:
            switch = Switch.get(switch_id=switch_id)
            if switch:
                switch.status = status
                switch.last_seen = datetime.now()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating switch status: {e}")
            return False

    @db_session
    def update_switch_power_state(self, switch_id: str, power_state: str) -> bool:
        try:
            switch = Switch.get(switch_id=switch_id)
            if switch:
                switch.power_state = power_state
                switch.last_seen = datetime.now()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating switch power state: {e}")
            return False

    @db_session
    def get_all_switches(self) -> list[SwitchDict]:
        switches = list(Switch.select())
        return [
            {
                "switch_id": switch.switch_id,
                "status": switch.status,
                "power_state": switch.power_state,
                "last_seen": switch.last_seen.isoformat(),
                "device_info": switch.device_info,
            }
            for switch in switches
        ]

    @db_session
    def get_all_switches_with_owners(self) -> list[SwitchWithOwnerDict]:
        """Get all switches with their owner information using a join"""
        # Get all switches with left join to users
        query = """
        SELECT s.switch_id, s.status, s.power_state, s.last_seen, s.device_info,
               u.slack_user_id, u.username, u.is_admin
        FROM switch s
        LEFT JOIN user u ON s.switch_id = u.switch_id
        ORDER BY s.switch_id
        """

        results = []
        for row in db.execute(query):
            switch_data = {
                "switch_id": row[0],
                "status": row[1],
                "power_state": row[2],
                "last_seen": row[3],
                "device_info": row[4],
                "owner": None,
            }

            # If there's an owner (user data is not null)
            if row[5]:  # slack_user_id is not None
                switch_data["owner"] = {
                    "slack_user_id": row[5],
                    "username": row[6],
                    "is_admin": bool(row[7]),
                }

            results.append(switch_data)

        return results

    @db_session
    def get_all_users(self) -> list[UserDict]:
        users = list(User.select())
        return [
            {
                "slack_user_id": user.slack_user_id,
                "username": user.username,
                "is_admin": user.is_admin,
                "switch_id": user.switch_id,
                "created_at": user.created_at.isoformat(),
            }
            for user in users
        ]

    @db_session
    def create_group(self, group_name: str) -> bool:
        try:
            if not Group.get(group_name=group_name):
                Group(group_name=group_name)
                return True
            return False
        except Exception as e:
            logger.error(f"Error creating group: {e}")
            return False

    @db_session
    def delete_group(self, group_name: str) -> bool:
        try:
            group = Group.get(group_name=group_name)
            if group:
                group.delete()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting group: {e}")
            return False

    @db_session
    def add_user_to_group(self, group_name: str, slack_user_id: str) -> bool:
        try:
            group = Group.get(group_name=group_name)
            user = User.get(slack_user_id=slack_user_id)
            if group and user:
                # Check if membership already exists
                existing = GroupMember.get(group=group, user=user)
                if not existing:
                    GroupMember(group=group, user=user)
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding user to group: {e}")
            return False

    @db_session
    def remove_user_from_group(self, group_name: str, slack_user_id: str) -> bool:
        try:
            group = Group.get(group_name=group_name)
            user = User.get(slack_user_id=slack_user_id)
            if group and user:
                membership = GroupMember.get(group=group, user=user)
                if membership:
                    membership.delete()
                    return True
            return False
        except Exception as e:
            logger.error(f"Error removing user from group: {e}")
            return False

    def get_group_members(self, group_name: str) -> list[str]:
        # Handle special 'all' group
        if group_name.lower() == "all":
            return [
                user["slack_user_id"]
                for user in self.get_all_users()
                if user["switch_id"] and user["switch_id"].strip()
            ]

        with db_session:
            group = Group.get(group_name=group_name)
            if group:
                return [member.user.slack_user_id for member in group.members]
            return []

    @db_session
    def get_all_groups(self) -> list[str]:
        groups = [group.group_name for group in list(Group.select())]

        # Always include the special 'all' group
        if "all" not in [g.lower() for g in groups]:
            groups.append("all")

        return groups

    @db_session
    def get_switch_owner(self, switch_id: str) -> OwnerDict | None:
        """Get the user who owns the specified switch"""
        user = User.get(switch_id=switch_id)
        if user:
            return {
                "slack_user_id": user.slack_user_id,
                "username": user.username,
                "is_admin": user.is_admin,
            }
        return None
