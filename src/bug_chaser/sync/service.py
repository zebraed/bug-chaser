from dataclasses import replace

import discord

from bug_chaser.config.forum import ForumConfig
from bug_chaser.core.models import SyncResult
from bug_chaser.discord.bird import ShadowBirdCollector
from bug_chaser.discord.gloop import GloopSnapshotBuilder
from bug_chaser.rules.engine import RuleEngine
from bug_chaser.sheets.exporter import SheetExporter
from bug_chaser.storage.sqlite_store import SQLiteStore


class SyncService:
    def __init__(
        self,
        collector: ShadowBirdCollector,
        snapshot_builder: GloopSnapshotBuilder,
        rule_engine: RuleEngine,
        store: SQLiteStore,
        sheet_exporter: SheetExporter | None = None,
    ) -> None:
        self._collector = collector
        self._snapshot_builder = snapshot_builder
        self._rule_engine = rule_engine
        self._store = store
        self._sheet_exporter = sheet_exporter

    async def sync_forum(self, config: ForumConfig, *, dry_run: bool = False) -> SyncResult:
        forum = config.forum
        errors: list[str] = []
        exported = 0
        stored = 0

        threads = await self._collector.collect(forum.channel_id)
        for thread in threads:
            try:
                raw_snapshot = await self._snapshot_builder.build(thread)
                status = self._rule_engine.evaluate(config, raw_snapshot)
                snapshot = replace(raw_snapshot, status=status)

                if not dry_run:
                    self._store.upsert_thread(forum.key, snapshot)
                    stored += 1

                if (
                    not dry_run
                    and forum.sheets.enabled
                    and self._sheet_exporter is not None
                ):
                    self._sheet_exporter.upsert_master_row(config, snapshot)
                    exported += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{thread.id}: {exc}")

        if not dry_run:
            self._store.record_sync_run(
                forum_key=forum.key,
                fetched=len(threads),
                stored=stored,
                exported=exported,
                errors=errors,
            )

        return SyncResult(
            forum_key=forum.key,
            fetched=len(threads),
            stored=stored,
            exported=exported,
            errors=tuple(errors),
        )

    async def sync_thread(
        self,
        config: ForumConfig,
        thread: discord.Thread,
        *,
        dry_run: bool = False,
    ) -> SyncResult:
        errors: list[str] = []
        exported = 0
        stored = 0
        try:
            raw_snapshot = await self._snapshot_builder.build(thread)
            status = self._rule_engine.evaluate(config, raw_snapshot)
            snapshot = replace(raw_snapshot, status=status)
            if not dry_run:
                self._store.upsert_thread(config.forum.key, snapshot)
                stored = 1
            if (
                not dry_run
                and config.forum.sheets.enabled
                and self._sheet_exporter is not None
            ):
                self._sheet_exporter.upsert_master_row(config, snapshot)
                exported = 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{thread.id}: {exc}")

        return SyncResult(
            forum_key=config.forum.key,
            fetched=1,
            stored=stored,
            exported=exported,
            errors=tuple(errors),
        )
