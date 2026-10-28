"""OpenAI-compatible chat-completions provider."""

import json
from collections.abc import AsyncIterator

import httpx

from backend.app.core.schemas import ChatMessage
from backend.app.core.config import Settings
from backend.app.providers.base import BaseLLMProvider, ProviderError, ProviderRegistration


class OpenAICompatibleProvider(BaseLLMProvider):
    """Connect to OpenAI or another compatible chat-completions API."""

    provider_id = "openai"
    display_name = "OpenAI-compatible"

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    @property
    def headers(self) -> dict[str, str]:
        """Return authorization headers when a key is configured."""
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    async def generate(self, messages: list[ChatMessage]) -> str:
        """Return a non-streaming compatible completion."""
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": self.model,
                        "messages": [item.model_dump() for item in messages],
                        "stream": False,
                    },
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except httpx.HTTPError as exc:
            raise ProviderError(f"OpenAI-compatible request failed: {exc}") from exc
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError("OpenAI-compatible API returned an invalid response.") from exc

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        """Yield Server-Sent Events content deltas."""
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": self.model,
                        "messages": [item.model_dump() for item in messages],
                        "stream": True,
                    },
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            content = json.loads(data)["choices"][0]["delta"].get("content") or ""
                        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
                            raise ProviderError("OpenAI-compatible API returned malformed streaming data.") from exc
                        if content:
                            yield content
        except httpx.HTTPError as exc:
            raise ProviderError(f"OpenAI-compatible request failed: {exc}") from exc


def get_provider_registration() -> ProviderRegistration:
    """Expose this provider to the auto-discovered provider registry."""
    def availability(settings: Settings) -> tuple[bool, str | None]:
        configured_url = settings.openai_base_url != "https://api.openai.com/v1"
        available = bool(settings.openai_api_key) or configured_url
        detail = None if available else "Set OPENAI_API_KEY or configure a local compatible URL."
        return available, detail

    return ProviderRegistration(
        provider_id="openai",
        display_name="OpenAI-compatible",
        get_model=lambda settings: settings.openai_model,
        get_availability=availability,
        create=lambda settings: OpenAICompatibleProvider(
            settings.openai_base_url, settings.openai_api_key, settings.openai_model
        ),
    )
