"""Ollama chat-completions provider."""

import json
from collections.abc import AsyncIterator

import httpx

from backend.app.core.schemas import ChatMessage
from backend.app.core.config import Settings
from backend.app.providers.base import BaseLLMProvider, ProviderError, ProviderRegistration


class OllamaProvider(BaseLLMProvider):
    """Use Ollama's local `/api/chat` endpoint."""

    provider_id = "ollama"
    display_name = "Ollama (local)"

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate(self, messages: list[ChatMessage]) -> str:
        """Return a non-streaming Ollama response."""
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={"model": self.model, "messages": [item.model_dump() for item in messages], "stream": False},
                )
                response.raise_for_status()
        except httpx.ConnectError as exc:
            raise self._connection_error() from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Ollama request failed: {exc}") from exc
        try:
            return response.json()["message"]["content"]
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError("Ollama returned an invalid response.") from exc

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        """Yield Ollama response chunks."""
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={"model": self.model, "messages": [item.model_dump() for item in messages], "stream": True},
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            payload = json.loads(line)
                            content = payload.get("message", {}).get("content", "")
                        except json.JSONDecodeError as exc:
                            raise ProviderError("Ollama returned malformed streaming data.") from exc
                        if content:
                            yield content
        except httpx.ConnectError as exc:
            raise self._connection_error() from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Ollama request failed: {exc}") from exc

    def _connection_error(self) -> ProviderError:
        """Explain how to restore a connection to the local Ollama service."""
        return ProviderError(
            f"Cannot connect to Ollama at {self.base_url}. Start the Ollama service "
            "(`sudo systemctl start ollama`) or run `ollama serve`, then verify the "
            f"configured model exists with `ollama list` (current model: {self.model})."
        )


def get_provider_registration() -> ProviderRegistration:
    """Expose this provider to the auto-discovered provider registry."""
    return ProviderRegistration(
        provider_id="ollama",
        display_name="Ollama (local)",
        get_model=lambda settings: settings.ollama_model,
        get_availability=lambda _: (True, None),
        create=lambda settings: OllamaProvider(settings.ollama_base_url, settings.ollama_model),
    )
