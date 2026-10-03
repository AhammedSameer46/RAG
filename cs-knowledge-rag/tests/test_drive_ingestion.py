from __future__ import annotations

from unittest.mock import Mock

import pytest

from cs_ingest.drive import DriveAPIError
from cs_ingest.drive_ingestion import (
    UnsupportedDriveFileTypeError,
    load_drive_file,
)


def _adapter(mime_type: str, content: bytes = b"file bytes") -> Mock:
    adapter = Mock()
    adapter.get_file_metadata.return_value = {
        "id": "drive-file-id",
        "name": "minutes.pdf" if mime_type == "application/pdf" else "data.xlsx",
        "mimeType": mime_type,
        "parents": ["folder-id", "root-id"],
        "modifiedTime": "2026-10-03T10:00:00Z",
        "webViewLink": "https://drive.google.com/file/drive-file-id",
    }
    adapter.download_file.return_value = content
    return adapter


def test_pdf_metadata_and_bytes_become_drive_ingestion_input():
    adapter = _adapter("application/pdf", b"%PDF-test")

    result = load_drive_file(adapter, "drive-file-id")

    assert result.file_id == "drive-file-id"
    assert result.filename == "minutes.pdf"
    assert result.file_type == "pdf"
    assert result.content == b"%PDF-test"
    adapter.get_file_metadata.assert_called_once_with("drive-file-id")
    adapter.download_file.assert_called_once_with("drive-file-id")


def test_xlsx_metadata_and_bytes_become_drive_ingestion_input():
    adapter = _adapter(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        b"xlsx bytes",
    )

    result = load_drive_file(adapter, "drive-file-id")

    assert result.file_type == "xlsx"
    assert result.filename == "data.xlsx"
    assert result.file_bytes == b"xlsx bytes"


def test_drive_provenance_is_preserved():
    adapter = _adapter("application/pdf")

    result = load_drive_file(adapter, "drive-file-id")

    assert result.drive_file_id == "drive-file-id"
    assert result.drive_file_name == "minutes.pdf"
    assert result.drive_mime_type == "application/pdf"
    assert result.drive_parent_ids == ("folder-id", "root-id")
    assert result.drive_modified_time == "2026-10-03T10:00:00Z"
    assert result.drive_web_view_link == (
        "https://drive.google.com/file/drive-file-id"
    )


def test_unsupported_mime_type_fails_clearly_without_download():
    adapter = _adapter("application/vnd.google-apps.document")

    with pytest.raises(UnsupportedDriveFileTypeError, match="MIME type"):
        load_drive_file(adapter, "drive-file-id")

    adapter.download_file.assert_not_called()


def test_adapter_download_errors_propagate_as_drive_errors():
    adapter = _adapter("application/pdf")
    error = DriveAPIError("Google Drive file download failed.")
    adapter.download_file.side_effect = error

    with pytest.raises(DriveAPIError) as raised:
        load_drive_file(adapter, "drive-file-id")

    assert raised.value is error
