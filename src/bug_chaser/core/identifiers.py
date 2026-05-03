"""
Validated identifiers for forum state keys (YAML `states` keys).
"""
from __future__ import annotations

import re

# Discord API: forum channel `available_tags` is limited to 20 per channel.
# https://discord.com/developers/docs/resources/channel
DISCORD_FORUM_MAX_AVAILABLE_TAGS = 20

# Forum tag `name` field: 0–20 characters (Discord API).
DISCORD_FORUM_TAG_NAME_MAX_LENGTH = 20

# Safe state ids: start with a letter, then lowercase letters, digits, underscores.
STATE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


_BUILTIN_THREAD_STATUSES = frozenset({"unknown", "open"})


def validate_thread_status_value(value: str) -> str:
    """
    Validate a persisted / computed thread status string.

    Allows built-in ``unknown`` and ``open``, or any valid YAML state id.
    """
    if value in _BUILTIN_THREAD_STATUSES:
        return value
    return validate_state_id(value)


def validate_state_id(name: str) -> str:
    """
    Validate a forum state key (YAML key under `states`).

    Raises:
        ValueError: If the string is not a safe state identifier.
    """
    if not STATE_ID_PATTERN.fullmatch(name):
        msg = (
            "Invalid state id: must match "
            r"^[a-z][a-z0-9_]{0,62}$"
            f"; got {name!r}"
        )
        raise ValueError(msg)
    return name
