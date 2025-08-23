"""Tests for user set functionality"""

import pytest
from unittest.mock import Mock
from datetime import datetime

from airdancer.handlers.user_handlers import UserSetCommand
from airdancer.handlers.admin_handlers import UserCommand
from airdancer.models.entities import User


class TestUserSetCommand:
    """Test user set command functionality"""

    @pytest.fixture
    def mock_database_service(self):
        return Mock()

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.user_id = "U12345678"
        context.respond = Mock()
        return context

    def test_user_set_bother_enable(self, mock_database_service, mock_context):
        """Test user set --bother command"""
        mock_context.args = ["--bother"]
        mock_database_service.set_botherable.return_value = True

        command = UserSetCommand(mock_database_service)
        command.execute(mock_context)

        mock_database_service.set_botherable.assert_called_once_with("U12345678", True)
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "enabled bother notifications" in response

    def test_user_set_bother_disable(self, mock_database_service, mock_context):
        """Test user set --no-bother command"""
        mock_context.args = ["--no-bother"]
        mock_database_service.set_botherable.return_value = True

        command = UserSetCommand(mock_database_service)
        command.execute(mock_context)

        mock_database_service.set_botherable.assert_called_once_with("U12345678", False)
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "disabled bother notifications" in response

    def test_user_set_no_args(self, mock_database_service, mock_context):
        """Test user set with no arguments shows usage"""
        mock_context.args = []

        command = UserSetCommand(mock_database_service)
        command.execute(mock_context)

        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "Usage:" in response or "one of the arguments" in response

    def test_user_set_database_failure(self, mock_database_service, mock_context):
        """Test user set when database operation fails"""
        mock_context.args = ["--bother"]
        mock_database_service.set_botherable.return_value = False

        command = UserSetCommand(mock_database_service)
        command.execute(mock_context)

        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "Failed to update settings" in response


class TestAdminUserSetCommand:
    """Test admin user set command functionality"""

    @pytest.fixture
    def mock_database_service(self):
        return Mock()

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.user_id = "U12345678"
        context.respond = Mock()
        context.client = Mock()
        return context

    def test_admin_user_set_admin_enable(self, mock_database_service, mock_context):
        """Test admin user set --admin command"""
        mock_context.args = ["set", "<@U87654321>", "--admin"]
        mock_context.client.users_info.return_value = {"ok": True}
        mock_database_service.get_all_users.return_value = []
        mock_database_service.set_admin.return_value = True

        command = UserCommand(mock_database_service)
        command.execute(mock_context)

        mock_database_service.set_admin.assert_called_once_with("U87654321", True)
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "granted admin privileges" in response

    def test_admin_user_set_admin_disable(self, mock_database_service, mock_context):
        """Test admin user set --no-admin command"""
        mock_context.args = ["set", "<@U87654321>", "--no-admin"]
        mock_context.client.users_info.return_value = {"ok": True}
        mock_database_service.get_all_users.return_value = []
        mock_database_service.set_admin.return_value = True

        command = UserCommand(mock_database_service)
        command.execute(mock_context)

        mock_database_service.set_admin.assert_called_once_with("U87654321", False)
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "revoked admin privileges" in response

    def test_admin_user_set_bother_enable(self, mock_database_service, mock_context):
        """Test admin user set --bother command"""
        mock_context.args = ["set", "<@U87654321>", "--bother"]
        mock_context.client.users_info.return_value = {"ok": True}
        mock_database_service.get_all_users.return_value = []
        mock_database_service.set_botherable.return_value = True

        command = UserCommand(mock_database_service)
        command.execute(mock_context)

        mock_database_service.set_botherable.assert_called_once_with("U87654321", True)
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "enabled bother notifications" in response

    def test_admin_user_set_bother_disable(self, mock_database_service, mock_context):
        """Test admin user set --no-bother command"""
        mock_context.args = ["set", "<@U87654321>", "--no-bother"]
        mock_context.client.users_info.return_value = {"ok": True}
        mock_database_service.get_all_users.return_value = []
        mock_database_service.set_botherable.return_value = True

        command = UserCommand(mock_database_service)
        command.execute(mock_context)

        mock_database_service.set_botherable.assert_called_once_with("U87654321", False)
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "disabled bother notifications" in response

    def test_admin_user_set_both_flags(self, mock_database_service, mock_context):
        """Test admin user set with both admin and bother flags"""
        mock_context.args = ["set", "<@U87654321>", "--admin", "--bother"]
        mock_context.client.users_info.return_value = {"ok": True}
        mock_database_service.get_all_users.return_value = []
        mock_database_service.set_admin.return_value = True
        mock_database_service.set_botherable.return_value = True

        command = UserCommand(mock_database_service)
        command.execute(mock_context)

        mock_database_service.set_admin.assert_called_once_with("U87654321", True)
        mock_database_service.set_botherable.assert_called_once_with("U87654321", True)
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "granted admin privileges" in response
        assert "enabled bother notifications" in response

    def test_admin_user_set_no_changes(self, mock_database_service, mock_context):
        """Test admin user set with no flags specified"""
        mock_context.args = ["set", "<@U87654321>"]
        mock_context.client.users_info.return_value = {"ok": True}
        mock_database_service.get_all_users.return_value = []

        command = UserCommand(mock_database_service)
        command.execute(mock_context)

        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "No changes specified" in response

    def test_admin_user_set_user_not_found(self, mock_database_service, mock_context):
        """Test admin user set with user that doesn't exist"""
        mock_context.args = ["set", "nonexistent", "--admin"]
        mock_context.client.users_info.side_effect = Exception("User not found")
        mock_database_service.get_all_users.return_value = []

        command = UserCommand(mock_database_service)
        command.execute(mock_context)

        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "Could not find user" in response


class TestBotherRespectsBotherableSetting:
    """Test that bother commands respect botherable setting"""

    @pytest.fixture
    def mock_database_service(self):
        return Mock()

    @pytest.fixture
    def mock_mqtt_service(self):
        return Mock()

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.user_id = "U12345678"
        context.respond = Mock()
        context.client = Mock()
        return context

    def test_bother_respects_botherable_false(
        self, mock_database_service, mock_mqtt_service, mock_context
    ):
        """Test that bother command respects botherable=False"""
        from airdancer.handlers.user_handlers import BotherCommand

        mock_context.args = ["<@U87654321>"]
        mock_user = User(
            slack_user_id="U87654321",
            username="testuser",
            switch_id="test_switch",
            is_admin=False,
            botherable=False,  # User has disabled bother
            created_at=datetime.now(),
        )
        mock_database_service.get_user.return_value = mock_user
        mock_database_service.get_all_groups.return_value = []
        mock_context.client.users_info.return_value = {"ok": True}

        command = BotherCommand(mock_database_service, mock_mqtt_service)
        command.execute(mock_context)

        # Should not call MQTT service since user is not botherable
        mock_mqtt_service.bother_switch.assert_not_called()
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "Failed to bother user" in response

    def test_bother_respects_botherable_true(
        self, mock_database_service, mock_mqtt_service, mock_context
    ):
        """Test that bother command works when botherable=True"""
        from airdancer.handlers.user_handlers import BotherCommand

        mock_context.args = ["<@U87654321>"]
        mock_user = User(
            slack_user_id="U87654321",
            username="testuser",
            switch_id="test_switch",
            is_admin=False,
            botherable=True,  # User allows bother
            created_at=datetime.now(),
        )
        mock_database_service.get_user.return_value = mock_user
        mock_database_service.get_all_groups.return_value = []
        mock_context.client.users_info.return_value = {"ok": True}
        mock_mqtt_service.bother_switch.return_value = True

        command = BotherCommand(mock_database_service, mock_mqtt_service)
        command.execute(mock_context)

        # Should call MQTT service since user is botherable
        mock_mqtt_service.bother_switch.assert_called_once_with("test_switch", 15)
        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "Successfully bothered user" in response
