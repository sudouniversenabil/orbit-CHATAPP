"""Anthropic Messages API provider."""

import json
from collections.abc import AsyncIterator

import httpx

from backend.app.core.schemas import ChatMessage
from backend.app.core.config import Settings
from backend.app.providers.base import BaseLLMProvider, ProviderError, ProviderRegistration


class AnthropicProvider(BaseLLMProvider):
    """Connect to the Anthropic Messages API."""

    provider_id = "anthropic"
    display_name = "Anthropic Claude"
    base_url = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def _payload(self, messages: list[ChatMessage], stream: bool) -> dict[str, object]:
        """Convert common chat messages to Anthropic's request format."""
        system = "\n".join(item.content for item in messages if item.role == "system")
        payload: dict[str, object] = {
            "model": self.model,
            "max_tokens": 2048,
            "messages": [
                {"role": item.role, "content": item.content}
                for item in messages
                if item.role != "system"
            ],
            "stream": stream,
        }
        if system:
            payload["system"] = system
        return payload

    @property
    def headers(self) -> dict[str, str]:
        """Return required Anthropic headers."""
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    async def generate(self, messages: list[ChatMessage]) -> str:
        """Return a complete Anthropic response."""
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    self.base_url, headers=self.headers, json=self._payload(messages, False)
                )
                response.raise_for_status()
                blocks = response.json()["content"]
                return "".join(block.get("text", "") for block in blocks if block.get("type") == "text")
        except httpx.HTTPError as exc:
            raise ProviderError(f"Anthropic request failed: {exc}") from exc
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError("Anthropic returned an invalid response.") from exc

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        """Yield text deltas from Anthropic Server-Sent Events."""
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST", self.base_url, headers=self.headers, json=self._payload(messages, True)
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        try:
                            event = json.loads(line[6:])
                        except json.JSONDecodeError as exc:
                            raise ProviderError("Anthropic returned malformed streaming data.") from exc
                        if event.get("type") == "content_block_delta":
                            text = event.get("delta", {}).get("text", "")
                            if text:
                                yield text
        except httpx.HTTPError as exc:
            raise ProviderError(f"Anthropic request failed: {exc}") from exc


def get_provider_registration() -> ProviderRegistration:
    """Expose this provider to the auto-discovered provider registry."""
    return ProviderRegistration(
        provider_id="anthropic",
        display_name="Anthropic Claude",
        get_model=lambda settings: settings.anthropic_model,
        get_availability=lambda settings: (
            bool(settings.anthropic_api_key),
            None if settings.anthropic_api_key else "Set ANTHROPIC_API_KEY.",
        ),
        create=lambda settings: AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model),
    )
