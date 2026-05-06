"""
User-overridable Discord bot reply strings (optional YAML).

Default path: ``<parent of BUG_CHASER_CONFIG_DIR>/bot_messages.yaml``
(e.g. ``config/bot_messages.yaml`` when forums live under ``config/forums``).

Override with ``BUG_CHASER_BOT_MESSAGES_FILE`` (must exist when set).
"""
import yaml
from pydantic import BaseModel, ConfigDict, Field

from bug_chaser.core.settings import AppSettings


def format_bot_message(template: str, **kwargs: object) -> str:
    """Format ``template`` with ``kwargs``; on failure return the template unchanged."""
    try:
        return template.format(**kwargs)
    except (KeyError, ValueError):
        return template


class CommandStrings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_line: str = (
        "{forum_key}: fetched={fetched}, stored={stored}, exported={exported}, errors={errors}"
    )
    run_empty: str = "No forums configured."
    channel_result: str = (
        "{forum_key}: fetched={fetched}, stored={stored}, exported={exported}, errors={errors}"
    )
    dry_run_line: str = "{forum_key}: fetched={fetched}, errors={errors}"
    thread_no_parent: str = "The target thread has no parent forum."
    thread_result: str = (
        "{forum_key}: stored={stored}, exported={exported}, errors={errors}"
    )
    export_sheets_disabled: str = "{forum_key}: Sheets disabled"
    export_line: str = "{forum_key}: exported={exported}, errors={errors}"
    status_line: str = (
        "{forum_key}: channel={channel_id}, sheets={sheets_enabled}, "
        "automation={automation_enabled}, comment={auto_comment}, "
        "tag={auto_tag}, archive={auto_archive}, lock={auto_lock}"
    )
    fairy: str = "うわぁーーーーーーーーーーーーーーーーーーーー！！！！！！！！！"
    sheets_not_configured: str = "Sheets is not configured in YAML."
    sheets_no_service_account: str = "Google Service Account is not configured."
    sheets_enabled: str = "Sheets sync enabled: {spreadsheet_id}"
    sheets_disabled: str = "Sheets sync disabled."
    automation_enabled: str = "Automation enabled: {feature}"
    automation_disabled: str = "Automation disabled: {feature}"
    thread_closed: str = "Thread closed."
    thread_reopened: str = "Thread reopened."


class GuildJoinStrings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    message: str = ""
    channel_id: int | None = Field(
        default=None,
        description=(
            "If set, send here when it exists in the guild; "
            "otherwise system channel or first writable text channel."
        ),
    )


class BotMessages(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commands: CommandStrings = Field(default_factory=CommandStrings)
    guild_join: GuildJoinStrings = Field(default_factory=GuildJoinStrings)


def load_bot_messages(settings: AppSettings) -> BotMessages:
    if settings.bot_messages_file is not None:
        path = settings.bot_messages_file
        if not path.is_file():
            msg = f"Bot messages file not found: {path}"
            raise FileNotFoundError(msg)
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return BotMessages.model_validate(raw)

    auto_path = settings.config_dir.parent / "bot_messages.yaml"
    if auto_path.is_file():
        raw = yaml.safe_load(auto_path.read_text(encoding="utf-8")) or {}
        return BotMessages.model_validate(raw)

    return BotMessages()
