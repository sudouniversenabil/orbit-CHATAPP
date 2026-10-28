"""Local notes and simple in-process reminders/timers."""

import asyncio
from datetime import datetime
import logging
from pathlib import Path
import re
import shutil

from backend.app.commands.base import CommandPlugin
from backend.app.core.schemas import CommandInfo

NOTE_DIR = Path.home() / ".local" / "share" / "desktop-assistant"
NOTE_FILE = NOTE_DIR / "notes.md"
logger = logging.getLogger(__name__)
TIMER_PATTERN = re.compile(
    r"^(?:set (?:a )?(?:timer|reminder)|remind me) (?:for |in )(?P<amount>\d+(?:\.\d+)?) "
    r"(?P<unit>seconds?|minutes?|hours?)(?: to (?P<message>.+))?$",
    re.IGNORECASE,
)


async def _notify_later(seconds: float, message: str) -> None:
    """Wait for a timer and send a desktop notification when available."""
    await asyncio.sleep(seconds)
    if shutil.which("notify-send"):
        process = await asyncio.create_subprocess_exec(
            "notify-send",
            "Desktop Assistant reminder",
            message,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, error = await process.communicate()
        if process.returncode:
            logger.error("notify-send failed: %s", error.decode(errors="replace").strip())


class ProductivityCommand(CommandPlugin):
    """Save notes and schedule short-lived local reminders."""

    info = CommandInfo(
        id="productivity",
        name="Notes and reminders",
        description="Save a note or schedule a reminder/timer for this running session.",
        examples=["create a note buy tea", "set a timer for 5 minutes", "remind me in 10 minutes to stretch"],
    )

    def matches(self, text: str) -> bool:
        """Recognize note creation and supported timer formats."""
        normalized = text.strip().casefold()
        return normalized.startswith(("create a note", "make a note")) or bool(TIMER_PATTERN.fullmatch(text.strip()))

    async def execute(self, text: str) -> str:
        """Save note text or schedule a bounded timer."""
        note_match = re.fullmatch(r"(?:create|make) a note(?:\s*[:,-]?\s+(.+))?", text.strip(), re.IGNORECASE)
        if note_match:
            content = (note_match.group(1) or "").strip()
            if not content:
                return "What would you like the note to say? Try “create a note buy tea”."
            NOTE_DIR.mkdir(parents=True, exist_ok=True)
            with NOTE_FILE.open("a", encoding="utf-8") as note_file:
                note_file.write(f"- {datetime.now().astimezone().isoformat(timespec='minutes')}: {content}\n")
            return f"Saved your note to {NOTE_FILE}."

        timer = TIMER_PATTERN.fullmatch(text.strip())
        if not timer:
            return "Please specify a timer duration, such as “set a timer for 5 minutes”."
        amount = float(timer.group("amount"))
        unit = timer.group("unit").casefold()
        multiplier = 1 if unit.startswith("second") else 60 if unit.startswith("minute") else 3600
        seconds = amount * multiplier
        if not 1 <= seconds <= 7 * 24 * 3600:
            return "Timer duration must be between one second and seven days."
        if not shutil.which("notify-send"):
            return "Timers need `notify-send`; install the Arch package `libnotify` first."
        message = timer.group("message") or "Your timer is finished."
        asyncio.create_task(_notify_later(seconds, message))
        return f"Reminder set for {amount:g} {unit}."


def get_commands() -> list[CommandPlugin]:
    """Return this module's command plugins."""
    return [ProductivityCommand()]
