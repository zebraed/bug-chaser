"""
Forum configuration models.
"""
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing_extensions import Self

from bug_chaser.core.identifiers import (
    DISCORD_FORUM_MAX_AVAILABLE_TAGS,
    DISCORD_FORUM_TAG_NAME_MAX_LENGTH,
    validate_state_id,
)


class SyncConfig(BaseModel):
    interval_minutes: int = Field(default=10, ge=1)
    dry_run_default: bool = True


class SheetsConfig(BaseModel):
    configured: bool = False
    enabled: bool = False
    auto_create: bool = True
    spreadsheet_id: str | None = None
    owner_email: str | None = None
    editor_emails: list[str] = Field(default_factory=list)
    master_sheet_name: str = "Master"
    progress_sheet_name: str = "Progress"

    @model_validator(mode="after")
    def validate_editor_when_configured(self) -> Self:
        if self.configured and not self.editor_emails:
            msg = "At least one editor email is required when sheets.configured is true."
            raise ValueError(msg)
        return self


class AutomationConfig(BaseModel):
    enabled: bool = False
    auto_comment: bool = False
    auto_tag: bool = False
    auto_archive: bool = False
    auto_lock: bool = False


class ForumSection(BaseModel):
    key: str
    guild_id: int
    channel_id: int
    sync: SyncConfig = Field(default_factory=SyncConfig)
    sheets: SheetsConfig = Field(default_factory=SheetsConfig)
    automation: AutomationConfig = Field(default_factory=AutomationConfig)


class StateRule(BaseModel):
    tags: list[str] = Field(default_factory=list)
    reactions: list[str] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def tag_names_match_discord_limits(cls, value: list[str]) -> list[str]:
        for tag in value:
            if not tag or len(tag) > DISCORD_FORUM_TAG_NAME_MAX_LENGTH:
                msg = (
                    f"Each tag name must be 1..{DISCORD_FORUM_TAG_NAME_MAX_LENGTH} "
                    f"characters (Discord forum tag name); got {tag!r}"
                )
                raise ValueError(msg)
        return value


class ActionRule(BaseModel):
    add_tags: list[str] = Field(default_factory=list)
    remove_tags: list[str] = Field(default_factory=list)
    add_comment: str | None = None
    archive: bool = False
    lock: bool = False
    reopen: bool = False


class ForumConfig(BaseModel):
    forum: ForumSection
    state_order: list[str] = Field(default_factory=list)
    states: dict[str, StateRule] = Field(default_factory=dict)
    actions: dict[str, ActionRule] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_states_and_order(self) -> Self:
        if len(self.states) > DISCORD_FORUM_MAX_AVAILABLE_TAGS:
            msg = (
                f"At most {DISCORD_FORUM_MAX_AVAILABLE_TAGS} state entries are allowed "
                "(same upper bound as Discord forum `available_tags` per channel)."
            )
            raise ValueError(msg)
        for name in self.states:
            validate_state_id(name)
        state_keys = set(self.states)
        order_set = set(self.state_order)
        if state_keys != order_set:
            msg = (
                "state_order must list exactly the keys under states once each "
                f"(states={sorted(state_keys)} vs state_order={list(self.state_order)!r})."
            )
            raise ValueError(msg)
        if len(self.state_order) != len(order_set):
            msg = "state_order must not contain duplicate entries."
            raise ValueError(msg)
        return self


class LoadedForumConfig(BaseModel):
    path: Path
    config: ForumConfig
