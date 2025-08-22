"""Simplified tests for command handlers"""

import pytest
from unittest.mock import Mock

from airdancer.handlers.base import CommandContext
from airdancer.handlers.user_handlers import UserCommandHandler, RegisterCommand
from airdancer.handlers.admin_handlers import AdminCommandHandler


class TestCommandContext:
    """Test CommandContext functionality"""

    @pytest.fixture
    def mock_respond(self):
        """Create a mock respond function"""
        return Mock()

    @pytest.fixture
    def mock_client(self):
        """Create a mock Slack client"""
        return Mock()

    @pytest.fixture
    def context(self, mock_respond, mock_client):
        """Create a CommandContext"""
        return CommandContext(
            user_id="U12345678",
            args=["test", "arg1", "arg2"],
            respond=mock_respond,
            client=mock_client,
        )

    def test_initialization(self, context, mock_respond, mock_client):
        """Test CommandContext initialization"""
        assert context.user_id == "U12345678"
        assert context.args == ["test", "arg1", "arg2"]
        assert context.respond == mock_respond
        assert context.client == mock_client

    def test_respond_method(self, context, mock_respond):
        """Test respond method delegation"""
        context.respond("test message")
        mock_respond.assert_called_once_with("test message")


class TestUserCommandHandler:
    """Test UserCommandHandler functionality"""

    @pytest.fixture
    def mock_database_service(self):
        """Create a mock database service"""
        return Mock()

    @pytest.fixture
    def mock_mqtt_service(self):
        """Create a mock MQTT service"""
        return Mock()

    @pytest.fixture
    def handler(self, mock_database_service, mock_mqtt_service):
        """Create a UserCommandHandler"""
        return UserCommandHandler(mock_database_service, mock_mqtt_service)

    @pytest.fixture
    def mock_context(self):
        """Create a mock context"""
        context = Mock()
        context.user_id = "U12345678"
        context.args = []
        return context

    def test_initialization(self, handler):
        """Test handler initialization"""
        assert "register" in handler.commands
        assert "bother" in handler.commands
        assert "users" in handler.commands
        assert "groups" in handler.commands

    def test_handle_unknown_command(self, handler, mock_context):
        """Test unknown command"""
        handler.handle_command("unknown", mock_context)

        mock_context.respond.assert_called_once()
        response = mock_context.respond.call_args[0][0]
        assert "Unknown command" in response

    def test_handle_valid_command(self, handler, mock_context):
        """Test handling a valid command"""
        mock_context.args = ["switch001"]

        # Mock the command execution
        from unittest.mock import patch

        with patch.object(
            handler.commands["register"], "can_execute", return_value=True
        ):
            with patch.object(handler.commands["register"], "execute") as mock_execute:
                handler.handle_command("register", mock_context)
                mock_execute.assert_called_once_with(mock_context)


class TestRegisterCommand:
    """Test RegisterCommand functionality"""

    @pytest.fixture
    def mock_database_service(self):
        """Create a mock database service"""
        return Mock()

    @pytest.fixture
    def command(self, mock_database_service):
        """Create a RegisterCommand"""
        return RegisterCommand(mock_database_service)

    @pytest.fixture
    def mock_context(self):
        """Create a mock context"""
        context = Mock()
        context.user_id = "U12345678"
        context.args = ["switch001"]
        return context

    def test_can_execute_with_args(self, command, mock_context):
        """Test can_execute with arguments"""
        assert command.can_execute(mock_context) is True

    def test_can_execute_without_args(self, command):
        """Test can_execute without arguments"""
        context = Mock()
        context.args = []
        assert command.can_execute(context) is False

    def test_execute_success(self, command, mock_context, mock_database_service):
        """Test successful registration"""
        mock_database_service.is_switch_registered.return_value = False
        mock_database_service.register_switch.return_value = True

        from unittest.mock import patch

        with patch(
            "airdancer.handlers.user_handlers.clean_switch_id", return_value="switch001"
        ):
            command.execute(mock_context)

        mock_database_service.register_switch.assert_called_once()
        mock_context.respond.assert_called_once()

    def test_execute_insufficient_args(self, command, mock_database_service):
        """Test execution with insufficient arguments"""
        context = Mock()
        context.args = []

        command.execute(context)

        context.respond.assert_called_once()
        response = context.respond.call_args[0][0]
        assert "Usage:" in response


class TestAdminCommandHandler:
    """Test AdminCommandHandler functionality"""

    @pytest.fixture
    def mock_database_service(self):
        """Create a mock database service"""
        return Mock()

    @pytest.fixture
    def mock_mqtt_service(self):
        """Create a mock MQTT service"""
        return Mock()

    @pytest.fixture
    def handler(self, mock_database_service, mock_mqtt_service):
        """Create an AdminCommandHandler"""
        return AdminCommandHandler(mock_database_service, mock_mqtt_service)

    def test_initialization(self, handler):
        """Test handler initialization"""
        assert hasattr(handler, "database_service")
        assert hasattr(handler, "mqtt_service")
