"""Table formatting utilities for switch and user data"""

import json
from datetime import datetime
from typing import NamedTuple

from ..models.entities import SwitchWithOwner, User


class SwitchTableRow(NamedTuple):
    """Processed switch data for table display"""

    switch_id: str
    status: str
    power: str
    last_seen: str
    ip_address: str
    username: str


class UserTableRow(NamedTuple):
    """Processed user data for table display"""

    username: str
    admin: str
    botherable: str


class AdminUserTableRow(NamedTuple):
    """Processed user data for admin table display (includes switch)"""

    username: str
    admin: str
    botherable: str
    switch: str


def process_switch_data(switches: list[SwitchWithOwner]) -> list[SwitchTableRow]:
    """Process switch data into table rows with shared formatting logic"""
    rows = []

    for switch in switches:
        # Status as plain text
        status_text = "online" if switch.status == "online" else "offline"

        # Power state as plain text
        power_text = (
            switch.power_state.lower() if switch.power_state != "unknown" else "unknown"
        )

        # Format last seen date
        try:
            last_seen = datetime.fromisoformat(str(switch.last_seen))
            last_seen_text = last_seen.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            last_seen_text = str(switch.last_seen)

        # Extract IP address from device_info
        ip_address = "unknown"
        if switch.device_info:
            try:
                device_data = json.loads(switch.device_info)
                ip_address = device_data.get("ip", "unknown")
            except (json.JSONDecodeError, TypeError):
                ip_address = "unknown"

        # Get username if switch has an owner
        username = switch.owner.username if switch.owner else "unassigned"

        rows.append(
            SwitchTableRow(
                switch_id=switch.switch_id,
                status=status_text,
                power=power_text,
                last_seen=last_seen_text,
                ip_address=ip_address,
                username=username,
            )
        )

    return rows


def process_user_data(users: list[User]) -> list[UserTableRow]:
    """Process user data into table rows with shared formatting logic"""
    rows = []

    for user in users:
        # Get username from slack user ID (remove @ prefix if present)
        username = user.username

        # Admin status as plain text
        admin_text = "yes" if user.is_admin else "no"

        # Botherable status as plain text
        botherable_text = "yes" if user.botherable else "no"

        rows.append(
            UserTableRow(
                username=username,
                admin=admin_text,
                botherable=botherable_text,
            )
        )

    return rows


def process_admin_user_data(users: list[User]) -> list[AdminUserTableRow]:
    """Process user data into admin table rows with shared formatting logic (includes switch)"""
    rows = []

    for user in users:
        # Get username
        username = user.username

        # Admin status as plain text
        admin_text = "yes" if user.is_admin else "no"

        # Botherable status as plain text
        botherable_text = "yes" if user.botherable else "no"

        # Switch name
        switch_text = (
            user.switch_id
            if user.switch_id and user.switch_id.strip()
            else "unassigned"
        )

        rows.append(
            AdminUserTableRow(
                username=username,
                admin=admin_text,
                botherable=botherable_text,
                switch=switch_text,
            )
        )

    return rows


def format_plain_table(rows: list[SwitchTableRow]) -> str:
    """Format switch data as a plain text table"""
    if not rows:
        return ""

    switch_lines = []
    for row in rows:
        # Format the line with consistent column widths
        switch_lines.append(
            f"{row.switch_id:<15} {row.status:<7} {row.power:<7} {row.last_seen:<16} {row.ip_address:<15} {row.username}"
        )

    # Create header and table
    header = f"{'Switch ID':<15} {'Status':<7} {'Power':<7} {'Last Seen':<16} {'IP Address':<15} Username"
    separator = "-" * 80

    return f"```\n{header}\n{separator}\n" + "\n".join(switch_lines) + "\n```"


def format_users_plain_table(rows: list[UserTableRow]) -> str:
    """Format user data as a plain text table"""
    if not rows:
        return ""

    user_lines = []
    for row in rows:
        # Format the line with consistent column widths
        user_lines.append(f"{row.username:<20} {row.admin:<5} {row.botherable}")

    # Create header and table
    header = f"{'Username':<20} {'Admin':<5} Botherable"
    separator = "-" * 40

    return f"```\n{header}\n{separator}\n" + "\n".join(user_lines) + "\n```"


def format_admin_users_plain_table(rows: list[AdminUserTableRow]) -> str:
    """Format admin user data as a plain text table (includes switch column)"""
    if not rows:
        return ""

    user_lines = []
    for row in rows:
        # Format the line with consistent column widths
        user_lines.append(
            f"{row.username:<20} {row.admin:<5} {row.botherable:<10} {row.switch}"
        )

    # Create header and table
    header = f"{'Username':<20} {'Admin':<5} {'Botherable':<10} Switch"
    separator = "-" * 60

    return f"```\n{header}\n{separator}\n" + "\n".join(user_lines) + "\n```"


def _create_box_table(headers: list[str], rows_data: list[list[str]]) -> str:
    """Generic function to create box tables using Unicode box drawing characters"""
    if not rows_data:
        return ""

    # Calculate column widths based on content
    col_widths = []
    for i, header in enumerate(headers):
        max_width = max(len(header), max(len(row[i]) for row in rows_data))
        col_widths.append(max_width)

    # Box drawing characters
    top_left = "┌"
    top_right = "┐"
    bottom_left = "└"
    bottom_right = "┘"
    horizontal = "─"
    vertical = "│"
    cross = "┼"
    top_tee = "┬"
    bottom_tee = "┴"
    left_tee = "├"
    right_tee = "┤"

    # Build the table
    lines = []

    # Top border
    top_line = top_left
    for i, width in enumerate(col_widths):
        top_line += horizontal * (width + 2)  # +2 for padding
        if i < len(col_widths) - 1:
            top_line += top_tee
    top_line += top_right
    lines.append(top_line)

    # Header row
    header_line = vertical
    for i, (header, width) in enumerate(zip(headers, col_widths)):
        header_line += f" {header:<{width}} "
        if i < len(col_widths) - 1:
            header_line += vertical
    header_line += vertical
    lines.append(header_line)

    # Header separator
    sep_line = left_tee
    for i, width in enumerate(col_widths):
        sep_line += horizontal * (width + 2)
        if i < len(col_widths) - 1:
            sep_line += cross
    sep_line += right_tee
    lines.append(sep_line)

    # Data rows
    for row in rows_data:
        data_line = vertical
        for i, (value, width) in enumerate(zip(row, col_widths)):
            data_line += f" {value:<{width}} "
            if i < len(col_widths) - 1:
                data_line += vertical
        data_line += vertical
        lines.append(data_line)

    # Bottom border
    bottom_line = bottom_left
    for i, width in enumerate(col_widths):
        bottom_line += horizontal * (width + 2)
        if i < len(col_widths) - 1:
            bottom_line += bottom_tee
    bottom_line += bottom_right
    lines.append(bottom_line)

    return "```\n" + "\n".join(lines) + "\n```"


def format_box_table(rows: list[SwitchTableRow]) -> str:
    """Format switch data as a box table using Unicode box drawing characters"""
    if not rows:
        return ""

    headers = ["Switch ID", "Status", "Power", "Last Seen", "IP Address", "Username"]
    rows_data = [
        [
            row.switch_id,
            row.status,
            row.power,
            row.last_seen,
            row.ip_address,
            row.username,
        ]
        for row in rows
    ]
    return _create_box_table(headers, rows_data)


def format_users_box_table(rows: list[UserTableRow]) -> str:
    """Format user data as a box table using Unicode box drawing characters"""
    if not rows:
        return ""

    headers = ["Username", "Admin", "Botherable"]
    rows_data = [[row.username, row.admin, row.botherable] for row in rows]
    return _create_box_table(headers, rows_data)


def format_admin_users_box_table(rows: list[AdminUserTableRow]) -> str:
    """Format admin user data as a box table using Unicode box drawing characters (includes switch column)"""
    if not rows:
        return ""

    headers = ["Username", "Admin", "Botherable", "Switch"]
    rows_data = [[row.username, row.admin, row.botherable, row.switch] for row in rows]
    return _create_box_table(headers, rows_data)
