from bug_chaser.core.settings import AppSettings


def test_empty_google_service_account_file_is_none() -> None:
    settings = AppSettings(
        BUG_CHASER_DISCORD_TOKEN="token",
        BUG_CHASER_GOOGLE_SERVICE_ACCOUNT_FILE="",
        _env_file=None,
    )

    assert settings.google_service_account_file is None


def test_empty_bot_messages_file_is_none() -> None:
    settings = AppSettings(
        BUG_CHASER_DISCORD_TOKEN="token",
        BUG_CHASER_BOT_MESSAGES_FILE="",
        _env_file=None,
    )

    assert settings.bot_messages_file is None
