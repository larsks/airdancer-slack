"""User resolution utilities for Airdancer Slack App"""

import logging
from ..handlers.base import CommandContext
from ..services.interfaces import DatabaseServiceInterface

logger = logging.getLogger(__name__)


def _ensure_user_in_database(
    user_id: str, username: str, database_service: DatabaseServiceInterface
) -> None:
    """Ensure user exists in database, adding them if they don't exist."""
    if not database_service.get_user(user_id):
        database_service.add_user(user_id, username)


def resolve_user_identifier(
    user_str: str, context: CommandContext, database_service: DatabaseServiceInterface
) -> str | None:
    """Resolve a user identifier to a Slack user ID.

    Handles multiple formats:
    - Direct user ID format: <@U12345>
    - Plain user ID format: U12345
    - Username format: @username or username

    Args:
        user_str: The user identifier string to resolve
        context: Command context containing Slack client
        database_service: Database service for user lookups and additions

    Returns:
        Slack user ID if found, None otherwise
    """
    # Handle direct user ID format <@U12345>
    if user_str.startswith("<@") and user_str.endswith(">"):
        user_id = user_str[2:-1]
        try:
            response = context.client.users_info(user=user_id)
            if response["ok"]:
                username = response.get("user", {}).get("name", user_id)
                _ensure_user_in_database(user_id, username, database_service)
                return user_id
        except Exception:
            return None

    # Handle plain user ID format (U12345)
    if user_str.startswith("U") and len(user_str) == 9:
        try:
            response = context.client.users_info(user=user_str)
            if response["ok"]:
                username = response.get("user", {}).get("name", user_str)
                _ensure_user_in_database(user_str, username, database_service)
                return user_str
        except Exception:
            return None

    # Handle username format @username or username
    username = user_str[1:] if user_str.startswith("@") else user_str

    # Check if we already have this user in our database by username
    # NOTE: This currently requires get_all_users() - ideally we should add
    # get_user_by_username() to DatabaseServiceInterface for efficiency
    all_users = database_service.get_all_users()
    for user in all_users:
        if user.username == username:
            return user.slack_user_id

    # If not in database, try to look up by username using Slack API
    try:
        response = context.client.users_list()
        if response["ok"]:
            for user in response["members"]:
                if user.get("name") == username and not user.get("deleted", False):
                    user_id = user["id"]
                    _ensure_user_in_database(user_id, username, database_service)
                    return user_id
    except Exception as e:
        logger.warning(f"Error looking up user '{username}' via API: {e}")

    return None
