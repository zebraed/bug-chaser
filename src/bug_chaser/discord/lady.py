from __future__ import annotations

import logging

import discord
from discord import app_commands

from bug_chaser.config.forum import ForumConfig
from bug_chaser.config.registry import ForumRegistry
from bug_chaser.core.models import ThreadStatus
from bug_chaser.core.settings import AppSettings
from bug_chaser.discord.bird import ShadowBirdCollector
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
        self._scheduler.start()

        if self._settings.command_guild_id:
            guild = discord.Object(id=self._settings.command_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self) -> None:
        logger.info("bug-chaser logged in as %s", self.user)

    async def on_thread_update(self, before: discord.Thread, after: discord.Thread) -> None:
        await self._maybe_apply_automation(after)

    async def _maybe_apply_automation(self, thread: discord.Thread) -> None:
        if thread.parent_id is None:
            return
        try:
            config = self._registry.get_by_channel_id(thread.parent_id)
        except KeyError:
            return

        snapshot = await self._snapshot_builder.build(thread)
        status = self._rule_engine.evaluate(config, snapshot)
        action_name = self._action_name_for_status(status)
        if action_name:
            await self._thread_manager.apply_action(config, thread, action_name)

    def _action_name_for_status(self, status: ThreadStatus) -> str | None:
        return {
            ThreadStatus.DUPLICATE: "when_duplicate",
            ThreadStatus.IN_PROGRESS: "when_in_progress",
            ThreadStatus.WIKI_EXPORTED: "when_wiki_exported",
            ThreadStatus.CLOSED: "when_closed",
        }.get(status)

    def _build_google_clients(self, settings: AppSettings) -> GoogleClients | None:
        if settings.google_service_account_file is None:
            return None
        return GoogleClients(settings.google_service_account_file)
