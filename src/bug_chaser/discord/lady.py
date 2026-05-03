"""
Shadow Lady is always watching YOU!

Discord Gateway for bug-chaser.
"""
from __future__ import annotations

import logging

import discord
from discord import app_commands

from bug_chaser.config.forum import ForumConfig
from bug_chaser.config.registry import ForumRegistry
from bug_chaser.core.models import ThreadSnapshot, ThreadStatus
from bug_chaser.core.settings import AppSettings
from bug_chaser.discord.bird import ShadowBirdCollector
from bug_chaser.discord.forum_validation import assert_configured_tags_exist_on_forums
from bug_chaser.discord.gloop import GloopSnapshotBuilder
from bug_chaser.discord.guard import RobotGuardThreadManager
from bug_chaser.discord.mothman import MothmanCommandHandler
from bug_chaser.rules.engine import RuleEngine
from bug_chaser.sheets.exporter import SheetExporter
from bug_chaser.sheets.google import GoogleClients
from bug_chaser.sheets.provisioner import SpreadsheetProvisioner
from bug_chaser.storage.sqlite_store import SQLiteStore
from bug_chaser.sync.scheduler import BugChaserScheduler
from bug_chaser.sync.service import SyncService

logger = logging.getLogger(__name__)


def action_name_for_status(status: str) -> str | None:
    if status in (ThreadStatus.OPEN.value, ThreadStatus.UNKNOWN.value):
        return None
    return f"when_{status}"


def action_name_for_added_tags(
    config: ForumConfig,
    before_tags: tuple[str, ...],
    after_tags: tuple[str, ...],
) -> str | None:
    added_tags = set(after_tags) - set(before_tags)
    if not added_tags:
        return None

    for state_name in config.state_order:
        rule = config.states.get(state_name)
        if rule is not None and any(tag in added_tags for tag in rule.tags):
            return f"when_{state_name}"
    return None


def should_apply_status_action(before_status: str, after_status: str) -> bool:
    return before_status != after_status and action_name_for_status(after_status) is not None


class ShadowLadyGateway(discord.Client):
    def __init__(
        self,
        settings: AppSettings,
        configs: list[ForumConfig],
        store: SQLiteStore,
    ) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.reactions = True
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)
        self._settings = settings
        self._registry = ForumRegistry(configs)
        self._store = store
        self._rule_engine = RuleEngine()
        self._snapshot_builder = GloopSnapshotBuilder()
        self._thread_manager = RobotGuardThreadManager()
        self._google_clients = self._build_google_clients(settings)
        self._scheduler: BugChaserScheduler | None = None
        self._startup_initialized = False

    async def setup_hook(self) -> None:
        collector = ShadowBirdCollector(self)
        sheet_exporter = (
            SheetExporter(self._google_clients)
            if self._google_clients is not None
            else None
        )
        provisioner = (
            SpreadsheetProvisioner(self._google_clients)
            if self._google_clients is not None
            else None
        )
        sync_service = SyncService(
            collector=collector,
            snapshot_builder=self._snapshot_builder,
            rule_engine=self._rule_engine,
            store=self._store,
            sheet_exporter=sheet_exporter,
        )
        handler = MothmanCommandHandler(
            registry=self._registry,
            sync_service=sync_service,
            store=self._store,
            provisioner=provisioner,
        )
        self.tree.add_command(handler.group)
        self._scheduler = BugChaserScheduler(self._registry, sync_service)

        if self._settings.command_guild_id:
            guild = discord.Object(id=self._settings.command_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self) -> None:
        if not self._startup_initialized:
            try:
                await assert_configured_tags_exist_on_forums(self, self._registry.all)
            except ValueError:
                logger.exception("Forum configuration validation failed; stopping client.")
                await self.close()
                return
            self._startup_initialized = True
            if self._scheduler is not None:
                self._scheduler.start()

        logger.info("bug-chaser logged in as %s", self.user)

    async def on_thread_update(self, before: discord.Thread, after: discord.Thread) -> None:
        await self._maybe_apply_automation(before, after)

    async def _maybe_apply_automation(
        self,
        before: discord.Thread,
        after: discord.Thread,
    ) -> None:
        if after.parent_id is None:
            return
        try:
            config = self._registry.get_by_channel_id(after.parent_id)
        except KeyError:
            return

        before_snapshot = self._build_thread_update_snapshot(before)
        after_snapshot = self._build_thread_update_snapshot(after)
        action_name = action_name_for_added_tags(
            config,
            before_snapshot.tags,
            after_snapshot.tags,
        )
        if action_name is None:
            before_status = self._rule_engine.evaluate(config, before_snapshot)
            after_status = self._rule_engine.evaluate(config, after_snapshot)
            if not should_apply_status_action(before_status, after_status):
                return
            action_name = action_name_for_status(after_status)

        if action_name:
            await self._thread_manager.apply_action(config, after, action_name)

    def _build_thread_update_snapshot(self, thread: discord.Thread) -> ThreadSnapshot:
        parent = thread.parent
        available_tags = (
            tuple(tag.name for tag in parent.available_tags)
            if isinstance(parent, discord.ForumChannel)
            else None
        )
        return ThreadSnapshot(
            thread_id=thread.id,
            forum_channel_id=thread.parent_id or 0,
            title=thread.name,
            body="",
            author_id=None,
            author_name=None,
            created_at=thread.created_at,
            tags=tuple(tag.name for tag in thread.applied_tags),
            available_tags=available_tags,
            reply_count=max((thread.message_count or 0) - 1, 0),
            archived=thread.archived,
            locked=thread.locked,
        )

    def _build_google_clients(self, settings: AppSettings) -> GoogleClients | None:
        if settings.google_service_account_file is None:
            return None
        return GoogleClients(settings.google_service_account_file)
