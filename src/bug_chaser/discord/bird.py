from __future__ import annotations

import discord


class ShadowBirdCollector:
    """Collects active and archived forum threads."""

    def __init__(self, client: discord.Client) -> None:
        self._client = client

    async def collect(self, channel_id: int) -> list[discord.Thread]:
        channel = self._client.get_channel(channel_id)
        if channel is None:
            channel = await self._client.fetch_channel(channel_id)
        if not isinstance(channel, discord.ForumChannel):
            msg = f"Channel {channel_id} is not a forum channel."
            raise TypeError(msg)

        threads: dict[int, discord.Thread] = {thread.id: thread for thread in channel.threads}
        async for thread in channel.archived_threads(limit=None):
            threads[thread.id] = thread
        return sorted(
            threads.values(),
            key=lambda thread: thread.created_at or discord.utils.utcnow(),
        )
