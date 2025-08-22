"""Type-safe entity models using Pydantic"""

from datetime import datetime
from pydantic import BaseModel, field_validator


class User(BaseModel):
    """User entity with validation"""

    slack_user_id: str
    username: str
    is_admin: bool = False
    switch_id: str | None = None
    created_at: datetime

    @field_validator("slack_user_id")
    @classmethod
    def validate_slack_user_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Slack user ID cannot be empty")
        # Slack user IDs start with U or W and are typically 9+ characters
        v = v.strip()
        if not (v.startswith(("U", "W")) and len(v) >= 9):
            raise ValueError("Invalid Slack user ID format")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Username cannot be empty")
        return v.strip()

    @field_validator("switch_id")
    @classmethod
    def validate_switch_id(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class Switch(BaseModel):
    """Switch entity with validation"""

    switch_id: str
    status: str = "offline"
    power_state: str = "unknown"
    last_seen: datetime
    device_info: str | None = None

    @field_validator("switch_id")
    @classmethod
    def validate_switch_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Switch ID cannot be empty")
        return v.strip()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed_statuses = ["online", "offline"]
        if v not in allowed_statuses:
            raise ValueError(f"Status must be one of {allowed_statuses}")
        return v

    @field_validator("power_state")
    @classmethod
    def validate_power_state(cls, v: str) -> str:
        allowed_states = ["ON", "OFF", "unknown"]
        if v not in allowed_states:
            raise ValueError(f"Power state must be one of {allowed_states}")
        return v


class Group(BaseModel):
    """Group entity with validation"""

    group_name: str
    created_at: datetime

    @field_validator("group_name")
    @classmethod
    def validate_group_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Group name cannot be empty")
        v = v.strip()
        # Basic validation for group names
        if len(v) < 1 or len(v) > 50:
            raise ValueError("Group name must be between 1 and 50 characters")
        return v


class GroupMember(BaseModel):
    """Group membership entity"""

    group_name: str
    slack_user_id: str

    @field_validator("group_name", "slack_user_id")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class Owner(BaseModel):
    """Switch owner information"""

    slack_user_id: str
    username: str
    is_admin: bool


class SwitchWithOwner(BaseModel):
    """Switch with owner information"""

    switch_id: str
    status: str
    power_state: str
    last_seen: datetime
    device_info: str | None = None
    owner: Owner | None = None


class SwitchCommand(BaseModel):
    """MQTT switch command with validation"""

    switch_id: str
    command: str
    value: str | None = None

    @field_validator("switch_id")
    @classmethod
    def validate_switch_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Switch ID cannot be empty")
        return v.strip()

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        allowed_commands = ["Power", "Power1", "TimedPower1"]
        if v not in allowed_commands:
            raise ValueError(f"Command must be one of {allowed_commands}")
        return v


class BotherRequest(BaseModel):
    """Request to bother a user or group"""

    target: str
    duration: int = 15
    requester_user_id: str

    @field_validator("target")
    @classmethod
    def validate_target(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Target cannot be empty")
        return v.strip()

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Duration must be positive")
        if v > 3600:  # Max 1 hour
            raise ValueError("Duration cannot exceed 3600 seconds")
        return v

    @field_validator("requester_user_id")
    @classmethod
    def validate_requester(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Requester user ID cannot be empty")
        return v.strip()
