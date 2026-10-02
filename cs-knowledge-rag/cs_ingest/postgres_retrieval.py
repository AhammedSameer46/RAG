"""PostgreSQL-backed retrieval with parity to the in-memory Retriever."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from psycopg import Connection

from .database import get_connection
from .retrieval import _contains_keyword, _flatten_text


class PostgresRetriever:
    """Retrieve normalized records and provenance from PostgreSQL."""

    def __init__(self, connection: Connection[Any] | None = None) -> None:
        self.connection = connection

    def query(
        self,
        *,
        date: str | None = None,
        record_type: str | None = None,
        person: str | None = None,
        event_name: str | None = None,
        date_role: str | None = None,
        keyword: str | None = None,
    ) -> dict[str, Any]:
        if record_type is not None and record_type not in {
            "meeting",
            "event",
            "attendance",
        }:
            raise ValueError("record_type must be meeting, event, or attendance")

        connection = self.connection or get_connection()
        close_connection = self.connection is None
        try:
            records = self._records(
                connection, date, record_type, person, event_name, date_role
            )
            matching_records = []
            for record in records:
                matched_fields: list[str] = []
                if keyword is not None and not _contains_keyword(
                    _flatten_text(record), keyword
                ):
                    continue
                if date is not None:
                    matched_fields.append("date")
                if date_role is not None and date is not None:
                    matched_fields.append("date_role")
                if person is not None:
                    matched_fields.append("person")
                if event_name is not None:
                    matched_fields.append("event_name")
                if keyword is not None:
                    matched_fields.append("record_keyword")
                if not matched_fields:
                    matched_fields.append("record")
                matching_records.append(
                    {**deepcopy(record), "matched_fields": matched_fields}
                )

            supporting_ids = {
                reference["evidence_id"]
                for record in matching_records
                for reference in record["evidence_refs"]
            }
            keyword_ids = set()
            if keyword is not None:
                keyword_ids = {
                    item["evidence_id"]
                    for item in self._evidence(connection)
                    if _contains_keyword(_flatten_text(item), keyword)
                }

            mention_ids = set()
            if date_role is not None:
                mention_ids = self._date_mention_ids(connection, date, date_role)
            elif date is not None and not (
                record_type or person or event_name or keyword
            ):
                mention_ids = self._date_mention_ids(connection, date, None)

            expanded_ids = supporting_ids | keyword_ids | mention_ids
            evidence_by_id = {
                item["evidence_id"]: item
                for item in self._evidence(connection, expanded_ids)
            }
            supporting = []
            matched = []
            all_evidence = []
            for evidence_id in sorted(expanded_ids):
                item = deepcopy(evidence_by_id[evidence_id])
                fields = []
                if evidence_id in supporting_ids:
                    fields.append("record_reference")
                if evidence_id in keyword_ids:
                    fields.append("keyword")
                if evidence_id in mention_ids:
                    fields.append("date_role" if date_role else "date_mention")
                item["matched_fields"] = fields
                all_evidence.append(item)
                if evidence_id in supporting_ids:
                    supporting.append(deepcopy(item))
                if evidence_id in keyword_ids or evidence_id in mention_ids:
                    matched.append(deepcopy(item))

            return {
                "filters": {
                    "date": date,
                    "record_type": record_type,
                    "person": person,
                    "event_name": event_name,
                    "date_role": date_role,
                    "keyword": keyword,
                },
                "records": matching_records,
                "evidence_units": all_evidence,
                "supporting_evidence_units": supporting,
                "matched_evidence_units": matched,
                "has_evidence": bool(all_evidence),
            }
        finally:
            if close_connection:
                connection.close()

    @staticmethod
    def _records(
        connection: Connection[Any],
        requested_date: str | None,
        record_type: str | None,
        person: str | None,
        event_name: str | None,
        date_role: str | None,
    ) -> list[dict[str, Any]]:
        conditions = []
        parameters: list[Any] = []
        if record_type is not None:
            conditions.append("record_type = %s")
            parameters.append(record_type)
        if requested_date is not None:
            conditions.append(
                """
                (
                    (record_type IN ('meeting', 'attendance')
                     AND attributes ->> 'meeting_date' = %s)
                    OR
                    (record_type = 'event'
                     AND (attributes ->> 'start_date' = %s
                          OR attributes ->> 'end_date' = %s))
                )
                """
            )
            parameters.extend([requested_date, requested_date, requested_date])
        if date_role is not None:
            conditions.append(
                """
                (
                    (record_type IN ('meeting', 'attendance')
                     AND %s = 'meeting_date'
                     AND attributes ->> 'meeting_date' IS NOT NULL)
                    OR
                    (record_type = 'event' AND
                     ((%s = 'event_date' AND
                       (attributes ->> 'start_date' IS NOT NULL
                        OR attributes ->> 'end_date' IS NOT NULL))
                      OR (%s = 'start_date' AND
                          attributes ->> 'start_date' IS NOT NULL)
                      OR (%s = 'end_date' AND
                          attributes ->> 'end_date' IS NOT NULL)))
                )
                """
            )
            parameters.extend([date_role] * 4)
        if person is not None:
            conditions.append("record_type = 'attendance' AND attributes ->> 'person' = %s")
            parameters.append(person)
        if event_name is not None:
            conditions.append("record_type = 'event' AND attributes ->> 'name' = %s")
            parameters.append(event_name)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT record_id, record_type, attributes
                FROM record
                {where}
                ORDER BY record_id
                """,
                parameters,
            )
            rows = cursor.fetchall()
        result = []
        for record_id, kind, attributes in rows:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT evidence_id
                    FROM record_evidence
                    WHERE record_id = %s
                    ORDER BY evidence_id
                    """,
                    (record_id,),
                )
                refs = [{"evidence_id": row[0]} for row in cursor.fetchall()]
            result.append(
                {
                    "record_id": record_id,
                    "record_type": kind,
                    "attributes": attributes,
                    "evidence_refs": refs,
                }
            )
        return result

    @staticmethod
    def _date_mention_ids(
        connection: Connection[Any], requested_date: str | None, role: str | None
    ) -> set[str]:
        conditions = []
        parameters: list[Any] = []
        if requested_date is not None:
            conditions.append("normalized_iso = %s")
            parameters.append(requested_date)
        if role is not None:
            conditions.append("date_role = %s")
            parameters.append(role)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT DISTINCT evidence_id FROM date_mention {where}",
                parameters,
            )
            return {row[0] for row in cursor.fetchall()}

    @staticmethod
    def _evidence(
        connection: Connection[Any], evidence_ids: set[str] | None = None
    ) -> list[dict[str, Any]]:
        parameters: list[Any] = []
        where = ""
        if evidence_ids is not None:
            if not evidence_ids:
                return []
            where = "WHERE evidence.evidence_id = ANY(%s)"
            parameters.append(list(evidence_ids))
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT evidence.evidence_id, evidence.source_id, source.filename,
                       evidence.kind, evidence.page, evidence.sheet,
                       evidence.row_number, evidence.cell, evidence.cell_range,
                       evidence.extracted_text, evidence.raw_values,
                       evidence.header_context
                FROM evidence
                JOIN source ON source.source_id = evidence.source_id
                {where}
                ORDER BY evidence.evidence_id
                """,
                parameters,
            )
            rows = cursor.fetchall()
        fields = (
            "evidence_id",
            "source_id",
            "filename",
            "kind",
            "page",
            "sheet",
            "row",
            "cell",
            "cell_range",
            "extracted_text",
            "raw_values",
            "header_context",
        )
        return [
            {key: value for key, value in zip(fields, row) if value is not None}
            for row in rows
        ]
