
from __future__ import annotations

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


def _connection():
    try:
        return get_connection()
    except DatabaseConfigurationError as exc:
        pytest.skip(str(exc))


def _source(source_id: str) -> dict:
    digest = uuid4().hex + uuid4().hex
    return {
        "source_id": source_id,
        "filename": "cleanup-test.pdf",
        "file_type": "pdf",
        "sha256": digest,
        "size_bytes": 128,
    }


def _dataset(source: dict, file_id: str, modified_at: datetime) -> dict:
    normalized_source = {
        **source,
        "drive_provenance": {
            "file_id": file_id,
            "modified_time": modified_at.isoformat(),
        },
    }
    return {
        "sources": [normalized_source],
        "evidence_units": [],
        "records": [],
        "date_mentions": [],
    }


def _classification(
    root_id: str,
    file_id: str,
    modified_at: datetime,
    kind: DriveSyncClassification,
) -> DriveSyncClassificationResult:
    current = CurrentDriveInventoryItem(
        root_folder_id=root_id,
        drive_file_id=file_id,
        name="cleanup-test.pdf",
        mime_type="application/pdf",
        parent_ids=(root_id,),
        modified_time=modified_at,
        web_view_link=None,
    )
    return DriveSyncClassificationResult(
        drive_file_id=file_id,
        classification=kind,
        current=current,
        previous=None,
    )


def _seed_run(repository: Repository, run_id: str, root_id: str, now: datetime):
    repository.save_drive_sync_run(
        {
            "sync_run_id": run_id,
            "root_folder_id": root_id,
            "started_at": now,
            "completed_at": None,
            "status": "running",
        }
    )


def _seed_drive_file(
    repository: Repository,
    *,
    file_id: str,
    root_id: str,
    source_id: str,
    run_id: str,
    now: datetime,
) -> None:
    repository.save_drive_file(
        {
            "drive_file_id": file_id,
            "root_folder_id": root_id,
            "source_id": source_id,
            "name": "cleanup-test.pdf",
            "mime_type": "application/pdf",
            "parent_ids": [root_id],
            "modified_time": now,
            "web_view_link": None,
            "indexed_modified_time": now,
            "last_seen_run_id": run_id,
            "last_seen_at": now,
            "last_indexed_at": now,
        }
    )


def _cleanup(connection, file_ids, source_ids, run_ids):
    with connection.transaction():
        connection.execute(
            "DELETE FROM drive_file WHERE drive_file_id = ANY(%s)",
            (file_ids,),
        )
        connection.execute(
            "DELETE FROM source WHERE source_id = ANY(%s)",
            (source_ids,),
        )
        connection.execute(
            "DELETE FROM drive_sync_run WHERE sync_run_id = ANY(%s)",
            (run_ids,),
        )


def test_modified_file_removes_unreferenced_old_source():
    connection = _connection()
    repository = Repository(connection)
    suffix = uuid4().hex
    root_id = f"cleanup-root-{suffix}"
    file_id = f"cleanup-file-{suffix}"
    run_id = f"cleanup-run-{suffix}"
    old_id = f"cleanup-old-{suffix}"
    new_id = f"cleanup-new-{suffix}"
    now = datetime.now(timezone.utc)
    later = now.replace(microsecond=0)

    # Keep timestamps distinct so the classification represents a modification.
    from datetime import timedelta
    later = now + timedelta(seconds=10)

    try:
        old_source = _source(old_id)
        new_source = _source(new_id)

        with connection.transaction():
            repository.save_source(old_source)
            _seed_run(repository, run_id, root_id, now)
            _seed_drive_file(
                repository,
                file_id=file_id,
                root_id=root_id,
                source_id=old_id,
                run_id=run_id,
                now=now,
            )

        with connection.transaction():
            persist_indexed_drive_file(
                repository,
                sync_run_id=run_id,
                observed_at=later,
                classification=_classification(
                    root_id, file_id, later, DriveSyncClassification.MODIFIED
                ),
                dataset=_dataset(new_source, file_id, later),
            )

        assert connection.execute(
            "SELECT 1 FROM source WHERE source_id = %s", (old_id,)
        ).fetchone() is None

        assert connection.execute(
            "SELECT source_id FROM drive_file WHERE drive_file_id = %s",
            (file_id,),
        ).fetchone() == (new_id,)

    finally:
        connection.rollback()
        _cleanup(connection, [file_id], [old_id, new_id], [run_id])
        connection.close()


def test_shared_old_source_is_preserved():
    connection = _connection()
    repository = Repository(connection)
    suffix = uuid4().hex
    root_id = f"shared-root-{suffix}"
    file_id = f"shared-file-{suffix}"
    other_file_id = f"shared-other-{suffix}"
    run_id = f"shared-run-{suffix}"
    old_id = f"shared-old-{suffix}"
    new_id = f"shared-new-{suffix}"
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    later = now + timedelta(seconds=10)

    try:
        old_source = _source(old_id)
        new_source = _source(new_id)

        with connection.transaction():
            repository.save_source(old_source)
            _seed_run(repository, run_id, root_id, now)
            for current_file_id in (file_id, other_file_id):
                _seed_drive_file(
                    repository,
                    file_id=current_file_id,
                    root_id=root_id,
                    source_id=old_id,
                    run_id=run_id,
                    now=now,
                )

        with connection.transaction():
            persist_indexed_drive_file(
                repository,
                sync_run_id=run_id,
                observed_at=later,
                classification=_classification(
                    root_id, file_id, later, DriveSyncClassification.MODIFIED
                ),
                dataset=_dataset(new_source, file_id, later),
            )

        assert connection.execute(
            "SELECT 1 FROM source WHERE source_id = %s", (old_id,)
        ).fetchone() is not None

        assert connection.execute(
            "SELECT source_id FROM drive_file WHERE drive_file_id = %s",
            (other_file_id,),
        ).fetchone() == (old_id,)

    finally:
        connection.rollback()
        _cleanup(
            connection,
            [file_id, other_file_id],
            [old_id, new_id],
            [run_id],
        )
        connection.close()


def test_identical_source_is_not_cleaned_up():
    connection = _connection()
    repository = Repository(connection)
    suffix = uuid4().hex
    root_id = f"same-root-{suffix}"
    file_id = f"same-file-{suffix}"
    run_id = f"same-run-{suffix}"
    source_id = f"same-source-{suffix}"
    now = datetime.now(timezone.utc)

    try:
        source = _source(source_id)

        with connection.transaction():
            repository.save_source(source)
            _seed_run(repository, run_id, root_id, now)
            _seed_drive_file(
                repository,
                file_id=file_id,
                root_id=root_id,
                source_id=source_id,
                run_id=run_id,
                now=now,
            )

        with connection.transaction():
            persist_indexed_drive_file(
                repository,
                sync_run_id=run_id,
                observed_at=now,
                classification=_classification(
                    root_id, file_id, now, DriveSyncClassification.MODIFIED
                ),
                dataset=_dataset(source, file_id, now),
            )

        assert connection.execute(
            "SELECT source_id FROM drive_file WHERE drive_file_id = %s",
            (file_id,),
        ).fetchone() == (source_id,)

        assert connection.execute(
            "SELECT 1 FROM source WHERE source_id = %s", (source_id,)
        ).fetchone() is not None

    finally:
        connection.rollback()
        _cleanup(connection, [file_id], [source_id], [run_id])
        connection.close()


def test_cleanup_failure_rolls_back_entire_update(monkeypatch):
    connection = _connection()
    repository = Repository(connection)
    suffix = uuid4().hex
    root_id = f"rollback-root-{suffix}"
    file_id = f"rollback-file-{suffix}"
    run_id = f"rollback-run-{suffix}"
    old_id = f"rollback-old-{suffix}"
    new_id = f"rollback-new-{suffix}"
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    later = now + timedelta(seconds=10)

    try:
        old_source = _source(old_id)
        new_source = _source(new_id)

        with connection.transaction():
            repository.save_source(old_source)
            _seed_run(repository, run_id, root_id, now)
            _seed_drive_file(
                repository,
                file_id=file_id,
                root_id=root_id,
                source_id=old_id,
                run_id=run_id,
                now=now,
            )

        original_cleanup = repository.cleanup_source_if_unreferenced

        def cleanup_then_fail(source_id: str) -> bool:
            original_cleanup(source_id)
            raise RuntimeError("simulated cleanup failure")

        monkeypatch.setattr(
            repository,
            "cleanup_source_if_unreferenced",
            cleanup_then_fail,
        )

        with pytest.raises(RuntimeError, match="simulated cleanup failure"):
            with connection.transaction():
                persist_indexed_drive_file(
                    repository,
                    sync_run_id=run_id,
                    observed_at=later,
                    classification=_classification(
                        root_id,
                        file_id,
                        later,
                        DriveSyncClassification.MODIFIED,
                    ),
                    dataset=_dataset(new_source, file_id, later),
                )

        # The transaction must restore the old association and source.
        assert connection.execute(
            "SELECT source_id FROM drive_file WHERE drive_file_id = %s",
            (file_id,),
        ).fetchone() == (old_id,)

        assert connection.execute(
            "SELECT 1 FROM source WHERE source_id = %s", (old_id,)
        ).fetchone() is not None

        assert connection.execute(
            "SELECT 1 FROM source WHERE source_id = %s", (new_id,)
        ).fetchone() is None

    finally:
        connection.rollback()
        _cleanup(connection, [file_id], [old_id, new_id], [run_id])
        connection.close()
