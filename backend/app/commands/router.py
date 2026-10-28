"""Auto-discovery and dispatch for command plugins."""

import importlib
import pkgutil

from backend.app.commands.base import CommandPlugin
from backend.app.core.schemas import CommandInfo


def discover_commands() -> list[CommandPlugin]:
    """Import command modules and collect plugins declared by `get_commands`."""
    plugins: list[CommandPlugin] = []
    package = importlib.import_module("backend.app.commands.plugins")
    for module_info in pkgutil.iter_modules(package.__path__, f"{package.__name__}."):
        module = importlib.import_module(module_info.name)
        factory = getattr(module, "get_commands", None)
        if factory is not None:
            plugins.extend(factory())
    return plugins


class CommandRouter:
    """Route recognized system commands before invoking an LLM."""

    def __init__(self, plugins: list[CommandPlugin] | None = None) -> None:
        self.plugins = plugins if plugins is not None else discover_commands()

    def list_commands(self) -> list[CommandInfo]:
        """Return public command descriptions."""
        return [plugin.info for plugin in self.plugins]

    async def route(self, text: str) -> str | None:
        """Execute the first matching plugin, or return None for LLM fallback."""
        normalized = text.strip()
        for plugin in self.plugins:
            if plugin.matches(normalized):
                return await plugin.execute(normalized)
        return None


command_router = CommandRouter()
