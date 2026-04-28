from __future__ import annotations

from bug_chaser.config.forum import ForumConfig


class ForumRegistry:
    def __init__(self, configs: list[ForumConfig]) -> None:
        self._by_key = {config.forum.key: config for config in configs}
        self._by_channel_id = {config.forum.channel_id: config for config in configs}

    @property
    def all(self) -> list[ForumConfig]:
        return list(self._by_key.values())

    def get_by_key(self, key: str) -> ForumConfig:
        config = self._by_key.get(key)
        if config is None:
            msg = f"Unknown forum key: {key}"
            raise KeyError(msg)
        return config

    def get_by_channel_id(self, channel_id: int) -> ForumConfig:
        config = self._by_channel_id.get(channel_id)
        if config is None:
            msg = f"Forum channel is not configured: {channel_id}"
            raise KeyError(msg)
        return config
