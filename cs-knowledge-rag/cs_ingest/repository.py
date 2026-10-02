"""Persistence operations for the existing normalized data model."""

from __future__ import annotations

from collections.abc import Mapping
from collections import defaultdict
from datetime import date
from typing import Any

from psycopg import Connection
from psycopg.types.json import Jsonb


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
