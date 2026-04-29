from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bug_chaser.discord.mothman import MothmanCommandHandler


def test_fairy_command_is_registered() -> None:
    handler = _handler()

    command = handler.group.get_command("fairy")

    assert command is not None


def _handler() -> MothmanCommandHandler:
    return MothmanCommandHandler(
        registry=SimpleNamespace(all=()),
        sync_service=SimpleNamespace(),
        store=SimpleNamespace(),
    )
