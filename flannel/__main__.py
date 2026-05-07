"""
Main entry point for flannel.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler

from flannel.config.bot_messages import load_bot_messages
from flannel.config.forum import ForumConfig
from flannel.config.loader import ForumConfigLoader
from flannel.core.settings import AppSettings
from flannel.discord.guard import GuardRobotGateway
from flannel.storage.sqlite_store import SQLiteStore


def _restore_runtime_flags(store: SQLiteStore, config: ForumConfig) -> None:
    """Override YAML values with flags persisted via commands.

    Args:
        store (SQLiteStore): The SQLite store.
        config (ForumConfig): The forum configuration.
    """
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


def _configure_logging(settings: AppSettings) -> None:
    """Set up root logger (stderr, and optionally a rotating log file).

    Args:
        settings (AppSettings): Application settings.
    """
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if settings.log_file is not None:
        settings.log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            settings.log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(logging.Formatter(fmt))
        handlers.append(file_handler)
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=handlers,
        force=True,
    )


def main() -> None:
    """Main entry point func for flannel."""
    settings = AppSettings()
    _configure_logging(settings)
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
