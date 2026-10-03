from __future__ import annotations

from unittest.mock import Mock

import pytest

from cs_ingest.drive import DriveAPIError
from cs_ingest.drive_discovery import (
    FOLDER_MIME_TYPE,
    DriveFileMetadata,
    discover_drive_files,
)


def _file(
    file_id: str,
    name: str,
    mime_type: str = "application/pdf",
    parents: list[str] | None = None,
) -> dict[str, object]:
    return {
        "id": file_id,
        "name": name,
        "mimeType": mime_type,
        "parents": parents or ["root"],
        "modifiedTime": "2026-10-03T10:00:00Z",
        "webViewLink": f"https://drive.google.com/file/{file_id}",
    }


def test_empty_root_returns_no_files():
    adapter = Mock()
    adapter.list_children.return_value = []

    assert discover_drive_files(adapter, "configured-root") == []
    adapter.list_children.assert_called_once_with("configured-root")


def test_direct_file_is_returned_without_download():
    adapter = Mock()
    adapter.list_children.return_value = [_file("pdf-1", "minutes.pdf")]

    result = discover_drive_files(adapter, "configured-root")

    assert result == [
        DriveFileMetadata(
            file_id="pdf-1",
            name="minutes.pdf",
            mime_type="application/pdf",
            parent_ids=("root",),
            modified_time="2026-10-03T10:00:00Z",
            web_view_link="https://drive.google.com/file/pdf-1",
        )
    ]
    adapter.download_file.assert_not_called()


def test_trashed_entries_are_excluded():
    adapter = Mock()
    trashed = _file("old", "old.pdf")
    trashed["trashed"] = True
    adapter.list_children.return_value = [trashed, _file("live", "live.pdf")]

    result = discover_drive_files(adapter, "root")

    assert [item.file_id for item in result] == ["live"]


def test_nested_folder_file_is_returned_but_folder_is_not():
    adapter = Mock()
    adapter.list_children.side_effect = [
        [_file("folder-1", "Arbitrary folder", FOLDER_MIME_TYPE)],
        [_file("xlsx-1", "attendance.xlsx", _xlsx_mime(), ["folder-1"])],
    ]

    result = discover_drive_files(adapter, "root")

    assert [item.file_id for item in result] == ["xlsx-1"]
    assert adapter.list_children.call_args_list == [
        (("root",),),
        (("folder-1",),),
    ]


def test_multiple_nested_levels_and_arbitrary_names_are_supported():
    adapter = Mock()
    adapter.list_children.side_effect = [
        [_file("folder-a", "Not a semantic type", FOLDER_MIME_TYPE)],
        [_file("folder-b", "2026 Archive", FOLDER_MIME_TYPE, ["folder-a"])],
        [_file("file-1", "record.xlsx", _xlsx_mime(), ["folder-b"])],
    ]

    result = discover_drive_files(adapter, "root")

    assert [item.name for item in result] == ["record.xlsx"]


def test_pagination_is_delegated_to_adapter():
    adapter = Mock()
    adapter.list_children.side_effect = [
        [
            _file("file-1", "first.pdf"),
            _file("file-2", "second.pdf"),
        ]
    ]

    result = discover_drive_files(adapter, "root")

    assert [item.file_id for item in result] == ["file-1", "file-2"]
    adapter.list_children.assert_called_once_with("root")


def test_metadata_fields_are_preserved_exactly():
    adapter = Mock()
    adapter.list_children.return_value = [
        {
            "id": "file-1",
            "name": "notice.pdf",
            "mimeType": "application/pdf",
            "parents": ["nested", "root"],
            "modifiedTime": "2026-09-01T12:34:56Z",
            "webViewLink": "https://example.test/file-1",
        }
    ]

    result = discover_drive_files(adapter, "root")

    assert result[0] == DriveFileMetadata(
        file_id="file-1",
        name="notice.pdf",
        mime_type="application/pdf",
        parent_ids=("nested", "root"),
        modified_time="2026-09-01T12:34:56Z",
        web_view_link="https://example.test/file-1",
    )


def test_api_errors_propagate_without_translation_or_download():
    adapter = Mock()
    error = DriveAPIError("Google Drive folder listing failed.")
    adapter.list_children.side_effect = error

    with pytest.raises(DriveAPIError) as raised:
        discover_drive_files(adapter, "root")

    assert raised.value is error
    adapter.download_file.assert_not_called()


def _xlsx_mime() -> str:
    return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
