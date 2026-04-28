from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from bug_chaser.config.forum import ForumConfig

if TYPE_CHECKING:
    from bug_chaser.sheets.google import GoogleClients

logger = logging.getLogger(__name__)


class SpreadsheetProvisioner:
    """Creates and shares spreadsheets for a forum."""

    def __init__(self, google_clients: GoogleClients) -> None:
        self._sheets = google_clients.sheets
        self._drive = google_clients.drive

    def ensure_spreadsheet(self, config: ForumConfig) -> str:
        sheets = config.forum.sheets
        if sheets.spreadsheet_id:
            return sheets.spreadsheet_id
        if not sheets.auto_create:
            msg = f"Spreadsheet id is required for forum {config.forum.key}."
            raise ValueError(msg)

        spreadsheet_id = self._create_spreadsheet(config)
        self._share_spreadsheet(spreadsheet_id, sheets.editor_emails)
        if sheets.owner_email:
            self._transfer_owner_if_possible(spreadsheet_id, sheets.owner_email)
        return spreadsheet_id

    def _create_spreadsheet(self, config: ForumConfig) -> str:
        sheets = config.forum.sheets
        title = f"bug-chaser - {config.forum.key}"
        body = {
            "properties": {"title": title},
            "sheets": [
                {"properties": {"title": sheets.master_sheet_name}},
                {"properties": {"title": sheets.progress_sheet_name}},
            ],
        }
        response = self._sheets.spreadsheets().create(body=body).execute()
        return response["spreadsheetId"]

    def _share_spreadsheet(self, spreadsheet_id: str, editor_emails: list[str]) -> None:
        for email in editor_emails:
            self._drive.permissions().create(
                fileId=spreadsheet_id,
                body={"type": "user", "role": "writer", "emailAddress": email},
                sendNotificationEmail=False,
            ).execute()

    def _transfer_owner_if_possible(self, spreadsheet_id: str, owner_email: str) -> None:
        permission = self._drive.permissions().create(
            fileId=spreadsheet_id,
            body={"type": "user", "role": "owner", "emailAddress": owner_email},
            transferOwnership=True,
            sendNotificationEmail=False,
        )
        try:
            permission.execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Owner transfer failed. The editor permission may still have been granted. "
                "Reason: %s",
                exc,
            )
