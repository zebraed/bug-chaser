import pytest

from bug_chaser.config.forum import ForumConfig
from bug_chaser.config.registry import ForumRegistry


def _config(key: str, channel_id: int) -> ForumConfig:
    return ForumConfig.model_validate(
        {
            "forum": {
                "key": key,
                "guild_id": 1,
                "channel_id": channel_id,
            },
            "state_order": [],
        }
    )


def test_get_by_key_returns_config() -> None:
    config = _config("my-forum", 100)
    registry = ForumRegistry([config])

    assert registry.get_by_key("my-forum") is config


def test_get_by_key_raises_for_unknown() -> None:
    registry = ForumRegistry([])

    with pytest.raises(KeyError, match="Unknown forum key"):
        registry.get_by_key("missing")


def test_get_by_channel_id_returns_config() -> None:
    config = _config("my-forum", 100)
    registry = ForumRegistry([config])

    assert registry.get_by_channel_id(100) is config


def test_get_by_channel_id_raises_for_unknown() -> None:
    registry = ForumRegistry([])

    with pytest.raises(KeyError, match="not configured"):
        registry.get_by_channel_id(999)


def test_all_returns_list_of_configs() -> None:
    c1 = _config("forum-a", 1)
    c2 = _config("forum-b", 2)
    registry = ForumRegistry([c1, c2])

    keys = {c.forum.key for c in registry.all}
    assert keys == {"forum-a", "forum-b"}
