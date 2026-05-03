from datetime import datetime, timezone
from pathlib import Path

from bug_chaser.config.forum import ForumConfig
from bug_chaser.core.models import AutomationFeature, ThreadSnapshot
from bug_chaser.storage.sqlite_store import SQLiteStore


def _minimal_config() -> ForumConfig:
    return ForumConfig.model_validate(
        {
            "forum": {
                "key": "test-forum",
                "guild_id": 1,
                "channel_id": 2,
            },
            "state_order": [],
        }
    )


def _sample_snapshot() -> ThreadSnapshot:
    return ThreadSnapshot(
        thread_id=100,
        forum_channel_id=2,
        title="Bug report",
        body="Details here",
        author_id=10,
        author_name="tester",
        created_at=datetime.now(timezone.utc),
        tags=("Tag1", "Tag2"),
        status="open",
    )


def test_initialize_creates_tables(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "db.sqlite3")
    store.initialize()

    assert (tmp_path / "db.sqlite3").exists()


def test_upsert_forum_and_thread(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "db.sqlite3")
    store.initialize()

    config = _minimal_config()
    store.upsert_forum(config)

    snapshot = _sample_snapshot()
    store.upsert_thread("test-forum", snapshot)

    store.upsert_thread("test-forum", snapshot)


def test_get_runtime_flags_returns_empty_when_not_set(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "db.sqlite3")
    store.initialize()

    flags = store.get_runtime_flags("nonexistent")

    assert flags == {}


def test_get_runtime_flags_returns_persisted_values(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "db.sqlite3")
    store.initialize()

    config = _minimal_config()
    store.upsert_forum(config)
    store.set_sheets_enabled("test-forum", True)
    store.set_automation_enabled("test-forum", AutomationFeature.AUTO_COMMENT, True)

    flags = store.get_runtime_flags("test-forum")

    assert flags["sheets_enabled"] is True
    assert flags["auto_comment"] is True


def test_record_sync_run(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "db.sqlite3")
    store.initialize()

    store.record_sync_run(
        forum_key="test-forum",
        fetched=10,
        stored=8,
        exported=5,
        errors=["err1"],
    )
