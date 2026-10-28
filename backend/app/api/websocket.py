"""WebSocket chat and voice streaming endpoint."""

import base64
import binascii
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import TypeAdapter, ValidationError

from backend.app.commands.router import command_router
from backend.app.core.config import get_settings
from backend.app.core.schemas import (
    ChatMessage,
    VoiceAudioRequest,
    VoiceClientRequest,
    VoiceServerEvent,
    VoiceSettingsRequest,
    VoiceTextRequest,
)
from backend.app.providers.base import ProviderError
from backend.app.providers.registry import registry
from backend.app.voice.stt import transcribe
from backend.app.voice.tts import speak
from backend.app.voice.wake_word import wake_word_command

logger = logging.getLogger(__name__)
router = APIRouter()
client_request_adapter = TypeAdapter(VoiceClientRequest)


async def _send_event(websocket: WebSocket, event: VoiceServerEvent) -> None:
    """Serialize a typed WebSocket event to the browser."""
    await websocket.send_json(event.model_dump(exclude_none=True))


@router.websocket("/ws/voice")
async def voice_socket(websocket: WebSocket) -> None:
    """Accept text or encoded audio messages and stream assistant replies."""
    await websocket.accept()
    settings = get_settings()
    wake_enabled = settings.wake_word_enabled
    tts_enabled = settings.tts_enabled
    wake_phrase = settings.wake_word
    conversation: list[ChatMessage] = []
    try:
        while True:
            raw_payload = await websocket.receive_json()
            try:
                payload = client_request_adapter.validate_python(raw_payload)
            except ValidationError as exc:
                await _send_event(
                    websocket,
                    VoiceServerEvent(type="error", message=f"Invalid WebSocket message: {exc.errors()[0]['msg']}"),
                )
                continue
            if isinstance(payload, VoiceSettingsRequest):
                if payload.wake_word_enabled is not None:
                    wake_enabled = payload.wake_word_enabled
                if payload.tts_enabled is not None:
                    tts_enabled = payload.tts_enabled
                if payload.wake_word is not None:
                    wake_phrase = payload.wake_word.strip() or settings.wake_word
                await _send_event(websocket, VoiceServerEvent(type="settings_ack"))
                continue
            if isinstance(payload, VoiceTextRequest):
                text = payload.text.strip()
            elif isinstance(payload, VoiceAudioRequest):
                try:
                    audio = base64.b64decode(payload.data, validate=True)
                except (ValueError, binascii.Error):
                    await _send_event(
                        websocket,
                        VoiceServerEvent(type="error", message="Audio payload is not valid base64."),
                    )
                    continue
                if not audio:
                    await _send_event(websocket, VoiceServerEvent(type="error", message="Audio payload is empty."))
                    continue
                try:
                    text = await transcribe(audio, payload.mime_type)
                except RuntimeError as exc:
                    logger.warning("Speech recognition unavailable: %s", exc)
                    await _send_event(websocket, VoiceServerEvent(type="error", message=str(exc)))
                    continue
                if not text:
                    await _send_event(websocket, VoiceServerEvent(type="transcript", text=""))
                    continue
                await _send_event(websocket, VoiceServerEvent(type="transcript", text=text))
            if not text:
                await _send_event(websocket, VoiceServerEvent(type="error", message="Message text cannot be empty."))
                continue
            if wake_enabled:
                after_wake = wake_word_command(text, wake_phrase)
                if after_wake is None:
                    await _send_event(
                        websocket,
                        VoiceServerEvent(type="wake_required", message=f"Start with “{wake_phrase}”."),
                    )
                    continue
                text = after_wake
                if not text:
                    await _send_event(websocket, VoiceServerEvent(type="wake_detected", message="I’m listening."))
                    continue
            await _stream_reply(websocket, text, tts_enabled, conversation)
    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected")


async def _stream_reply(
    websocket: WebSocket,
    text: str,
    tts_enabled: bool,
    conversation: list[ChatMessage],
) -> None:
    """Dispatch a command or stream an LLM response."""
    try:
        conversation.append(ChatMessage(role="user", content=text))
        command_response = await command_router.route(text)
        if command_response is not None:
            conversation.append(ChatMessage(role="assistant", content=command_response))
            await _send_event(
                websocket,
                VoiceServerEvent(type="assistant_start", command_handled=True),
            )
            await _send_event(websocket, VoiceServerEvent(type="token", text=command_response))
            await _send_event(websocket, VoiceServerEvent(type="assistant_done", command_handled=True))
            if tts_enabled:
                await speak(command_response)
            return
        provider = registry.create()
        await _send_event(
            websocket,
            VoiceServerEvent(type="assistant_start", command_handled=False),
        )
        full_response = ""
        async for chunk in provider.stream(conversation[-20:]):
            full_response += chunk
            await _send_event(websocket, VoiceServerEvent(type="token", text=chunk))
        conversation.append(ChatMessage(role="assistant", content=full_response))
        await _send_event(
            websocket,
            VoiceServerEvent(type="assistant_done", command_handled=False),
        )
        if tts_enabled:
            await speak(full_response)
    except (ProviderError, ValueError, RuntimeError) as exc:
        logger.warning("WebSocket request could not be completed: %s", exc)
        await _send_event(websocket, VoiceServerEvent(type="error", message=str(exc)))
