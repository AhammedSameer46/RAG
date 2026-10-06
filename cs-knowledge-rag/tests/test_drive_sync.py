from datetime import datetime, timezone

import pytest

from cs_ingest.drive_discovery import DriveFileMetadata
from cs_ingest.drive_sync import (
    DriveSyncClassification,
    DriveSyncClassificationResult,
    PreviousDriveFileState,
    classify_drive_inventory,
    select_content_sync_candidates,
)


ROOT = "root-a"


def _current(file_id: str, modified_time: str | None) -> DriveFileMetadata:
    return DriveFileMetadata(
        file_id=file_id,
        name=f"{file_id}.pdf",
        mime_type="application/pdf",
        parent_ids=(ROOT,),
        modified_time=modified_time,
        web_view_link=None,
    )


def _previous(
    file_id: str,
    modified_time: datetime | None,
    root_folder_id: str = ROOT,
) -> PreviousDriveFileState:
    return PreviousDriveFileState(root_folder_id, file_id, modified_time)


def test_new_file_is_classified():
    result = classify_drive_inventory(
        ROOT,
        [_current("new", "2026-10-03T10:00:00Z")],
        [],
        True,
    )

    assert [(item.drive_file_id, item.classification) for item in result] == [
        ("new", DriveSyncClassification.NEW)
    ]


def test_unchanged_file_is_classified():
    timestamp = datetime(2026, 10, 3, 10, tzinfo=timezone.utc)

    result = classify_drive_inventory(
        ROOT,
        [_current("same", "2026-10-03T10:00:00Z")],
        [_previous("same", timestamp)],
        True,
    )

    assert result[0].classification is DriveSyncClassification.UNCHANGED


def test_modified_file_is_classified():
    result = classify_drive_inventory(
        ROOT,
        [_current("changed", "2026-10-03T11:00:00Z")],
        [_previous(
            "changed",
            datetime(2026, 10, 3, 10, tzinfo=timezone.utc),
        )],
        True,
    )

    assert result[0].classification is DriveSyncClassification.MODIFIED


def test_deleted_file_requires_successful_inventory():
    result = classify_drive_inventory(
        ROOT,
        [],
        [_previous(
            "deleted",
            datetime(2026, 10, 3, 10, tzinfo=timezone.utc),
        )],
        True,
    )

    assert result[0].classification is DriveSyncClassification.DELETED


def test_failed_inventory_emits_no_deleted_files():
    result = classify_drive_inventory(
        ROOT,
        [],
        [_previous(
            "deleted",
            datetime(2026, 10, 3, 10, tzinfo=timezone.utc),
        )],
        False,
    )

    assert result == []


def test_previous_state_is_isolated_by_root():
    result = classify_drive_inventory(
        ROOT,
        [],
        [
            _previous(
                "other-root-file",
                datetime(2026, 10, 3, 10, tzinfo=timezone.utc),
                "root-b",
            )
        ],
        True,
    )

    assert result == []


def test_results_are_sorted_by_drive_file_id():
    result = classify_drive_inventory(
        ROOT,
        [
            _current("z-file", None),
            _current("a-file", None),
        ],
        [],
        False,
    )

    assert [item.drive_file_id for item in result] == [
        "a-file",
        "z-file",
    ]


def test_missing_timestamp_does_not_imply_modification():
    timestamp = datetime(2026, 10, 3, 10, tzinfo=timezone.utc)

    result = classify_drive_inventory(
        ROOT,
        [_current("missing", None)],
        [_previous("missing", timestamp)],
        True,
    )

    assert result[0].classification is DriveSyncClassification.UNCHANGED


def test_duplicate_current_drive_ids_are_rejected():
    current = [
        _current("duplicate", "2026-10-03T10:00:00Z"),
        _current("duplicate", "2026-10-03T11:00:00Z"),
    ]

    with pytest.raises(ValueError, match="duplicate file IDs"):
        classify_drive_inventory(
            ROOT,
            current,
            [],
            True,
        )


def test_naive_drive_timestamp_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        classify_drive_inventory(
            ROOT,
            [_current("naive", "2026-10-03T10:00:00")],
            [],
            True,
        )


def _classification(
    drive_file_id: str,
    classification: DriveSyncClassification,
):
    return DriveSyncClassificationResult(
        drive_file_id=drive_file_id,
        classification=classification,
        current=None,
        previous=None,
    )


def test_content_sync_candidates_select_new_file():
    result = select_content_sync_candidates(
        [_classification("new", DriveSyncClassification.NEW)]
    )

    assert [item.drive_file_id for item in result] == ["new"]


def test_content_sync_candidates_select_modified_file():
    result = select_content_sync_candidates(
        [_classification("changed", DriveSyncClassification.MODIFIED)]
    )

    assert [item.drive_file_id for item in result] == ["changed"]


def test_content_sync_candidates_skip_unchanged_and_deleted_files():
    result = select_content_sync_candidates(
        [
            _classification("same", DriveSyncClassification.UNCHANGED),
            _classification("gone", DriveSyncClassification.DELETED),
        ]
    )

    assert result == []


def test_content_sync_candidates_return_only_new_and_modified_files():
    result = select_content_sync_candidates(
        [
            _classification("same", DriveSyncClassification.UNCHANGED),
            _classification("changed", DriveSyncClassification.MODIFIED),
            _classification("gone", DriveSyncClassification.DELETED),
            _classification("new", DriveSyncClassification.NEW),
        ]
    )

    assert [item.drive_file_id for item in result] == ["changed", "new"]


def test_content_sync_candidates_are_sorted_deterministically():
    result = select_content_sync_candidates(
        [
            _classification("z-file", DriveSyncClassification.NEW),
            _classification("a-file", DriveSyncClassification.MODIFIED),
        ]
    )

    assert [item.drive_file_id for item in result] == ["a-file", "z-file"]


def test_content_sync_candidate_selection_does_not_change_classifications():
    classifications = [
        _classification("new", DriveSyncClassification.NEW),
        _classification("same", DriveSyncClassification.UNCHANGED),
    ]

    select_content_sync_candidates(classifications)

    assert [item.classification for item in classifications] == [
        DriveSyncClassification.NEW,
        DriveSyncClassification.UNCHANGED,
    ]
