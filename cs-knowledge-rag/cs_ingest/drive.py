"""Small Google Drive adapter for read-only institutional source access."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import os
from pathlib import Path
from typing import Any, Final, Mapping

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload


_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CREDENTIALS_FILE = _PROJECT_ROOT / "credentials.json"
_DEFAULT_TOKEN_FILE = _PROJECT_ROOT / "token.json"
_SCOPES: Final[tuple[str, ...]] = (
    "https://www.googleapis.com/auth/drive.readonly",
)
_METADATA_FIELDS = "id,name,mimeType,parents,modifiedTime,webViewLink"


class DriveError(RuntimeError):
    """Base class for application-level Google Drive errors."""


class DriveConfigurationError(DriveError):
    """Google Drive configuration or credential files are invalid or missing."""


class DriveAuthenticationError(DriveError):
    """Google Drive authentication could not be completed."""


class DriveAPIError(DriveError):
    """A Google Drive API request failed."""


@dataclass(frozen=True)
class DriveConfig:
    """Google Drive paths and optional configured root folder."""

    credentials_file: Path = _DEFAULT_CREDENTIALS_FILE
    token_file: Path = _DEFAULT_TOKEN_FILE
    root_folder_id: str | None = None

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> "DriveConfig":
        values = os.environ if environ is None else environ
        return cls(
            credentials_file=Path(
                values.get(
                    "CS_RAG_GOOGLE_CREDENTIALS_FILE",
                    str(_DEFAULT_CREDENTIALS_FILE),
                )
            ),
            token_file=Path(
                values.get(
                    "CS_RAG_GOOGLE_TOKEN_FILE",
                    str(_DEFAULT_TOKEN_FILE),
                )
            ),
            root_folder_id=values.get("CS_RAG_DRIVE_ROOT_FOLDER_ID") or None,
        )


class GoogleDriveAdapter:
    """Authenticate to and access Google Drive through the v3 API."""

    def __init__(
        self,
        config: DriveConfig | None = None,
        *,
        service: Any | None = None,
    ) -> None:
        self.config = config or DriveConfig.from_environment()
        self._service = service

    def authenticate(self) -> Credentials:
        """Authenticate and create the Drive API service."""
        credentials: Credentials | None = None
        if self.config.token_file.exists():
            try:
                credentials = Credentials.from_authorized_user_file(
                    str(self.config.token_file),
                    list(_SCOPES),
                )
            except (OSError, ValueError) as exc:
                raise DriveAuthenticationError(
                    f"Could not read Google Drive token file: "
                    f"{self.config.token_file}"
                ) from exc

        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except (OSError, RefreshError, ValueError) as exc:
                raise DriveAuthenticationError(
                    "Could not refresh Google Drive credentials."
                ) from exc

        if not credentials or not credentials.valid:
            if not self.config.credentials_file.is_file():
                raise DriveConfigurationError(
                    "Google Drive credentials file was not found: "
                    f"{self.config.credentials_file}"
                )
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.config.credentials_file),
                    list(_SCOPES),
                )
                credentials = flow.run_local_server(port=0)
            except (OSError, ValueError) as exc:
                raise DriveAuthenticationError(
                    "Could not authenticate with Google Drive credentials."
                ) from exc
            try:
                self.config.token_file.write_text(
                    credentials.to_json(),
                    encoding="utf-8",
                )
            except OSError as exc:
                raise DriveAuthenticationError(
                    f"Could not save Google Drive token file: "
                    f"{self.config.token_file}"
                ) from exc

        self._service = build("drive", "v3", credentials=credentials)
        return credentials

    def get_file_metadata(self, file_id: str) -> dict[str, Any]:
        """Return stable metadata for one Drive file."""
        response = self._execute(
            "metadata lookup",
            lambda: self._get_service()
            .files()
            .get(fileId=file_id, fields=_METADATA_FIELDS)
            .execute(),
        )
        return dict(response)

    def list_children(self, folder_id: str) -> list[dict[str, Any]]:
        """List all non-trashed direct children of a Drive folder."""
        files: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            response = self._execute(
                "folder listing",
                lambda page_token=page_token: self._get_service()
                .files()
                .list(
                    q=f"'{folder_id}' in parents and trashed = false",
                    pageSize=100,
                    pageToken=page_token,
                    fields=f"nextPageToken,files({_METADATA_FIELDS})",
                )
                .execute(),
            )
            files.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                return files

    def download_file(self, file_id: str) -> bytes:
        """Download a Drive file as bytes."""
        buffer = BytesIO()
        try:
            request = self._get_service().files().get_media(fileId=file_id)
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        except HttpError as exc:
            raise self._api_error("file download", exc) from exc
        return buffer.getvalue()

    def _get_service(self) -> Any:
        if self._service is None:
            self.authenticate()
        if self._service is None:
            raise DriveAuthenticationError(
                "Google Drive service was not initialized."
            )
        return self._service

    @staticmethod
    def _execute(operation: str, request: Any) -> Any:
        try:
            return request()
        except HttpError as exc:
            raise GoogleDriveAdapter._api_error(operation, exc) from exc

    @staticmethod
    def _api_error(operation: str, exc: HttpError) -> DriveAPIError:
        status = getattr(exc.resp, "status", "unknown")
        return DriveAPIError(
            f"Google Drive {operation} failed with HTTP status {status}."
        )
