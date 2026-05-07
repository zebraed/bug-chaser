"""
Registry for forum configurations.
"""
from bug_chaser.config.forum import ForumConfig


class ForumRegistry:
    """Registry for forum configurations."""
    def __init__(self, configs: list[ForumConfig]) -> None:
        """Initialize the forum registry.

        Args:
            configs (list[ForumConfig]): The forum configurations.
        """
        self._by_key = {config.forum.key: config for config in configs}
        self._by_channel_id = {config.forum.channel_id: config for config in configs}

    @property
    def all(self) -> list[ForumConfig]:
        """Get all forum configurations."""
        return list(self._by_key.values())

    def get_by_key(self, key: str) -> ForumConfig:
        """Get a forum configuration by key.

        Args:
            key (str): The key of the forum configuration to get.

        Returns:
            The forum configuration.
        """
        config = self._by_key.get(key)
        if config is None:
            msg = f"Unknown forum key: {key}"
            raise KeyError(msg)
        return config

    def get_by_channel_id(self, channel_id: int) -> ForumConfig:
        """Get a forum configuration by channel id.

        Args:
            channel_id (int): The channel id of the forum configuration to get.

        Returns:
            The forum configuration.
        """
        config = self._by_channel_id.get(channel_id)
        if config is None:
            msg = f"Forum channel is not configured: {channel_id}"
            raise KeyError(msg)
        return config
