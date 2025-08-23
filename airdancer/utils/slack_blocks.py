"""Utilities for Slack Block Kit responses"""

import logging
from typing import List, Dict, Any, Callable, Union

logger = logging.getLogger(__name__)


def send_blocks_response(
    blocks: List[Dict[str, Any]],
    context_respond: Callable[[Union[str, Dict[str, Any]]], None],
    fallback_text: str,
    fallback_content_generator: Callable[[], str] = None,
) -> None:
    """
    Send a Slack blocks response with fallback handling.

    Args:
        blocks: List of Slack Block Kit blocks
        context_respond: The respond function from CommandContext
        fallback_text: Text to use as fallback title/content
        fallback_content_generator: Optional function to generate detailed fallback content
    """
    # Try different approaches for sending blocks
    try:
        # Method 1: Direct blocks parameter (for slash commands)
        context_respond(blocks=blocks)
    except TypeError:
        try:
            # Method 2: Dictionary with blocks (for some response types)
            context_respond({"text": fallback_text, "blocks": blocks})
        except Exception:
            # Method 3: Fallback to text format
            logger.info("Blocks not supported, using text fallback")
            if fallback_content_generator:
                fallback_content = fallback_content_generator()
            else:
                fallback_content = fallback_text
            context_respond(fallback_content)


def create_header_block(title: str) -> Dict[str, Any]:
    """Create a header block with the given title."""
    return {
        "type": "header",
        "text": {"type": "plain_text", "text": title},
    }


def create_divider_block() -> Dict[str, Any]:
    """Create a divider block."""
    return {"type": "divider"}


def create_section_block(
    text: str, fields: List[Dict[str, Any]] = None, accessory: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Create a section block with optional fields and accessory.

    Args:
        text: Main text for the section (markdown format)
        fields: Optional list of field objects
        accessory: Optional accessory element (button, image, etc.)
    """
    section = {
        "type": "section",
        "text": {"type": "mrkdwn", "text": text},
    }

    if fields:
        section["fields"] = fields

    if accessory:
        section["accessory"] = accessory

    return section


def create_button_accessory(
    text: str, action_id: str, value: str, style: str = "primary"
) -> Dict[str, Any]:
    """
    Create a button accessory for use in section blocks.

    Args:
        text: Button text
        action_id: Action ID for the button
        value: Value to pass when button is clicked
        style: Button style (primary, danger, etc.)
    """
    return {
        "type": "button",
        "text": {"type": "plain_text", "text": text},
        "action_id": action_id,
        "value": value,
        "style": style,
    }


def create_field(title: str, content: str) -> Dict[str, Any]:
    """Create a field for use in section blocks."""
    return {
        "type": "mrkdwn",
        "text": f"*{title}:*\n{content}",
    }
