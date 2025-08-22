"""Tests for Pydantic models and entities"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from airdancer.models.entities import (
    User,
    Switch,
    Group,
    GroupMember,
    Owner,
    SwitchWithOwner,
    SwitchCommand,
    BotherRequest,
)


class TestUser:
    """Test User entity"""

    def test_valid_user(self):
        """Test creating a valid user"""
        now = datetime.now()
        user = User(
            slack_user_id="U12345678",
            username="testuser",
            is_admin=False,
            switch_id="switch001",
            created_at=now,
        )

        assert user.slack_user_id == "U12345678"
        assert user.username == "testuser"
        assert user.is_admin is False
        assert user.switch_id == "switch001"
        assert user.created_at == now

    def test_user_defaults(self):
        """Test user with default values"""
        now = datetime.now()
        user = User(
            slack_user_id="U12345678",
            username="testuser",
            created_at=now,
        )

        assert user.is_admin is False
        assert user.switch_id is None

    def test_invalid_slack_user_id_empty(self):
        """Test invalid empty Slack user ID"""
        with pytest.raises(ValidationError) as exc_info:
            User(
                slack_user_id="",
                username="testuser",
                created_at=datetime.now(),
            )

        assert "Slack user ID cannot be empty" in str(exc_info.value)

    def test_invalid_slack_user_id_too_short(self):
        """Test invalid short Slack user ID"""
        with pytest.raises(ValidationError) as exc_info:
            User(
                slack_user_id="U123",
                username="testuser",
                created_at=datetime.now(),
            )

        assert "Invalid Slack user ID format" in str(exc_info.value)

    def test_invalid_slack_user_id_wrong_prefix(self):
        """Test invalid Slack user ID prefix"""
        with pytest.raises(ValidationError) as exc_info:
            User(
                slack_user_id="X12345678",
                username="testuser",
                created_at=datetime.now(),
            )

        assert "Invalid Slack user ID format" in str(exc_info.value)

    def test_valid_slack_user_id_w_prefix(self):
        """Test valid Slack user ID with W prefix"""
        user = User(
            slack_user_id="W12345678",
            username="testuser",
            created_at=datetime.now(),
        )

        assert user.slack_user_id == "W12345678"

    def test_slack_user_id_trimming(self):
        """Test that Slack user ID is trimmed"""
        user = User(
            slack_user_id="  U12345678  ",
            username="testuser",
            created_at=datetime.now(),
        )

        assert user.slack_user_id == "U12345678"

    def test_invalid_username_empty(self):
        """Test invalid empty username"""
        with pytest.raises(ValidationError) as exc_info:
            User(
                slack_user_id="U12345678",
                username="",
                created_at=datetime.now(),
            )

        assert "Username cannot be empty" in str(exc_info.value)

    def test_username_trimming(self):
        """Test that username is trimmed"""
        user = User(
            slack_user_id="U12345678",
            username="  testuser  ",
            created_at=datetime.now(),
        )

        assert user.username == "testuser"

    def test_switch_id_validation_empty_becomes_none(self):
        """Test that empty switch_id becomes None"""
        user = User(
            slack_user_id="U12345678",
            username="testuser",
            switch_id="   ",
            created_at=datetime.now(),
        )

        assert user.switch_id is None

    def test_switch_id_trimming(self):
        """Test that switch_id is trimmed"""
        user = User(
            slack_user_id="U12345678",
            username="testuser",
            switch_id="  switch001  ",
            created_at=datetime.now(),
        )

        assert user.switch_id == "switch001"


class TestSwitch:
    """Test Switch entity"""

    def test_valid_switch(self):
        """Test creating a valid switch"""
        now = datetime.now()
        switch = Switch(
            switch_id="switch001",
            status="online",
            power_state="ON",
            last_seen=now,
            device_info="test device",
        )

        assert switch.switch_id == "switch001"
        assert switch.status == "online"
        assert switch.power_state == "ON"
        assert switch.last_seen == now
        assert switch.device_info == "test device"

    def test_switch_defaults(self):
        """Test switch with default values"""
        now = datetime.now()
        switch = Switch(
            switch_id="switch001",
            last_seen=now,
        )

        assert switch.status == "offline"
        assert switch.power_state == "unknown"
        assert switch.device_info is None

    def test_invalid_switch_id_empty(self):
        """Test invalid empty switch ID"""
        with pytest.raises(ValidationError) as exc_info:
            Switch(
                switch_id="",
                last_seen=datetime.now(),
            )

        assert "Switch ID cannot be empty" in str(exc_info.value)

    def test_switch_id_trimming(self):
        """Test that switch ID is trimmed"""
        switch = Switch(
            switch_id="  switch001  ",
            last_seen=datetime.now(),
        )

        assert switch.switch_id == "switch001"

    def test_invalid_status(self):
        """Test invalid status"""
        with pytest.raises(ValidationError) as exc_info:
            Switch(
                switch_id="switch001",
                status="invalid",
                last_seen=datetime.now(),
            )

        assert "Status must be one of" in str(exc_info.value)

    def test_valid_statuses(self):
        """Test all valid statuses"""
        now = datetime.now()

        for status in ["online", "offline"]:
            switch = Switch(
                switch_id="switch001",
                status=status,
                last_seen=now,
            )
            assert switch.status == status

    def test_invalid_power_state(self):
        """Test invalid power state"""
        with pytest.raises(ValidationError) as exc_info:
            Switch(
                switch_id="switch001",
                power_state="invalid",
                last_seen=datetime.now(),
            )

        assert "Power state must be one of" in str(exc_info.value)

    def test_valid_power_states(self):
        """Test all valid power states"""
        now = datetime.now()

        for power_state in ["ON", "OFF", "unknown"]:
            switch = Switch(
                switch_id="switch001",
                power_state=power_state,
                last_seen=now,
            )
            assert switch.power_state == power_state


class TestGroup:
    """Test Group entity"""

    def test_valid_group(self):
        """Test creating a valid group"""
        now = datetime.now()
        group = Group(
            group_name="testgroup",
            created_at=now,
        )

        assert group.group_name == "testgroup"
        assert group.created_at == now

    def test_invalid_group_name_empty(self):
        """Test invalid empty group name"""
        with pytest.raises(ValidationError) as exc_info:
            Group(
                group_name="",
                created_at=datetime.now(),
            )

        assert "Group name cannot be empty" in str(exc_info.value)

    def test_group_name_trimming(self):
        """Test that group name is trimmed"""
        group = Group(
            group_name="  testgroup  ",
            created_at=datetime.now(),
        )

        assert group.group_name == "testgroup"

    def test_group_name_length_validation(self):
        """Test group name length validation"""
        now = datetime.now()

        # Too long name
        with pytest.raises(ValidationError) as exc_info:
            Group(
                group_name="a" * 51,
                created_at=now,
            )

        assert "must be between 1 and 50 characters" in str(exc_info.value)

        # Valid length names
        Group(group_name="a", created_at=now)  # 1 character
        Group(group_name="a" * 50, created_at=now)  # 50 characters


class TestGroupMember:
    """Test GroupMember entity"""

    def test_valid_group_member(self):
        """Test creating a valid group member"""
        member = GroupMember(
            group_name="testgroup",
            slack_user_id="U12345678",
        )

        assert member.group_name == "testgroup"
        assert member.slack_user_id == "U12345678"

    def test_invalid_group_name_empty(self):
        """Test invalid empty group name"""
        with pytest.raises(ValidationError) as exc_info:
            GroupMember(
                group_name="",
                slack_user_id="U12345678",
            )

        assert "Field cannot be empty" in str(exc_info.value)

    def test_invalid_slack_user_id_empty(self):
        """Test invalid empty Slack user ID"""
        with pytest.raises(ValidationError) as exc_info:
            GroupMember(
                group_name="testgroup",
                slack_user_id="",
            )

        assert "Field cannot be empty" in str(exc_info.value)

    def test_field_trimming(self):
        """Test that fields are trimmed"""
        member = GroupMember(
            group_name="  testgroup  ",
            slack_user_id="  U12345678  ",
        )

        assert member.group_name == "testgroup"
        assert member.slack_user_id == "U12345678"


class TestOwner:
    """Test Owner entity"""

    def test_valid_owner(self):
        """Test creating a valid owner"""
        owner = Owner(
            slack_user_id="U12345678",
            username="testuser",
            is_admin=True,
        )

        assert owner.slack_user_id == "U12345678"
        assert owner.username == "testuser"
        assert owner.is_admin is True


class TestSwitchWithOwner:
    """Test SwitchWithOwner entity"""

    def test_switch_with_owner(self):
        """Test creating a switch with owner"""
        now = datetime.now()
        owner = Owner(
            slack_user_id="U12345678",
            username="testuser",
            is_admin=False,
        )

        switch = SwitchWithOwner(
            switch_id="switch001",
            status="online",
            power_state="ON",
            last_seen=now,
            device_info="test device",
            owner=owner,
        )

        assert switch.switch_id == "switch001"
        assert switch.owner == owner

    def test_switch_without_owner(self):
        """Test creating a switch without owner"""
        switch = SwitchWithOwner(
            switch_id="switch001",
            status="online",
            power_state="ON",
            last_seen=datetime.now(),
            device_info="test device",
            owner=None,
        )

        assert switch.owner is None


class TestSwitchCommand:
    """Test SwitchCommand entity"""

    def test_valid_switch_command(self):
        """Test creating a valid switch command"""
        command = SwitchCommand(
            switch_id="switch001",
            command="Power1",
            value="ON",
        )

        assert command.switch_id == "switch001"
        assert command.command == "Power1"
        assert command.value == "ON"

    def test_switch_command_no_value(self):
        """Test switch command without value"""
        command = SwitchCommand(
            switch_id="switch001",
            command="Power",
        )

        assert command.value is None

    def test_invalid_command(self):
        """Test invalid command"""
        with pytest.raises(ValidationError) as exc_info:
            SwitchCommand(
                switch_id="switch001",
                command="InvalidCommand",
            )

        assert "Command must be one of" in str(exc_info.value)

    def test_valid_commands(self):
        """Test all valid commands"""
        for command in ["Power", "Power1", "TimedPower1"]:
            cmd = SwitchCommand(
                switch_id="switch001",
                command=command,
            )
            assert cmd.command == command


class TestBotherRequest:
    """Test BotherRequest entity"""

    def test_valid_bother_request(self):
        """Test creating a valid bother request"""
        request = BotherRequest(
            target="U12345678",
            duration=30,
            requester_user_id="U87654321",
        )

        assert request.target == "U12345678"
        assert request.duration == 30
        assert request.requester_user_id == "U87654321"

    def test_bother_request_defaults(self):
        """Test bother request with default duration"""
        request = BotherRequest(
            target="U12345678",
            requester_user_id="U87654321",
        )

        assert request.duration == 15

    def test_invalid_target_empty(self):
        """Test invalid empty target"""
        with pytest.raises(ValidationError) as exc_info:
            BotherRequest(
                target="",
                requester_user_id="U87654321",
            )

        assert "Target cannot be empty" in str(exc_info.value)

    def test_invalid_duration_zero(self):
        """Test invalid zero duration"""
        with pytest.raises(ValidationError) as exc_info:
            BotherRequest(
                target="U12345678",
                duration=0,
                requester_user_id="U87654321",
            )

        assert "Duration must be positive" in str(exc_info.value)

    def test_invalid_duration_negative(self):
        """Test invalid negative duration"""
        with pytest.raises(ValidationError) as exc_info:
            BotherRequest(
                target="U12345678",
                duration=-5,
                requester_user_id="U87654321",
            )

        assert "Duration must be positive" in str(exc_info.value)

    def test_invalid_duration_too_long(self):
        """Test invalid too long duration"""
        with pytest.raises(ValidationError) as exc_info:
            BotherRequest(
                target="U12345678",
                duration=3601,
                requester_user_id="U87654321",
            )

        assert "Duration cannot exceed 3600 seconds" in str(exc_info.value)

    def test_invalid_requester_empty(self):
        """Test invalid empty requester"""
        with pytest.raises(ValidationError) as exc_info:
            BotherRequest(
                target="U12345678",
                requester_user_id="",
            )

        assert "Requester user ID cannot be empty" in str(exc_info.value)

    def test_field_trimming(self):
        """Test that fields are trimmed"""
        request = BotherRequest(
            target="  U12345678  ",
            requester_user_id="  U87654321  ",
        )

        assert request.target == "U12345678"
        assert request.requester_user_id == "U87654321"
