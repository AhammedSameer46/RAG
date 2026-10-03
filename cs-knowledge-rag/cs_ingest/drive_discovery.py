"""Recursive, read-only discovery of files below a Google Drive folder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


class DriveDiscoveryAdapter(Protocol):
    """Minimum adapter contract required for recursive discovery."""

    def list_children(self, folder_id: str) -> list[dict[str, Any]]:
        ...


@dataclass(frozen=True)
class DriveFileMetadata:
    """Drive metadata retained for a discovered non-folder file."""

    file_id: str
    name: str
    mime_type: str
    parent_ids: tuple[str, ...]
    modified_time: str | None
    web_view_link: str | None


def discover_drive_files(
    adapter: DriveDiscoveryAdapter,
    root_folder_id: str,
) -> list[DriveFileMetadata]:
    """Recursively discover all non-folder files below the root folder."""
    discovered: list[DriveFileMetadata] = []
    _discover_children(adapter, root_folder_id, discovered, set())
    return discovered


def _discover_children(
    adapter: DriveDiscoveryAdapter,
    folder_id: str,
    discovered: list[DriveFileMetadata],
    visited_folders: set[str],
) -> None:
    if folder_id in visited_folders:
        return
    visited_folders.add(folder_id)
    for metadata in adapter.list_children(folder_id):
        if metadata.get("trashed", False):
            continue
        child_id = metadata["id"]
        if metadata.get("mimeType") == FOLDER_MIME_TYPE:
            _discover_children(adapter, child_id, discovered, visited_folders)
            continue
        discovered.append(_file_metadata(metadata))


def _file_metadata(metadata: dict[str, Any]) -> DriveFileMetadata:
    return DriveFileMetadata(
        file_id=metadata["id"],
        name=metadata["name"],
        mime_type=metadata["mimeType"],
        parent_ids=tuple(metadata.get("parents", [])),
        modified_time=metadata.get("modifiedTime"),
        web_view_link=metadata.get("webViewLink"),
    )
