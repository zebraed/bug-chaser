import pytest

from bug_chaser.config.forum import ForumConfig
from bug_chaser.core.identifiers import DISCORD_FORUM_MAX_AVAILABLE_TAGS


def _minimal_forum() -> dict:
    return {
        "forum": {
            "key": "example",
            "guild_id": 1,
            "channel_id": 2,
        },
    }


def test_state_order_must_match_states() -> None:
    with pytest.raises(ValueError, match="state_order"):
        ForumConfig.model_validate(
            {
                **_minimal_forum(),
                "states": {"a": {"tags": ["X"]}, "b": {"tags": ["Y"]}},
                "state_order": ["a"],
            }
        )


def test_invalid_state_id_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid state id"):
        ForumConfig.model_validate(
            {
                **_minimal_forum(),
                "states": {"Bad-Key": {"tags": ["X"]}},
                "state_order": ["Bad-Key"],
            }
        )


def test_tag_name_length_rejected() -> None:
    long_tag = "x" * (21)
    with pytest.raises(ValueError, match="tag name"):
        ForumConfig.model_validate(
            {
                **_minimal_forum(),
                "states": {"s": {"tags": [long_tag]}},
                "state_order": ["s"],
            }
        )


def test_too_many_states_rejected() -> None:
    states = {f"s{i}": {"tags": ["T"]} for i in range(DISCORD_FORUM_MAX_AVAILABLE_TAGS + 1)}
    state_order = [f"s{i}" for i in range(DISCORD_FORUM_MAX_AVAILABLE_TAGS + 1)]
    with pytest.raises(ValueError, match="20"):
        ForumConfig.model_validate(
            {
                **_minimal_forum(),
                "states": states,
                "state_order": state_order,
            }
        )
