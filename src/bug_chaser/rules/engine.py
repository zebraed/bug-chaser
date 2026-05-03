from __future__ import annotations

import logging

from bug_chaser.config.forum import ForumConfig
from bug_chaser.core.models import ThreadSnapshot, ThreadStatus

logger = logging.getLogger(__name__)


class RuleEngine:
    """Evaluates forum-specific tag rules."""

    def evaluate(self, config: ForumConfig, snapshot: ThreadSnapshot) -> ThreadStatus:
        tag_set = set(snapshot.tags)
        self._log_missing_configured_tags(config, snapshot)

        if self._matches_tags(config, "duplicate", tag_set):
            return ThreadStatus.DUPLICATE
        if self._matches_tags(config, "exported", tag_set):
            return ThreadStatus.EXPORTED
        if self._matches_tags(config, "closed", tag_set):
            return ThreadStatus.CLOSED
        if self._matches_tags(config, "in_progress", tag_set):
            return ThreadStatus.IN_PROGRESS
        if self._matches_tags(config, "open", tag_set):
            return ThreadStatus.OPEN
        return ThreadStatus.OPEN

    def _matches_tags(self, config: ForumConfig, state_name: str, tag_set: set[str]) -> bool:
        rule = config.states.get(state_name)
        if rule is None:
            return False
        return any(tag in tag_set for tag in rule.tags)

    def _log_missing_configured_tags(self, config: ForumConfig, snapshot: ThreadSnapshot) -> None:
        if snapshot.available_tags is None:
            return

        available = set(snapshot.available_tags)
        for state_name, rule in config.states.items():
            missing = [tag for tag in rule.tags if tag not in available]
            if missing:
                logger.warning(
                    "Configured tags are not available in forum. forum_key=%s "
                    "forum_channel_id=%s state=%s missing_tags=%s",
                    config.forum.key,
                    snapshot.forum_channel_id,
                    state_name,
                    ", ".join(missing),
                )
