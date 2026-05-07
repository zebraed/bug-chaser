from pathlib import Path

import pytest
import yaml

from flannel.config.bot_messages import (
    BotMessages,
    format_bot_message,
    load_bot_messages,
)
from flannel.core.settings import AppSettings


def test_format_bot_message_replaces_placeholders() -> None:
    assert (
        format_bot_message("a={a} b={b}", a=1, b=2)
        == "a=1 b=2"
    )


def test_format_bot_message_ignores_invalid_template() -> None:
    assert format_bot_message("{missing}", a=1) == "{missing}"


def test_load_bot_messages_default() -> None:
    settings = AppSettings(
        FLANNEL_DISCORD_TOKEN="t",
        _env_file=None,
    )
    m = load_bot_messages(settings)
    assert m.commands.run_empty == "No forums configured."


def test_load_bot_messages_from_config_dir(tmp_path: Path) -> None:
    forums = tmp_path / "forums"
    forums.mkdir()
    path = tmp_path / "bot_messages.yaml"
    path.write_text(
        yaml.dump({"commands": {"fairy": "custom"}}),
        encoding="utf-8",
    )
    settings = AppSettings(
        FLANNEL_DISCORD_TOKEN="t",
        FLANNEL_CONFIG_DIR=forums,
        _env_file=None,
    )
    m = load_bot_messages(settings)
    assert m.commands.fairy == "custom"
    assert m.commands.run_empty == "No forums configured."


def test_load_bot_messages_explicit_path(tmp_path: Path) -> None:
    p = tmp_path / "m.yaml"
    p.write_text(
        yaml.dump({"commands": {"fairy": "x"}}),
        encoding="utf-8",
    )
    settings = AppSettings(
        FLANNEL_DISCORD_TOKEN="t",
        FLANNEL_BOT_MESSAGES_FILE=p,
        _env_file=None,
    )
    assert load_bot_messages(settings).commands.fairy == "x"


def test_load_bot_messages_explicit_path_missing() -> None:
    settings = AppSettings(
        FLANNEL_DISCORD_TOKEN="t",
        FLANNEL_BOT_MESSAGES_FILE=Path("nonexistent_bot_messages.yaml"),
        _env_file=None,
    )
    with pytest.raises(FileNotFoundError):
        load_bot_messages(settings)


def test_bot_messages_model_merges_defaults() -> None:
    m = BotMessages.model_validate({"commands": {"fairy": "z"}})
    assert m.commands.fairy == "z"
    assert m.commands.run_empty == "No forums configured."
    assert not m.guild_join.enabled
    assert m.guild_join.message == ""
