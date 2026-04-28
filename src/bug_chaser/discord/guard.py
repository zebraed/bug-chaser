from __future__ import annotations

import logging

import discord

from bug_chaser.config.forum import ActionRule, ForumConfig

logger = logging.getLogger(__name__)


class RobotGuardThreadManager:
    """Applies forum management actions when automation is enabled."""

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

        if automation.auto_tag:
            await self._apply_tags(thread, action)
        if automation.auto_comment and action.add_comment:
            await thread.send(action.add_comment)
        if automation.auto_archive and action.archive:
            await thread.edit(archived=True)
        if automation.auto_lock and action.lock:
            await thread.edit(locked=True)
        if action.reopen:
            await thread.edit(archived=False, locked=False)

    async def _apply_tags(self, thread: discord.Thread, action: ActionRule) -> None:
        parent = thread.parent
        if not isinstance(parent, discord.ForumChannel):
            return

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
        await thread.edit(applied_tags=list(current.values()))
