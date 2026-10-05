"""Deterministic classification of Google Drive inventory changes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Iterable

from .drive_discovery import DriveFileMetadata


class DriveSyncClassification(StrEnum):
    """Classification of a Drive object relative to indexed state."""

    NEW = "NEW"
    MODIFIED = "MODIFIED"
    UNCHANGED = "UNCHANGED"
    DELETED = "DELETED"


@dataclass(frozen=True)
class CurrentDriveInventoryItem:
    """A discovered Drive object with a normalized operational timestamp."""

    root_folder_id: str
    drive_file_id: str
    name: str
    mime_type: str
    parent_ids: tuple[str, ...]
    modified_time: datetime | None
    web_view_link: str | None

    @classmethod
    def from_discovered(
        cls,
        root_folder_id: str,
        item: DriveFileMetadata,
    ) -> CurrentDriveInventoryItem:
        return cls(
            root_folder_id=root_folder_id,
            drive_file_id=item.file_id,
            name=item.name,
            mime_type=item.mime_type,
            parent_ids=item.parent_ids,
            modified_time=_parse_modified_time(item.modified_time),
            web_view_link=item.web_view_link,
        )


@dataclass(frozen=True)
class PreviousDriveFileState:
    """Previously indexed state for one Drive object."""

    root_folder_id: str
    drive_file_id: str
    indexed_modified_time: datetime | None


@dataclass(frozen=True)
class DriveSyncClassificationResult:
    """Classification for one current or previously indexed Drive object."""

    drive_file_id: str
    classification: DriveSyncClassification
    current: CurrentDriveInventoryItem | None
    previous: PreviousDriveFileState | None


def classify_drive_inventory(
    root_folder_id: str,
    current_inventory: Iterable[DriveFileMetadata],
    previous_state: Iterable[PreviousDriveFileState],
    discovery_completed: bool,
) -> list[DriveSyncClassificationResult]:
    """Classify current and prior Drive objects without mutating persistence."""
    current_items = [
        CurrentDriveInventoryItem.from_discovered(root_folder_id, item)
        for item in current_inventory
    ]
    previous_items = [
        item for item in previous_state if item.root_folder_id == root_folder_id
    ]
    current = {item.drive_file_id: item for item in current_items}
    previous = {
        item.drive_file_id: item for item in previous_items
    }
    if len(current) != len(current_items):
        raise ValueError("Current Drive inventory contains duplicate file IDs.")
    if len(previous) != len(previous_items):
        raise ValueError("Previous Drive state contains duplicate file IDs.")

    results = [
        _classify_present_file(current_item, previous.get(file_id))
        for file_id, current_item in current.items()
    ]
    if discovery_completed:
        results.extend(
            DriveSyncClassificationResult(
                drive_file_id=file_id,
                classification=DriveSyncClassification.DELETED,
                current=None,
                previous=previous_item,
            )
            for file_id, previous_item in previous.items()
            if file_id not in current
        )
    return sorted(results, key=lambda result: result.drive_file_id)


def _classify_present_file(
    current: CurrentDriveInventoryItem,
    previous: PreviousDriveFileState | None,
) -> DriveSyncClassificationResult:
    if previous is None:
        classification = DriveSyncClassification.NEW
    elif _timestamps_indicate_change(
        current.modified_time, previous.indexed_modified_time
    ):
        classification = DriveSyncClassification.MODIFIED
    else:
        classification = DriveSyncClassification.UNCHANGED
    return DriveSyncClassificationResult(
        drive_file_id=current.drive_file_id,
        classification=classification,
        current=current,
        previous=previous,
    )


def _timestamps_indicate_change(
    current: datetime | None,
    previous: datetime | None,
) -> bool:
    """Only comparable, present timestamps can signal a modification."""
    return current is not None and previous is not None and current != previous


def _parse_modified_time(value: str | None) -> datetime | None:
    if value is None:
        return None
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("Drive modified_time must be timezone-aware.")
    return timestamp
