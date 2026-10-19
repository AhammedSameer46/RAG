
"""Caller-owned orchestration primitives for Drive object-state synchronization."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from .drive_discovery import (
    DriveDiscoveryAdapter,
    DriveFileMetadata,
    discover_drive_files,
)
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


class DriveContentIndexRepository(Protocol):
    """Repository operations needed to persist one indexed Drive file."""

    def save_normalized_dataset(self, dataset: dict[str, Any]) -> None: ...

    def save_drive_file(self, drive_file: dict[str, Any]) -> None: ...

    def get_drive_file_source_id(self, drive_file_id: str) -> str | None: ...

    def cleanup_source_if_unreferenced(self, source_id: str) -> bool: ...


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
                "last_indexed_at": (
                    None if prior is None else prior.last_indexed_at
                ),
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


def persist_indexed_drive_file(
    repository: DriveContentIndexRepository,
    *,
    sync_run_id: str,
    observed_at: datetime,
    classification: DriveSyncClassificationResult,
    dataset: dict[str, Any],
) -> None:
    """Persist normalized content and Drive state atomically.

    The caller owns the database transaction. New content, Drive metadata,
    and any obsolete-source cleanup must commit or roll back together.
    """
    if classification.classification not in {
        DriveSyncClassification.NEW,
        DriveSyncClassification.MODIFIED,
    }:
        raise ValueError(
            "Only NEW or MODIFIED Drive files can be content-indexed."
        )

    current = classification.current
    if current is None:
        raise ValueError(
            "A content-indexing classification must include current Drive metadata."
        )

    sources = dataset.get("sources")
    if not isinstance(sources, list) or len(sources) != 1:
        raise ValueError(
            "The normalized dataset must contain exactly one source."
        )

    source = sources[0]
    if not isinstance(source, dict):
        raise ValueError("The normalized source must be a dictionary.")

    source_id = source.get("source_id")
    if not isinstance(source_id, str) or not source_id:
        raise ValueError(
            "The normalized source must have a non-empty source_id."
        )

    provenance = source.get("drive_provenance")
    if not isinstance(provenance, dict):
        raise ValueError(
            "The normalized source must contain Drive provenance."
        )

    if provenance.get("file_id") != current.drive_file_id:
        raise ValueError(
            "The normalized source's Drive file ID does not match "
            "the classified Drive file."
        )

    content_modified_time = _parse_content_modified_time(
        provenance.get("modified_time")
    )

    if content_modified_time is None or current.modified_time is None:
        raise ValueError(
            "Drive modification time is unknown; refusing to mark "
            "potentially stale content as indexed."
        )

    if content_modified_time != current.modified_time:
        raise ValueError(
            "The Drive file's modification time changed between discovery "
            "and content download; refusing to mark potentially stale "
            "content as indexed."
        )

    # Remember the previous source association before changing the Drive row.
    old_source_id = repository.get_drive_file_source_id(
        current.drive_file_id
    )

    # All writes are part of the caller-owned transaction.
    repository.save_normalized_dataset(dataset)

    repository.save_drive_file(
        {
            "drive_file_id": current.drive_file_id,
            "root_folder_id": current.root_folder_id,
            "source_id": source_id,
            "name": current.name,
            "mime_type": current.mime_type,
            "parent_ids": list(current.parent_ids),
            "modified_time": current.modified_time,
            "web_view_link": current.web_view_link,
            "indexed_modified_time": content_modified_time,
            "last_seen_run_id": sync_run_id,
            "last_seen_at": observed_at,
            "last_indexed_at": observed_at,
        }
    )

    # Remove old content only after the Drive row points to the new source.
    # The repository checks whether another Drive file still references it.
    if old_source_id is not None and old_source_id != source_id:
        repository.cleanup_source_if_unreferenced(old_source_id)


def _parse_content_modified_time(value: Any) -> datetime | None:
    """Parse an ISO timestamp and reject timestamps without a timezone."""
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError(
            "Drive provenance modified_time must be an ISO string or None."
        )

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            "Drive provenance contains an invalid modified_time."
        ) from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(
            "Drive provenance modified_time must include a timezone."
        )

    return parsed
