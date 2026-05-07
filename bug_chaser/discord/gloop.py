"""
Gloop Gloop Gloop

Builder for normalized forum thread snapshots.
"""
from collections.abc import Sequence

import discord

from bug_chaser.core.models import ReactionCount, ThreadSnapshot


class GloopSnapshotBuilder:
    """Builds normalized snapshots from Discord forum threads."""

    async def build(self, thread: discord.Thread) -> ThreadSnapshot:
        starter_message = await self._fetch_starter_message(thread)
        tags = tuple(tag.name for tag in getattr(thread, "applied_tags", []))
        available_tags = self._available_forum_tags(thread)
        reactions = self._reaction_counts(starter_message.reactions if starter_message else [])
        body = starter_message.content if starter_message else ""
        author = starter_message.author if starter_message else None

        return ThreadSnapshot(
            thread_id=thread.id,
            forum_channel_id=thread.parent_id or 0,
            title=thread.name,
            body=body,
            author_id=author.id if author else None,
            author_name=str(author) if author else None,
            created_at=thread.created_at,
            tags=tags,
            available_tags=available_tags,
            reactions=reactions,
            reply_count=max((thread.message_count or 0) - 1, 0),
            url=starter_message.jump_url if starter_message else None,
            archived=thread.archived,
            locked=thread.locked,
        )

    async def _fetch_starter_message(self, thread: discord.Thread) -> discord.Message | None:
        """Fetch the starter message for the thread.

        Args:
            thread (discord.Thread): The thread to fetch the starter message for.

        Returns:
            The starter message for the thread, or None if the starter message is not found.
        """
        try:
            return await thread.fetch_message(thread.id)
        except discord.NotFound:
            return None

    def _available_forum_tags(self, thread: discord.Thread) -> tuple[str, ...] | None:
        """Get the available forum tags for the thread.

        Args:
            thread (discord.Thread): The thread to get the available forum tags for.

        Returns:
            A tuple of available forum tags, or None if the thread has no parent forum.
        """
        parent = thread.parent
        if not isinstance(parent, discord.ForumChannel):
            return None
        return tuple(tag.name for tag in parent.available_tags)

    def _reaction_counts(self, reactions: Sequence[discord.Reaction]) -> tuple[ReactionCount, ...]:
        return tuple(
            ReactionCount(emoji=str(reaction.emoji), count=reaction.count)
            for reaction in reactions
        )
