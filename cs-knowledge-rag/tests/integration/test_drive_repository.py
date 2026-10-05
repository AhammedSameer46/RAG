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
    sync_run_id = f"drive-run-{suffix}"
    drive_file_id = f"drive-file-{suffix}"
    started_at = datetime(2026, 10, 3, tzinfo=timezone.utc)
    completed_at = datetime(2026, 10, 3, 0, 1, tzinfo=timezone.utc)

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
                    "sync_run_id": sync_run_id,
                    "root_folder_id": "configured-root",
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "status": "succeeded",
                }
            )
            repository.save_drive_file(
                {
                    "drive_file_id": drive_file_id,
                    "root_folder_id": "configured-root",
                    "source_id": source_id,
                    "name": "drive.pdf",
                    "mime_type": "application/pdf",
                    "parent_ids": ["nested-folder", "configured-root"],
                    "modified_time": completed_at,
                    "web_view_link": "https://drive.google.com/file/drive-file",
                    "indexed_modified_time": completed_at,
                    "last_seen_run_id": sync_run_id,
                    "last_seen_at": completed_at,
                    "last_indexed_at": completed_at,
                }
            )
            repository.save_drive_file(
                {
                    "drive_file_id": drive_file_id,
                    "root_folder_id": "configured-root",
                    "source_id": source_id,
                    "name": "renamed-drive.pdf",
                    "mime_type": "application/pdf",
                    "parent_ids": ["configured-root"],
                    "modified_time": completed_at,
                    "web_view_link": None,
                    "indexed_modified_time": completed_at,
                    "last_seen_run_id": sync_run_id,
                    "last_seen_at": completed_at,
                    "last_indexed_at": completed_at,
                }
            )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT root_folder_id, source_id, name, parent_ids,
                       last_seen_run_id
                FROM drive_file
                WHERE drive_file_id = %s
                """,
                (drive_file_id,),
            )
            assert cursor.fetchone() == (
                "configured-root",
                source_id,
                "renamed-drive.pdf",
                ["configured-root"],
                sync_run_id,
            )
            cursor.execute(
                """
                SELECT root_folder_id, status, completed_at
                FROM drive_sync_run
                WHERE sync_run_id = %s
                """,
                (sync_run_id,),
            )
            assert cursor.fetchone() == (
                "configured-root",
                "succeeded",
                completed_at,
            )
    finally:
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
                cursor.execute(
                    "DELETE FROM source WHERE source_id = %s",
                    (source_id,),
                )
        connection.close()
