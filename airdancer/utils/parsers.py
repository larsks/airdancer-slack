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
