"""Google Gemini generateContent provider."""

import json
from collections.abc import AsyncIterator

import httpx

from backend.app.core.schemas import ChatMessage
from backend.app.core.config import Settings
from backend.app.providers.base import BaseLLMProvider, ProviderError, ProviderRegistration


class GeminiProvider(BaseLLMProvider):
    """Connect to Gemini's REST API."""

    provider_id = "gemini"
    display_name = "Google Gemini"
    base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def _payload(self, messages: list[ChatMessage]) -> dict[str, object]:
        """Convert common chat messages into Gemini contents."""
        system = "\n".join(item.content for item in messages if item.role == "system")
        payload: dict[str, object] = {
            "contents": [
                {
                    "role": "model" if item.role == "assistant" else "user",
                    "parts": [{"text": item.content}],
                }
                for item in messages
                if item.role != "system"
            ]
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        return payload

    async def generate(self, messages: list[ChatMessage]) -> str:
        """Return a complete Gemini response."""
        url = f"{self.base_url}/{self.model}:generateContent"
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(url, params={"key": self.api_key}, json=self._payload(messages))
                response.raise_for_status()
                return self._extract(response.json())
        except httpx.HTTPError as exc:
            raise ProviderError(f"Gemini request failed: {exc}") from exc
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError("Gemini returned an invalid response.") from exc

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        """Yield text chunks from Gemini's server-sent event stream."""
        url = f"{self.base_url}/{self.model}:streamGenerateContent"
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    url,
                    params={"key": self.api_key, "alt": "sse"},
                    json=self._payload(messages),
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        try:
                            text = self._extract(json.loads(line[6:]))
                        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
                            raise ProviderError("Gemini returned malformed streaming data.") from exc
                        if text:
                            yield text
        except httpx.HTTPError as exc:
            raise ProviderError(f"Gemini request failed: {exc}") from exc

    @staticmethod
    def _extract(payload: dict[str, object]) -> str:
        """Extract text from a Gemini candidate response."""
        candidates = payload["candidates"]
        return "".join(part.get("text", "") for part in candidates[0]["content"]["parts"])


def get_provider_registration() -> ProviderRegistration:
    """Expose this provider to the auto-discovered provider registry."""
    return ProviderRegistration(
        provider_id="gemini",
        display_name="Google Gemini",
        get_model=lambda settings: settings.gemini_model,
        get_availability=lambda settings: (
            bool(settings.gemini_api_key),
            None if settings.gemini_api_key else "Set GEMINI_API_KEY.",
        ),
        create=lambda settings: GeminiProvider(settings.gemini_api_key, settings.gemini_model),
    )
