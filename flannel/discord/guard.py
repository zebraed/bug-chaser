"""
あ！野生のガードロボが飛び出してきた！

Discord Gateway for flannel.
"""
import logging

import discord
from discord import app_commands

from flannel.config.bot_messages import BotMessages, GuildJoinStrings
from flannel.config.forum import ForumConfig
from flannel.config.registry import ForumRegistry
from flannel.core.models import ThreadSnapshot, ThreadStatus
from flannel.core.settings import AppSettings
from flannel.discord.bird import ShadowBirdCollector
from flannel.discord.forum_validation import assert_configured_tags_exist_on_forums
from flannel.discord.gloop import GloopSnapshotBuilder
from flannel.discord.lady import ShadowLadyThreadManager
from flannel.discord.mothman import MothmanCommandHandler
from flannel.rules.engine import RuleEngine
from flannel.sheets.exporter import SheetExporter
from flannel.sheets.google import GoogleClients
from flannel.sheets.provisioner import SpreadsheetProvisioner
from flannel.storage.sqlite_store import SQLiteStore
from flannel.sync.scheduler import FlannelScheduler
from flannel.sync.service import SyncService

logger = logging.getLogger(__name__)


def action_name_for_status(status: str) -> str | None:
    """Get the action name for the status.

    Args:
        status (str): The status to get the action name for.

    Returns:
        The action name for the status, or None if the status is not a valid status.
    """
    if status in (ThreadStatus.OPEN.value, ThreadStatus.UNKNOWN.value):
        return None
    return f"when_{status}"


def action_name_for_added_tags(
    config: ForumConfig,
    before_tags: tuple[str, ...],
    after_tags: tuple[str, ...],
) -> str | None:
    """Get the action name for the added tags.

    Args:
        config (ForumConfig): The forum configuration.
        before_tags (tuple[str, ...]): The tags before the update.
        after_tags (tuple[str, ...]): The tags after the update.

    Returns:
        The action name for the added tags, or None if there are no added tags.
    """
    added_tags = set(after_tags) - set(before_tags)
    if not added_tags:
        return None

    for state_name in config.state_order:
        rule = config.states.get(state_name)
        if rule is not None and any(tag in added_tags for tag in rule.tags):
            return f"when_{state_name}"
    return None


def should_apply_status_action(before_status: str, after_status: str) -> bool:
    """Check if the status action should be applied.

    Args:
        before_status (str): The status before the update.
        after_status (str): The status after the update.

    Returns:
        True if the status action should be applied, False otherwise.
    """
    return before_status != after_status and action_name_for_status(after_status) is not None


class GuardRobotGateway(discord.Client):
    def __init__(
        self,
        settings: AppSettings,
        configs: list[ForumConfig],
        store: SQLiteStore,
        bot_messages: BotMessages | None = None,
    ) -> None:
        """Initialize the Discord Gateway.

        Args:
            settings (AppSettings): The application settings.
            configs (list[ForumConfig]): The forum configurations.
            store (SQLiteStore): The SQLite store.
            bot_messages (BotMessages | None): The bot messages.
        """
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
        self._thread_manager = ShadowLadyThreadManager()
        self._google_clients = self._build_google_clients(settings)
        self._scheduler: FlannelScheduler | None = None
        self._startup_initialized = False
        self._bot_messages = bot_messages or BotMessages()

    async def setup_hook(self) -> None:
        """Setup the Discord Gateway.
        """
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
            messages=self._bot_messages,
        )
        self.tree.add_command(handler.group)
        self._scheduler = FlannelScheduler(self._registry, sync_service)

        if self._settings.command_guild_id:
            guild = discord.Object(id=self._settings.command_guild_id)
            self.tree.copy_global_to(guild=guild)
            try:
                await self.tree.sync(guild=guild)
            except discord.Forbidden:
                logger.exception(
                    "Guild command sync skipped (missing access): guild_id=%s",
                    self._settings.command_guild_id,
                )
        else:
            await self.tree.sync()

    async def on_ready(self) -> None:
        """Handle the Discord Gateway ready event.
        """
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
            await self._send_pending_guild_join_messages()

        logger.info("flannel logged in as %s", self.user)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Handle the Guild Join event.

        Args:
            guild (discord.Guild): The guild that the bot joined.
        """
        await self._sync_joined_command_guild(guild)
        await self._maybe_send_guild_join_message(guild)

    async def _sync_joined_command_guild(self, guild: discord.Guild) -> None:
        """Sync guild commands after the bot gains access to the configured guild."""
        if self._settings.command_guild_id != guild.id:
            return

        try:
            await self.tree.sync(guild=discord.Object(id=guild.id))
        except discord.Forbidden:
            logger.exception(
                "Guild command sync skipped (missing access): guild_id=%s",
                guild.id,
            )

    async def _send_pending_guild_join_messages(self) -> None:
        """Send guild join messages missed while the client was offline."""
        for guild in self.guilds:
            if not self._store.has_sent_guild_join_message(guild.id):
                await self._maybe_send_guild_join_message(guild)

    def _reconcile_guild_join_pending(self, guild_id: int, gj: GuildJoinStrings) -> None:
        """Drop stale explicit-channel retry rows (config changed)."""
        if gj.channel_id is None:
            self._store.clear_guild_join_pending(guild_id)
            return
        pending = self._store.get_guild_join_pending_channel_id(guild_id)
        if pending is not None and pending != gj.channel_id:
            self._store.clear_guild_join_pending(guild_id)

    async def _send_guild_join_explicit_channel(
        self,
        guild: discord.Guild,
        gj: GuildJoinStrings,
        target_id: int,
    ) -> None:
        """Send only to ``channel_id``; record pending retry if blocked by permissions."""
        me = guild.me
        if me is None:
            logger.warning(
                "Guild join message skipped (no member): guild_id=%s",
                guild.id,
            )
            return

        raw = guild.get_channel(target_id)
        if raw is None or not isinstance(raw, discord.abc.Messageable):
            logger.warning(
                "Guild join explicit channel missing: guild_id=%s channel_id=%s",
                guild.id,
                target_id,
            )
            self._store.set_guild_join_pending(guild.id, target_id)
            return

        if hasattr(raw, "permissions_for"):
            perms = raw.permissions_for(me)
            if not perms.view_channel or not perms.send_messages:
                logger.warning(
                    "Guild join explicit channel lacks permission: "
                    "guild_id=%s channel_id=%s",
                    guild.id,
                    target_id,
                )
                self._store.set_guild_join_pending(guild.id, target_id)
                return

        try:
            await raw.send(gj.message)
        except discord.Forbidden:
            logger.exception(
                "Guild join Forbidden on explicit channel: guild_id=%s channel_id=%s",
                guild.id,
                target_id,
            )
            self._store.set_guild_join_pending(guild.id, target_id)
            return
        except discord.HTTPException:
            logger.exception(
                "Failed guild join on explicit channel: guild_id=%s channel_id=%s",
                guild.id,
                target_id,
            )
            return

        self._store.mark_guild_join_message_sent(guild.id)

    async def _send_guild_join_fallback_channels(
        self,
        guild: discord.Guild,
        gj: GuildJoinStrings,
    ) -> None:
        """System channel, then first writable text channel (no ``channel_id``)."""
        channel: discord.abc.Messageable | None = None
        sys_ch = guild.system_channel
        if isinstance(sys_ch, discord.abc.Messageable):
            channel = sys_ch

        if channel is None:
            me = guild.me
            for text_ch in guild.text_channels:
                if me is not None and text_ch.permissions_for(me).send_messages:
                    channel = text_ch
                    break

        if channel is None:
            logger.warning(
                "Guild join message skipped (no channel): guild_id=%s",
                guild.id,
            )
            return

        me = guild.me
        if (
            me is not None
            and hasattr(channel, "permissions_for")
            and not channel.permissions_for(me).send_messages
        ):
            logger.warning(
                "Guild join message skipped (no permission): guild_id=%s channel_id=%s",
                guild.id,
                getattr(channel, "id", None),
            )
            return

        try:
            await channel.send(gj.message)
        except discord.HTTPException:
            logger.exception(
                "Failed to send guild join message: guild_id=%s",
                guild.id,
            )
            return

        self._store.mark_guild_join_message_sent(guild.id)

    async def _maybe_send_guild_join_message(self, guild: discord.Guild) -> None:
        """Send the configured guild join message once per guild."""
        gj = self._bot_messages.guild_join
        if not gj.enabled or not gj.message.strip():
            self._store.clear_guild_join_pending(guild.id)
            return

        if self._store.has_sent_guild_join_message(guild.id):
            return

        self._reconcile_guild_join_pending(guild.id, gj)

        if gj.channel_id is not None:
            await self._send_guild_join_explicit_channel(guild, gj, gj.channel_id)
        else:
            await self._send_guild_join_fallback_channels(guild, gj)

    async def on_guild_channel_update(
        self,
        before: discord.abc.GuildChannel,
        after: discord.abc.GuildChannel,
    ) -> None:
        """Retry guild join after channel permission / visibility may have changed."""
        gj = self._bot_messages.guild_join
        if (
            not gj.enabled
            or not gj.message.strip()
            or gj.channel_id is None
        ):
            return
        guild = after.guild
        pending = self._store.get_guild_join_pending_channel_id(guild.id)
        if pending is None or pending != after.id or after.id != gj.channel_id:
            return
        if self._store.has_sent_guild_join_message(guild.id):
            return
        await self._maybe_send_guild_join_message(guild)

    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        """Retry when the bot member object changes (e.g. roles)."""
        if self.user is None or after.id != self.user.id:
            return
        gj = self._bot_messages.guild_join
        if (
            not gj.enabled
            or not gj.message.strip()
            or gj.channel_id is None
        ):
            return
        if self._store.get_guild_join_pending_channel_id(after.guild.id) is None:
            return
        if self._store.has_sent_guild_join_message(after.guild.id):
            return
        await self._maybe_send_guild_join_message(after.guild)

    async def on_guild_role_update(self, before: discord.Role, after: discord.Role) -> None:
        """Retry when a role permission mask changes (may affect channel access)."""
        gj = self._bot_messages.guild_join
        if (
            not gj.enabled
            or not gj.message.strip()
            or gj.channel_id is None
        ):
            return
        guild = after.guild
        if self._store.get_guild_join_pending_channel_id(guild.id) is None:
            return
        if self._store.has_sent_guild_join_message(guild.id):
            return
        await self._maybe_send_guild_join_message(guild)

    async def on_thread_update(self, before: discord.Thread, after: discord.Thread) -> None:
        """Handle the Thread Update event.

        Args:
            before (discord.Thread): The thread before the update.
            after (discord.Thread): The thread after the update.
        """
        await self._maybe_apply_automation(before, after)

    async def _maybe_apply_automation(
        self,
        before: discord.Thread,
        after: discord.Thread,
    ) -> None:
        """Maybe apply automation to the thread.

        Args:
            before (discord.Thread): The thread before the update.
            after (discord.Thread): The thread after the update.
        """
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
        """Build a thread update snapshot.

        Args:
            thread (discord.Thread): The thread to build the snapshot for.

        Returns:
            A thread update snapshot.
        """
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
        """Build Google clients.

        Args:
            settings (AppSettings): The application settings.

        Returns:
            Google clients, or None if the Google service account file is not set.
        """
        if settings.google_service_account_file is None:
            return None
        return GoogleClients(settings.google_service_account_file)
