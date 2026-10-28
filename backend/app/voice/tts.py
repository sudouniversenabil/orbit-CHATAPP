"""Optional offline speech synthesis using pyttsx3/espeak-ng."""

import asyncio

from backend.app.core.config import get_settings


async def speak(text: str) -> None:
    """Speak text through the host's default audio output."""
    if not get_settings().tts_enabled or not text:
        return
    await asyncio.to_thread(_speak_sync, text)


def _speak_sync(text: str) -> None:
    """Run pyttsx3 outside the event loop."""
    try:
        import pyttsx3
    except ImportError as exc:
        raise RuntimeError("Offline speech needs pyttsx3 and espeak-ng.") from exc
    engine = pyttsx3.init()
    voice_name = get_settings().tts_voice
    if voice_name:
        matching = [voice.id for voice in engine.getProperty("voices") if voice_name.lower() in voice.id.lower()]
        if not matching:
            raise RuntimeError(f"No installed TTS voice matches {voice_name!r}.")
        engine.setProperty("voice", matching[0])
    engine.say(text)
    engine.runAndWait()
