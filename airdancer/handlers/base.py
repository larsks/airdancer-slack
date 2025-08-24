"""Base command handler classes"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class CommandContext:
    """Context for command execution"""

    user_id: str
    args: list[str]
    respond: Callable[[str | dict[str, Any]], None]
    client: Any


class BaseCommand(ABC):
    """Base class for all commands"""

    @abstractmethod
    def execute(self, context: CommandContext) -> None:
        """Execute the command"""
        pass

    @abstractmethod
    def can_execute(self, context: CommandContext) -> bool:
        """Check if the command can be executed with the given context"""
        pass
