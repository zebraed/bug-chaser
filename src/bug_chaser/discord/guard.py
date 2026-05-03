"""
あ！野生のガードロボが飛び出してきた！

Manager for applying forum management actions.
"""
from __future__ import annotations

import asyncio
import logging

import discord

from bug_chaser.config.forum import ActionRule, ForumConfig

logger = logging.getLogger(__name__)


class RobotGuardThreadManager:
    """Applies forum management actions when automation is enabled."""

    def __init__(self, archive_delay_seconds: float = 1.0) -> None:
        self._archive_delay_seconds = archive_delay_seconds

    async def apply_action(
        self,
        config: ForumConfig,
        thread: discord.Thread,
        action_name: str,
    ) -> None:
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
            await thread.send(action.add_comment)
            sent_comment = True
        if edit_kwargs:
            await thread.edit(**edit_kwargs)
        if sent_comment and final_edit_kwargs.get("archived") is True:
            await asyncio.sleep(self._archive_delay_seconds)
        if final_edit_kwargs:
            await thread.edit(**final_edit_kwargs)

    def _desired_tags(
        self,
        thread: discord.Thread,
        action: ActionRule,
    ) -> list[discord.ForumTag] | None:
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
