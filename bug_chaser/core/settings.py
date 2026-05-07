"""
Runtime settings for the application.
"""
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Runtime settings for the application."""
    discord_token: str = Field(alias="BUG_CHASER_DISCORD_TOKEN")
    config_dir: Path = Field(
        default=Path("config/forums"),
        alias="BUG_CHASER_CONFIG_DIR",
    )
    database_path: Path = Field(
        default=Path("data/bug_chaser.sqlite3"),
        alias="BUG_CHASER_DB_PATH",
    )
    google_service_account_file: Path | None = Field(
        default=None,
        alias="BUG_CHASER_GOOGLE_SERVICE_ACCOUNT_FILE",
    )
    command_guild_id: int | None = Field(
        default=None,
        alias="BUG_CHASER_COMMAND_GUILD_ID",
    )
    bot_messages_file: Path | None = Field(
        default=None,
        alias="BUG_CHASER_BOT_MESSAGES_FILE",
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("google_service_account_file", mode="before")
    @classmethod
    def empty_google_service_account_file_is_none(
        cls,
        value: object,
    ) -> object:
        """Convert an empty Google service account file to None.

        Args:
            value (object): The value to convert.

        Returns:
            The converted value.
        """
        if value == "":
            return None
        return value

    @field_validator("bot_messages_file", mode="before")
    @classmethod
    def empty_bot_messages_file_is_none(
        cls,
        value: object,
    ) -> object:
        """Convert an empty bot messages file to None.

        Args:
            value (object): The value to convert.

        Returns:
            The converted value.
        """
        if value == "":
            return None
        return value
