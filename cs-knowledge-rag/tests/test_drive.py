from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cs_ingest.drive import (
    DriveConfig,
    DriveConfigurationError,
    DriveAPIError,
    GoogleDriveAdapter,
)


def test_config_reads_environment_and_uses_project_defaults(monkeypatch):
    monkeypatch.setenv("CS_RAG_GOOGLE_CREDENTIALS_FILE", "custom.json")
    monkeypatch.setenv("CS_RAG_GOOGLE_TOKEN_FILE", "custom-token.json")
    monkeypatch.setenv("CS_RAG_DRIVE_ROOT_FOLDER_ID", "root-id")

    config = DriveConfig.from_environment()

    assert config == DriveConfig(
        credentials_file=Path("custom.json"),
        token_file=Path("custom-token.json"),
        root_folder_id="root-id",
    )


def test_missing_credentials_file_raises_clear_error(tmp_path):
    adapter = GoogleDriveAdapter(
        DriveConfig(
            credentials_file=tmp_path / "missing.json",
            token_file=tmp_path / "token.json",
        )
    )

    with pytest.raises(DriveConfigurationError, match="credentials file"):
        adapter.authenticate()


def test_list_children_paginates_and_preserves_metadata():
    service = Mock()
    service.files().list.side_effect = [
        Mock(
            execute=Mock(
                return_value={
                    "files": [{"id": "one", "name": "One"}],
                    "nextPageToken": "next",
                }
            )
        ),
        Mock(
            execute=Mock(
                return_value={
                    "files": [
                        {
                            "id": "two",
                            "name": "Two",
                            "mimeType": "application/pdf",
                            "parents": ["root"],
                            "modifiedTime": "2026-10-03T00:00:00Z",
                            "webViewLink": "https://drive.google.com/file/two",
                        }
                    ]
                }
            )
        ),
    ]
    adapter = GoogleDriveAdapter(service=service)

    assert adapter.list_children("root") == [
        {"id": "one", "name": "One"},
        {
            "id": "two",
            "name": "Two",
            "mimeType": "application/pdf",
            "parents": ["root"],
            "modifiedTime": "2026-10-03T00:00:00Z",
            "webViewLink": "https://drive.google.com/file/two",
        },
    ]


def test_get_metadata():
    service = Mock()
    service.files().get.return_value.execute.return_value = {
        "id": "file-id",
        "name": "minutes.pdf",
        "mimeType": "application/pdf",
        "parents": ["root"],
        "modifiedTime": "2026-10-03T00:00:00Z",
        "webViewLink": "https://drive.google.com/file/file-id",
    }

    adapter = GoogleDriveAdapter(service=service)

    assert adapter.get_file_metadata("file-id")["name"] == "minutes.pdf"


def test_download_file_returns_bytes():
    service = Mock()
    downloader = Mock()
    downloader.next_chunk.side_effect = [(None, False), (None, True)]

    with patch("cs_ingest.drive.MediaIoBaseDownload", return_value=downloader):
        result = GoogleDriveAdapter(service=service).download_file("file-id")

    assert result == b""
    service.files().get_media.assert_called_once_with(fileId="file-id")


def test_api_failures_become_application_errors():
    service = Mock()
    response = Mock(status=403)
    from googleapiclient.errors import HttpError

    service.files().get.return_value.execute.side_effect = HttpError(
        response, b"forbidden"
    )

    with pytest.raises(DriveAPIError, match="HTTP status 403"):
        GoogleDriveAdapter(service=service).get_file_metadata("file-id")
