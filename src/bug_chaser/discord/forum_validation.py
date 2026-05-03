"""
Startup checks: YAML tag names must exist on the parent forum channel.
"""
from __future__ import annotations

import discord

from bug_chaser.config.forum import ForumConfig


def list_missing_config_tags(
    config: ForumConfig,
    available_tag_names: frozenset[str],
) -> list[tuple[str, str]]:
    """Return ``(state_id, tag_name)`` pairs for tags referenced in YAML but not on the forum."""
    missing: list[tuple[str, str]] = []
    for state_name, rule in config.states.items():
        for tag in rule.tags:
            if tag not in available_tag_names:
                missing.append((state_name, tag))
    return missing


async def assert_configured_tags_exist_on_forums(
    client: discord.Client,
    configs: list[ForumConfig],
) -> None:
    """
    Ensure every tag referenced under ``states`` exists on the forum channel.

    Raises:
        ValueError: If any configured tag name is missing from the channel's
            ``available_tags``, or the channel is missing / not a forum.
    """
    for config in configs:
        await _assert_tags_for_forum(client, config)


async def _assert_tags_for_forum(client: discord.Client, config: ForumConfig) -> None:
    channel = client.get_channel(config.forum.channel_id)
    if channel is None:
        channel = await client.fetch_channel(config.forum.channel_id)

    if not isinstance(channel, discord.ForumChannel):
        msg = (
            f"Forum channel_id is not a GUILD_FORUM channel: "
            f"forum_key={config.forum.key} channel_id={config.forum.channel_id}"
        )
        raise ValueError(msg)

    available = frozenset(tag.name for tag in channel.available_tags)
    missing = list_missing_config_tags(config, available)

    if missing:
        detail = "; ".join(f"{state}:{tag!r}" for state, tag in missing)
        msg = (
            f"Configured tag names are not on the forum channel (fix YAML or Discord): "
            f"forum_key={config.forum.key} channel_id={config.forum.channel_id} "
            f"missing={detail}"
        )
        raise ValueError(msg)
