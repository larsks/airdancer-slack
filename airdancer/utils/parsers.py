"""Argument parsers for commands"""

import argparse


class HelpRequestedException(Exception):
    """Exception raised when --help is requested"""

    def __init__(self, help_text: str):
        self.help_text = help_text
        super().__init__("Help requested")


class HelpRequestedAction(argparse.Action):
    """Custom action that raises HelpRequestedException when --help is used"""

    def __init__(
        self,
        option_strings,
        dest,
        nargs=None,
        const=None,
        default=None,
        type=None,
        choices=None,
        required=False,
        help=None,
        metavar=None,
    ):
        super().__init__(
            option_strings,
            dest,
            0,  # nargs=0 means no value is consumed
            const,
            default,
            type,
            choices,
            required,
            help,
            metavar,
        )

    def __call__(
        self, parser: argparse.ArgumentParser, namespace, values, option_string=None
    ):
        raise HelpRequestedException(parser.format_help())


class SlackCommandParser(argparse.ArgumentParser):
    """Base class for Slack command parsers with standardized help handling"""

    def __init__(self, *args, **kwargs):
        # Force exit_on_error=False and add_help=False
        kwargs["exit_on_error"] = False
        kwargs["add_help"] = False
        super().__init__(*args, **kwargs)
        # Add standard --help option with custom action
        self.add_argument(
            "--help", action=HelpRequestedAction, help="Show this help message"
        )


def create_bother_parser() -> SlackCommandParser:
    """Create argument parser for bother command"""
    parser = SlackCommandParser(
        prog="bother",
        description="Activate switch for user or group",
    )
    parser.add_argument(
        "--duration",
        "-d",
        type=int,
        default=15,
        help="Duration in seconds (default: 15)",
    )
    parser.add_argument("target", help="Target user or group to bother")

    return parser


def create_user_set_parser() -> SlackCommandParser:
    """Create argument parser for user set command"""
    parser = SlackCommandParser(
        prog="set",
        description="Configure your user settings",
    )

    bother_group = parser.add_mutually_exclusive_group(required=True)
    bother_group.add_argument(
        "--bother",
        action="store_true",
        help="Allow other users to bother you (default)",
    )
    bother_group.add_argument(
        "--no-bother",
        action="store_true",
        help="Prevent other users from bothering you",
    )

    return parser


def create_admin_user_set_parser() -> SlackCommandParser:
    """Create argument parser for admin user set command"""
    parser = SlackCommandParser(
        prog="user set",
        description="Configure user settings (admin)",
    )

    parser.add_argument("user", help="User to modify (username or @mention)")

    # Admin privileges group
    admin_group = parser.add_mutually_exclusive_group()
    admin_group.add_argument(
        "--admin", action="store_true", help="Grant admin privileges to user"
    )
    admin_group.add_argument(
        "--no-admin", action="store_true", help="Revoke admin privileges from user"
    )

    # Bother permissions group
    bother_group = parser.add_mutually_exclusive_group()
    bother_group.add_argument(
        "--bother", action="store_true", help="Allow other users to bother this user"
    )
    bother_group.add_argument(
        "--no-bother",
        action="store_true",
        help="Prevent other users from bothering this user",
    )

    return parser


def create_switch_list_parser() -> SlackCommandParser:
    """Create argument parser for switch list command"""
    parser = SlackCommandParser(
        prog="switch list",
        description="List all discovered switches",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed switch information in interactive format",
    )
    parser.add_argument(
        "--box",
        "-b",
        action="store_true",
        help="Display table with box drawing characters",
    )

    return parser


def create_users_list_parser() -> SlackCommandParser:
    """Create argument parser for users list command"""
    parser = SlackCommandParser(
        prog="users",
        description="List all registered users",
    )
    parser.add_argument(
        "--short",
        "-s",
        action="store_true",
        help="Show simple plain-text table format",
    )
    parser.add_argument(
        "--box",
        "-b",
        action="store_true",
        help="Display table with box drawing characters",
    )

    return parser


def create_admin_user_list_parser() -> SlackCommandParser:
    """Create argument parser for admin user list command"""
    parser = SlackCommandParser(
        prog="user list",
        description="List all registered users (admin only)",
    )
    parser.add_argument(
        "--short",
        "-s",
        action="store_true",
        help="Show simple plain-text table format",
    )
    parser.add_argument(
        "--box",
        "-b",
        action="store_true",
        help="Display table with box drawing characters",
    )

    return parser


def create_register_parser() -> SlackCommandParser:
    """Create argument parser for register command"""
    parser = SlackCommandParser(
        prog="register",
        description="Register a switch to your account",
    )
    parser.add_argument("switch_id", help="Switch ID to register")
    return parser


def create_unregister_parser() -> SlackCommandParser:
    """Create argument parser for unregister command (admin only)"""
    parser = SlackCommandParser(
        prog="unregister",
        description="Remove a user's switch registration (admin only)",
    )
    parser.add_argument("user", help="User to unregister (username or @mention)")
    return parser


def create_groups_parser() -> SlackCommandParser:
    """Create argument parser for groups command"""
    parser = SlackCommandParser(
        prog="groups",
        description="List all available groups",
    )
    return parser
