"""
Shadow Lady is always watching YOU!

Manager for applying forum management actions.

#TODO if bot comment is already sent, don't send it again.
"""
import asyncio
import logging

import discord

from flannel.config.forum import ActionRule, ForumConfig

logger = logging.getLogger(__name__)


class ShadowLadyThreadManager:
    """Applies forum management actions when automation is enabled."""

    def __init__(
        self,
        archive_delay_seconds: float = 1.0,
    ) -> None:
        self._archive_delay_seconds = archive_delay_seconds
        self._comment_locks: dict[tuple[int, str], asyncio.Lock] = {}

    async def apply_action(
        self,
        config: ForumConfig,
        thread: discord.Thread,
        action_name: str,
    ) -> None:
        """Apply the action to the thread.

        Args:
            config (ForumConfig): The forum configuration.
            thread (discord.Thread): The thread to apply the action to.
            action_name (str): The name of the action to apply.
        """
        automation = config.forum.automation
        if not automation.enabled:
            return

        action = config.actions.get(action_name)
        if action is None:
            return

        edit_kwargs: dict[str, object] = {}
        if automation.auto_tag:
            applied_tags = self._desired_tags(
                thread,
                action,
            )
            if applied_tags is not None:
                edit_kwargs["applied_tags"] = applied_tags
        final_edit_kwargs: dict[str, object] = {}
        if automation.auto_archive and action.archive:
            final_edit_kwargs["archived"] = True
        if automation.auto_lock and action.lock:
            final_edit_kwargs["locked"] = True
        if action.reopen:
            final_edit_kwargs["archived"] = False
            final_edit_kwargs["locked"] = False

        sent_comment = False
        if automation.auto_comment and action.add_comment:
            sent_comment = await self._send_comment(
                thread,
                action.add_comment,
            )
        if edit_kwargs:
            await thread.edit(**edit_kwargs)
        if sent_comment and final_edit_kwargs.get("archived") is True:
            await asyncio.sleep(self._archive_delay_seconds)
        if final_edit_kwargs:
            await thread.edit(**final_edit_kwargs)

    async def _send_comment(
        self,
        thread: discord.Thread,
        content: str,
    ) -> bool:
        """Send a comment to the thread.

        Args:
            thread (discord.Thread): The thread to send the comment to.
            content (str): The content of the comment to send.

        Returns:
            True if the comment was sent, False otherwise.
        """
        lock_key = (thread.id, content)
        lock = self._comment_locks.setdefault(lock_key, asyncio.Lock())
        async with lock:
            if await self._has_existing_bot_comment(thread, content):
                return False
            await thread.send(content)
            return True

    async def _has_existing_bot_comment(
        self,
        thread: discord.Thread,
        content: str,
    ) -> bool:
        """Check if the thread has an existing bot comment.

        Args:
            thread (discord.Thread): The thread to check.
            content (str): The content of the bot comment to check.

        Returns:
            True if the thread has an existing bot comment, False otherwise.
        """
        try:
            async for message in thread.history(limit=1):
                if message.content == content and getattr(
                    message.author,
                    "bot",
                    False,
                ):
                    return True
        except discord.HTTPException:
            logger.warning(
                "Could not inspect thread history before sending automation "
                "comment. thread_id=%s",
                thread.id,
            )
        return False

    def _desired_tags(
        self,
        thread: discord.Thread,
        action: ActionRule,
    ) -> list[discord.ForumTag] | None:
        """Get the desired tags for the thread.

        Args:
            thread (discord.Thread): The thread to get the desired tags for.
            action (ActionRule): The action to apply.

        Returns:
            A list of desired tags, or None if the thread has no parent forum.
        """
        parent = thread.parent
        if not isinstance(parent, discord.ForumChannel):
            return None

        current = {tag.name: tag for tag in thread.applied_tags}
        available = {tag.name: tag for tag in parent.available_tags}
        for tag_name in action.remove_tags:
            current.pop(tag_name, None)
        for tag_name in action.add_tags:
            # Forum-specific YAML may mention tags that have not been created yet.
            tag = available.get(tag_name)
            if tag is not None:
                current[tag.name] = tag
            else:
                logger.warning(
                    "Configured action tag is not available in forum. thread_id=%s tag=%s",
                    thread.id,
                    tag_name,
                )

        desired = list(current.values())
        if {tag.name for tag in desired} == {tag.name for tag in thread.applied_tags}:
            return None
        return desired
