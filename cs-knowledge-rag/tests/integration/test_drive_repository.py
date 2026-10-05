from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import psycopg
import pytest

from cs_ingest.database import DatabaseConfigurationError, get_connection
from cs_ingest.repository import Repository


def _database_connection():
    try:
        return get_connection()
    except DatabaseConfigurationError as exc:
        pytest.skip(str(exc))
    except (OSError, psycopg.Error) as exc:
        pytest.skip(f"PostgreSQL is unavailable: {type(exc).__name__}")


def test_repository_persists_drive_sync_state():
    connection = _database_connection()
    suffix = uuid4().hex
    source_id = f"sha256:{uuid4().hex + uuid4().hex}"
    running_run_id = f"drive-run-running-{suffix}"
    failed_run_id = f"drive-run-failed-{suffix}"
    drive_file_id = f"drive-file-{suffix}"
    started_at = datetime(2026, 10, 3, tzinfo=timezone.utc)
    succeeded_at = datetime(2026, 10, 3, 0, 1, tzinfo=timezone.utc)
    failed_at = datetime(2026, 10, 3, 0, 2, tzinfo=timezone.utc)
    root_folder_id = f"configured-root-{suffix}"

    try:
        repository = Repository(connection)
        with connection.transaction():
            repository.save_source(
                {
                    "source_id": source_id,
                    "filename": f"drive-{suffix}.pdf",
                    "file_type": "pdf",
                    "sha256": source_id.removeprefix("sha256:"),
                    "size_bytes": 10,
                }
            )
            repository.save_drive_sync_run(
                {
                    "sync_run_id": running_run_id,
                    "root_folder_id": root_folder_id,
                    "started_at": started_at,
                    "completed_at": None,
                    "status": "running",
                }
            )
            repository.save_drive_sync_run(
                {
                    "sync_run_id": running_run_id,
                    "root_folder_id": root_folder_id,
                    "started_at": started_at,
                    "completed_at": succeeded_at,
                    "status": "succeeded",
                }
            )
            repository.save_drive_sync_run(
                {
                    "sync_run_id": failed_run_id,
                    "root_folder_id": root_folder_id,
                    "started_at": started_at,
                    "completed_at": None,
                    "status": "running",
                }
            )
            repository.save_drive_sync_run(
                {
                    "sync_run_id": failed_run_id,
                    "root_folder_id": root_folder_id,
                    "started_at": started_at,
                    "completed_at": failed_at,
                    "status": "failed",
                }
            )
            repository.save_drive_file(
                {
                    "drive_file_id": drive_file_id,
                    "root_folder_id": root_folder_id,
                    "source_id": source_id,
                    "name": "drive.pdf",
                    "mime_type": "application/pdf",
                    "parent_ids": [f"nested-folder-{suffix}", root_folder_id],
                    "modified_time": succeeded_at,
                    "web_view_link": "https://drive.google.com/file/drive-file",
                    "indexed_modified_time": succeeded_at,
                    "last_seen_run_id": running_run_id,
                    "last_seen_at": succeeded_at,
                    "last_indexed_at": succeeded_at,
                }
            )
            repository.save_drive_file(
                {
                    "drive_file_id": drive_file_id,
                    "root_folder_id": root_folder_id,
                    "source_id": None,
                    "name": "renamed-drive.pdf",
                    "mime_type": "application/pdf",
                    "parent_ids": [root_folder_id],
                    "modified_time": None,
                    "web_view_link": None,
                    "indexed_modified_time": None,
                    "last_seen_run_id": failed_run_id,
                    "last_seen_at": failed_at,
                    "last_indexed_at": None,
                }
            )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT root_folder_id, source_id, name, mime_type, parent_ids,
                       modified_time, web_view_link, indexed_modified_time,
                       last_seen_run_id, last_seen_at, last_indexed_at
                FROM drive_file
                WHERE drive_file_id = %s
                """,
                (drive_file_id,),
            )
            assert cursor.fetchone() == (
                root_folder_id,
                None,
                "renamed-drive.pdf",
                "application/pdf",
                [root_folder_id],
                None,
                None,
                None,
                failed_run_id,
                failed_at,
                None,
            )
            cursor.execute(
                """
                SELECT root_folder_id, status, started_at, completed_at
                FROM drive_sync_run
                WHERE sync_run_id = %s
                """,
                (running_run_id,),
            )
            assert cursor.fetchone() == (
                root_folder_id,
                "succeeded",
                started_at,
                succeeded_at,
            )
            cursor.execute(
                """
                SELECT root_folder_id, status, started_at, completed_at
                FROM drive_sync_run
                WHERE sync_run_id = %s
                """,
                (failed_run_id,),
            )
            assert cursor.fetchone() == (
                root_folder_id,
                "failed",
                started_at,
                failed_at,
            )

    finally:
        connection.rollback()
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM drive_file WHERE drive_file_id = %s",
                    (drive_file_id,),
                )
                cursor.execute(
                    "DELETE FROM drive_sync_run WHERE sync_run_id IN (%s, %s)",
                    (running_run_id, failed_run_id),
                )
                cursor.execute(
                    "DELETE FROM source WHERE source_id = %s",
                    (source_id,),
                )
        connection.close()


def test_repository_preserves_caller_transaction_ownership():
    connection = _database_connection()
    suffix = uuid4().hex
    sync_run_id = f"drive-run-rollback-{suffix}"
    drive_file_id = f"drive-file-rollback-{suffix}"
    started_at = datetime(2026, 10, 3, tzinfo=timezone.utc)

    try:
        repository = Repository(connection)
        with pytest.raises(RuntimeError, match="rollback test"):
            with connection.transaction():
                repository.save_drive_sync_run(
                    {
                        "sync_run_id": sync_run_id,
                        "root_folder_id": f"configured-root-{suffix}",
                        "started_at": started_at,
                        "completed_at": None,
                        "status": "running",
                    }
                )
                repository.save_drive_file(
                    {
                        "drive_file_id": drive_file_id,
                        "root_folder_id": f"configured-root-{suffix}",
                        "source_id": None,
                        "name": "rollback.pdf",
                        "mime_type": "application/pdf",
                        "parent_ids": [],
                        "modified_time": None,
                        "web_view_link": None,
                        "indexed_modified_time": None,
                        "last_seen_run_id": sync_run_id,
                        "last_seen_at": started_at,
                        "last_indexed_at": None,
                    }
                )
                assert connection.closed == 0
                raise RuntimeError("rollback test")

        assert connection.closed == 0
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM drive_sync_run WHERE sync_run_id = %s",
                (sync_run_id,),
            )
            assert cursor.fetchone() == (0,)
            cursor.execute(
                "SELECT count(*) FROM drive_file WHERE drive_file_id = %s",
                (drive_file_id,),
            )
            assert cursor.fetchone() == (0,)
    finally:
        connection.rollback()
        connection.close()
