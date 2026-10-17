from datetime import datetime, timezone
from uuid import uuid4

import pytest

from cs_ingest.database import DatabaseConfigurationError, get_connection
from cs_ingest.drive_sync import (
    CurrentDriveInventoryItem,
    DriveSyncClassification,
    DriveSyncClassificationResult,
)
from cs_ingest.drive_sync_orchestration import persist_indexed_drive_file
from cs_ingest.repository import Repository


def _get_connection_or_skip():
    try:
        return get_connection()
    except DatabaseConfigurationError as exc:
        pytest.skip(str(exc))


def _make_dataset(source_id: str) -> dict:
    return {
        "sources": [
            {
                "source_id": source_id,
                "filename": "integration-lecture.pdf",
                "file_type": "pdf",
                "sha256": "a" * 64,
                "size_bytes": 128,
            }
        ],
        "evidence_units": [],
        "records": [],
        "date_mentions": [],
    }


def _make_classification(
    root_folder_id: str,
    drive_file_id: str,
    modified_at: datetime,
) -> DriveSyncClassificationResult:
    current = CurrentDriveInventoryItem(
        root_folder_id=root_folder_id,
        drive_file_id=drive_file_id,
        name="integration-lecture.pdf",
        mime_type="application/pdf",
        parent_ids=(root_folder_id,),
        modified_time=modified_at,
        web_view_link=None,
    )
    return DriveSyncClassificationResult(
        drive_file_id=drive_file_id,
        classification=DriveSyncClassification.NEW,
        current=current,
        previous=None,
    )


def _cleanup(
    connection,
    source_id: str,
    drive_file_id: str,
    run_id: str,
) -> None:
    connection.execute(
        "DELETE FROM drive_file WHERE drive_file_id = %s",
        (drive_file_id,),
    )
    connection.execute(
        "DELETE FROM source WHERE source_id = %s",
        (source_id,),
    )
    connection.execute(
        "DELETE FROM drive_sync_run WHERE sync_run_id = %s",
        (run_id,),
    )


def test_indexed_content_and_drive_state_are_atomic(monkeypatch) -> None:
    connection = _get_connection_or_skip()
    source_id = f"test-source-{uuid4()}"
    drive_file_id = f"test-drive-file-{uuid4()}"
    root_folder_id = f"test-root-{uuid4()}"
    run_id = f"test-run-{uuid4()}"
    modified_at = datetime(2026, 10, 15, 10, 30, tzinfo=timezone.utc)
    observed_at = datetime.now(timezone.utc)

    repository = Repository(connection)
    dataset = _make_dataset(source_id)
    dataset["sources"][0]["drive_provenance"] = {
        "file_id": drive_file_id,
        "modified_time": modified_at.isoformat(),
    }
    classification = _make_classification(
        root_folder_id,
        drive_file_id,
        modified_at,
    )

    try:
        # drive_file.last_seen_run_id references this sync run.
        with connection.transaction():
            repository.save_drive_sync_run(
                {
                    "sync_run_id": run_id,
                    "root_folder_id": root_folder_id,
                    "started_at": observed_at,
                    "completed_at": None,
                    "status": "running",
                }
            )

        # Simulate failure during the second write, after the normalized
        # dataset has already been written inside the same transaction.
        def fail_save_drive_file(_drive_file):
            raise RuntimeError("simulated drive state write failure")

        with monkeypatch.context() as patch:
            patch.setattr(
                repository,
                "save_drive_file",
                fail_save_drive_file,
            )

            with pytest.raises(
                RuntimeError,
                match="simulated drive state write failure",
            ):
                with connection.transaction():
                    persist_indexed_drive_file(
                        repository,
                        sync_run_id=run_id,
                        observed_at=observed_at,
                        classification=classification,
                        dataset=dataset,
                    )

        # Neither write should survive the failed transaction.
        source_row = connection.execute(
            "SELECT source_id FROM source WHERE source_id = %s",
            (source_id,),
        ).fetchone()
        drive_row = connection.execute(
            "SELECT source_id FROM drive_file WHERE drive_file_id = %s",
            (drive_file_id,),
        ).fetchone()

        assert source_row is None
        assert drive_row is None

        # Retry without the injected failure.
        with connection.transaction():
            persist_indexed_drive_file(
                repository,
                sync_run_id=run_id,
                observed_at=observed_at,
                classification=classification,
                dataset=dataset,
            )

        source_row = connection.execute(
            "SELECT source_id FROM source WHERE source_id = %s",
            (source_id,),
        ).fetchone()
        drive_row = connection.execute(
            """
            SELECT source_id, indexed_modified_time, last_indexed_at
            FROM drive_file
            WHERE drive_file_id = %s
            """,
            (drive_file_id,),
        ).fetchone()

        assert source_row == (source_id,)
        assert drive_row is not None
        assert drive_row[0] == source_id
        assert drive_row[1] == modified_at
        assert drive_row[2] == observed_at

    finally:
        try:
            with connection.transaction():
                _cleanup(
                    connection,
                    source_id,
                    drive_file_id,
                    run_id,
                )
        finally:
            connection.close()
