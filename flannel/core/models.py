"""
Core domain models.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from flannel.core.identifiers import validate_thread_status_value


class ThreadStatus(str, Enum):
    """Built-in status values only; YAML-defined states use the same string storage."""

    UNKNOWN = "unknown"
    OPEN = "open"


class AutomationFeature(str, Enum):
    ALL = "all"
    AUTO_COMMENT = "auto_comment"
    AUTO_TAG = "auto_tag"
    AUTO_ARCHIVE = "auto_archive"
    AUTO_LOCK = "auto_lock"


@dataclass(frozen=True)
class ReactionCount:
    emoji: str
    count: int


@dataclass(frozen=True)
class ThreadSnapshot:
    thread_id: int
    forum_channel_id: int
    title: str
    body: str
    author_id: int | None
    author_name: str | None
    created_at: datetime | None
    tags: tuple[str, ...] = field(default_factory=tuple)
    available_tags: tuple[str, ...] | None = None
    reactions: tuple[ReactionCount, ...] = field(default_factory=tuple)
    reply_count: int = 0
    url: str | None = None
    archived: bool = False
    locked: bool = False
    status: str = ThreadStatus.UNKNOWN.value

    def __post_init__(self) -> None:
        validate_thread_status_value(self.status)

    def reaction_summary(self) -> str:
        return ", ".join(f"{reaction.emoji}:{reaction.count}" for reaction in self.reactions)

    def tag_summary(self) -> str:
        return ", ".join(self.tags)


@dataclass(frozen=True)
class SyncResult:
    forum_key: str
    fetched: int
    stored: int
    exported: int
    errors: tuple[str, ...] = field(default_factory=tuple)
