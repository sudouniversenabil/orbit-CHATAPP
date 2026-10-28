"""Whitelisted application and website launch/close commands."""

import asyncio
import re
import shutil
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import psutil

from backend.app.commands.base import CommandPlugin
from backend.app.core.schemas import CommandInfo

APP_ALIASES = {
    "firefox": ("firefox",),
    "terminal": ("xterm", "kitty", "foot", "konsole", "gnome-terminal", "alacritty"),
    "vs code": ("code",),
    "vscode": ("code",),
    "file manager": ("xdg-open",),
}
APP_PROCESSES = {
    "firefox": ("firefox",),
    "terminal": ("xterm", "kitty", "foot", "konsole", "gnome-terminal", "alacritty"),
    "vs code": ("code",),
    "vscode": ("code",),
    "file manager": ("thunar", "dolphin", "nautilus", "pcmanfm"),
}
APP_PATTERN = "|".join(sorted((re.escape(name) for name in APP_ALIASES), key=len, reverse=True))


async def run_program(*args: str) -> tuple[int, str]:
    """Run a fixed executable and argument list without a shell."""
    if not shutil.which(args[0]):
        return 127, f"Required program {args[0]!r} is not installed."
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    return process.returncode or 0, stderr.decode(errors="replace").strip()


async def launch_program(*args: str) -> tuple[int, str]:
    """Start a whitelisted desktop application without waiting for it to exit."""
    if not shutil.which(args[0]):
        return 127, f"Required program {args[0]!r} is not installed."
    try:
        await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        return 1, str(exc)
    return 0, ""


class AppControlCommand(CommandPlugin):
    """Open allowlisted applications/websites or close allowlisted processes."""

    info = CommandInfo(
        id="app_control",
        name="Application and website control",
        description="Open allowlisted desktop apps and websites; close allowlisted apps.",
        examples=[
            "open Firefox",
            "open terminal",
            "open VS Code",
            "open file manager",
            "open example.com",
            "close Firefox",
            "search for lo-fi music on YouTube",
        ],
    )

    def matches(self, text: str) -> bool:
        lowered = text.casefold()
        lowered = lowered.strip().rstrip(" .!?")
        return bool(
            re.fullmatch(rf"(?:please )?open (?:{APP_PATTERN})", lowered)
            or re.fullmatch(r"(?:please )?open (?:https?://)?[^\s]+", lowered)
            or re.fullmatch(rf"(?:please )?close (?:{APP_PATTERN})", lowered)
            or re.fullmatch(r"search for .+ on (?:google|youtube)", lowered)
        )

    async def execute(self, text: str) -> str:
        """Launch or close a fixed, allowlisted target."""
        text = text.strip().rstrip(" .!?")
        match = re.fullmatch(rf"(?:please )?open ({APP_PATTERN})", text.casefold())
        if match:
            app = match.group(1)
            if app == "file manager":
                code, error = await launch_program("xdg-open", str(Path.home()))
                return "Opened the file manager." if code == 0 else f"Could not open the file manager: {error}"
            candidates = APP_ALIASES[app]
            executable = next((candidate for candidate in candidates if shutil.which(candidate)), None)
            if executable is None:
                return f"None of the configured launchers for {app} are installed."
            code, error = await launch_program(executable)
            return f"Opened {app}." if code == 0 else f"Could not open {app}: {error}"

        match = re.fullmatch(rf"(?:please )?close ({APP_PATTERN})", text.casefold())
        if match:
            app = match.group(1)
            running_names = {
                str(process.info["name"]).casefold()
                for process in psutil.process_iter(["name"], ad_value="")
                if process.info["name"]
            }
            executable = next(
                (name for name in APP_PROCESSES[app] if name.casefold() in running_names),
                None,
            )
            if executable is None:
                return f"No running {app} process was found."
            if not shutil.which("pkill"):
                return "The `pkill` utility is not installed."
            code, error = await run_program("pkill", "-x", executable)
            if code == 0:
                return f"Closed {app}."
            if code == 1:
                return f"No running {app} process was found."
            return f"Could not close {app}: {error}"

        match = re.fullmatch(r"search for (.+) on (google|youtube)", text, re.IGNORECASE)
        if match:
            query, engine = match.groups()
            parameter = "q" if engine.casefold() == "google" else "search_query"
            base_url = (
                "https://www.google.com/search"
                if engine.casefold() == "google"
                else "https://www.youtube.com/results"
            )
            url = f"{base_url}?{urlencode({parameter: query.strip()})}"
            code, error = await launch_program("xdg-open", url)
            return f"Searching {engine.title()} for {query.strip()}." if code == 0 else f"Could not start the search: {error}"

        match = re.fullmatch(r"(?:please )?open ((?:https?://)?[^\s]+)", text.strip(), re.IGNORECASE)
        if not match:
            return "I could not identify a safe application or website to open."
        target = match.group(1)
        url = target if "://" in target else f"https://{target}"
        parsed = urlsplit(url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or ("." not in parsed.hostname and parsed.hostname != "localhost")
            or parsed.username
            or parsed.password
        ):
            return "Please provide a valid http(s) website address."
        code, error = await launch_program("xdg-open", url)
        return "Opened the website in your default browser." if code == 0 else f"Could not open the website: {error}"


def get_commands() -> list[CommandPlugin]:
    """Return this module's command plugins."""
    return [AppControlCommand()]
