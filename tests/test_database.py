import os
import tempfile
import pytest
from datetime import datetime
from pony.orm import db_session, Database, Required, Optional, Set

from airdancer.models.entities import User, Switch, SwitchWithOwner, Owner


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    # Create a temporary file for the test database
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        temp_db_path = tmp.name

    # Create a separate database instance for testing
    test_db = Database()

    # Define test entities
    class TestUser(test_db.Entity):
        slack_user_id = Required(str, unique=True)
        username = Required(str)
        is_admin = Required(bool, default=False)
        switch_id = Optional(str)
        created_at = Required(datetime, default=datetime.now)
        groups = Set("TestGroupMember")

    class TestSwitch(test_db.Entity):
        switch_id = Required(str, unique=True)
        status = Required(str, default="offline")
        power_state = Required(str, default="unknown")
        last_seen = Required(datetime, default=datetime.now)
        device_info = Optional(str)

    class TestGroup(test_db.Entity):
        group_name = Required(str, unique=True)
        created_at = Required(datetime, default=datetime.now)
        members = Set("TestGroupMember")

    class TestGroupMember(test_db.Entity):
        group = Required(TestGroup)
        user = Required(TestUser)

    # Bind and create tables
    test_db.bind("sqlite", temp_db_path)
    test_db.generate_mapping(create_tables=True)

    # Create a test database manager that uses our test entities
    class TestDatabaseManager:
        def __init__(self, db_path: str = temp_db_path):
            self.db = test_db
            self.User = TestUser
            self.Switch = TestSwitch
            self.Group = TestGroup
            self.GroupMember = TestGroupMember

        @db_session
        def add_user(
            self, slack_user_id: str, username: str, is_admin: bool = False
        ) -> bool:
            try:
                user = self.User.get(slack_user_id=slack_user_id)
                if user:
                    user.username = username
                    user.is_admin = is_admin
                else:
                    self.User(
                        slack_user_id=slack_user_id,
                        username=username,
                        is_admin=is_admin,
                    )
                return True
            except Exception as e:
                print(f"Error adding user: {e}")
                return False

        @db_session
        def get_user(self, slack_user_id: str) -> User | None:
            user = self.User.get(slack_user_id=slack_user_id)
            if user:
                return User(
                    slack_user_id=user.slack_user_id,
                    username=user.username,
                    is_admin=user.is_admin,
                    switch_id=user.switch_id,
                    created_at=user.created_at,
                )
            return None

        def is_admin(self, slack_user_id: str) -> bool:
            user = self.get_user(slack_user_id)
            return bool(user and user.is_admin)

        @db_session
        def set_admin(self, slack_user_id: str, is_admin: bool) -> bool:
            try:
                user = self.User.get(slack_user_id=slack_user_id)
                if user:
                    user.is_admin = is_admin
                    return True
                return False
            except Exception as e:
                print(f"Error setting admin status: {e}")
                return False

        @db_session
        def register_switch(self, slack_user_id: str, switch_id: str) -> bool:
            try:
                user = self.User.get(slack_user_id=slack_user_id)
                if not user:
                    return False

                # Check if switch is already registered to another user
                existing_user = self.User.get(switch_id=switch_id)
                if existing_user and existing_user.slack_user_id != slack_user_id:
                    print(
                        f"Switch {switch_id} is already registered to user {existing_user.slack_user_id}"
                    )
                    return False

                user.switch_id = switch_id
                return True
            except Exception as e:
                print(f"Error registering switch: {e}")
                return False

        @db_session
        def unregister_user(self, slack_user_id: str) -> bool:
            try:
                user = self.User.get(slack_user_id=slack_user_id)
                if user:
                    user.delete()
                    return True
                return False
            except Exception as e:
                print(f"Error unregistering user: {e}")
                return False

        @db_session
        def add_switch(self, switch_id: str, device_info: str = "") -> bool:
            try:
                switch = self.Switch.get(switch_id=switch_id)
                if switch:
                    switch.status = "online"
                    switch.device_info = device_info
                    switch.last_seen = datetime.now()
                else:
                    self.Switch(
                        switch_id=switch_id, status="online", device_info=device_info
                    )
                return True
            except Exception as e:
                print(f"Error adding switch: {e}")
                return False

        @db_session
        def update_switch_status(self, switch_id: str, status: str) -> bool:
            try:
                switch = self.Switch.get(switch_id=switch_id)
                if switch:
                    switch.status = status
                    switch.last_seen = datetime.now()
                    return True
                return False
            except Exception as e:
                print(f"Error updating switch status: {e}")
                return False

        @db_session
        def update_switch_power_state(self, switch_id: str, power_state: str) -> bool:
            try:
                switch = self.Switch.get(switch_id=switch_id)
                if switch:
                    switch.power_state = power_state
                    switch.last_seen = datetime.now()
                    return True
                return False
            except Exception as e:
                print(f"Error updating switch power state: {e}")
                return False

        @db_session
        def get_all_switches(self) -> list[Switch]:
            switches = list(self.Switch.select())
            return [
                Switch(
                    switch_id=switch.switch_id,
                    status=switch.status,
                    power_state=switch.power_state,
                    last_seen=switch.last_seen,
                    device_info=switch.device_info,
                )
                for switch in switches
            ]

        @db_session
        def get_all_users(self) -> list[User]:
            users = list(self.User.select())
            return [
                User(
                    slack_user_id=user.slack_user_id,
                    username=user.username,
                    is_admin=user.is_admin,
                    switch_id=user.switch_id,
                    created_at=user.created_at,
                )
                for user in users
            ]

        @db_session
        def create_group(self, group_name: str) -> bool:
            try:
                if not self.Group.get(group_name=group_name):
                    self.Group(group_name=group_name)
                    return True
                return False
            except Exception as e:
                print(f"Error creating group: {e}")
                return False

        @db_session
        def delete_group(self, group_name: str) -> bool:
            try:
                group = self.Group.get(group_name=group_name)
                if group:
                    group.delete()
                    return True
                return False
            except Exception as e:
                print(f"Error deleting group: {e}")
                return False

        @db_session
        def add_user_to_group(self, group_name: str, slack_user_id: str) -> bool:
            try:
                group = self.Group.get(group_name=group_name)
                user = self.User.get(slack_user_id=slack_user_id)
                if group and user:
                    existing = self.GroupMember.get(group=group, user=user)
                    if not existing:
                        self.GroupMember(group=group, user=user)
                    return True
                return False
            except Exception as e:
                print(f"Error adding user to group: {e}")
                return False

        @db_session
        def remove_user_from_group(self, group_name: str, slack_user_id: str) -> bool:
            try:
                group = self.Group.get(group_name=group_name)
                user = self.User.get(slack_user_id=slack_user_id)
                if group and user:
                    membership = self.GroupMember.get(group=group, user=user)
                    if membership:
                        membership.delete()
                        return True
                return False
            except Exception as e:
                print(f"Error removing user from group: {e}")
                return False

        def get_group_members(self, group_name: str):
            if group_name.lower() == "all":
                return [
                    user.slack_user_id
                    for user in self.get_all_users()
                    if user.switch_id
                ]

            with db_session:
                group = self.Group.get(group_name=group_name)
                if group:
                    return [member.user.slack_user_id for member in group.members]
                return []

        @db_session
        def get_all_groups(self):
            groups = [group.group_name for group in list(self.Group.select())]
            if "all" not in [g.lower() for g in groups]:
                groups.append("all")
            return groups

        @db_session
        def get_switch_owner(self, switch_id: str) -> Owner | None:
            """Get the user who owns the specified switch"""
            user = self.User.get(switch_id=switch_id)
            if user:
                return Owner(
                    slack_user_id=user.slack_user_id,
                    username=user.username,
                    is_admin=user.is_admin,
                )
            return None

        @db_session
        def is_switch_registered(self, switch_id: str) -> bool:
            """Check if a switch is already registered to any user"""
            return self.User.get(switch_id=switch_id) is not None

        @db_session
        def get_all_switches_with_owners(self) -> list[SwitchWithOwner]:
            """Get all switches with their owner information using a join (mock version)"""
            # For testing, we'll simulate the join using our existing entities
            switches = list(self.Switch.select())
            results = []

            for switch in switches:
                owner = None
                # Find owner
                user = self.User.get(switch_id=switch.switch_id)
                if user:
                    owner = Owner(
                        slack_user_id=user.slack_user_id,
                        username=user.username,
                        is_admin=user.is_admin,
                    )

                switch_data = SwitchWithOwner(
                    switch_id=switch.switch_id,
                    status=switch.status,
                    power_state=switch.power_state,
                    last_seen=switch.last_seen,
                    device_info=switch.device_info,
                    owner=owner,
                )

                results.append(switch_data)

            return results

    db_manager = TestDatabaseManager()

    yield db_manager

    # Cleanup
    try:
        os.unlink(temp_db_path)
    except OSError:
        pass


class TestDatabaseOperations:
    """Test suite for database operations"""

    def test_add_and_get_user(self, temp_db):
        """Test adding and retrieving users"""
        # Add a user
        result = temp_db.add_user("U10000000230000045678", "testuser", False)
        assert result is True

        # Get the user
        user = temp_db.get_user("U10000000230000045678")
        assert user is not None
        assert user.slack_user_id == "U10000000230000045678"
        assert user.username == "testuser"
        assert user.is_admin is False
        assert user.switch_id is None

    def test_add_admin_user(self, temp_db):
        """Test adding admin users"""
        result = temp_db.add_user("U78901234", "admin", True)
        assert result is True

        user = temp_db.get_user("U78901234")
        assert user.is_admin is True
        assert temp_db.is_admin("U78901234") is True

    def test_update_existing_user(self, temp_db):
        """Test updating existing user information"""
        # Add user
        temp_db.add_user("U100000002300000", "oldname", False)

        # Update user
        result = temp_db.add_user("U100000002300000", "newname", True)
        assert result is True

        # Verify update
        user = temp_db.get_user("U100000002300000")
        assert user.username == "newname"
        assert user.is_admin is True

    def test_set_admin_status(self, temp_db):
        """Test changing admin status"""
        # Add regular user
        temp_db.add_user("U45600000", "user", False)

        # Make admin
        result = temp_db.set_admin("U45600000", True)
        assert result is True
        assert temp_db.is_admin("U45600000") is True

        # Remove admin
        result = temp_db.set_admin("U45600000", False)
        assert result is True
        assert temp_db.is_admin("U45600000") is False

    def test_register_switch(self, temp_db):
        """Test registering switches to users"""
        # Add user first
        temp_db.add_user("U100000002300000", "user", False)

        # Register switch
        result = temp_db.register_switch("U100000002300000", "switch001")
        assert result is True

        # Verify registration
        user = temp_db.get_user("U100000002300000")
        assert user.switch_id == "switch001"

    def test_unregister_user(self, temp_db):
        """Test unregistering users"""
        # Add user
        temp_db.add_user("U99900000", "temp", False)
        assert temp_db.get_user("U99900000") is not None

        # Unregister
        result = temp_db.unregister_user("U99900000")
        assert result is True

        # Verify deletion
        assert temp_db.get_user("U99900000") is None

    def test_switch_operations(self, temp_db):
        """Test switch add, update, and retrieval operations"""
        # Add switch
        result = temp_db.add_switch("sw001", '{"ip": "192.168.1.100"}')
        assert result is True

        # Update status
        result = temp_db.update_switch_status("sw001", "online")
        assert result is True

        # Update power state
        result = temp_db.update_switch_power_state("sw001", "ON")
        assert result is True

        # Get all switches
        switches = temp_db.get_all_switches()
        assert len(switches) == 1
        assert switches[0].switch_id == "sw001"
        assert switches[0].status == "online"
        assert switches[0].power_state == "ON"
        assert switches[0].device_info == '{"ip": "192.168.1.100"}'

    def test_update_existing_switch(self, temp_db):
        """Test updating existing switch information"""
        # Add switch
        temp_db.add_switch("sw002", "old_info")

        # Update with new info
        result = temp_db.add_switch("sw002", "new_info")
        assert result is True

        # Verify update
        switches = temp_db.get_all_switches()
        switch = next(s for s in switches if s.switch_id == "sw002")
        assert switch.device_info == "new_info"
        assert switch.status == "online"

    def test_group_operations(self, temp_db):
        """Test group creation, deletion, and member management"""
        # Create group
        result = temp_db.create_group("testgroup")
        assert result is True

        # Try to create duplicate group
        result = temp_db.create_group("testgroup")
        assert result is False

        # Add users
        temp_db.add_user("U10000000", "user1", False)
        temp_db.add_user("U20000000", "user2", False)

        # Add users to group
        result = temp_db.add_user_to_group("testgroup", "U10000000")
        assert result is True
        result = temp_db.add_user_to_group("testgroup", "U20000000")
        assert result is True

        # Get group members
        members = temp_db.get_group_members("testgroup")
        assert len(members) == 2
        assert "U10000000" in members
        assert "U20000000" in members

        # Remove user from group
        result = temp_db.remove_user_from_group("testgroup", "U10000000")
        assert result is True

        # Verify removal
        members = temp_db.get_group_members("testgroup")
        assert len(members) == 1
        assert "U20000000" in members

        # Delete group
        result = temp_db.delete_group("testgroup")
        assert result is True

    def test_special_all_group(self, temp_db):
        """Test the special 'all' group functionality"""
        # Add users with and without switches
        temp_db.add_user("U10000000", "user1", False)
        temp_db.add_user("U20000000", "user2", False)
        temp_db.add_user("U30000000", "user3", False)

        # Register switches for some users
        temp_db.register_switch("U10000000", "sw1")
        temp_db.register_switch("U30000000", "sw3")

        # Get 'all' group members
        members = temp_db.get_group_members("all")
        assert len(members) == 2
        assert "U10000000" in members
        assert "U30000000" in members
        assert "U20000000" not in members  # No switch registered

    def test_get_all_operations(self, temp_db):
        """Test get_all_* operations"""
        # Add test data
        temp_db.add_user("U10000000", "user1", False)
        temp_db.add_user("U20000000", "admin", True)
        temp_db.add_switch("sw1")
        temp_db.add_switch("sw2")
        temp_db.create_group("group1")
        temp_db.create_group("group2")

        # Test get_all_users
        users = temp_db.get_all_users()
        assert len(users) == 2

        # Test get_all_switches
        switches = temp_db.get_all_switches()
        assert len(switches) == 2

        # Test get_all_groups (includes special 'all' group)
        groups = temp_db.get_all_groups()
        assert len(groups) == 3
        assert "all" in groups
        assert "group1" in groups
        assert "group2" in groups

    def test_switch_owner_functionality(self, temp_db):
        """Test switch owner lookup functionality"""
        # Add user and register switch
        temp_db.add_user("U100000002300000", "alice", True)  # Admin user
        temp_db.register_switch("U100000002300000", "switch001")

        # Test getting switch owner
        owner = temp_db.get_switch_owner("switch001")
        assert owner is not None
        assert owner.slack_user_id == "U100000002300000"
        assert owner.username == "alice"
        assert owner.is_admin is True

        # Test unregistered switch
        temp_db.add_switch("unregistered_switch")
        owner = temp_db.get_switch_owner("unregistered_switch")
        assert owner is None

        # Test nonexistent switch
        owner = temp_db.get_switch_owner("NONEXISTENT")
        assert owner is None

    def test_switches_with_owners_join(self, temp_db):
        """Test the optimized get_all_switches_with_owners method"""
        # Add users and switches
        temp_db.add_user("U100000002300000", "alice", True)  # Admin user
        temp_db.add_user("U45600000", "bob", False)  # Regular user

        # Add switches first, then register them to users
        temp_db.add_switch("switch001")
        temp_db.add_switch("switch002")
        temp_db.add_switch("unregistered_switch")

        # Register switches to users
        temp_db.register_switch("U100000002300000", "switch001")
        temp_db.register_switch("U45600000", "switch002")

        # Get all switches with owners
        switches = temp_db.get_all_switches_with_owners()
        assert len(switches) == 3

        # Find specific switches
        switch001 = next(s for s in switches if s.switch_id == "switch001")
        switch002 = next(s for s in switches if s.switch_id == "switch002")
        unregistered = next(s for s in switches if s.switch_id == "unregistered_switch")

        # Test switch001 (admin owner)
        assert switch001.owner is not None
        assert switch001.owner.slack_user_id == "U100000002300000"
        assert switch001.owner.username == "alice"
        assert switch001.owner.is_admin is True

        # Test switch002 (regular owner)
        assert switch002.owner is not None
        assert switch002.owner.slack_user_id == "U45600000"
        assert switch002.owner.username == "bob"
        assert switch002.owner.is_admin is False

        # Test unregistered switch
        assert unregistered.owner is None

    def test_nonexistent_operations(self, temp_db):
        """Test operations on nonexistent entities"""
        # Operations on nonexistent user
        assert temp_db.get_user("NONEXISTENT") is None
        assert temp_db.is_admin("NONEXISTENT") is False
        assert temp_db.set_admin("NONEXISTENT", True) is False
        assert temp_db.register_switch("NONEXISTENT", "sw1") is False
        assert temp_db.unregister_user("NONEXISTENT") is False

        # Operations on nonexistent switch
        assert temp_db.update_switch_status("NONEXISTENT", "online") is False
        assert temp_db.update_switch_power_state("NONEXISTENT", "ON") is False

        # Operations on nonexistent group
        assert temp_db.delete_group("NONEXISTENT") is False
        assert temp_db.add_user_to_group("NONEXISTENT", "U10000000") is False
        assert temp_db.remove_user_from_group("NONEXISTENT", "U10000000") is False
        assert temp_db.get_group_members("NONEXISTENT") == []

        # Operations on nonexistent switch owner
        assert temp_db.get_switch_owner("NONEXISTENT") is None

    def test_prevent_duplicate_switch_registration(self, temp_db):
        """Test that a switch cannot be registered to multiple users"""
        # Add two users
        temp_db.add_user("U10000000", "user1", False)
        temp_db.add_user("U20000000", "user2", False)

        # Register switch to first user
        result = temp_db.register_switch("U10000000", "shared_switch")
        assert result is True

        # Verify first user has the switch
        user1 = temp_db.get_user("U10000000")
        assert user1.switch_id == "shared_switch"

        # Try to register same switch to second user - should fail
        result = temp_db.register_switch("U20000000", "shared_switch")
        assert result is False

        # Verify second user does not have the switch
        user2 = temp_db.get_user("U20000000")
        assert user2.switch_id is None

        # Verify switch is still registered to first user
        owner = temp_db.get_switch_owner("shared_switch")
        assert owner is not None
        assert owner.slack_user_id == "U10000000"

        # Test is_switch_registered method
        assert temp_db.is_switch_registered("shared_switch") is True
        assert temp_db.is_switch_registered("nonexistent_switch") is False

    def test_re_register_same_switch_to_same_user(self, temp_db):
        """Test that a user can re-register their own switch"""
        # Add user and register switch
        temp_db.add_user("U10000000", "user1", False)
        result = temp_db.register_switch("U10000000", "user_switch")
        assert result is True

        # Re-register same switch to same user - should succeed
        result = temp_db.register_switch("U10000000", "user_switch")
        assert result is True

        # Verify user still has the switch
        user = temp_db.get_user("U10000000")
        assert user.switch_id == "user_switch"

    def test_register_different_switches_to_different_users(self, temp_db):
        """Test that different switches can be registered to different users"""
        # Add two users
        temp_db.add_user("U10000000", "user1", False)
        temp_db.add_user("U20000000", "user2", False)

        # Register different switches
        result1 = temp_db.register_switch("U10000000", "switch1")
        result2 = temp_db.register_switch("U20000000", "switch2")

        assert result1 is True
        assert result2 is True

        # Verify both registrations
        user1 = temp_db.get_user("U10000000")
        user2 = temp_db.get_user("U20000000")

        assert user1.switch_id == "switch1"
        assert user2.switch_id == "switch2"

        # Verify ownership
        owner1 = temp_db.get_switch_owner("switch1")
        owner2 = temp_db.get_switch_owner("switch2")

        assert owner1.slack_user_id == "U10000000"
        assert owner2.slack_user_id == "U20000000"
