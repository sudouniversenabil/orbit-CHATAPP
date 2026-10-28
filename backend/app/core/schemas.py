"""Pydantic request and response schemas shared by the API."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A message in a conversation."""

    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    """Request body for a chat completion."""

    messages: list[ChatMessage] = Field(min_length=1)


class ChatResponse(BaseModel):
    """Chat completion response, optionally including a routed system command."""

    response: str
    command_handled: bool = False


class ModelInfo(BaseModel):
    """A selectable LLM provider and its configured model."""

    id: str
    name: str
    model: str
    available: bool
    active: bool
    detail: str | None = None


class ModelSelectionRequest(BaseModel):
    """Request to change the active provider."""

    provider_id: str = Field(min_length=1)


class ModelSelectionResponse(BaseModel):
    """Result of changing the active provider."""

    active_provider: str
    model: str


class CommandInfo(BaseModel):
    """Public description of an available system command."""

    id: str
    name: str
    description: str
    examples: list[str]


class HealthResponse(BaseModel):
    """Backend health status."""

    status: Literal["ok"] = "ok"
    app: str


class VoiceTextRequest(BaseModel):
    """WebSocket message containing recognized or typed text."""

    type: Literal["text"]
    text: str = Field(min_length=1)


class VoiceAudioRequest(BaseModel):
    """WebSocket message containing a base64-encoded audio segment."""

    type: Literal["audio"]
    data: str = Field(min_length=1, max_length=32_000_000)
    mime_type: str = "audio/webm"


class VoiceSettingsRequest(BaseModel):
    """WebSocket message updating session voice preferences."""

    type: Literal["settings"]
    wake_word_enabled: bool | None = None
    wake_word: str | None = None
    tts_enabled: bool | None = None


VoiceClientRequest = Annotated[
    VoiceTextRequest | VoiceAudioRequest | VoiceSettingsRequest,
    Field(discriminator="type"),
]


class VoiceServerEvent(BaseModel):
    """A typed server-to-browser WebSocket event."""

    type: Literal[
        "settings_ack",
        "error",
        "transcript",
        "wake_required",
        "wake_detected",
        "assistant_start",
        "token",
        "assistant_done",
    ]
    text: str | None = None
    message: str | None = None
    command_handled: bool | None = None
