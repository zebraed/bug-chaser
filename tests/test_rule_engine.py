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

    assert RuleEngine().evaluate(config, snapshot) == ThreadStatus.IN_PROGRESS


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

    assert RuleEngine().evaluate(config, snapshot) == ThreadStatus.DUPLICATE


def test_rule_engine_ignores_configured_tags_that_are_not_on_thread() -> None:
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

    assert RuleEngine().evaluate(config, snapshot) == ThreadStatus.OPEN


def test_rule_engine_logs_configured_tags_that_are_not_available(caplog) -> None:
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
        available_tags=("対応中（Wiki転記不要）",),
    )

    with caplog.at_level(logging.WARNING, logger="bug_chaser.rules.engine"):
        assert RuleEngine().evaluate(config, snapshot) == ThreadStatus.OPEN

    assert "missing_tags=重複" in caplog.text
