"""Database ORM models using PonyORM"""

from datetime import datetime
from pony.orm import Database, Required, Optional, Set as PonySet

# Initialize PonyORM database
db = Database()


class DatabaseUser(db.Entity):
    """PonyORM User entity"""

    _table_ = "user"
    slack_user_id = Required(str, unique=True)
    username = Required(str)
    is_admin = Required(bool, default=False)
    switch_id = Optional(str)
    created_at = Required(datetime, default=datetime.now)
    groups = PonySet("DatabaseGroupMember")


class DatabaseSwitch(db.Entity):
    """PonyORM Switch entity"""

    _table_ = "switch"
    switch_id = Required(str, unique=True)
    status = Required(str, default="offline")
    power_state = Required(str, default="unknown")
    last_seen = Required(datetime, default=datetime.now)
    device_info = Optional(str)


class DatabaseGroup(db.Entity):
    """PonyORM Group entity"""

    _table_ = "group"
    group_name = Required(str, unique=True)
    created_at = Required(datetime, default=datetime.now)
    members = PonySet("DatabaseGroupMember")


class DatabaseGroupMember(db.Entity):
    """PonyORM GroupMember entity"""

    _table_ = "groupmember"
    group = Required(DatabaseGroup)
    user = Required(DatabaseUser)


