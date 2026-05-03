import logging
from datetime import datetime, timezone

from bug_chaser.config.forum import ForumConfig
from bug_chaser.core.models import ThreadSnapshot, ThreadStatus
from bug_chaser.rules.engine import RuleEngine


def test_rule_engine_prefers_tags() -> None:
    config = ForumConfig.model_validate(
        {
            "forum": {
                "key": "example",
                "guild_id": 1,
                "channel_id": 2,
            },
            "states": {
                "duplicate": {"tags": ["重複"]},
                "in_progress": {"tags": ["対応中（Wiki転記不要）"]},
            },
            "state_order": ["duplicate", "in_progress"],
        }
    )
    snapshot = ThreadSnapshot(
        thread_id=10,
        forum_channel_id=2,
        title="Bug",
        body="Body",
        author_id=3,
        author_name="tester",
        created_at=datetime.now(timezone.utc),
        tags=("対応中（Wiki転記不要）",),
    )

    assert RuleEngine().evaluate(config, snapshot) == "in_progress"


def test_rule_engine_detects_duplicate() -> None:
    config = ForumConfig.model_validate(
        {
            "forum": {
                "key": "example",
                "guild_id": 1,
                "channel_id": 2,
            },
            "states": {
                "duplicate": {"tags": ["重複"]},
                "in_progress": {"tags": ["対応中（Wiki転記不要）"]},
            },
            "state_order": ["duplicate", "in_progress"],
        }
    )
    snapshot = ThreadSnapshot(
        thread_id=10,
        forum_channel_id=2,
        title="Bug",
        body="Body",
        author_id=3,
        author_name="tester",
        created_at=datetime.now(timezone.utc),
        tags=("重複", "対応中（Wiki転記不要）"),
    )

    assert RuleEngine().evaluate(config, snapshot) == "duplicate"


def test_rule_engine_open_when_no_tags_match() -> None:
    config = ForumConfig.model_validate(
        {
            "forum": {
                "key": "example",
                "guild_id": 1,
                "channel_id": 2,
            },
            "states": {
                "duplicate": {"tags": ["重複"]},
                "in_progress": {"tags": ["対応中（Wiki転記不要）"]},
                "exported": {"tags": ["Wiki転記済み"]},
                "closed": {"tags": ["解決済み"]},
            },
            "state_order": ["duplicate", "in_progress", "exported", "closed"],
        }
    )
    snapshot = ThreadSnapshot(
        thread_id=10,
        forum_channel_id=2,
        title="Bug",
        body="Body",
        author_id=3,
        author_name="tester",
        created_at=datetime.now(timezone.utc),
        tags=(),
    )

    assert RuleEngine().evaluate(config, snapshot) == ThreadStatus.OPEN.value


def test_rule_engine_warns_when_no_state_matches(caplog) -> None:
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
    snapshot = ThreadSnapshot(
        thread_id=10,
        forum_channel_id=2,
        title="Bug",
        body="Body",
        author_id=3,
        author_name="tester",
        created_at=datetime.now(timezone.utc),
        tags=("Unknown Tag",),
    )

    with caplog.at_level(logging.WARNING, logger="bug_chaser.rules.engine"):
        assert RuleEngine().evaluate(config, snapshot) == ThreadStatus.OPEN.value

    assert "No configured state matched thread tags" in caplog.text
