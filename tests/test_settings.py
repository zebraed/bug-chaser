from flannel.core.settings import AppSettings


def test_empty_google_service_account_file_is_none() -> None:
    settings = AppSettings(
        FLANNEL_DISCORD_TOKEN="token",
        FLANNEL_GOOGLE_SERVICE_ACCOUNT_FILE="",
        _env_file=None,
    )

    assert settings.google_service_account_file is None


def test_empty_bot_messages_file_is_none() -> None:
    settings = AppSettings(
        FLANNEL_DISCORD_TOKEN="token",
        FLANNEL_BOT_MESSAGES_FILE="",
        _env_file=None,
    )

    assert settings.bot_messages_file is None


def test_empty_log_file_is_none() -> None:
    settings = AppSettings(
        FLANNEL_DISCORD_TOKEN="token",
        FLANNEL_LOG_FILE="",
        _env_file=None,
    )

    assert settings.log_file is None
