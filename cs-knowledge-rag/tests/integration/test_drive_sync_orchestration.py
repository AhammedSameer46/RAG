from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import psycopg
import pytest

from cs_ingest.database import DatabaseConfigurationError, get_connection
from cs_ingest.drive_discovery import DriveFileMetadata
from cs_ingest.drive_sync_orchestration import (
    classify_drive_state,
    persist_successful_drive_state,
    record_drive_sync_failure,
    start_drive_sync_run,
)
from cs_ingest.repository import Repository


def _database_connection():
    try:
        return get_connection()
    except DatabaseConfigurationError as exc:
        pytest.skip(str(exc))
    except (OSError, psycopg.Error) as exc:
        pytest.skip(f"PostgreSQL is unavailable: {type(exc).__name__}")


def _file(file_id: str, root_folder_id: str) -> DriveFileMetadata:
    return DriveFileMetadata(
        file_id=file_id,
        name=f"{file_id}.pdf",
        mime_type="application/pdf",
        parent_ids=(root_folder_id,),
        modified_time="2026-10-06T10:00:00Z",
        web_view_link=None,
    )


def test_successful_drive_sync_state_transaction_is_durable():
    connection = _database_connection()
    suffix = uuid4().hex
    root_folder_id = f"orchestration-root-{suffix}"
    sync_run_id = f"orchestration-run-success-{suffix}"
    drive_file_id = f"orchestration-file-{suffix}"
    started_at = datetime(2026, 10, 6, 10, tzinfo=timezone.utc)
    observed_at = datetime(2026, 10, 6, 11, tzinfo=timezone.utc)

    try:
        repository = Repository(connection)
        with connection.transaction():
            start_drive_sync_run(
                repository,
                sync_run_id=sync_run_id,
                root_folder_id=root_folder_id,
                started_at=started_at,
            )

        inventory = [_file(drive_file_id, root_folder_id)]
        classifications = classify_drive_state(
            repository,
            root_folder_id=root_folder_id,
            inventory=inventory,
        )
        with connection.transaction():
            persist_successful_drive_state(
                repository,
                sync_run_id=sync_run_id,
                root_folder_id=root_folder_id,
                started_at=started_at,
                observed_at=observed_at,
                classifications=classifications,
            )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT status, completed_at
                FROM drive_sync_run
                WHERE sync_run_id = %s
                """,
                (sync_run_id,),
            )
            assert cursor.fetchone() == ("succeeded", observed_at)
            cursor.execute(
                """
                SELECT root_folder_id, last_seen_run_id
                FROM drive_file
                WHERE drive_file_id = %s
                """,
                (drive_file_id,),
            )
            assert cursor.fetchone() == (root_folder_id, sync_run_id)
    finally:
        connection.rollback()
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM drive_file WHERE drive_file_id = %s",
                    (drive_file_id,),
                )
                cursor.execute(
                    "DELETE FROM drive_sync_run WHERE sync_run_id = %s",
                    (sync_run_id,),
                )
        connection.close()


def test_failed_drive_sync_state_transaction_is_rolled_back_before_failure_status():
    connection = _database_connection()
    suffix = uuid4().hex
    root_folder_id = f"orchestration-root-{suffix}"
    sync_run_id = f"orchestration-run-failure-{suffix}"
    first_file_id = f"orchestration-file-first-{suffix}"
    second_file_id = f"orchestration-file-second-{suffix}"
    started_at = datetime(2026, 10, 6, 10, tzinfo=timezone.utc)
    observed_at = datetime(2026, 10, 6, 11, tzinfo=timezone.utc)

    try:
        repository = Repository(connection)
        with connection.transaction():
            start_drive_sync_run(
                repository,
                sync_run_id=sync_run_id,
                root_folder_id=root_folder_id,
                started_at=started_at,
            )

        classifications = classify_drive_state(
            repository,
            root_folder_id=root_folder_id,
            inventory=[
                _file(first_file_id, root_folder_id),
                _file(second_file_id, root_folder_id),
            ],
        )
        original_save = repository.save_drive_file
        calls = 0

        def fail_after_first(drive_file):
            nonlocal calls
            calls += 1
            original_save(drive_file)
            if calls == 1:
                raise RuntimeError("simulated phase 3 failure")

        repository.save_drive_file = fail_after_first
        with pytest.raises(RuntimeError, match="simulated phase 3 failure"):
            with connection.transaction():
                persist_successful_drive_state(
                    repository,
                    sync_run_id=sync_run_id,
                    root_folder_id=root_folder_id,
                    started_at=started_at,
                    observed_at=observed_at,
                    classifications=classifications,
                )

        with connection.transaction():
            record_drive_sync_failure(
                repository,
                sync_run_id=sync_run_id,
                root_folder_id=root_folder_id,
                started_at=started_at,
                completed_at=observed_at,
            )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT status, completed_at
                FROM drive_sync_run
                WHERE sync_run_id = %s
                """,
                (sync_run_id,),
            )
            assert cursor.fetchone() == ("failed", observed_at)
            cursor.execute(
                """
                SELECT count(*)
                FROM drive_file
                WHERE drive_file_id IN (%s, %s)
                """,
                (first_file_id, second_file_id),
            )
            assert cursor.fetchone() == (0,)
            cursor.execute(
                """
                SELECT count(*)
                FROM drive_sync_run
                WHERE sync_run_id = %s AND status = 'succeeded'
                """,
                (sync_run_id,),
            )
            assert cursor.fetchone() == (0,)
    finally:
        connection.rollback()
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM drive_file WHERE drive_file_id IN (%s, %s)",
                    (first_file_id, second_file_id),
                )
                cursor.execute(
                    "DELETE FROM drive_sync_run WHERE sync_run_id = %s",
                    (sync_run_id,),
                )
        connection.close()
