"""
Google clients for the application.

#TODO WIP
"""
from pathlib import Path
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SHEETS_SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
)


class GoogleClients:
    """Google clients for the application."""
    def __init__(self, service_account_file: Path) -> None:
        """Initialize the Google clients.

        Args:
            service_account_file (Path): The path to the service account file.(JSON)
        """
        credentials = Credentials.from_service_account_file(
            service_account_file,
            scopes=SHEETS_SCOPES,
        )
        self.sheets: Any = build("sheets", "v4", credentials=credentials)
        self.drive: Any = build("drive", "v3", credentials=credentials)
