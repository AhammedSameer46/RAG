"""Caller-owned orchestration primitives for Drive object-state synchronization."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from .drive_discovery import DriveDiscoveryAdapter, DriveFileMetadata, discover_drive_files
from .drive_sync import (
    DriveSyncClassification,
    DriveSyncClassificationResult,
    PreviousDriveFileState,
    classify_drive_inventory,
)


class DriveSyncRepository(Protocol):
    def save_drive_sync_run(self, sync_run: dict[str, Any]) -> None: ...

    def list_drive_file_states(
        self, root_folder_id: str
    ) -> list[PreviousDriveFileState]: ...

    def save_drive_file(self, drive_file: dict[str, Any]) -> None: ...


@dataclass(frozen=True)
class DriveSyncRunResult:
    sync_run_id: str
    root_folder_id: str
    classifications: tuple[DriveSyncClassificationResult, ...]


def start_drive_sync_run(
    repository: DriveSyncRepository,
    *,
    sync_run_id: str,
    root_folder_id: str,
    started_at: datetime,
) -> None:
    """Write the running state; the caller must commit before discovery."""
    repository.save_drive_sync_run(
        {
            "sync_run_id": sync_run_id,
            "root_folder_id": root_folder_id,
            "started_at": started_at,
            "completed_at": None,
            "status": "running",
        }
    )


def discover_drive_inventory(
    adapter: DriveDiscoveryAdapter,
    root_folder_id: str,
    *,
    discover: Callable[
        [DriveDiscoveryAdapter, str], list[DriveFileMetadata]
    ] = discover_drive_files,
) -> list[DriveFileMetadata]:
    """Discover after the caller has committed the running state."""
    return discover(adapter, root_folder_id)


def classify_drive_state(
    repository: DriveSyncRepository,
    *,
    root_folder_id: str,
    inventory: Iterable[DriveFileMetadata],
) -> list[DriveSyncClassificationResult]:
    """Read prior state and classify one successfully discovered inventory."""
    previous = repository.list_drive_file_states(root_folder_id)
    return classify_drive_inventory(
        root_folder_id,
        inventory,
        previous,
        discovery_completed=True,
    )


def persist_successful_drive_state(
    repository: DriveSyncRepository,
    *,
    sync_run_id: str,
    root_folder_id: str,
    started_at: datetime,
    observed_at: datetime,
    classifications: Iterable[DriveSyncClassificationResult],
) -> DriveSyncRunResult:
    """Persist state and success; the caller must commit this transaction."""
    classification_list = list(classifications)
    previous_by_id = {
        result.drive_file_id: result.previous
        for result in classification_list
        if result.previous is not None
    }
    for result in classification_list:
        if result.classification is DriveSyncClassification.DELETED:
            continue
        current = result.current
        if current is None:
            raise RuntimeError("Non-deleted classification has no current file.")
        prior = previous_by_id.get(result.drive_file_id)
        repository.save_drive_file(
            {
                "drive_file_id": current.drive_file_id,
                "root_folder_id": current.root_folder_id,
                "source_id": None if prior is None else prior.source_id,
                "name": current.name,
                "mime_type": current.mime_type,
                "parent_ids": list(current.parent_ids),
                "modified_time": current.modified_time,
                "web_view_link": current.web_view_link,
                "indexed_modified_time": (
                    None if prior is None else prior.indexed_modified_time
                ),
                "last_seen_run_id": sync_run_id,
                "last_seen_at": observed_at,
                "last_indexed_at": None if prior is None else prior.last_indexed_at,
            }
        )
    repository.save_drive_sync_run(
        {
            "sync_run_id": sync_run_id,
            "root_folder_id": root_folder_id,
            "started_at": started_at,
            "completed_at": observed_at,
            "status": "succeeded",
        }
    )
    return DriveSyncRunResult(
        sync_run_id=sync_run_id,
        root_folder_id=root_folder_id,
        classifications=tuple(classification_list),
    )


def record_drive_sync_failure(
    repository: DriveSyncRepository,
    *,
    sync_run_id: str,
    root_folder_id: str,
    started_at: datetime,
    completed_at: datetime,
) -> None:
    """Write failed state in a new caller-owned transaction."""
    repository.save_drive_sync_run(
        {
            "sync_run_id": sync_run_id,
            "root_folder_id": root_folder_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "status": "failed",
        }
    )
