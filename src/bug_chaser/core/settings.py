from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    discord_token: str = Field(alias="BUG_CHASER_DISCORD_TOKEN")
    config_dir: Path = Field(default=Path("config/forums"), alias="BUG_CHASER_CONFIG_DIR")
    database_path: Path = Field(default=Path("data/bug_chaser.sqlite3"), alias="BUG_CHASER_DB_PATH")
    google_service_account_file: Path | None = Field(
        default=None,
        alias="BUG_CHASER_GOOGLE_SERVICE_ACCOUNT_FILE",
    )
    command_guild_id: int | None = Field(default=None, alias="BUG_CHASER_COMMAND_GUILD_ID")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
