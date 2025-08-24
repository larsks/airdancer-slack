"""Custom exceptions for the Airdancer application"""

import logging

logger = logging.getLogger(__name__)


class AirdancerException(Exception):
    """Base exception for all Airdancer errors"""

    def __init__(self, message: str, user_message: str | None = None):
        super().__init__(message)
        self.user_message = user_message or message


class UserNotFoundError(AirdancerException):
    """Raised when user is not found"""

    def __init__(self, user_identifier: str):
        super().__init__(
            f"User not found: {user_identifier}",
            f"❌ User not found: {user_identifier}. Please check the username or ID.",
        )


class SwitchRegistrationError(AirdancerException):
    """Raised when switch registration fails"""

    def __init__(self, message: str, user_message: str | None = None):
        super().__init__(
            message, user_message or "❌ Failed to register switch. Please try again."
        )


class SwitchAlreadyRegisteredError(SwitchRegistrationError):
    """Raised when attempting to register an already registered switch"""

    def __init__(self, switch_id: str, owner_id: str):
        super().__init__(
            f"Switch {switch_id} is already registered to user {owner_id}",
            f"❌ Switch `{switch_id}` is already registered to another user. Please contact an administrator if you believe this is an error.",
        )


class MQTTConnectionError(AirdancerException):
    """Raised when MQTT operations fail"""

    def __init__(self, operation: str, switch_id: str | None = None):
        switch_info = f" for switch {switch_id}" if switch_id else ""
        super().__init__(
            f"MQTT {operation} failed{switch_info}",
            f"❌ Communication error with device{switch_info}. Please try again later.",
        )


class DatabaseError(AirdancerException):
    """Raised when database operations fail"""

    def __init__(self, operation: str, details: str | None = None):
        message = f"Database {operation} failed"
        if details:
            message += f": {details}"
        super().__init__(message, "❌ Database error occurred. Please try again later.")


class ValidationError(AirdancerException):
    """Raised when input validation fails"""

    def __init__(self, field: str, value: str, requirement: str):
        super().__init__(
            f"Validation failed for {field}='{value}': {requirement}",
            f"❌ Invalid {field}: {requirement}",
        )


class PermissionError(AirdancerException):
    """Raised when user lacks required permissions"""

    def __init__(self, operation: str):
        super().__init__(
            f"Permission denied for operation: {operation}",
            f"❌ You don't have permission to perform this operation: {operation}",
        )


class CommandError(AirdancerException):
    """Raised when command execution fails"""

    def __init__(self, command: str, reason: str):
        super().__init__(
            f"Command '{command}' failed: {reason}",
            f"❌ Command '{command}' failed: {reason}",
        )
