from datetime import datetime, timezone

import pytest

from bug_chaser.core.identifiers import validate_state_id, validate_thread_status_value
from bug_chaser.core.models import ThreadSnapshot


def test_validate_state_id_rejects_unsafe_strings() -> None:
    for bad in ("", "9x", "Hello", "a-b", "open\n", "x" * 100):
        with pytest.raises(ValueError):
            validate_state_id(bad)


def test_validate_thread_status_value_accepts_builtin_and_state_ids() -> None:
    assert validate_thread_status_value("unknown") == "unknown"
    assert validate_thread_status_value("open") == "open"
    assert validate_thread_status_value("in_progress") == "in_progress"


def test_thread_snapshot_validates_status() -> None:
    with pytest.raises(ValueError):
        ThreadSnapshot(
            thread_id=1,
            forum_channel_id=2,
            title="t",
            body="b",
            author_id=None,
            author_name=None,
            created_at=None,
            status="UPPER",
        )


def test_thread_snapshot_accepts_resolved_state() -> None:
    s = ThreadSnapshot(
        thread_id=1,
        forum_channel_id=2,
        title="t",
        body="b",
        author_id=None,
        author_name=None,
        created_at=datetime.now(timezone.utc),
        status="my_custom_state",
    )
    assert s.status == "my_custom_state"
