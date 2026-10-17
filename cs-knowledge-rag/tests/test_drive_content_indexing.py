
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from cs_ingest.drive_sync import (
    CurrentDriveInventoryItem,
    DriveSyncClassification,
    DriveSyncClassificationResult,
)
from cs_ingest.drive_sync_orchestration import persist_indexed_drive_file


MODIFIED_AT = datetime(2026, 10, 15, 10, 30, tzinfo=timezone.utc)
OBSERVED_AT = datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)


def _classification(
    status: DriveSyncClassification = DriveSyncClassification.NEW,
) -> DriveSyncClassificationResult:
    current = CurrentDriveInventoryItem(
        root_folder_id="root-123",
        drive_file_id="file-123",
        name="lecture.pdf",
        mime_type="application/pdf",
        parent_ids=("root-123",),
        modified_time=MODIFIED_AT,
        web_view_link="https://drive.google.com/file/d/file-123",
    )
    return DriveSyncClassificationResult(
        drive_file_id="file-123",
        classification=status,
        current=current,
        previous=None,
    )


def _dataset(
    *,
    file_id: str = "file-123",
    modified_time: str | None = "2026-10-15T10:30:00Z",
) -> dict:
    return {
        "sources": [
            {
                "source_id": "source-123",
                "filename": "lecture.pdf",
                "file_type": "pdf",
                "sha256": "abc123",
                "size_bytes": 100,
                "drive_provenance": {
                    "file_id": file_id,
                    "modified_time": modified_time,
                },
            }
        ],
        "evidence": [],
        "records": [],
        "date_mentions": [],
    }


def test_persists_normalized_content_and_indexed_drive_state() -> None:
    repository = Mock()
    dataset = _dataset()

    persist_indexed_drive_file(
        repository,
        sync_run_id="run-123",
        observed_at=OBSERVED_AT,
        classification=_classification(),
        dataset=dataset,
    )

    repository.save_normalized_dataset.assert_called_once_with(dataset)
    repository.save_drive_file.assert_called_once_with(
        {
            "drive_file_id": "file-123",
            "root_folder_id": "root-123",
            "source_id": "source-123",
            "name": "lecture.pdf",
            "mime_type": "application/pdf",
            "parent_ids": ["root-123"],
            "modified_time": MODIFIED_AT,
            "web_view_link": "https://drive.google.com/file/d/file-123",
            "indexed_modified_time": MODIFIED_AT,
            "last_seen_run_id": "run-123",
            "last_seen_at": OBSERVED_AT,
            "last_indexed_at": OBSERVED_AT,
        }
    )
    repository.save_normalized_dataset.assert_called_once()
    repository.save_drive_file.assert_called_once()


@pytest.mark.parametrize(
    "status",
    [
        DriveSyncClassification.UNCHANGED,
        DriveSyncClassification.DELETED,
    ],
)
def test_rejects_files_that_are_not_content_sync_candidates(
    status: DriveSyncClassification,
) -> None:
    repository = Mock()

    with pytest.raises(ValueError, match="Only NEW or MODIFIED"):
        persist_indexed_drive_file(
            repository,
            sync_run_id="run-123",
            observed_at=OBSERVED_AT,
            classification=_classification(status),
            dataset=_dataset(),
        )

    repository.save_normalized_dataset.assert_not_called()
    repository.save_drive_file.assert_not_called()


def test_rejects_dataset_with_multiple_sources() -> None:
    repository = Mock()
    dataset = _dataset()
    dataset["sources"].append(dict(dataset["sources"][0]))

    with pytest.raises(ValueError, match="exactly one source"):
        persist_indexed_drive_file(
            repository,
            sync_run_id="run-123",
            observed_at=OBSERVED_AT,
            classification=_classification(),
            dataset=dataset,
        )

    repository.save_normalized_dataset.assert_not_called()
    repository.save_drive_file.assert_not_called()


def test_rejects_mismatched_drive_file_id() -> None:
    repository = Mock()

    with pytest.raises(ValueError, match="file ID does not match"):
        persist_indexed_drive_file(
            repository,
            sync_run_id="run-123",
            observed_at=OBSERVED_AT,
            classification=_classification(),
            dataset=_dataset(file_id="another-file"),
        )

    repository.save_normalized_dataset.assert_not_called()
    repository.save_drive_file.assert_not_called()


def test_rejects_content_if_drive_modified_time_changed() -> None:
    repository = Mock()

    with pytest.raises(ValueError, match="modification time changed"):
        persist_indexed_drive_file(
            repository,
            sync_run_id="run-123",
            observed_at=OBSERVED_AT,
            classification=_classification(),
            dataset=_dataset(modified_time="2026-10-15T11:00:00Z"),
        )

    repository.save_normalized_dataset.assert_not_called()
    repository.save_drive_file.assert_not_called()


def test_rejects_timezone_naive_content_timestamp() -> None:
    repository = Mock()

    with pytest.raises(ValueError, match="must include a timezone"):
        persist_indexed_drive_file(
            repository,
            sync_run_id="run-123",
            observed_at=OBSERVED_AT,
            classification=_classification(),
            dataset=_dataset(modified_time="2026-10-15T10:30:00"),
        )

    repository.save_normalized_dataset.assert_not_called()
    repository.save_drive_file.assert_not_called()



def test_rejects_content_when_modified_time_is_unknown() -> None:
    repository = Mock()

    with pytest.raises(ValueError, match="modification time is unknown"):
        persist_indexed_drive_file(
            repository,
            sync_run_id="run-123",
            observed_at=OBSERVED_AT,
            classification=_classification(),
            dataset=_dataset(modified_time=None),
        )

    repository.save_normalized_dataset.assert_not_called()
    repository.save_drive_file.assert_not_called()
