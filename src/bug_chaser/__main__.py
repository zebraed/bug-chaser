from __future__ import annotations

import logging

from bug_chaser.config.bot_messages import load_bot_messages
from bug_chaser.config.forum import ForumConfig
from bug_chaser.config.loader import ForumConfigLoader
from bug_chaser.core.settings import AppSettings
from bug_chaser.discord.guard import GuardRobotGateway
from bug_chaser.storage.sqlite_store import SQLiteStore


def _restore_runtime_flags(store: SQLiteStore, config: ForumConfig) -> None:
    """Override YAML values with flags persisted via commands."""
    flags = store.get_runtime_flags(config.forum.key)
    if not flags:
        return

    if "sheets_enabled" in flags:
        config.forum.sheets.enabled = flags["sheets_enabled"]
    if "automation_enabled" in flags:
        config.forum.automation.enabled = flags["automation_enabled"]
    if "auto_comment" in flags:
        config.forum.automation.auto_comment = flags["auto_comment"]
    if "auto_tag" in flags:
        config.forum.automation.auto_tag = flags["auto_tag"]
    if "auto_archive" in flags:
        config.forum.automation.auto_archive = flags["auto_archive"]
    if "auto_lock" in flags:
        config.forum.automation.auto_lock = flags["auto_lock"]


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = AppSettings()
    loaded_configs = ForumConfigLoader(settings.config_dir).load_all()
    configs = [loaded.config for loaded in loaded_configs]

    store = SQLiteStore(settings.database_path)
    store.initialize()
    for config in configs:
        store.upsert_forum(config)
        _restore_runtime_flags(store, config)

    bot_messages = load_bot_messages(settings)
    client = GuardRobotGateway(
        settings=settings,
        configs=configs,
        store=store,
        bot_messages=bot_messages,
    )
    client.run(settings.discord_token)


if __name__ == "__main__":
    main()
