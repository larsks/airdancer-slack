"""Argument parsers for commands"""

import argparse


def create_bother_parser() -> argparse.ArgumentParser:
    """Create argument parser for bother command"""
    parser = argparse.ArgumentParser(
        prog="bother",
        description="Activate switch for user or group",
        add_help=False,  # We'll handle help ourselves
        exit_on_error=False,  # Don't call sys.exit on error
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


def create_user_set_parser() -> argparse.ArgumentParser:
    """Create argument parser for user set command"""
    parser = argparse.ArgumentParser(
        prog="set",
        description="Configure your user settings",
        add_help=False,
        exit_on_error=False,
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


def create_admin_user_set_parser() -> argparse.ArgumentParser:
    """Create argument parser for admin user set command"""
    parser = argparse.ArgumentParser(
        prog="user set",
        description="Configure user settings (admin)",
        add_help=False,
        exit_on_error=False,
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


def create_switch_list_parser() -> argparse.ArgumentParser:
    """Create argument parser for switch list command"""
    parser = argparse.ArgumentParser(
        prog="switch list",
        description="List all discovered switches",
        add_help=False,
        exit_on_error=False,
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed switch information in interactive format",
    )

    return parser
