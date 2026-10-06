"""Persistence operations for the existing normalized data model."""

from __future__ import annotations

from collections.abc import Mapping
from collections import defaultdict
from datetime import date
from typing import Any

from psycopg import Connection
from psycopg.types.json import Jsonb

from .drive_sync import PreviousDriveFileState


class Repository:
    """Persist normalized sources, evidence, records, and date mentions.

    The caller owns the connection and transaction boundary. Methods do not
    commit or close the supplied connection.
    """

    def __init__(self, connection: Connection[Any]) -> None:
        self.connection = connection

    def save_source(self, source: Mapping[str, Any]) -> None:
        self.connection.execute(
            """
            INSERT INTO source
                (source_id, filename, file_type, sha256, size_bytes)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (source_id) DO UPDATE SET
                filename = EXCLUDED.filename,
                file_type = EXCLUDED.file_type,
                sha256 = EXCLUDED.sha256,
                size_bytes = EXCLUDED.size_bytes
            """,
            (
                source["source_id"],
                source["filename"],
                source["file_type"],
                source["sha256"],
                source["size_bytes"],
            ),
        )

    def save_evidence(self, evidence: Mapping[str, Any]) -> None:
        self.connection.execute(
            """
            INSERT INTO evidence
                (evidence_id, source_id, kind, page, sheet, row_number, cell,
                 cell_range, extracted_text, raw_values, header_context)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (evidence_id) DO UPDATE SET
                source_id = EXCLUDED.source_id,
                kind = EXCLUDED.kind,
                page = EXCLUDED.page,
                sheet = EXCLUDED.sheet,
                row_number = EXCLUDED.row_number,
                cell = EXCLUDED.cell,
                cell_range = EXCLUDED.cell_range,
                extracted_text = EXCLUDED.extracted_text,
                raw_values = EXCLUDED.raw_values,
                header_context = EXCLUDED.header_context
            """,
            (
                evidence["evidence_id"],
                evidence["source_id"],
                evidence["kind"],
                evidence.get("page"),
                evidence.get("sheet"),
                evidence.get("row"),
                evidence.get("cell"),
                evidence.get("cell_range"),
                evidence.get("extracted_text"),
                _jsonb(evidence.get("raw_values")),
                _jsonb(evidence.get("header_context")),
            ),
        )

    def save_record(self, record: Mapping[str, Any]) -> None:
        self.connection.execute(
            """
            INSERT INTO record (record_id, record_type, attributes)
            VALUES (%s, %s, %s)
            ON CONFLICT (record_id) DO UPDATE SET
                record_type = EXCLUDED.record_type,
                attributes = EXCLUDED.attributes
            """,
            (
                record["record_id"],
                record["record_type"],
                Jsonb(record["attributes"]),
            ),
        )

    def save_record_evidence(self, record_id: str, evidence_id: str) -> None:
        self.connection.execute(
            """
            INSERT INTO record_evidence (record_id, evidence_id)
            VALUES (%s, %s)
            ON CONFLICT (record_id, evidence_id) DO NOTHING
            """,
            (record_id, evidence_id),
        )

    def save_date_mention(
        self, mention: Mapping[str, Any], occurrence: int = 1
    ) -> None:
        """Persist one mention occurrence without duplicating a prior save."""
        normalized_iso = date.fromisoformat(str(mention["normalized_iso"]))
        self.connection.execute(
            """
            INSERT INTO date_mention
                (evidence_id, original_text, normalized_iso, date_role)
            SELECT %s, %s, %s, %s
            WHERE %s > (
                SELECT count(*)
                FROM date_mention
                WHERE evidence_id = %s
                  AND original_text = %s
                  AND normalized_iso = %s
                  AND date_role IS NOT DISTINCT FROM %s
            )
            """,
            (
                mention["evidence_id"],
                mention["original_text"],
                normalized_iso,
                mention.get("date_role"),
                occurrence,
                mention["evidence_id"],
                mention["original_text"],
                normalized_iso,
                mention.get("date_role"),
            ),
        )

    def save_drive_sync_run(self, sync_run: Mapping[str, Any]) -> None:
        """Persist one Drive sync-run state without owning the transaction."""
        self.connection.execute(
            """
            INSERT INTO drive_sync_run
                (sync_run_id, root_folder_id, started_at, completed_at, status)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (sync_run_id) DO UPDATE SET
                root_folder_id = EXCLUDED.root_folder_id,
                started_at = EXCLUDED.started_at,
                completed_at = EXCLUDED.completed_at,
                status = EXCLUDED.status
            """,
            (
                sync_run["sync_run_id"],
                sync_run["root_folder_id"],
                sync_run["started_at"],
                sync_run.get("completed_at"),
                sync_run["status"],
            ),
        )

    def save_drive_file(self, drive_file: Mapping[str, Any]) -> None:
        """Persist the latest state for one Drive object."""
        self.connection.execute(
            """
            INSERT INTO drive_file
                (drive_file_id, root_folder_id, source_id, name, mime_type,
                 parent_ids, modified_time, web_view_link,
                 indexed_modified_time, last_seen_run_id, last_seen_at,
                 last_indexed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (drive_file_id) DO UPDATE SET
                root_folder_id = EXCLUDED.root_folder_id,
                source_id = EXCLUDED.source_id,
                name = EXCLUDED.name,
                mime_type = EXCLUDED.mime_type,
                parent_ids = EXCLUDED.parent_ids,
                modified_time = EXCLUDED.modified_time,
                web_view_link = EXCLUDED.web_view_link,
                indexed_modified_time = EXCLUDED.indexed_modified_time,
                last_seen_run_id = EXCLUDED.last_seen_run_id,
                last_seen_at = EXCLUDED.last_seen_at,
                last_indexed_at = EXCLUDED.last_indexed_at
            """,
            (
                drive_file["drive_file_id"],
                drive_file["root_folder_id"],
                drive_file.get("source_id"),
                drive_file["name"],
                drive_file["mime_type"],
                Jsonb(drive_file["parent_ids"]),
                drive_file.get("modified_time"),
                drive_file.get("web_view_link"),
                drive_file.get("indexed_modified_time"),
                drive_file.get("last_seen_run_id"),
                drive_file["last_seen_at"],
                drive_file.get("last_indexed_at"),
            ),
        )

    def list_drive_file_states(
        self,
        root_folder_id: str,
    ) -> list[PreviousDriveFileState]:
        """Return prior Drive state for one configured root."""
        rows = self.connection.execute(
            """
            SELECT root_folder_id, drive_file_id, indexed_modified_time,
                   source_id, last_indexed_at
            FROM drive_file
            WHERE root_folder_id = %s
            ORDER BY drive_file_id
            """,
            (root_folder_id,),
        ).fetchall()
        return [
            PreviousDriveFileState(
                root_folder_id=row[0],
                drive_file_id=row[1],
                indexed_modified_time=row[2],
                source_id=row[3],
                last_indexed_at=row[4],
            )
            for row in rows
        ]

    def save_normalized_dataset(self, dataset: Mapping[str, Any]) -> None:
        """Persist one normalized dataset using the caller's transaction."""
        for source in dataset["sources"]:
            self.save_source(source)
        for evidence in dataset["evidence_units"]:
            self.save_evidence(evidence)
        for record in dataset["records"]:
            self.save_record(record)
            for reference in record["evidence_refs"]:
                self.save_record_evidence(
                    record["record_id"], reference["evidence_id"]
                )
        occurrences: defaultdict[tuple[Any, ...], int] = defaultdict(int)
        for mention in dataset["date_mentions"]:
            identity = (
                mention["evidence_id"],
                mention["original_text"],
                mention["normalized_iso"],
                mention.get("date_role"),
            )
            occurrences[identity] += 1
            self.save_date_mention(mention, occurrences[identity])


def _jsonb(value: Any) -> Jsonb[Any] | None:
    return None if value is None else Jsonb(value)
