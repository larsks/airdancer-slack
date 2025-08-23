"""Centralized error handling for command execution"""

import logging
from .exceptions import (
    AirdancerException,
    UserNotFoundError,
    SwitchAlreadyRegisteredError,
    ValidationError,
    PermissionError,
)
from .handlers.base import CommandContext

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling for command execution"""

    @staticmethod
    def handle_command_error(error: Exception, context: CommandContext) -> None:
        """Handle errors that occur during command execution"""
        try:
            if isinstance(error, AirdancerException):
                # Our custom exceptions have user-friendly messages
                context.respond(error.user_message)
                logger.warning(f"Command error: {error}")
            else:
                # Unexpected errors should be logged but show generic message to user
                logger.exception(f"Unexpected error in command handling: {error}")
                context.respond(
                    "❌ An unexpected error occurred. Please try again or contact support."
                )
        except Exception as handler_error:
            # If even error handling fails, log it and show minimal message
            logger.critical(f"Error handler failed: {handler_error}")
            try:
                context.respond("❌ System error occurred.")
            except Exception:
                # Last resort - just log it
                logger.critical("Failed to send error response to user")

    @staticmethod
    def wrap_command_execution(command_func, context: CommandContext, *args, **kwargs):
        """Decorator-like function to wrap command execution with error handling"""
        try:
            return command_func(*args, **kwargs)
        except Exception as e:
            ErrorHandler.handle_command_error(e, context)
            return None


def handle_errors(func):
    """Decorator to automatically handle errors in command methods"""

    def wrapper(self, context: CommandContext, *args, **kwargs):
        try:
            return func(self, context, *args, **kwargs)
        except Exception as e:
            ErrorHandler.handle_command_error(e, context)
            return None

    return wrapper


# Utility functions for raising common errors
def raise_user_not_found(user_identifier: str) -> None:
    """Convenience function to raise UserNotFoundError"""
    raise UserNotFoundError(user_identifier)


def raise_permission_denied(operation: str) -> None:
    """Convenience function to raise PermissionError"""
    raise PermissionError(operation)


def raise_validation_error(field: str, value: str, requirement: str) -> None:
    """Convenience function to raise ValidationError"""
    raise ValidationError(field, value, requirement)


def raise_switch_already_registered(switch_id: str, owner_id: str) -> None:
    """Convenience function to raise SwitchAlreadyRegisteredError"""
    raise SwitchAlreadyRegisteredError(switch_id, owner_id)
