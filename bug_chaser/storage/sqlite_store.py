"""
SQLite persistence for snapshots and per-forum feature flags.

Database schema:
    - forum_channels: Forum channel configurations.
    - threads: Thread snapshots.
    - feature_flags: Per-forum feature flags.
    - sync_runs: Sync run history.
    - guild_join_messages: Guild join message delivery history.
    - guild_join_pending: Guild join retry wait (explicit channel_id only).

#TODO Do we need to separate the schema into other files?
"""
import json
import sqlite3
from pathlib import Path

from bug_chaser.config.forum import ForumConfig
from bug_chaser.core.models import AutomationFeature, ThreadSnapshot


class SQLiteStore:
    """SQLite persistence for snapshots and per-forum feature flags."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS forum_channels (
                    forum_key TEXT PRIMARY KEY,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL UNIQUE,
                    sheets_enabled INTEGER NOT NULL DEFAULT 0,
                    automation_enabled INTEGER NOT NULL DEFAULT 0,
                    spreadsheet_id TEXT
                );

                CREATE TABLE IF NOT EXISTS threads (
                    thread_id INTEGER PRIMARY KEY,
                    forum_key TEXT NOT NULL,
                    forum_channel_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    author_id INTEGER,
                    author_name TEXT,
                    created_at TEXT,
                    tags_json TEXT NOT NULL,
                    reactions_json TEXT NOT NULL,
                    reply_count INTEGER NOT NULL,
                    url TEXT,
                    archived INTEGER NOT NULL,
                    locked INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    last_synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS feature_flags (
                    forum_key TEXT NOT NULL,
                    feature TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (forum_key, feature)
                );

                CREATE TABLE IF NOT EXISTS sync_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    forum_key TEXT NOT NULL,
                    fetched INTEGER NOT NULL,
                    stored INTEGER NOT NULL,
                    exported INTEGER NOT NULL,
                    errors_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS guild_join_messages (
                    guild_id INTEGER PRIMARY KEY,
                    sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS guild_join_pending (
                    guild_id INTEGER PRIMARY KEY,
                    channel_id INTEGER NOT NULL
                );
                """
            )

    def upsert_forum(self, config: ForumConfig) -> None:
        """Upsert the forum configuration into the database.

        Args:
            config (ForumConfig): The forum configuration.
        """
        forum = config.forum
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO forum_channels (
                    forum_key, guild_id, channel_id, sheets_enabled,
                    automation_enabled, spreadsheet_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(forum_key) DO UPDATE SET
                    guild_id = excluded.guild_id,
                    channel_id = excluded.channel_id,
                    spreadsheet_id = COALESCE(
                        excluded.spreadsheet_id,
                        forum_channels.spreadsheet_id
                    )
                """,
                (
                    forum.key,
                    forum.guild_id,
                    forum.channel_id,
                    int(forum.sheets.enabled),
                    int(forum.automation.enabled),
                    forum.sheets.spreadsheet_id,
                ),
            )

    def upsert_thread(self, forum_key: str, snapshot: ThreadSnapshot) -> None:
        """Upsert the thread snapshot into the database.

        Args:
            forum_key (str): The forum key.
            snapshot (ThreadSnapshot): The thread snapshot.
        """
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO threads (
                    thread_id, forum_key, forum_channel_id, title, body,
                    author_id, author_name, created_at, tags_json,
                    reactions_json, reply_count, url, archived, locked, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(thread_id) DO UPDATE SET
                    title = excluded.title,
                    body = excluded.body,
                    author_id = excluded.author_id,
                    author_name = excluded.author_name,
                    created_at = excluded.created_at,
                    tags_json = excluded.tags_json,
                    reactions_json = excluded.reactions_json,
                    reply_count = excluded.reply_count,
                    url = excluded.url,
                    archived = excluded.archived,
                    locked = excluded.locked,
                    status = excluded.status,
                    last_synced_at = CURRENT_TIMESTAMP
                """,
                (
                    snapshot.thread_id,
                    forum_key,
                    snapshot.forum_channel_id,
                    snapshot.title,
                    snapshot.body,
                    snapshot.author_id,
                    snapshot.author_name,
                    snapshot.created_at.isoformat() if snapshot.created_at else None,
                    json.dumps(list(snapshot.tags), ensure_ascii=False),
                    json.dumps(
                        [
                            {"emoji": reaction.emoji, "count": reaction.count}
                            for reaction in snapshot.reactions
                        ],
                        ensure_ascii=False,
                    ),
                    snapshot.reply_count,
                    snapshot.url,
                    int(snapshot.archived),
                    int(snapshot.locked),
                    snapshot.status,
                ),
            )

    def set_sheets_enabled(self, forum_key: str, enabled: bool) -> None:
        """Set the Sheets sync enabled flag for a forum.

        Args:
            forum_key (str): The forum key.
            enabled (bool): Whether Sheets sync is enabled.
        """
        with self._connect() as connection:
            connection.execute(
                "UPDATE forum_channels SET sheets_enabled = ? WHERE forum_key = ?",
                (int(enabled), forum_key),
            )

    def set_spreadsheet_id(self, forum_key: str, spreadsheet_id: str) -> None:
        """Set the spreadsheet id for a forum.

        Args:
            forum_key (str): The forum key.
            spreadsheet_id (str): The spreadsheet id.
        """
        with self._connect() as connection:
            connection.execute(
                "UPDATE forum_channels SET spreadsheet_id = ? WHERE forum_key = ?",
                (spreadsheet_id, forum_key),
            )

    def set_automation_enabled(
        self,
        forum_key: str,
        feature: AutomationFeature,
        enabled: bool,
    ) -> None:
        """Set the automation enabled flag for a forum.

        Args:
            forum_key (str): The forum key.
            feature (AutomationFeature): The feature to enable.
            enabled (bool): Whether the feature is enabled.
        """
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO feature_flags (forum_key, feature, enabled)
                VALUES (?, ?, ?)
                ON CONFLICT(forum_key, feature) DO UPDATE SET
                    enabled = excluded.enabled,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (forum_key, feature.value, int(enabled)),
            )

    def get_runtime_flags(self, forum_key: str) -> dict[str, bool]:
        """Load persisted runtime flags for a forum.

        Args:
            forum_key (str): The forum key.

        Returns:
            A dict with keys like ``sheets_enabled``, ``automation_enabled``,
            ``auto_comment``, etc. Missing keys mean no override was saved.
        """
        result: dict[str, bool] = {}
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT sheets_enabled, automation_enabled
                FROM forum_channels
                WHERE forum_key = ?
                """,
                (forum_key,),
            ).fetchone()
            if row is not None:
                result["sheets_enabled"] = bool(row[0])
                result["automation_enabled"] = bool(row[1])

            for feature_row in connection.execute(
                """
                SELECT feature, enabled
                FROM feature_flags
                WHERE forum_key = ?
                """,
                (forum_key,),
            ):
                result[feature_row[0]] = bool(feature_row[1])
        return result

    def record_sync_run(
        self,
        forum_key: str,
        fetched: int,
        stored: int,
        exported: int,
        errors: list[str],
    ) -> None:
        """Record a sync run.

        Args:
            forum_key (str): The forum key.
            fetched (int): The number of threads fetched.
            stored (int): The number of threads stored.
            exported (int): The number of threads exported.
            errors (list[str]): The list of errors.
        """
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sync_runs (
                    forum_key, fetched, stored, exported, errors_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    forum_key,
                    fetched,
                    stored,
                    exported,
                    json.dumps(errors, ensure_ascii=False),
                ),
            )

    def has_sent_guild_join_message(self, guild_id: int) -> bool:
        """Check whether the guild join message was already sent."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM guild_join_messages
                WHERE guild_id = ?
                """,
                (guild_id,),
            ).fetchone()
        return row is not None

    def mark_guild_join_message_sent(self, guild_id: int) -> None:
        """Mark the guild join message as sent for a guild."""
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO guild_join_messages (guild_id)
                VALUES (?)
                ON CONFLICT(guild_id) DO NOTHING
                """,
                (guild_id,),
            )
            connection.execute(
                "DELETE FROM guild_join_pending WHERE guild_id = ?",
                (guild_id,),
            )

    def get_guild_join_pending_channel_id(self, guild_id: int) -> int | None:
        """Return channel_id waiting for permission, if any."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT channel_id
                FROM guild_join_pending
                WHERE guild_id = ?
                """,
                (guild_id,),
            ).fetchone()
        return int(row[0]) if row is not None else None

    def set_guild_join_pending(self, guild_id: int, channel_id: int) -> None:
        """Remember to retry guild join when channel permissions allow sending."""
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO guild_join_pending (guild_id, channel_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    channel_id = excluded.channel_id
                """,
                (guild_id, channel_id),
            )

    def clear_guild_join_pending(self, guild_id: int) -> None:
        """Drop retry state for a guild."""
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM guild_join_pending WHERE guild_id = ?",
                (guild_id,),
            )

    def _connect(self) -> sqlite3.Connection:
        """Connect to the SQLite database.

        Returns:
            The SQLite connection.
        """
        return sqlite3.connect(self._database_path)
