"""Time and system-status commands."""

from datetime import datetime
import asyncio
import re

import psutil

from backend.app.commands.base import CommandPlugin
from backend.app.core.schemas import CommandInfo


class SystemInfoCommand(CommandPlugin):
    """Report current time and basic host resource usage."""

    info = CommandInfo(
        id="system_info",
        name="Time and system status",
        description="Read the local time, CPU, memory, and battery status.",
        examples=["what time is it", "system status"],
    )

    def matches(self, text: str) -> bool:
        """Recognize time and system status questions."""
        normalized = text.strip().casefold().rstrip(" .!?")
        return bool(re.fullmatch(r"(?:what time is it|what's the time|current time)", normalized)) or (
            normalized in {"system status", "system information", "how is my system"}
        )

    async def execute(self, text: str) -> str:
        """Return the requested information."""
        if "time" in text.casefold():
            return datetime.now().astimezone().strftime("It is %A, %I:%M %p %Z.")
        memory = psutil.virtual_memory()
        battery = psutil.sensors_battery()
        battery_text = "Battery: unavailable."
        if battery is not None:
            plugged = "charging" if battery.power_plugged else "on battery"
            battery_text = f"Battery: {battery.percent:.0f}% ({plugged})."
        cpu_percent = await asyncio.to_thread(psutil.cpu_percent, interval=0.15)
        return (
            f"CPU: {cpu_percent:.0f}% used. "
            f"RAM: {memory.percent:.0f}% used ({memory.used // (1024**2)} / {memory.total // (1024**2)} MiB). "
            f"{battery_text}"
        )


def get_commands() -> list[CommandPlugin]:
    """Return this module's command plugins."""
    return [SystemInfoCommand()]
