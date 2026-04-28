from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    def validate_editor_when_configured(self) -> SheetsConfig:
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


class ActionRule(BaseModel):
    add_tags: list[str] = Field(default_factory=list)
    remove_tags: list[str] = Field(default_factory=list)
    add_comment: str | None = None
    archive: bool = False
    lock: bool = False
    reopen: bool = False


class ForumConfig(BaseModel):
    forum: ForumSection
    states: dict[str, StateRule] = Field(default_factory=dict)
    actions: dict[str, ActionRule] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @field_validator("states")
    @classmethod
    def ensure_known_state_names(cls, value: dict[str, StateRule]) -> dict[str, StateRule]:
        allowed = {"duplicate", "in_progress", "wiki_exported", "closed", "open"}
        unknown = set(value) - allowed
        if unknown:
            msg = f"Unknown state rule names: {', '.join(sorted(unknown))}"
            raise ValueError(msg)
        return value


class LoadedForumConfig(BaseModel):
    path: Path
    config: ForumConfig
