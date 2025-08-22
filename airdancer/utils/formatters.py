"""Utility functions for formatting and parsing"""


def clean_switch_id(switch_str: str) -> str:
    """Remove formatting characters commonly used in Slack messages"""
    # Strip backticks, quotes, and whitespace
    cleaned = switch_str.strip()
    if cleaned.startswith("`") and cleaned.endswith("`"):
        cleaned = cleaned[1:-1]
    if cleaned.startswith('"') and cleaned.endswith('"'):
        cleaned = cleaned[1:-1]
    if cleaned.startswith("'") and cleaned.endswith("'"):
        cleaned = cleaned[1:-1]
    return cleaned.strip()


def parse_user_mention(user_str: str) -> str:
    """Parse user mention to extract user ID or username"""
    # Handle both @username and <@U1234567890> formats
    if user_str.startswith("<@") and user_str.endswith(">"):
        return user_str[2:-1]
    elif user_str.startswith("@"):
        return user_str[1:]
    else:
        return user_str
