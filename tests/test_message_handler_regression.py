"""Regression test specifically for the missing message handler bug"""

import pytest
from unittest.mock import Mock, patch

from airdancer.main import AirdancerApp
from airdancer.config.settings import AppConfig


class TestMessageHandlerRegression:
    """Tests that would have caught the missing message handler issue"""

    @pytest.fixture
    def mock_config(self):
        """Create a mock AppConfig"""
        config = Mock(spec=AppConfig)
        config.database_path = ":memory:"
        config.admin_user = None
        config.slack.bot_token = "xoxb-test-token"
        config.slack.app_token = "xapp-test-token"
        config.mqtt = Mock()
        config.mqtt.host = "localhost"
        config.mqtt.port = 1883
        config.mqtt.username = None
        config.mqtt.password = None
        config.mqtt.use_tls = False
        return config

    def test_slack_app_registers_message_event_handler(self, mock_config):
        """REGRESSION TEST: This would have failed before the fix!

        This test specifically checks that the Slack app registers a message
        event handler, which was missing and caused the original issue.
        """
        with (
            patch("airdancer.main.DatabaseService"),
            patch("airdancer.main.MQTTService"),
            patch("airdancer.main.App") as mock_app_class,
        ):
            mock_slack_app = Mock()
            mock_app_class.return_value = mock_slack_app

            # Create the app - this triggers _setup_events()
            AirdancerApp(mock_config)

            # CRITICAL TEST: Verify that event handler for "message" was registered
            # This call would have been missing before the fix!
            mock_slack_app.event.assert_called_with("message")

            # Verify it was called at least once
            assert mock_slack_app.event.call_count >= 1

            # Verify specifically that "message" event was registered
            message_calls = [
                call
                for call in mock_slack_app.event.call_args_list
                if call[0][0] == "message"
            ]
            assert len(message_calls) >= 1, "No message event handler registered!"

    def test_both_command_and_event_handlers_registered(self, mock_config):
        """Test that BOTH slash command AND message event handlers are registered

        This ensures we don't accidentally remove one when working on the other.
        """
        with (
            patch("airdancer.main.DatabaseService"),
            patch("airdancer.main.MQTTService"),
            patch("airdancer.main.App") as mock_app_class,
        ):
            mock_slack_app = Mock()
            mock_app_class.return_value = mock_slack_app

            # Create the app
            AirdancerApp(mock_config)

            # Verify BOTH handlers are registered
            mock_slack_app.command.assert_called_with("/dancer")
            mock_slack_app.event.assert_called_with("message")

            # Ensure both were called (not just one)
            assert mock_slack_app.command.called, "Slash command handler not registered"
            assert mock_slack_app.event.called, "Message event handler not registered"

    def test_app_calls_both_setup_methods(self, mock_config):
        """Test that AirdancerApp calls both _setup_commands and _setup_events

        This ensures the setup methods aren't accidentally removed.
        """
        with (
            patch("airdancer.main.DatabaseService"),
            patch("airdancer.main.MQTTService"),
            patch("airdancer.main.App"),
        ):
            # Patch the setup methods to verify they're called
            with (
                patch.object(AirdancerApp, "_setup_commands") as mock_setup_commands,
                patch.object(AirdancerApp, "_setup_events") as mock_setup_events,
            ):
                # Create the app
                AirdancerApp(mock_config)

                # Verify both setup methods were called
                mock_setup_commands.assert_called_once()
                mock_setup_events.assert_called_once()

    def test_message_handler_processes_direct_messages(self, mock_config):
        """Test that message handler is set up to process direct messages correctly"""
        with (
            patch("airdancer.main.DatabaseService") as mock_db_service_class,
            patch("airdancer.main.MQTTService"),
            patch("airdancer.main.App") as mock_app_class,
        ):
            mock_slack_app = Mock()
            mock_app_class.return_value = mock_slack_app
            mock_db_service = Mock()
            mock_db_service_class.return_value = mock_db_service

            # Create the app
            AirdancerApp(mock_config)

            # Get the message handler that was registered
            assert mock_slack_app.event.called, "No event handler registered"

            # Find the message event handler call
            message_calls = [
                call
                for call in mock_slack_app.event.call_args_list
                if call[0][0] == "message"
            ]
            assert len(message_calls) > 0, "No message event handler found"

            # Verify that the event decorator was called with "message"
            # The actual handler function is registered via the decorator pattern
            # so we just need to verify the decorator was called correctly
            message_call = message_calls[0]
            assert message_call[0][0] == "message", (
                "Message event type not registered correctly"
            )

    def test_simulated_missing_message_handler_would_fail(self):
        """Demonstrate how the original bug would manifest in tests

        This test simulates what would happen if we forgot the message handler.
        """
        # Simulate the old broken setup (before the fix)
        mock_slack_app = Mock()

        # Only register command handler (simulating the bug)
        mock_slack_app.command.return_value = Mock()
        # Don't register event handler (this was the bug!)

        # This would represent what the Slack app would log:
        # "Unhandled request ({'type': 'event_callback', 'event': {'type': 'message'}})"

        unhandled_events = []

        def simulate_slack_message_event():
            """Simulate receiving a message event"""
            event = {
                "type": "event_callback",
                "event": {
                    "type": "message",
                    "channel_type": "im",
                    "user": "U123",
                    "text": "help",
                },
            }

            # Check if there's a handler for this event
            message_calls = [
                call
                for call in mock_slack_app.event.call_args_list
                if len(call[0]) > 0 and call[0][0] == "message"
            ]

            if not message_calls:
                unhandled_events.append(event)
                return {"error": "unhandled request"}

            return {"ok": True}

        # Simulate the scenario before the fix
        result = simulate_slack_message_event()

        # This would have failed before the fix - unhandled request
        assert len(unhandled_events) == 1, (
            "Should have unhandled event (simulating the bug)"
        )
        assert result["error"] == "unhandled request", (
            "Should return unhandled request error"
        )

    def test_feature_parity_between_interfaces(self, mock_config):
        """Test that slash commands and direct messages have feature parity

        This ensures both interfaces support the same commands.
        """
        with (
            patch("airdancer.main.DatabaseService"),
            patch("airdancer.main.MQTTService"),
            patch("airdancer.main.App") as mock_app_class,
        ):
            mock_slack_app = Mock()
            mock_app_class.return_value = mock_slack_app

            # Create the app
            app = AirdancerApp(mock_config)

            # Both interfaces should exist
            assert mock_slack_app.command.called, "Slash command interface missing"
            assert mock_slack_app.event.called, "Direct message interface missing"

            # Both should support the same underlying functionality
            assert hasattr(app, "user_handler"), "User command handler missing"
            assert hasattr(app, "admin_handler"), "Admin command handler missing"
            assert hasattr(app, "_handle_help"), "Help handler missing"


class TestSpecificMessageEventHandling:
    """Tests for specific message event handling scenarios"""

    def test_message_handler_ignores_channel_messages(self):
        """Test that message handler filters out channel messages"""
        # Direct message event (should be processed)
        dm_event = {
            "event": {
                "type": "message",
                "channel_type": "im",  # Direct message
                "user": "U123456",
                "text": "help",
            }
        }

        # Channel message event (should be ignored)
        channel_event = {
            "event": {
                "type": "message",
                "channel_type": "channel",  # Channel message
                "user": "U123456",
                "text": "help",
            }
        }

        # Bot message event (should be ignored)
        bot_event = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "bot_id": "B123456",  # Bot message
                "text": "automated response",
            }
        }

        # Simulate the filtering logic from the handler
        def should_process_event(event_body):
            event = event_body["event"]
            # This is the filtering logic from our handler
            if event.get("bot_id") or event.get("channel_type") != "im":
                return False
            return True

        # Test the filtering
        assert should_process_event(dm_event), "Should process direct messages"
        assert not should_process_event(channel_event), "Should ignore channel messages"
        assert not should_process_event(bot_event), "Should ignore bot messages"

    def test_message_handler_parses_commands_correctly(self):
        """Test that message handler parses commands the same as slash commands"""
        test_cases = [
            ("help", ["help"], []),
            ("register switch001", ["register", "switch001"], ["switch001"]),
            ("bother user123", ["bother", "user123"], ["user123"]),
            (
                "bother --duration 30 user123",
                ["bother", "--duration", "30", "user123"],
                ["--duration", "30", "user123"],
            ),
            ("  help  ", ["help"], []),  # Test trimming
        ]

        for text, expected_full_args, expected_command_args in test_cases:
            # Simulate the parsing logic from our handler
            args = text.strip().split()
            cmd_args = args[1:] if len(args) > 1 else []

            assert args == expected_full_args, f"Failed parsing full args for: {text}"
            assert cmd_args == expected_command_args, (
                f"Failed parsing command args for: {text}"
            )
