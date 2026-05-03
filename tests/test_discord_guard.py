from bug_chaser.config.forum import ForumConfig
from bug_chaser.core.models import ThreadStatus
from bug_chaser.discord.guard import (
    action_name_for_added_tags,
    action_name_for_status,
    should_apply_status_action,
)


def test_status_action_names() -> None:
    assert action_name_for_status("duplicate") == "when_duplicate"
    assert action_name_for_status("in_progress") == "when_in_progress"
    assert action_name_for_status("exported") == "when_exported"
    assert action_name_for_status("closed") == "when_closed"
    assert action_name_for_status("custom_state") == "when_custom_state"
    assert action_name_for_status(ThreadStatus.OPEN.value) is None
    assert action_name_for_status(ThreadStatus.UNKNOWN.value) is None


def test_same_status_does_not_reapply_action() -> None:
    for s in ("open", "closed", "in_progress", "unknown"):
        assert not should_apply_status_action(s, s)


def test_status_transition_applies_action_only_for_actionable_status() -> None:
    assert should_apply_status_action(ThreadStatus.OPEN.value, "closed")
    assert should_apply_status_action(ThreadStatus.OPEN.value, "duplicate")
    assert should_apply_status_action(ThreadStatus.OPEN.value, "in_progress")
    assert not should_apply_status_action("closed", ThreadStatus.OPEN.value)


def test_added_state_tag_selects_action_even_with_conflicting_tag() -> None:
    config = _forum_config()

    action_name = action_name_for_added_tags(
        config,
        before_tags=("解決済み",),
        after_tags=("解決済み", "対応中"),
    )

    assert action_name == "when_in_progress"


def test_no_added_state_tag_does_not_select_action() -> None:
    config = _forum_config()

    action_name = action_name_for_added_tags(
        config,
        before_tags=("解決済み", "対応中"),
        after_tags=("解決済み", "対応中"),
    )

    assert action_name is None


def _forum_config() -> ForumConfig:
    return ForumConfig.model_validate(
        {
            "forum": {
                "key": "example",
                "guild_id": 1,
                "channel_id": 2,
            },
            "states": {
                "duplicate": {"tags": ["重複"]},
                "in_progress": {"tags": ["対応中"]},
                "exported": {"tags": ["Wiki転記済み"]},
                "closed": {"tags": ["解決済み"]},
            },
            "state_order": ["duplicate", "in_progress", "exported", "closed"],
        }
    )
