from __future__ import annotations

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


def test_repository_persists_and_rolls_back_normalized_data():
    connection = _database_connection()
    suffix = uuid4().hex
    pdf_sha256 = uuid4().hex + uuid4().hex
    sheet_sha256 = uuid4().hex + uuid4().hex
    pdf_source_id = f"sha256:{pdf_sha256}"
    sheet_source_id = f"sha256:{sheet_sha256}"
    pdf_evidence_id = f"{pdf_source_id}:pdf-page:1"
    sheet_evidence_id = f"{sheet_source_id}:sheet:Attendance:row:2"
    meeting_id = f"meeting:repository-test-{suffix}"
    event_id = f"event:repository-test-{suffix}"
    date_mention = {
        "evidence_id": pdf_evidence_id,
        "original_text": "18 July 2026",
        "normalized_iso": "2026-07-18",
        "date_role": "meeting_date",
    }
    dataset = {
        "sources": [
            {
                "source_id": pdf_source_id,
                "filename": f"repository-{suffix}.pdf",
                "file_type": "pdf",
                "sha256": pdf_sha256,
                "size_bytes": 100,
            },
            {
                "source_id": sheet_source_id,
                "filename": f"repository-{suffix}.xlsx",
                "file_type": "xlsx",
                "sha256": sheet_sha256,
                "size_bytes": 200,
            },
        ],
        "evidence_units": [
            {
                "source_id": pdf_source_id,
                "evidence_id": pdf_evidence_id,
                "kind": "pdf_page",
                "page": 1,
                "extracted_text": "Meeting evidence",
            },
            {
                "source_id": sheet_source_id,
                "evidence_id": sheet_evidence_id,
                "kind": "worksheet_row",
                "sheet": "Attendance",
                "row": 2,
                "cell_range": "A2:C2",
                "raw_values": {"A": "Dr. Test", "B": "Present"},
                "header_context": {"A": "Faculty", "B": "Status"},
            },
        ],
        "records": [
            {
                "record_id": meeting_id,
                "record_type": "meeting",
                "attributes": {"meeting_date": "2026-07-18", "nested": {"count": 2}},
                "evidence_refs": [{"evidence_id": pdf_evidence_id}],
            },
            {
                "record_id": event_id,
                "record_type": "event",
                "attributes": {"name": "Repository Event", "participants": [1, 2]},
                "evidence_refs": [
                    {"evidence_id": pdf_evidence_id},
                    {"evidence_id": sheet_evidence_id},
                ],
            },
        ],
        "date_mentions": [date_mention],
    }

    try:
        repository = Repository(connection)
        with connection.transaction():
            repository.save_normalized_dataset(dataset)
            repository.save_normalized_dataset(dataset)

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM source WHERE source_id IN (%s, %s)",
                (pdf_source_id, sheet_source_id),
            )
            assert cursor.fetchone() == (2,)
            cursor.execute(
                "SELECT count(*) FROM evidence WHERE evidence_id IN (%s, %s)",
                (pdf_evidence_id, sheet_evidence_id),
            )
            assert cursor.fetchone() == (2,)
            cursor.execute(
                "SELECT page, extracted_text FROM evidence WHERE evidence_id = %s",
                (pdf_evidence_id,),
            )
            assert cursor.fetchone() == (1, "Meeting evidence")
            cursor.execute(
                "SELECT sheet, row_number, cell_range, raw_values->>'B' "
                "FROM evidence WHERE evidence_id = %s",
                (sheet_evidence_id,),
            )
            assert cursor.fetchone() == ("Attendance", 2, "A2:C2", "Present")
            cursor.execute(
                "SELECT count(*) FROM record_evidence WHERE evidence_id = %s",
                (pdf_evidence_id,),
            )
            assert cursor.fetchone() == (2,)
            cursor.execute(
                "SELECT attributes->'nested'->>'count' FROM record WHERE record_id = %s",
                (meeting_id,),
            )
            assert cursor.fetchone() == ("2",)
            cursor.execute(
                "SELECT date_role FROM date_mention WHERE evidence_id = %s",
                (pdf_evidence_id,),
            )
            assert cursor.fetchone() == ("meeting_date",)

        with pytest.raises(psycopg.Error):
            with connection.transaction():
                repository.save_record(
                    {
                        "record_id": f"invalid-{suffix}",
                        "record_type": "not-a-record-type",
                        "attributes": {},
                    }
                )

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM record WHERE record_id = %s",
                (f"invalid-{suffix}",),
            )
            assert cursor.fetchone() == (0,)
    finally:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM date_mention WHERE evidence_id IN (%s, %s)",
                    (pdf_evidence_id, sheet_evidence_id),
                )
                cursor.execute(
                    "DELETE FROM record_evidence WHERE record_id IN (%s, %s)",
                    (meeting_id, event_id),
                )
                cursor.execute(
                    "DELETE FROM record WHERE record_id IN (%s, %s)",
                    (meeting_id, event_id),
                )
                cursor.execute(
                    "DELETE FROM evidence WHERE evidence_id IN (%s, %s)",
                    (pdf_evidence_id, sheet_evidence_id),
                )
                cursor.execute(
                    "DELETE FROM source WHERE source_id IN (%s, %s)",
                    (pdf_source_id, sheet_source_id),
                )
        connection.close()
