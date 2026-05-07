import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from flannel.config.forum import ForumConfig
from flannel.core.models import ThreadSnapshot
from flannel.rules.engine import RuleEngine
from flannel.sync.service import SyncService


def _config(sheets_enabled: bool = False) -> ForumConfig:
    return ForumConfig.model_validate(
        {
            "forum": {
                "key": "test-forum",
                "guild_id": 1,
                "channel_id": 2,
                "sheets": {"enabled": sheets_enabled, "configured": sheets_enabled},
            },
            "state_order": [],
        }
    )


def _snapshot() -> ThreadSnapshot:
    return ThreadSnapshot(
        thread_id=100,
        forum_channel_id=2,
        title="Bug",
        body="Body",
        author_id=1,
        author_name="user",
        created_at=datetime.now(timezone.utc),
        status="open",
    )


class FakeCollector:
    def __init__(self, threads: list[Any]) -> None:
        self._threads = threads

    async def collect(self, channel_id: int) -> list[Any]:
        return self._threads


class FakeSnapshotBuilder:
    def __init__(self, snapshot: ThreadSnapshot) -> None:
        self._snapshot = snapshot

    async def build(self, thread: Any) -> ThreadSnapshot:
        return self._snapshot


class FakeStore:
    def __init__(self) -> None:
        self.upserted_threads: list[tuple[str, ThreadSnapshot]] = []
        self.sync_runs: list[dict[str, Any]] = []

    def upsert_thread(self, forum_key: str, snapshot: ThreadSnapshot) -> None:
        self.upserted_threads.append((forum_key, snapshot))

    def record_sync_run(
        self,
        forum_key: str,
        fetched: int,
        stored: int,
        exported: int,
        errors: list[str],
    ) -> None:
        self.sync_runs.append(
            {
                "forum_key": forum_key,
                "fetched": fetched,
                "stored": stored,
                "exported": exported,
                "errors": errors,
            }
        )


def test_sync_forum_dry_run_does_not_store() -> None:
    fake_thread = SimpleNamespace(id=100)
    service = SyncService(
        collector=FakeCollector([fake_thread]),
        snapshot_builder=FakeSnapshotBuilder(_snapshot()),
        rule_engine=RuleEngine(),
        store=FakeStore(),
    )

    result = asyncio.run(service.sync_forum(_config(), dry_run=True))

    assert result.fetched == 1
    assert result.stored == 0
    assert service._store.upserted_threads == []
    assert service._store.sync_runs == []


def test_sync_forum_stores_when_not_dry_run() -> None:
    fake_thread = SimpleNamespace(id=100)
    store = FakeStore()
    service = SyncService(
        collector=FakeCollector([fake_thread]),
        snapshot_builder=FakeSnapshotBuilder(_snapshot()),
        rule_engine=RuleEngine(),
        store=store,
    )

    result = asyncio.run(service.sync_forum(_config(), dry_run=False))

    assert result.fetched == 1
    assert result.stored == 1
    assert len(store.upserted_threads) == 1
    assert len(store.sync_runs) == 1


def test_sync_forum_collects_errors() -> None:
    fake_thread = SimpleNamespace(id=100)

    class FailingBuilder:
        async def build(self, thread: Any) -> ThreadSnapshot:
            raise ValueError("build failed")

    store = FakeStore()
    service = SyncService(
        collector=FakeCollector([fake_thread]),
        snapshot_builder=FailingBuilder(),
        rule_engine=RuleEngine(),
        store=store,
    )

    result = asyncio.run(service.sync_forum(_config(), dry_run=False))

    assert result.fetched == 1
    assert result.stored == 0
    assert len(result.errors) == 1
    assert "build failed" in result.errors[0]
