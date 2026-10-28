"""Tests for provider selection and response parsing."""

import pytest

from backend.app.core.config import Settings
from backend.app.core.schemas import ChatMessage
from backend.app.providers.anthropic import AnthropicProvider
from backend.app.providers.gemini import GeminiProvider
from backend.app.providers.ollama import OllamaProvider
from backend.app.providers.registry import ProviderRegistry


def test_provider_registry_lists_all_integrations() -> None:
    registry = ProviderRegistry(Settings())
    assert {model.id for model in registry.models()} == {"ollama", "openai", "anthropic", "gemini"}
    assert registry.create("ollama").model == "llama3.2"


def test_anthropic_payload_moves_system_message() -> None:
    provider = AnthropicProvider("secret", "claude-test")
    payload = provider._payload(
        [ChatMessage(role="system", content="Be brief."), ChatMessage(role="user", content="Hi")],
        stream=False,
    )
    assert payload["system"] == "Be brief."
    assert payload["messages"] == [{"role": "user", "content": "Hi"}]


def test_gemini_extracts_text_response() -> None:
    result = GeminiProvider._extract(
        {"candidates": [{"content": {"parts": [{"text": "Hi"}, {"text": " there"}]}}]}
    )
    assert result == "Hi there"


def test_registry_rejects_unconfigured_cloud_provider() -> None:
    registry = ProviderRegistry(Settings(anthropic_api_key=""))
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        registry.create("anthropic")


def test_ollama_connection_error_has_recovery_steps() -> None:
    provider = OllamaProvider("http://localhost:11434", "llama3.2")
    error = provider._connection_error()
    assert "Cannot connect to Ollama at http://localhost:11434" in str(error)
    assert "ollama serve" in str(error)
    assert "ollama list" in str(error)
