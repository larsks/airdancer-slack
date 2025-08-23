"""Comprehensive tests for all command implementations"""

import pytest
from unittest.mock import Mock
from datetime import datetime

from airdancer.handlers.base import CommandContext
from airdancer.handlers.user_handlers import (
    RegisterCommand,
    BotherCommand,
    ListUsersCommand,
    ListGroupsCommand,
)
from airdancer.handlers.admin_handlers import (
    UnregisterCommand,
    SwitchCommand,
    UserCommand,
    GroupCommand,
)
from airdancer.models.entities import User, SwitchWithOwner, Owner


class TestUserCommands:
    """Test user command implementations"""

    @pytest.fixture
    def mock_database_service(self):
        """Create a mock database service"""
        return Mock()

    @pytest.fixture
    def mock_mqtt_service(self):
        """Create a mock MQTT service"""
        return Mock()

    @pytest.fixture
    def mock_context(self):
        """Create a mock command context"""
        context = Mock(spec=CommandContext)
        context.user_id = "U12345678"
        context.args = []
        context.respond = Mock()
        context.client = Mock()
        return context

    def test_register_command_success(self, mock_database_service, mock_context):
        """Test successful switch registration"""
        mock_context.args = ["switch001"]
        mock_database_service.is_switch_registered.return_value = False
        mock_database_service.register_switch.return_value = True

        command = RegisterCommand(mock_database_service)
        command.execute(mock_context)

        mock_database_service.register_switch.assert_called_once_with(
            "U12345678", "switch001"
        )
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "Successfully registered" in response

    def test_register_command_already_registered_same_user(
        self, mock_database_service, mock_context
    ):
        """Test registering switch already registered to same user"""

        mock_context.args = ["switch001"]
        # Mock the enhanced database service to throw SwitchAlreadyRegisteredError for same user
        # Since it's the same user, the enhanced service should actually succeed, so let's test that
        mock_database_service.register_switch.return_value = True

        command = RegisterCommand(mock_database_service)
        command.execute(mock_context)

        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        # When same user re-registers, it should succeed
        assert "Successfully registered" in response

    def test_register_command_already_registered_different_user(
        self, mock_database_service, mock_context
    ):
        """Test registering switch already registered to different user"""
        from airdancer.exceptions import SwitchAlreadyRegisteredError

        mock_context.args = ["switch001"]
        # Mock the enhanced database service to throw SwitchAlreadyRegisteredError for different user
        mock_database_service.register_switch.side_effect = (
            SwitchAlreadyRegisteredError("switch001", "U87654321")
        )

        command = RegisterCommand(mock_database_service)
        command.execute(mock_context)

        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "already registered to another user" in response

    def test_register_command_invalid_args(self, mock_database_service, mock_context):
        """Test register command with invalid arguments"""
        mock_context.args = []

        command = RegisterCommand(mock_database_service)
        command.execute(mock_context)

        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "Usage:" in response

    def test_bother_command_success(
        self, mock_database_service, mock_mqtt_service, mock_context
    ):
        """Test successful bother command"""
        mock_context.args = ["U87654321"]
        mock_user = User(
            slack_user_id="U87654321",
            username="testuser",
            switch_id="switch001",
            created_at=datetime.now(),
        )
        mock_database_service.get_user.return_value = mock_user
        mock_database_service.get_all_groups.return_value = ["testgroup"]
        mock_database_service.get_all_users.return_value = []  # Empty for fallback path
        mock_context.client.users_info.return_value = {
            "ok": True
        }  # Mock Slack API call
        mock_mqtt_service.bother_switch.return_value = True

        command = BotherCommand(mock_database_service, mock_mqtt_service)
        command.execute(mock_context)

        mock_mqtt_service.bother_switch.assert_called_once_with("switch001", 15)
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "Successfully bothered" in response

    def test_bother_command_group(
        self, mock_database_service, mock_mqtt_service, mock_context
    ):
        """Test bother command with group target"""
        mock_context.args = ["testgroup"]
        mock_database_service.get_all_groups.return_value = ["testgroup"]
        mock_database_service.get_group_members.return_value = [
            "U12345678",
            "U87654321",
        ]

        mock_user1 = User(
            slack_user_id="U12345678",
            username="user1",
            switch_id="switch001",
            created_at=datetime.now(),
        )
        mock_user2 = User(
            slack_user_id="U87654321",
            username="user2",
            switch_id="switch002",
            created_at=datetime.now(),
        )

        def get_user_side_effect(user_id):
            if user_id == "U12345678":
                return mock_user1
            elif user_id == "U87654321":
                return mock_user2
            return None

        mock_database_service.get_user.side_effect = get_user_side_effect
        mock_mqtt_service.bother_switch.return_value = True

        command = BotherCommand(mock_database_service, mock_mqtt_service)
        command.execute(mock_context)

        assert mock_mqtt_service.bother_switch.call_count == 2
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "Bothered 2 members" in response

    def test_list_users_command(self, mock_database_service, mock_context):
        """Test list users command"""
        mock_users = [
            User(
                slack_user_id="U12345678",
                username="user1",
                switch_id="switch001",
                is_admin=False,
                created_at=datetime.now(),
            ),
            User(
                slack_user_id="U87654321",
                username="user2",
                switch_id="switch002",
                is_admin=True,
                created_at=datetime.now(),
            ),
            User(
                slack_user_id="U11111111",
                username="user3",
                switch_id=None,
                is_admin=False,
                created_at=datetime.now(),
            ),
        ]
        mock_database_service.get_all_users.return_value = mock_users

        command = ListUsersCommand(mock_database_service)
        command.execute(mock_context)

        mock_context.respond.assert_called_once()

        # Handle different call patterns from send_blocks_response
        call_args = mock_context.respond.call_args
        if call_args.kwargs and "blocks" in call_args.kwargs:
            # Called with blocks keyword argument
            blocks = call_args.kwargs["blocks"]
            # Convert blocks to text for testing
            response_text = ""
            for block in blocks:
                if block.get("type") == "header":
                    response_text += block["text"]["text"] + "\n"
                elif block.get("type") == "section":
                    response_text += block["text"]["text"] + "\n"
        elif (
            call_args.args
            and isinstance(call_args.args[0], dict)
            and "blocks" in call_args.args[0]
        ):
            # Called with dict containing blocks
            response_dict = call_args.args[0]
            blocks = response_dict["blocks"]
            response_text = ""
            for block in blocks:
                if block.get("type") == "header":
                    response_text += block["text"]["text"] + "\n"
                elif block.get("type") == "section":
                    response_text += block["text"]["text"] + "\n"
        else:
            # Called with text fallback
            response_text = call_args.args[0]

        assert "User Directory" in response_text  # Updated header text
        assert "U12345678" in response_text
        assert "U87654321" in response_text
        assert "👑" in response_text  # Admin badge
        # Note: U11111111 might appear in blocks format, so we check for the switch status instead
        assert "No switch registered" in response_text

    def test_list_groups_command(self, mock_database_service, mock_context):
        """Test list groups command"""
        mock_database_service.get_all_groups.return_value = ["group1", "group2", "all"]
        mock_database_service.get_group_members.side_effect = lambda group: {
            "group1": ["U12345678"],
            "group2": ["U12345678", "U87654321"],
            "all": ["U12345678"],
        }.get(group, [])

        command = ListGroupsCommand(mock_database_service)
        command.execute(mock_context)

        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "Available Groups:" in response
        assert "group1" in response
        assert "1 members" in response
        assert "2 members" in response


class TestAdminCommands:
    """Test admin command implementations"""

    @pytest.fixture
    def mock_database_service(self):
        """Create a mock database service"""
        service = Mock()
        service.is_admin.return_value = True  # Default to admin user
        return service

    @pytest.fixture
    def mock_mqtt_service(self):
        """Create a mock MQTT service"""
        return Mock()

    @pytest.fixture
    def mock_context(self):
        """Create a mock command context"""
        context = Mock(spec=CommandContext)
        context.user_id = "U12345678"
        context.args = []
        context.respond = Mock()
        context.client = Mock()
        context.client.users_info.return_value = {"user": {"name": "testuser"}}
        return context

    def test_unregister_command_success(self, mock_database_service, mock_context):
        """Test successful user unregistration"""
        mock_context.args = ["U87654321"]
        mock_database_service.unregister_user.return_value = True

        command = UnregisterCommand(mock_database_service)
        command.execute(mock_context)

        mock_database_service.unregister_user.assert_called_once_with("U87654321")
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "Successfully unregistered" in response

    def test_unregister_command_not_admin(self, mock_database_service, mock_context):
        """Test unregister command by non-admin user"""
        mock_database_service.is_admin.return_value = False

        command = UnregisterCommand(mock_database_service)
        assert not command.can_execute(mock_context)

    def test_switch_list_command(
        self, mock_database_service, mock_mqtt_service, mock_context
    ):
        """Test switch list command"""
        mock_context.args = ["list"]
        mock_owner = Owner(
            slack_user_id="U12345678", username="testuser", is_admin=True
        )
        mock_switches = [
            SwitchWithOwner(
                switch_id="switch001",
                status="online",
                power_state="ON",
                last_seen=datetime.now(),
                device_info="Device 1",
                owner=mock_owner,
            ),
            SwitchWithOwner(
                switch_id="switch002",
                status="offline",
                power_state="OFF",
                last_seen=datetime.now(),
                device_info="Device 2",
                owner=None,
            ),
        ]
        mock_database_service.get_all_switches_with_owners.return_value = mock_switches

        command = SwitchCommand(mock_database_service, mock_mqtt_service)
        command.execute(mock_context)

        mock_context.respond.assert_called()

        # The new implementation first tries to send blocks, then falls back to text
        # Check if blocks were attempted first
        call_args = mock_context.respond.call_args

        # It could be called with blocks keyword argument or with text fallback
        if call_args.kwargs and "blocks" in call_args.kwargs:
            # Block-based response was used
            blocks = call_args.kwargs["blocks"]
            assert any("Discovered Switches" in str(block) for block in blocks)
            assert any("switch001" in str(block) for block in blocks)
            assert any("switch002" in str(block) for block in blocks)
        else:
            # Text fallback was used
            response = call_args[0][0] if call_args[0] else str(call_args)
            assert "Discovered Switches" in response
            assert "switch001" in response
            assert "switch002" in response
            assert "🟢" in response  # Online status
            assert "👑" in response  # Admin badge

    def test_switch_show_command(
        self, mock_database_service, mock_mqtt_service, mock_context
    ):
        """Test switch show command"""
        mock_context.args = ["show", "switch001"]
        mock_owner = Owner(
            slack_user_id="U12345678", username="testuser", is_admin=True
        )
        mock_switches = [
            SwitchWithOwner(
                switch_id="switch001",
                status="online",
                power_state="ON",
                last_seen=datetime.now(),
                device_info="Test Device",
                owner=mock_owner,
            )
        ]
        mock_database_service.get_all_switches_with_owners.return_value = mock_switches

        command = SwitchCommand(mock_database_service, mock_mqtt_service)
        command.execute(mock_context)

        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "Switch Details:" in response
        assert "switch001" in response
        assert "Online" in response
        assert "Test Device" in response

    def test_switch_control_commands(
        self, mock_database_service, mock_mqtt_service, mock_context
    ):
        """Test switch control commands (on/off/toggle)"""
        test_cases = [
            ("on", "switch_on"),
            ("off", "switch_off"),
            ("toggle", "switch_toggle"),
        ]

        for action, mqtt_method in test_cases:
            mock_context.args = [action, "switch001"]
            getattr(mock_mqtt_service, mqtt_method).return_value = True

            command = SwitchCommand(mock_database_service, mock_mqtt_service)
            command.execute(mock_context)

            getattr(mock_mqtt_service, mqtt_method).assert_called_with("switch001")
            mock_context.respond.assert_called()
            response = mock_context.respond.call_args[0][0]
            assert f"Successfully {action}" in response

    def test_user_list_command(self, mock_database_service, mock_context):
        """Test user list admin command"""
        mock_context.args = ["list"]
        mock_users = [
            User(
                slack_user_id="U12345678",
                username="user1",
                switch_id="switch001",
                is_admin=False,
                created_at=datetime.now(),
            ),
            User(
                slack_user_id="U87654321",
                username="user2",
                switch_id=None,
                is_admin=True,
                created_at=datetime.now(),
            ),
        ]
        mock_database_service.get_all_users.return_value = mock_users

        command = UserCommand(mock_database_service)
        command.execute(mock_context)

        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "All Users:" in response
        assert "U12345678" in response
        assert "U87654321" in response
        assert "👑" in response  # Admin badge

    def test_user_show_command(self, mock_database_service, mock_context):
        """Test user show command"""
        mock_context.args = ["show", "<@U87654321>"]
        mock_user = User(
            slack_user_id="U87654321",
            username="testuser",
            switch_id="switch001",
            is_admin=True,
            created_at=datetime.now(),
        )
        mock_database_service.get_user.return_value = mock_user
        mock_database_service.get_all_users.return_value = [mock_user]
        mock_context.client.users_info.return_value = {
            "ok": True,
            "user": {"name": "testuser"},
        }

        command = UserCommand(mock_database_service)
        command.execute(mock_context)

        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "User Details:" in response
        assert "U87654321" in response
        assert "Yes 👑" in response  # Admin status

    def test_user_set_admin_commands(self, mock_database_service, mock_context):
        """Test user set admin commands"""
        mock_context.args = ["set", "<@U87654321>", "--admin"]
        mock_user = User(
            slack_user_id="U87654321",
            username="testuser",
            switch_id=None,
            is_admin=False,
            created_at=datetime.now(),
        )
        mock_database_service.get_all_users.return_value = [mock_user]
        mock_database_service.set_admin.return_value = True
        mock_context.client.users_info.return_value = {"ok": True}

        command = UserCommand(mock_database_service)
        command.execute(mock_context)

        mock_database_service.set_admin.assert_called_once_with("U87654321", True)
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "granted admin privileges" in response

    def test_user_register_command(self, mock_database_service, mock_context):
        """Test user register command (admin registers switch for another user)"""
        mock_context.args = ["register", "<@U87654321>", "switch001"]
        mock_user = User(
            slack_user_id="U87654321",
            username="testuser",
            switch_id=None,
            is_admin=False,
            created_at=datetime.now(),
        )
        mock_database_service.get_all_users.return_value = [mock_user]
        mock_database_service.register_switch.return_value = True
        mock_context.client.users_info.return_value = {"ok": True}

        command = UserCommand(mock_database_service)
        command.execute(mock_context)

        mock_database_service.register_switch.assert_called_once_with(
            "U87654321", "switch001"
        )
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "Successfully registered switch `switch001` to <@U87654321>" in response

    def test_user_register_command_new_user(self, mock_database_service, mock_context):
        """Test user register command with a user who doesn't exist in database yet"""
        mock_context.args = ["register", "<@U87654321>", "switch001"]
        # Simulate user not in database initially
        mock_database_service.get_all_users.return_value = []
        mock_database_service.get_user.return_value = None
        mock_database_service.add_user.return_value = True
        mock_database_service.register_switch.return_value = True
        mock_context.client.users_info.return_value = {
            "ok": True,
            "user": {"name": "testuser"},
        }

        command = UserCommand(mock_database_service)
        command.execute(mock_context)

        # Should add user to database first, then register switch
        mock_database_service.add_user.assert_called_once_with("U87654321", "testuser")
        mock_database_service.register_switch.assert_called_once_with(
            "U87654321", "switch001"
        )
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "Successfully registered switch `switch001` to <@U87654321>" in response

    def test_group_list_command(self, mock_database_service, mock_context):
        """Test group list command"""
        mock_context.args = ["list"]
        mock_database_service.get_all_groups.return_value = ["group1", "group2", "all"]
        mock_database_service.get_group_members.side_effect = lambda group: {
            "group1": ["U12345678"],
            "group2": ["U12345678", "U87654321"],
            "all": ["U12345678"],
        }.get(group, [])

        command = GroupCommand(mock_database_service)
        command.execute(mock_context)

        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "All Groups:" in response
        assert "group1" in response
        assert "1 members" in response

    def test_group_create_command(self, mock_database_service, mock_context):
        """Test group create command"""
        mock_context.args = ["create", "newgroup"]
        mock_database_service.create_group.return_value = True

        command = GroupCommand(mock_database_service)
        command.execute(mock_context)

        mock_database_service.create_group.assert_called_once_with("newgroup")
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "Created group" in response

    def test_group_destroy_command(self, mock_database_service, mock_context):
        """Test group destroy command"""
        mock_context.args = ["destroy", "testgroup"]
        mock_database_service.delete_group.return_value = True

        command = GroupCommand(mock_database_service)
        command.execute(mock_context)

        mock_database_service.delete_group.assert_called_once_with("testgroup")
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "Destroyed group" in response

    def test_group_destroy_all_protected(self, mock_database_service, mock_context):
        """Test that 'all' group cannot be destroyed"""
        mock_context.args = ["destroy", "all"]

        command = GroupCommand(mock_database_service)
        command.execute(mock_context)

        mock_database_service.delete_group.assert_not_called()
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "Cannot destroy the special" in response

    def test_group_add_users_command(self, mock_database_service, mock_context):
        """Test group add users command"""
        mock_context.args = ["add", "testgroup", "<@U12345678>", "<@U87654321>"]
        mock_database_service.add_user_to_group.return_value = True
        mock_database_service.get_all_users.return_value = [
            User(
                slack_user_id="U12345678", username="user1", created_at=datetime.now()
            ),
            User(
                slack_user_id="U87654321", username="user2", created_at=datetime.now()
            ),
        ]
        mock_context.client.users_info.return_value = {
            "ok": True,
            "user": {"name": "testuser"},
        }

        command = GroupCommand(mock_database_service)
        command.execute(mock_context)

        assert mock_database_service.add_user_to_group.call_count == 2
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "Added 2 user(s)" in response

    def test_group_remove_users_command(self, mock_database_service, mock_context):
        """Test group remove users command"""
        mock_context.args = ["remove", "testgroup", "<@U12345678>"]
        mock_database_service.remove_user_from_group.return_value = True
        mock_database_service.get_all_users.return_value = [
            User(slack_user_id="U12345678", username="user1", created_at=datetime.now())
        ]
        mock_context.client.users_info.return_value = {
            "ok": True,
            "user": {"name": "testuser"},
        }

        command = GroupCommand(mock_database_service)
        command.execute(mock_context)

        mock_database_service.remove_user_from_group.assert_called_once_with(
            "testgroup", "U12345678"
        )
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "Removed 1 user(s)" in response


class TestCommandValidation:
    """Test command validation and error cases"""

    @pytest.fixture
    def mock_database_service(self):
        """Create a mock database service"""
        service = Mock()
        service.is_admin.return_value = True
        return service

    @pytest.fixture
    def mock_mqtt_service(self):
        """Create a mock MQTT service"""
        return Mock()

    @pytest.fixture
    def mock_context(self):
        """Create a mock command context"""
        context = Mock(spec=CommandContext)
        context.user_id = "U12345678"
        context.args = []
        context.respond = Mock()
        context.client = Mock()
        return context

    def test_commands_require_admin_permission(
        self, mock_database_service, mock_mqtt_service, mock_context
    ):
        """Test that admin commands require admin permission"""
        mock_database_service.is_admin.return_value = False

        admin_commands = [
            UnregisterCommand(mock_database_service),
            SwitchCommand(mock_database_service, mock_mqtt_service),
            UserCommand(mock_database_service),
            GroupCommand(mock_database_service),
        ]

        for command in admin_commands:
            assert not command.can_execute(mock_context), (
                f"{command.__class__.__name__} should require admin"
            )

    def test_user_commands_dont_require_admin(
        self, mock_database_service, mock_mqtt_service, mock_context
    ):
        """Test that user commands don't require admin permission"""
        mock_database_service.is_admin.return_value = False

        user_commands = [
            ListUsersCommand(mock_database_service),
            ListGroupsCommand(mock_database_service),
        ]

        for command in user_commands:
            assert command.can_execute(mock_context), (
                f"{command.__class__.__name__} should not require admin"
            )

    def test_register_command_requires_args(self, mock_database_service, mock_context):
        """Test that register command requires arguments"""
        mock_context.args = []

        command = RegisterCommand(mock_database_service)
        assert not command.can_execute(mock_context)

    def test_bother_command_requires_args(
        self, mock_database_service, mock_mqtt_service, mock_context
    ):
        """Test that bother command requires arguments"""
        mock_context.args = []

        command = BotherCommand(mock_database_service, mock_mqtt_service)
        assert not command.can_execute(mock_context)

    def test_invalid_command_args_return_usage(
        self, mock_database_service, mock_mqtt_service, mock_context
    ):
        """Test that invalid arguments return usage messages"""
        test_cases = [
            (SwitchCommand(mock_database_service, mock_mqtt_service), []),
            (UserCommand(mock_database_service), []),
            (GroupCommand(mock_database_service), []),
        ]

        for command, args in test_cases:
            mock_context.args = args
            command.execute(mock_context)

            mock_context.respond.assert_called()
            response = mock_context.respond.call_args[0][0]
            assert "Usage:" in response, (
                f"{command.__class__.__name__} should return usage message"
            )
