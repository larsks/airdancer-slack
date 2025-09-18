"""Tests for SlackCommandParser help functionality"""

import pytest
import argparse
from airdancer.utils.parsers import (
    SlackCommandParser,
    HelpRequestedException,
    HelpRequestedAction,
)


class TestSlackCommandParserHelp:
    """Test help functionality in SlackCommandParser"""

    def test_help_flag_raises_exception_with_required_args(self):
        """Test that --help flag works even when required arguments are missing"""
        parser = SlackCommandParser(prog="test", description="Test parser")
        parser.add_argument("required_arg", help="Required argument")

        with pytest.raises(HelpRequestedException) as exc_info:
            parser.parse_args(["--help"])

        # Verify the help text is included in the exception
        help_text = exc_info.value.help_text
        assert "test" in help_text
        assert "Test parser" in help_text
        assert "required_arg" in help_text

    def test_help_with_bother_command_structure(self):
        """Test help functionality with bother command structure"""
        parser = SlackCommandParser(
            prog="bother", description="Activate switch for user or group"
        )
        parser.add_argument("target", help="Target user or group to bother")
        parser.add_argument(
            "--duration", "-d", type=int, default=15, help="Duration in seconds"
        )

        with pytest.raises(HelpRequestedException) as exc_info:
            parser.parse_args(["--help"])

        help_text = exc_info.value.help_text
        assert "bother" in help_text
        assert "target" in help_text
        assert "--duration" in help_text
        assert "Duration in seconds" in help_text
        assert "Activate switch for user or group" in help_text

    def test_normal_parsing_still_works(self):
        """Test that normal argument parsing continues to work"""
        parser = SlackCommandParser(prog="test", description="Test parser")
        parser.add_argument("target", help="Target argument")
        parser.add_argument(
            "--duration", "-d", type=int, default=15, help="Duration in seconds"
        )

        # Should not raise any exception
        args = parser.parse_args(["testuser", "--duration", "30"])

        assert args.target == "testuser"
        assert args.duration == 30
        # The help attribute should not be present or should be False
        assert not hasattr(args, "help") or not args.help

    def test_missing_required_args_raises_normal_exceptions(self):
        """Test that missing required arguments still raise normal ArgumentParser exceptions"""
        parser = SlackCommandParser(prog="test", description="Test parser")
        parser.add_argument("target", help="Target argument")

        # Should raise ArgumentError (not HelpRequestedException)
        with pytest.raises(argparse.ArgumentError):
            parser.parse_args([])  # Missing required argument

    def test_help_action_class_behavior(self):
        """Test the HelpRequestedAction class directly"""
        parser = SlackCommandParser(prog="test", description="Test parser")

        # The action should be an instance of HelpRequestedAction
        help_action = None
        for action in parser._actions:
            if "--help" in action.option_strings:
                help_action = action
                break

        assert help_action is not None
        assert isinstance(help_action, HelpRequestedAction)
        assert help_action.nargs == 0  # Should consume no arguments

    def test_help_exception_contains_formatted_help(self):
        """Test that HelpRequestedException contains properly formatted help text"""
        parser = SlackCommandParser(
            prog="register", description="Register a switch to your account"
        )
        parser.add_argument("switch_id", help="Switch ID to register")

        with pytest.raises(HelpRequestedException) as exc_info:
            parser.parse_args(["--help"])

        help_text = exc_info.value.help_text

        # Should contain standard argparse help format elements
        assert "usage:" in help_text.lower()
        assert "register" in help_text
        assert "switch_id" in help_text
        assert "Switch ID to register" in help_text
        assert "--help" in help_text  # Should show the help option too

    def test_help_with_optional_args_only(self):
        """Test help functionality with only optional arguments"""
        parser = SlackCommandParser(
            prog="groups", description="List all available groups"
        )
        # No required arguments

        with pytest.raises(HelpRequestedException) as exc_info:
            parser.parse_args(["--help"])

        help_text = exc_info.value.help_text
        assert "groups" in help_text
        assert "List all available groups" in help_text
        assert "--help" in help_text

    def test_help_parsing_vs_normal_parsing(self):
        """Test that help parsing happens before normal validation"""
        parser = SlackCommandParser(prog="test", description="Test parser")
        parser.add_argument("required", help="Required argument")
        parser.add_argument("--optional", help="Optional argument")

        # Help should work even with invalid combinations
        with pytest.raises(HelpRequestedException):
            parser.parse_args(["--help", "--invalid-flag"])

        # Normal parsing should validate properly
        args = parser.parse_args(["required_value", "--optional", "optional_value"])
        assert args.required == "required_value"
        assert args.optional == "optional_value"
