"""
Scheduler for flannel.
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from flannel.config.registry import ForumRegistry
from flannel.sync.service import SyncService

logger = logging.getLogger(__name__)


class FlannelScheduler:
    def __init__(self, registry: ForumRegistry, sync_service: SyncService) -> None:
        """Initialize the scheduler.

        Args:
            registry (ForumRegistry): The forum registry.
            sync_service (SyncService): The sync service.
        """
        self._registry = registry
        self._sync_service = sync_service
        self._scheduler = AsyncIOScheduler()

    def start(self) -> None:
        """Start the scheduler.
        """
        for config in self._registry.all:
            self._scheduler.add_job(
                self._run_forum,
                "interval",
                minutes=config.forum.sync.interval_minutes,
                args=[config.forum.key],
                id=f"sync:{config.forum.key}",
                replace_existing=True,
                max_instances=1,
            )
        self._scheduler.start()

    async def _run_forum(self, forum_key: str) -> None:
        """Run the sync for a forum.

        Args:
            forum_key (str): The forum key.
        """
        config = self._registry.get_by_key(forum_key)
        try:
            result = await self._sync_service.sync_forum(
                config,
                dry_run=config.forum.sync.dry_run_default,
            )
            logger.info(
                "Scheduled sync finished for %s: fetched=%s stored=%s exported=%s errors=%s",
                result.forum_key,
                result.fetched,
                result.stored,
                result.exported,
                len(result.errors),
            )
        except Exception:
            logger.exception("Scheduled sync failed for %s", forum_key)
