"""Tests for safe command routing and the plugin set."""

import pytest

from backend.app.commands.base import CommandPlugin
from backend.app.commands.plugins.app_control import AppControlCommand
from backend.app.commands.router import CommandRouter
from backend.app.core.schemas import CommandInfo


class EchoCommand(CommandPlugin):
    """Small command stub used by router tests."""

    info = CommandInfo(id="echo", name="Echo", description="Test plugin.", examples=["echo"])

    def matches(self, text: str) -> bool:
        return text.startswith("echo ")

    async def execute(self, text: str) -> str:
        return text[5:]


@pytest.mark.asyncio
async def test_router_dispatches_matching_command() -> None:
    router = CommandRouter([EchoCommand()])
    assert await router.route("echo hello") == "hello"


@pytest.mark.asyncio
async def test_router_returns_none_for_unknown_command() -> None:
    router = CommandRouter([EchoCommand()])
    assert await router.route("tell me a joke") is None


def test_discovery_exposes_command_skills() -> None:
    router = CommandRouter()
    ids = {item.id for item in router.list_commands()}
    assert {"app_control", "media", "system_info", "productivity"} <= ids


def test_app_control_recognizes_search_but_not_arbitrary_execution() -> None:
    command = AppControlCommand()
    assert command.matches("search for lo-fi music on YouTube")
    assert command.matches("open https://example.com")
    assert not command.matches("run rm -rf /")
