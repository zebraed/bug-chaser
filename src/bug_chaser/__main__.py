from __future__ import annotations

import logging

from bug_chaser.config.bot_messages import load_bot_messages
from bug_chaser.config.loader import ForumConfigLoader
from bug_chaser.core.settings import AppSettings
from bug_chaser.discord.lady import ShadowLadyGateway
from bug_chaser.storage.sqlite_store import SQLiteStore


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

    bot_messages = load_bot_messages(settings)
    client = ShadowLadyGateway(
        settings=settings,
        configs=configs,
        store=store,
        bot_messages=bot_messages,
    )
    client.run(settings.discord_token)


if __name__ == "__main__":
    main()
