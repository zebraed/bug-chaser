from flannel.config.forum import ForumConfig
from flannel.discord.forum_validation import list_missing_config_tags


def test_list_missing_config_tags_empty_when_all_present() -> None:
    config = ForumConfig.model_validate(
        {
            "forum": {
                "key": "example",
                "guild_id": 1,
                "channel_id": 2,
            },
            "states": {
                "closed": {"tags": ["解決済み"]},
            },
            "state_order": ["closed"],
        }
    )
    assert not list_missing_config_tags(
        config,
        frozenset({"解決済み", "その他"}),
    )


def test_list_missing_config_tags_reports_unknown_tag() -> None:
    config = ForumConfig.model_validate(
        {
            "forum": {
                "key": "example",
                "guild_id": 1,
                "channel_id": 2,
            },
            "states": {
                "closed": {"tags": ["存在しない"]},
            },
            "state_order": ["closed"],
        }
    )
    assert list_missing_config_tags(config, frozenset({"解決済み"})) == [
        ("closed", "存在しない"),
    ]
