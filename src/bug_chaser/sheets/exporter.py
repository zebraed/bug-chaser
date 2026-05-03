from __future__ import annotations

from typing import TYPE_CHECKING

from bug_chaser.config.forum import ForumConfig
from bug_chaser.core.models import ThreadSnapshot

if TYPE_CHECKING:
    from bug_chaser.sheets.google import GoogleClients

MASTER_HEADERS = [
    "Thread ID",
    "URL",
    "Forum Channel",
    "Title",
    "Body",
    "Author",
    "Created At",
    "Tags",
    "Reactions",
    "Reply Count",
    "Status",
    "Last Synced At",
]


class SheetExporter:
    """Exports thread snapshots to the bot-managed master sheet."""

    def __init__(self, google_clients: GoogleClients) -> None:
        self._sheets = google_clients.sheets

    def upsert_master_row(self, config: ForumConfig, snapshot: ThreadSnapshot) -> None:
        spreadsheet_id = config.forum.sheets.spreadsheet_id
        if not spreadsheet_id:
            msg = f"Spreadsheet id is not set for forum {config.forum.key}."
            raise ValueError(msg)

        sheet_name = config.forum.sheets.master_sheet_name
        self._ensure_headers(spreadsheet_id, sheet_name)
        existing = self._find_row(spreadsheet_id, sheet_name, snapshot.thread_id)
        values = self._row_values(snapshot)
        if existing is None:
            self._append_row(spreadsheet_id, sheet_name, values)
        else:
            self._update_row(spreadsheet_id, sheet_name, existing, values)

    def _ensure_headers(self, spreadsheet_id: str, sheet_name: str) -> None:
        range_name = f"{sheet_name}!A1:L1"
        current = (
            self._sheets.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
            .get("values", [])
        )
        if current and current[0] == MASTER_HEADERS:
            return
        self._sheets.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="RAW",
            body={"values": [MASTER_HEADERS]},
        ).execute()

    def _find_row(self, spreadsheet_id: str, sheet_name: str, thread_id: int) -> int | None:
        values = (
            self._sheets.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A:A")
            .execute()
            .get("values", [])
        )
        target = str(thread_id)
        for index, row in enumerate(values, start=1):
            if row and row[0] == target:
                return index
        return None

    def _append_row(self, spreadsheet_id: str, sheet_name: str, values: list[str | int]) -> None:
        self._sheets.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A:L",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [values]},
        ).execute()

    def _update_row(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        row_number: int,
        values: list[str | int],
    ) -> None:
        self._sheets.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A{row_number}:L{row_number}",
            valueInputOption="RAW",
            body={"values": [values]},
        ).execute()

    def _row_values(self, snapshot: ThreadSnapshot) -> list[str | int]:
        return [
            str(snapshot.thread_id),
            snapshot.url or "",
            str(snapshot.forum_channel_id),
            snapshot.title,
            snapshot.body,
            snapshot.author_name or "",
            snapshot.created_at.isoformat() if snapshot.created_at else "",
            snapshot.tag_summary(),
            snapshot.reaction_summary(),
            snapshot.reply_count,
            snapshot.status,
            "",
        ]
