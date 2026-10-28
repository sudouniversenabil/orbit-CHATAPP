"""Offline and optional cloud speech-to-text adapters."""

import asyncio
import tempfile
import threading
from pathlib import Path

import httpx

from backend.app.core.config import get_settings

_whisper_model: object | None = None
_whisper_model_lock = threading.Lock()


async def transcribe(audio: bytes, mime_type: str = "audio/webm") -> str:
    """Transcribe browser audio using the configured offline or cloud engine."""
    settings = get_settings()
    if settings.stt_provider == "cloud":
        if not settings.openai_api_key:
            raise RuntimeError("Cloud transcription requires OPENAI_API_KEY.")
        return await _cloud_transcribe(audio, mime_type, settings.openai_api_key, settings.openai_transcription_model)
    if settings.stt_provider != "offline":
        raise RuntimeError(f"Unsupported STT_PROVIDER: {settings.stt_provider}")
    return await asyncio.to_thread(
        _offline_transcribe, audio, mime_type, settings.stt_model, settings.stt_language
    )


def _offline_transcribe(audio: bytes, mime_type: str, model_name: str, language: str) -> str:
    """Run faster-whisper in a worker thread."""
    global _whisper_model
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("Offline transcription needs faster-whisper; install requirements.txt.") from exc
    if _whisper_model is None:
        with _whisper_model_lock:
            if _whisper_model is None:
                _whisper_model = WhisperModel(model_name, device="cpu", compute_type="int8")
    suffix = ".wav" if "wav" in mime_type.lower() else ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix) as audio_file:
        audio_file.write(audio)
        audio_file.flush()
        segments, _ = _whisper_model.transcribe(
            audio_file.name,
            language=language or None,
            beam_size=3,
            vad_filter=True,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()


async def _cloud_transcribe(audio: bytes, mime_type: str, api_key: str, model: str) -> str:
    """Send audio to the OpenAI-compatible transcription endpoint."""
    extension = "wav" if "wav" in mime_type else "webm"
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                data={"model": model},
                files={"file": (f"voice.{extension}", audio, mime_type)},
            )
            response.raise_for_status()
            return response.json()["text"]
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Cloud transcription failed: {exc}") from exc
    except (KeyError, TypeError) as exc:
        raise RuntimeError("Cloud transcription returned an invalid response.") from exc
