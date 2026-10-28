"""Common interface for language-model providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Callable

from backend.app.core.schemas import ChatMessage
from backend.app.core.config import Settings


class ProviderError(RuntimeError):
    """Raised when a provider cannot complete a request."""


@dataclass(frozen=True)
class ProviderRegistration:
    """Factory metadata discovered from a provider module."""

    provider_id: str
    display_name: str
    get_model: Callable[[Settings], str]
    get_availability: Callable[[Settings], tuple[bool, str | None]]
    create: Callable[[Settings], "BaseLLMProvider"]


class BaseLLMProvider(ABC):
    """Abstract interface implemented by every language-model provider."""

    provider_id: str
    display_name: str
    model: str

    @abstractmethod
    async def generate(self, messages: list[ChatMessage]) -> str:
        """Return a complete response for the given conversation."""

    @abstractmethod
    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        """Yield response text in progressively generated chunks."""
