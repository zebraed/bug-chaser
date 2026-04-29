from __future__ import annotations

import discord
from discord import app_commands

from bug_chaser.config.forum import ForumConfig
from bug_chaser.config.registry import ForumRegistry
from bug_chaser.core.models import AutomationFeature
from bug_chaser.sheets.provisioner import SpreadsheetProvisioner
from bug_chaser.storage.sqlite_store import SQLiteStore
from bug_chaser.sync.service import SyncService


class MothmanCommandHandler:
    def __init__(
        self,
        registry: ForumRegistry,
        sync_service: SyncService,
        store: SQLiteStore,
        provisioner: SpreadsheetProvisioner | None = None,
    ) -> None:
        self._registry = registry
        self._sync_service = sync_service
        self._store = store
        self._provisioner = provisioner
        self.group = app_commands.Group(name="bugchaser", description="bug-chaser management")
        self._register_commands()

    def _register_commands(self) -> None:
        self.group.command(name="run", description="Sync all configured forums.")(self.run)
        self.group.command(name="channel", description="Sync one configured forum channel.")(
            self.channel,
        )
        self.group.command(name="thread", description="Sync one forum thread by id or URL.")(
            self.thread,
        )
        self.group.command(name="dry-run", description="Preview sync without writing changes.")(
            self.dry_run,
        )
        self.group.command(name="status", description="Show configured forum status.")(self.status)
        self.group.command(name="fairy", description="Summon the fairy.")(self.fairy)
        self.group.command(name="export", description="Export configured forums to Sheets.")(
            self.export
        )
        self.group.command(name="close", description="Lock and archive a thread by id or URL.")(
            self.close
        )
        self.group.command(
            name="reopen",
            description="Unlock and unarchive a thread by id or URL.",
        )(
            self.reopen,
        )

        sheets = app_commands.Group(name="sheets", description="Manage optional Sheets sync")
        sheets.command(name="on", description="Enable Sheets sync for a forum.")(self.sheets_on)
        sheets.command(name="off", description="Disable Sheets sync for a forum.")(self.sheets_off)
        self.group.add_command(sheets)

        automation = app_commands.Group(
            name="automation",
            description="Manage Discord-side automation",
        )
        automation.command(name="on", description="Enable automation for a forum.")(
            self.automation_on,
        )
        automation.command(name="off", description="Disable automation for a forum.")(
            self.automation_off,
        )
        self.group.add_command(automation)

    async def run(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        lines: list[str] = []
        for config in self._registry.all:
            result = await self._sync_service.sync_forum(config)
            lines.append(
                f"{result.forum_key}: fetched={result.fetched}, "
                f"stored={result.stored}, exported={result.exported}, errors={len(result.errors)}"
            )
        await interaction.followup.send("\n".join(lines) or "No forums configured.", ephemeral=True)

    async def channel(
        self,
        interaction: discord.Interaction,
        forum_channel: discord.ForumChannel,
    ) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        config = self._registry.get_by_channel_id(forum_channel.id)
        result = await self._sync_service.sync_forum(config)
        await interaction.followup.send(
            f"{result.forum_key}: fetched={result.fetched}, stored={result.stored}, "
            f"exported={result.exported}, errors={len(result.errors)}",
            ephemeral=True,
        )

    async def dry_run(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        lines: list[str] = []
        for config in self._registry.all:
            result = await self._sync_service.sync_forum(config, dry_run=True)
            lines.append(
                f"{result.forum_key}: fetched={result.fetched}, "
                f"errors={len(result.errors)}"
            )
        await interaction.followup.send("\n".join(lines), ephemeral=True)

    async def thread(self, interaction: discord.Interaction, thread_url_or_id: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        thread = await self._fetch_thread(interaction.client, thread_url_or_id)
        if thread.parent_id is None:
            await interaction.followup.send(
                "The target thread has no parent forum.",
                ephemeral=True,
            )
            return
        config = self._registry.get_by_channel_id(thread.parent_id)
        result = await self._sync_service.sync_thread(config, thread)
        await interaction.followup.send(
            f"{result.forum_key}: stored={result.stored}, exported={result.exported}, "
            f"errors={len(result.errors)}",
            ephemeral=True,
        )

    async def export(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        lines: list[str] = []
        for config in self._registry.all:
            if not config.forum.sheets.enabled:
                lines.append(f"{config.forum.key}: Sheets disabled")
                continue
            result = await self._sync_service.sync_forum(config)
            lines.append(
                f"{config.forum.key}: exported={result.exported}, "
                f"errors={len(result.errors)}"
            )
        await interaction.followup.send("\n".join(lines), ephemeral=True)

    async def status(self, interaction: discord.Interaction) -> None:
        lines = [
            f"{config.forum.key}: channel={config.forum.channel_id}, "
            f"sheets={config.forum.sheets.enabled}, "
            f"automation={config.forum.automation.enabled}, "
            f"comment={config.forum.automation.auto_comment}, "
            f"tag={config.forum.automation.auto_tag}, "
            f"archive={config.forum.automation.auto_archive}, "
            f"lock={config.forum.automation.auto_lock}"
            for config in self._registry.all
        ]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    async def fairy(self, interaction: discord.Interaction) -> None:
        _msg = "うわぁーーーーーーーーーーーーーーーーーーーー！！！！！！！！！"
        await interaction.response.send_message(_msg)

    async def sheets_on(
        self,
        interaction: discord.Interaction,
        forum_channel: discord.ForumChannel,
    ) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        config = self._registry.get_by_channel_id(forum_channel.id)
        if not config.forum.sheets.configured:
            await interaction.followup.send("Sheets is not configured in YAML.", ephemeral=True)
            return
        if self._provisioner is None:
            await interaction.followup.send(
                "Google Service Account is not configured.",
                ephemeral=True,
            )
            return
        spreadsheet_id = self._provisioner.ensure_spreadsheet(config)
        config.forum.sheets.spreadsheet_id = spreadsheet_id
        config.forum.sheets.enabled = True
        self._store.set_spreadsheet_id(config.forum.key, spreadsheet_id)
        self._store.set_sheets_enabled(config.forum.key, True)
        await interaction.followup.send(
            f"Sheets sync enabled: {spreadsheet_id}",
            ephemeral=True,
        )

    async def sheets_off(
        self,
        interaction: discord.Interaction,
        forum_channel: discord.ForumChannel,
    ) -> None:
        config = self._registry.get_by_channel_id(forum_channel.id)
        config.forum.sheets.enabled = False
        self._store.set_sheets_enabled(config.forum.key, False)
        await interaction.response.send_message("Sheets sync disabled.", ephemeral=True)

    async def automation_on(
        self,
        interaction: discord.Interaction,
        forum_channel: discord.ForumChannel,
        feature: AutomationFeature = AutomationFeature.ALL,
    ) -> None:
        config = self._registry.get_by_channel_id(forum_channel.id)
        self._set_automation_feature(config, feature, True)
        self._store.set_automation_enabled(config.forum.key, feature, True)
        await interaction.response.send_message(
            f"Automation enabled: {feature.value}",
            ephemeral=True,
        )

    async def automation_off(
        self,
        interaction: discord.Interaction,
        forum_channel: discord.ForumChannel,
        feature: AutomationFeature = AutomationFeature.ALL,
    ) -> None:
        config = self._registry.get_by_channel_id(forum_channel.id)
        self._set_automation_feature(config, feature, False)
        self._store.set_automation_enabled(config.forum.key, feature, False)
        await interaction.response.send_message(
            f"Automation disabled: {feature.value}",
            ephemeral=True,
        )

    async def close(self, interaction: discord.Interaction, thread_url_or_id: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        thread = await self._fetch_thread(interaction.client, thread_url_or_id)
        await thread.edit(archived=True, locked=True)
        await interaction.followup.send("Thread closed.", ephemeral=True)

    async def reopen(self, interaction: discord.Interaction, thread_url_or_id: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        thread = await self._fetch_thread(interaction.client, thread_url_or_id)
        await thread.edit(archived=False, locked=False)
        await interaction.followup.send("Thread reopened.", ephemeral=True)

    async def _fetch_thread(
        self,
        client: discord.Client,
        thread_url_or_id: str,
    ) -> discord.Thread:
        thread_id = self._parse_thread_id(thread_url_or_id)
        channel = client.get_channel(thread_id)
        if channel is None:
            channel = await client.fetch_channel(thread_id)
        if not isinstance(channel, discord.Thread):
            msg = f"Target is not a thread: {thread_url_or_id}"
            raise TypeError(msg)
        return channel

    def _parse_thread_id(self, thread_url_or_id: str) -> int:
        normalized = thread_url_or_id.rstrip("/")
        last_part = normalized.rsplit("/", maxsplit=1)[-1]
        return int(last_part)

    def _set_automation_feature(
        self,
        config: ForumConfig,
        feature: AutomationFeature,
        enabled: bool,
    ) -> None:
        automation = config.forum.automation
        if feature == AutomationFeature.ALL:
            automation.enabled = enabled
            automation.auto_comment = enabled
            automation.auto_tag = enabled
            automation.auto_archive = enabled
            automation.auto_lock = enabled
            return

        automation.enabled = enabled or automation.enabled
        setattr(automation, feature.value, enabled)
        if not (
            automation.auto_comment
            or automation.auto_tag
            or automation.auto_archive
            or automation.auto_lock
        ):
            automation.enabled = False
