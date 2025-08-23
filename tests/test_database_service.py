"""Tests for database service layer"""

import tempfile
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from airdancer.services.database_service import DatabaseService
from airdancer.models.entities import User, Switch, SwitchWithOwner, Owner


class TestDatabaseService:
    """Test DatabaseService functionality"""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            return tmp.name

    @pytest.fixture
    def db_service(self, temp_db_path):
        """Create a DatabaseService with temporary database"""
        return DatabaseService(temp_db_path)

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock DatabaseManager"""
        return Mock()

    @pytest.fixture
    def db_service_with_mock(self, mock_db_manager):
        """Create a DatabaseService with mocked DatabaseManager"""
        with patch("airdancer.services.database_service.DatabaseManager") as mock_class:
            mock_class.return_value = mock_db_manager
            service = DatabaseService(":memory:")
            service._db_manager = mock_db_manager
            return service

    def test_initialization_with_relative_path(self):
        """Test that relative paths are converted to absolute"""
        with patch("airdancer.services.database_service.DatabaseManager") as mock_class:
            DatabaseService("test.db")
            # Should be called with absolute path
            args, kwargs = mock_class.call_args
            assert args[0].endswith("test.db")
            assert args[0].startswith("/")

    def test_initialization_with_absolute_path(self):
        """Test that absolute paths are kept as-is"""
        abs_path = "/absolute/path/test.db"
        with patch("airdancer.services.database_service.DatabaseManager") as mock_class:
            DatabaseService(abs_path)
            mock_class.assert_called_once_with(abs_path)

    def test_add_user(self, db_service_with_mock, mock_db_manager):
        """Test adding a user"""
        mock_db_manager.add_user.return_value = True

        result = db_service_with_mock.add_user("U12345678", "testuser", False)

        assert result is True
        mock_db_manager.add_user.assert_called_once_with("U12345678", "testuser", False)

    def test_get_user(self, db_service_with_mock, mock_db_manager):
        """Test getting a user"""
        expected_user = User(
            slack_user_id="U12345678",
            username="testuser",
            is_admin=False,
            switch_id=None,
            created_at=datetime.now(),
        )
        mock_db_manager.get_user.return_value = expected_user

        result = db_service_with_mock.get_user("U12345678")

        assert result == expected_user
        mock_db_manager.get_user.assert_called_once_with("U12345678")

    def test_get_user_not_found(self, db_service_with_mock, mock_db_manager):
        """Test getting a user that doesn't exist"""
        mock_db_manager.get_user.return_value = None

        result = db_service_with_mock.get_user("U12345678")

        assert result is None
        mock_db_manager.get_user.assert_called_once_with("U12345678")

    def test_is_admin(self, db_service_with_mock, mock_db_manager):
        """Test checking admin status"""
        mock_db_manager.is_admin.return_value = True

        result = db_service_with_mock.is_admin("U12345678")

        assert result is True
        mock_db_manager.is_admin.assert_called_once_with("U12345678")

    def test_set_admin(self, db_service_with_mock, mock_db_manager):
        """Test setting admin status"""
        mock_db_manager.set_admin.return_value = True

        result = db_service_with_mock.set_admin("U12345678", True)

        assert result is True
        mock_db_manager.set_admin.assert_called_once_with("U12345678", True)

    def test_register_switch(self, db_service_with_mock, mock_db_manager):
        """Test registering a switch"""
        from airdancer.models.entities import User
        from datetime import datetime
        
        # Mock the methods called by enhanced register_switch
        mock_db_manager.is_switch_registered.return_value = False
        mock_db_manager.get_user.return_value = User(
            slack_user_id="U12345678", 
            username="testuser", 
            is_admin=False,
            switch_id=None,
            created_at=datetime.now()
        )
        mock_db_manager.register_switch.return_value = True

        result = db_service_with_mock.register_switch("U12345678", "switch001")

        assert result is True
        mock_db_manager.register_switch.assert_called_once_with(
            "U12345678", "switch001"
        )

    def test_unregister_user(self, db_service_with_mock, mock_db_manager):
        """Test unregistering a user"""
        mock_db_manager.unregister_user.return_value = True

        result = db_service_with_mock.unregister_user("U12345678")

        assert result is True
        mock_db_manager.unregister_user.assert_called_once_with("U12345678")

    def test_add_switch(self, db_service_with_mock, mock_db_manager):
        """Test adding a switch"""
        mock_db_manager.add_switch.return_value = True

        result = db_service_with_mock.add_switch("switch001", "device_info")

        assert result is True
        mock_db_manager.add_switch.assert_called_once_with("switch001", "device_info")

    def test_update_switch_status(self, db_service_with_mock, mock_db_manager):
        """Test updating switch status"""
        mock_db_manager.update_switch_status.return_value = True

        result = db_service_with_mock.update_switch_status("switch001", "online")

        assert result is True
        mock_db_manager.update_switch_status.assert_called_once_with(
            "switch001", "online"
        )

    def test_update_switch_power_state(self, db_service_with_mock, mock_db_manager):
        """Test updating switch power state"""
        mock_db_manager.update_switch_power_state.return_value = True

        result = db_service_with_mock.update_switch_power_state("switch001", "ON")

        assert result is True
        mock_db_manager.update_switch_power_state.assert_called_once_with(
            "switch001", "ON"
        )

    def test_get_all_switches(self, db_service_with_mock, mock_db_manager):
        """Test getting all switches"""
        expected_switches = [
            Switch(
                switch_id="switch001",
                status="online",
                power_state="ON",
                last_seen=datetime.now(),
                device_info="info1",
            ),
            Switch(
                switch_id="switch002",
                status="offline",
                power_state="OFF",
                last_seen=datetime.now(),
                device_info="info2",
            ),
        ]
        mock_db_manager.get_all_switches.return_value = expected_switches

        result = db_service_with_mock.get_all_switches()

        assert result == expected_switches
        mock_db_manager.get_all_switches.assert_called_once()

    def test_get_all_switches_with_owners(self, db_service_with_mock, mock_db_manager):
        """Test getting all switches with owners"""
        owner = Owner(slack_user_id="U12345678", username="testuser", is_admin=False)
        expected_switches = [
            SwitchWithOwner(
                switch_id="switch001",
                status="online",
                power_state="ON",
                last_seen=datetime.now(),
                device_info="info1",
                owner=owner,
            ),
            SwitchWithOwner(
                switch_id="switch002",
                status="offline",
                power_state="OFF",
                last_seen=datetime.now(),
                device_info="info2",
                owner=None,
            ),
        ]
        mock_db_manager.get_all_switches_with_owners.return_value = expected_switches

        result = db_service_with_mock.get_all_switches_with_owners()

        assert result == expected_switches
        mock_db_manager.get_all_switches_with_owners.assert_called_once()

    def test_get_all_users(self, db_service_with_mock, mock_db_manager):
        """Test getting all users"""
        expected_users = [
            User(
                slack_user_id="U12345678",
                username="user1",
                is_admin=False,
                switch_id="switch001",
                created_at=datetime.now(),
            ),
            User(
                slack_user_id="U87654321",
                username="user2",
                is_admin=True,
                switch_id=None,
                created_at=datetime.now(),
            ),
        ]
        mock_db_manager.get_all_users.return_value = expected_users

        result = db_service_with_mock.get_all_users()

        assert result == expected_users
        mock_db_manager.get_all_users.assert_called_once()

    def test_create_group(self, db_service_with_mock, mock_db_manager):
        """Test creating a group"""
        mock_db_manager.create_group.return_value = True

        result = db_service_with_mock.create_group("testgroup")

        assert result is True
        mock_db_manager.create_group.assert_called_once_with("testgroup")

    def test_delete_group(self, db_service_with_mock, mock_db_manager):
        """Test deleting a group"""
        mock_db_manager.delete_group.return_value = True

        result = db_service_with_mock.delete_group("testgroup")

        assert result is True
        mock_db_manager.delete_group.assert_called_once_with("testgroup")

    def test_add_user_to_group(self, db_service_with_mock, mock_db_manager):
        """Test adding user to group"""
        mock_db_manager.add_user_to_group.return_value = True

        result = db_service_with_mock.add_user_to_group("testgroup", "U12345678")

        assert result is True
        mock_db_manager.add_user_to_group.assert_called_once_with(
            "testgroup", "U12345678"
        )

    def test_remove_user_from_group(self, db_service_with_mock, mock_db_manager):
        """Test removing user from group"""
        mock_db_manager.remove_user_from_group.return_value = True

        result = db_service_with_mock.remove_user_from_group("testgroup", "U12345678")

        assert result is True
        mock_db_manager.remove_user_from_group.assert_called_once_with(
            "testgroup", "U12345678"
        )

    def test_get_group_members(self, db_service_with_mock, mock_db_manager):
        """Test getting group members"""
        expected_members = ["U12345678", "U87654321"]
        mock_db_manager.get_group_members.return_value = expected_members

        result = db_service_with_mock.get_group_members("testgroup")

        assert result == expected_members
        mock_db_manager.get_group_members.assert_called_once_with("testgroup")

    def test_get_all_groups(self, db_service_with_mock, mock_db_manager):
        """Test getting all groups"""
        expected_groups = ["group1", "group2", "all"]
        mock_db_manager.get_all_groups.return_value = expected_groups

        result = db_service_with_mock.get_all_groups()

        assert result == expected_groups
        mock_db_manager.get_all_groups.assert_called_once()

    def test_get_switch_owner(self, db_service_with_mock, mock_db_manager):
        """Test getting switch owner"""
        expected_owner = Owner(
            slack_user_id="U12345678", username="testuser", is_admin=False
        )
        mock_db_manager.get_switch_owner.return_value = expected_owner

        result = db_service_with_mock.get_switch_owner("switch001")

        assert result == expected_owner
        mock_db_manager.get_switch_owner.assert_called_once_with("switch001")

    def test_is_switch_registered(self, db_service_with_mock, mock_db_manager):
        """Test checking if switch is registered"""
        mock_db_manager.is_switch_registered.return_value = True

        result = db_service_with_mock.is_switch_registered("switch001")

        assert result is True
        mock_db_manager.is_switch_registered.assert_called_once_with("switch001")

    def test_integration_with_real_database(self, db_service):
        """Test basic integration with real database"""
        # Add a user
        result = db_service.add_user("U12345678", "testuser", False)
        assert result is True

        # Get the user
        user = db_service.get_user("U12345678")
        assert user is not None
        assert user.slack_user_id == "U12345678"
        assert user.username == "testuser"
        assert user.is_admin is False

        # Test admin status
        assert db_service.is_admin("U12345678") is False

        # Set admin status
        result = db_service.set_admin("U12345678", True)
        assert result is True
        assert db_service.is_admin("U12345678") is True

        # Register a switch
        result = db_service.register_switch("U12345678", "switch001")
        assert result is True

        # Add switch to database
        result = db_service.add_switch("switch001", "test device info")
        assert result is True

        # Get all switches
        switches = db_service.get_all_switches()
        assert len(switches) == 1
        assert switches[0].switch_id == "switch001"

        # Get all users
        users = db_service.get_all_users()
        assert len(users) == 1
        assert users[0].slack_user_id == "U12345678"
