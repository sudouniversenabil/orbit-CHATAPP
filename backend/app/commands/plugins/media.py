"""Volume, brightness, and media-player commands."""

import re

from backend.app.commands.base import CommandPlugin
from backend.app.commands.plugins.app_control import run_program
from backend.app.core.schemas import CommandInfo


class MediaCommand(CommandPlugin):
    """Control media players and common desktop audio/display levels."""

    info = CommandInfo(
        id="media",
        name="Media and device controls",
        description="Adjust volume and brightness or control the active media player.",
        examples=["volume up", "volume down", "mute", "brightness up", "play music", "pause music", "next music"],
    )
    patterns = (
        r"(?:volume|turn the volume) (?:up|higher|\+)",
        r"(?:volume|turn the volume) (?:down|lower|-)",
        r"(?:mute|mute volume|unmute|toggle mute)",
        r"volume mute",
        r"(?:brightness|screen brightness) (?:up|higher|\+)",
        r"(?:brightness|screen brightness) (?:down|lower|-)",
        r"(?:play|pause|next|previous)(?: music)?",
    )

    def matches(self, text: str) -> bool:
        """Recognize only supported media and device actions."""
        normalized = text.strip().casefold().rstrip(" .!?")
        return any(re.fullmatch(pattern, normalized) for pattern in self.patterns)

    async def execute(self, text: str) -> str:
        """Execute a fixed control action with explicit program arguments."""
        command = text.strip().casefold().rstrip(" .!?")
        if command in {"volume up", "turn the volume up", "volume higher", "volume +"}:
            return await self._run("pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%", success="Volume increased.")
        if command in {"volume down", "turn the volume down", "volume lower", "volume -"}:
            return await self._run("pactl", "set-sink-volume", "@DEFAULT_SINK@", "-5%", success="Volume decreased.")
        if command in {"mute", "mute volume", "volume mute", "toggle mute"}:
            return await self._run("pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle", success="Toggled mute.")
        if command == "unmute":
            return await self._run("pactl", "set-sink-mute", "@DEFAULT_SINK@", "0", success="Unmuted.")
        if command in {"brightness up", "screen brightness up", "brightness higher", "brightness +"}:
            return await self._run("brightnessctl", "set", "+5%", success="Brightness increased.")
        if command in {"brightness down", "screen brightness down", "brightness lower", "brightness -"}:
            return await self._run("brightnessctl", "set", "5%-", success="Brightness decreased.")
        action = command.removesuffix(" music")
        if action in {"play", "pause", "next", "previous"}:
            return await self._run("playerctl", action, success=f"Sent {action} to the active media player.")
        return "That media control is not supported."

    @staticmethod
    async def _run(*args: str, success: str) -> str:
        """Run an allowlisted control utility and report missing utilities/errors."""
        code, error = await run_program(*args)
        if code == 0:
            return success
        if code == 127:
            return error
        return f"Command failed: {error or 'the desktop control utility returned an error.'}"


def get_commands() -> list[CommandPlugin]:
    """Return this module's command plugins."""
    return [MediaCommand()]
