import logging

from bug_chaser.config.forum import ForumConfig
from bug_chaser.core.models import ThreadSnapshot, ThreadStatus

logger = logging.getLogger(__name__)


class RuleEngine:
    """Evaluates forum-specific tag rules."""

    def evaluate(self, config: ForumConfig, snapshot: ThreadSnapshot) -> str:
        """Evaluate the thread snapshot and return the state id.

        Args:
            config (ForumConfig): The forum configuration.
            snapshot (ThreadSnapshot): The thread snapshot.

        Returns:
            The state id.
        """
        tag_set = set(snapshot.tags)

        if not config.state_order:
            return ThreadStatus.OPEN.value

        for state_id in config.state_order:
            if self._matches_tags(config, state_id, tag_set):
                return state_id

        logger.warning(
            "No configured state matched thread tags; treating as open. "
            "forum_key=%s forum_channel_id=%s thread_id=%s tags=%s",
            config.forum.key,
            snapshot.forum_channel_id,
            snapshot.thread_id,
            ", ".join(snapshot.tags),
        )
        return ThreadStatus.OPEN.value

    def _matches_tags(self, config: ForumConfig, state_name: str, tag_set: set[str]) -> bool:
        """Check if the state matches the thread tags.

        Args:
            config (ForumConfig): The forum configuration.
            state_name (str): The name of the state to check.
            tag_set (set[str]): The set of tags to check.
        """
        rule = config.states.get(state_name)
        if rule is None:
            return False
        return any(tag in tag_set for tag in rule.tags)
