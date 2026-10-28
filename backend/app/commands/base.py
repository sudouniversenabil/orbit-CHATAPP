"""Interfaces for command plugins."""

from abc import ABC, abstractmethod

from backend.app.core.schemas import CommandInfo


class CommandPlugin(ABC):
    """Base class for a command that can safely perform one system action."""

    info: CommandInfo

    @abstractmethod
    def matches(self, text: str) -> bool:
        """Return whether this plugin recognizes the input."""

    @abstractmethod
    async def execute(self, text: str) -> str:
        """Perform the recognized action and return a user-facing result."""
