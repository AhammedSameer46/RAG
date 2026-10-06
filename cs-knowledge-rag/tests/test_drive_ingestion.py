from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from cs_ingest.drive import DriveAPIError
from cs_ingest.drive_ingestion import (
    UnsupportedDriveFileTypeError,
    ingest_drive_file,
    load_drive_file,
    normalize_drive_file,
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


def test_pdf_is_materialized_and_sent_to_existing_ingestion(monkeypatch):
    adapter = _adapter("application/pdf", b"%PDF-test")
    observed: dict[str, object] = {}

    def fake_ingest_directory(input_dir):
        path = Path(input_dir)
        observed["path"] = path
        observed["files"] = [item.name for item in path.iterdir()]
        observed["content"] = (path / "minutes.pdf").read_bytes()
        return {
            "schema_version": 1,
            "sources": [{"filename": "minutes.pdf", "file_type": "pdf"}],
            "pdf_pages": [],
            "worksheets": [],
            "dates": [],
        }

    monkeypatch.setattr(
        "cs_ingest.drive_ingestion.ingest_directory",
        fake_ingest_directory,
    )

    result = ingest_drive_file(adapter, "drive-file-id")

    assert result["sources"][0]["filename"] == "minutes.pdf"
    assert observed["files"] == ["minutes.pdf"]
    assert observed["content"] == b"%PDF-test"
    assert not observed["path"].exists()


def test_pdf_raw_source_preserves_drive_provenance(monkeypatch):
    adapter = _adapter("application/pdf", b"%PDF-test")
    monkeypatch.setattr(
        "cs_ingest.drive_ingestion.ingest_directory",
        lambda input_dir: {
            "schema_version": 1,
            "sources": [
                {
                    "filename": "minutes.pdf",
                    "file_type": "pdf",
                    "sha256": "a" * 64,
                    "size_bytes": 9,
                }
            ],
            "pdf_pages": [],
            "worksheets": [],
            "dates": [],
        },
    )

    result = ingest_drive_file(adapter, "drive-file-id")

    assert result["sources"][0]["drive_provenance"] == {
        "file_id": "drive-file-id",
        "file_name": "minutes.pdf",
        "mime_type": "application/pdf",
        "parent_ids": ["folder-id", "root-id"],
        "modified_time": "2026-10-03T10:00:00Z",
        "web_view_link": "https://drive.google.com/file/drive-file-id",
    }


def test_xlsx_is_materialized_with_original_filename(monkeypatch):
    adapter = _adapter(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        b"xlsx bytes",
    )
    observed: dict[str, object] = {}

    def fake_ingest_directory(input_dir):
        path = Path(input_dir)
        observed["files"] = [item.name for item in path.iterdir()]
        observed["content"] = (path / "data.xlsx").read_bytes()
        return {
            "schema_version": 1,
            "sources": [{"filename": "data.xlsx", "file_type": "xlsx"}],
            "pdf_pages": [],
            "worksheets": [{"source": "data.xlsx"}],
            "dates": [],
        }

    monkeypatch.setattr(
        "cs_ingest.drive_ingestion.ingest_directory",
        fake_ingest_directory,
    )

    result = ingest_drive_file(adapter, "drive-file-id")

    assert result["sources"][0]["filename"] == "data.xlsx"
    assert observed["files"] == ["data.xlsx"]
    assert observed["content"] == b"xlsx bytes"


def test_xlsx_raw_source_preserves_drive_provenance_without_optional_fields(
    monkeypatch,
):
    adapter = _adapter(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    adapter.get_file_metadata.return_value["modifiedTime"] = None
    adapter.get_file_metadata.return_value["webViewLink"] = None

    monkeypatch.setattr(
        "cs_ingest.drive_ingestion.ingest_directory",
        lambda input_dir: {
            "schema_version": 1,
            "sources": [
                {
                    "filename": "data.xlsx",
                    "file_type": "xlsx",
                    "sha256": "b" * 64,
                    "size_bytes": 10,
                }
            ],
            "pdf_pages": [],
            "worksheets": [],
            "dates": [],
        },
    )

    result = ingest_drive_file(adapter, "drive-file-id")

    assert result["sources"][0]["drive_provenance"]["modified_time"] is None
    assert result["sources"][0]["drive_provenance"]["web_view_link"] is None


def test_materialized_file_is_cleaned_up_when_extraction_fails(monkeypatch):
    adapter = _adapter("application/pdf", b"%PDF-test")
    observed: dict[str, Path] = {}

    def failing_ingest_directory(input_dir):
        path = Path(input_dir)
        observed["path"] = path
        assert (path / "minutes.pdf").exists()
        raise ValueError("extraction failed")

    monkeypatch.setattr(
        "cs_ingest.drive_ingestion.ingest_directory",
        failing_ingest_directory,
    )

    with pytest.raises(ValueError, match="extraction failed"):
        ingest_drive_file(adapter, "drive-file-id")

    assert not observed["path"].exists()


def test_drive_adapter_errors_propagate_before_materialization():
    adapter = Mock()
    error = DriveAPIError("Google Drive file download failed.")
    adapter.get_file_metadata.side_effect = error

    with pytest.raises(DriveAPIError) as raised:
        ingest_drive_file(adapter, "drive-file-id")

    assert raised.value is error


def test_normalize_drive_file_returns_normalized_source_with_drive_provenance(
    monkeypatch,
):
    adapter = _adapter("application/pdf", b"%PDF-test")

    monkeypatch.setattr(
        "cs_ingest.drive_ingestion.ingest_directory",
        lambda input_dir: {
            "schema_version": 1,
            "sources": [
                {
                    "filename": "minutes.pdf",
                    "file_type": "pdf",
                    "sha256": "a" * 64,
                    "size_bytes": 9,
                }
            ],
            "pdf_pages": [],
            "worksheets": [],
            "dates": [],
        },
    )

    monkeypatch.setattr(
        "cs_ingest.drive_ingestion.normalize_ingestion",
        lambda extracted: {
            "schema_version": 1,
            "sources": [
                {
                    **extracted["sources"][0],
                    "source_id": (
                        "sha256:" + extracted["sources"][0]["sha256"]
                    ),
                }
            ],
            "evidence_units": [],
            "date_mentions": [],
            "records": [],
        },
    )

    result = normalize_drive_file(adapter, "drive-file-id")

    source = result["sources"][0]

    assert source["source_id"] == "sha256:" + "a" * 64
    assert source["filename"] == "minutes.pdf"
    assert source["file_type"] == "pdf"
    assert source["drive_provenance"]["file_id"] == "drive-file-id"
    assert source["drive_provenance"]["mime_type"] == "application/pdf"
