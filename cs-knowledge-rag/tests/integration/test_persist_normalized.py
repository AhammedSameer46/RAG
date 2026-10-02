from __future__ import annotations

from pathlib import Path

import psycopg
import pytest

from cs_ingest.database import DatabaseConfigurationError, get_connection
from cs_ingest.persist import load_normalized_dataset, persist_dataset


ROOT = Path(__file__).parents[2]


class _RollbackTest(Exception):
    pass


def _database_connection():
    try:
        return get_connection()
    except DatabaseConfigurationError as exc:
        pytest.skip(str(exc))
    except (OSError, psycopg.Error) as exc:
        pytest.skip(f"PostgreSQL is unavailable: {type(exc).__name__}")


def _counts(connection, dataset):
    source_ids = [item["source_id"] for item in dataset["sources"]]
    evidence_ids = [item["evidence_id"] for item in dataset["evidence_units"]]
    record_ids = [item["record_id"] for item in dataset["records"]]
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM source WHERE source_id = ANY(%s)", (source_ids,)
        )
        sources = cursor.fetchone()[0]
        cursor.execute(
            "SELECT count(*) FROM evidence WHERE evidence_id = ANY(%s)",
            (evidence_ids,),
        )
        evidence = cursor.fetchone()[0]
        cursor.execute(
            "SELECT count(*) FROM record WHERE record_id = ANY(%s)", (record_ids,)
        )
        records = cursor.fetchone()[0]
        cursor.execute(
            """
            SELECT count(*) FROM record_evidence
            WHERE record_id = ANY(%s) AND evidence_id = ANY(%s)
            """,
            (record_ids, evidence_ids),
        )
        relationships = cursor.fetchone()[0]
        cursor.execute(
            "SELECT count(*) FROM date_mention WHERE evidence_id = ANY(%s)",
            (evidence_ids,),
        )
        date_mentions = cursor.fetchone()[0]
    return sources, evidence, records, relationships, date_mentions


def test_persist_normalized_fixture_is_faithful_and_idempotent():
    dataset = load_normalized_dataset(ROOT / "output" / "sample_normalized.json")
    expected = (
        len(dataset["sources"]),
        len(dataset["evidence_units"]),
        len(dataset["records"]),
        sum(len(record["evidence_refs"]) for record in dataset["records"]),
        len(dataset["date_mentions"]),
    )
    connection = _database_connection()
    try:
        try:
            with connection.transaction():
                persist_dataset(dataset, connection)
                first_counts = _counts(connection, dataset)
                persist_dataset(dataset, connection)
                second_counts = _counts(connection, dataset)
                assert first_counts == expected
                assert second_counts == expected

                pdf = next(
                    item for item in dataset["evidence_units"] if item["kind"] == "pdf_page"
                )
                sheet = next(
                    item
                    for item in dataset["evidence_units"]
                    if item["kind"] == "worksheet_row"
                )
                first_record = dataset["records"][0]
                mention = dataset["date_mentions"][0]
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT source_id, filename FROM source WHERE source_id = %s",
                        (pdf["source_id"],),
                    )
                    assert cursor.fetchone() == (
                        pdf["source_id"],
                        next(
                            source["filename"]
                            for source in dataset["sources"]
                            if source["source_id"] == pdf["source_id"]
                        ),
                    )
                    cursor.execute(
                        "SELECT kind, page, extracted_text FROM evidence "
                        "WHERE evidence_id = %s",
                        (pdf["evidence_id"],),
                    )
                    assert cursor.fetchone() == (
                        pdf["kind"],
                        pdf["page"],
                        pdf["extracted_text"],
                    )
                    cursor.execute(
                        "SELECT kind, sheet, row_number, cell_range, raw_values, "
                        "header_context FROM evidence WHERE evidence_id = %s",
                        (sheet["evidence_id"],),
                    )
                    row = cursor.fetchone()
                    assert row[:4] == (
                        sheet["kind"],
                        sheet["sheet"],
                        sheet["row"],
                        sheet["cell_range"],
                    )
                    assert row[4] == sheet["raw_values"]
                    assert row[5] == sheet["header_context"]
                    cursor.execute(
                        "SELECT record_type, attributes FROM record WHERE record_id = %s",
                        (first_record["record_id"],),
                    )
                    assert cursor.fetchone() == (
                        first_record["record_type"],
                        first_record["attributes"],
                    )
                    cursor.execute(
                        "SELECT original_text, normalized_iso, date_role, evidence_id "
                        "FROM date_mention WHERE evidence_id = %s "
                        "AND original_text = %s",
                        (mention["evidence_id"], mention["original_text"]),
                    )
                    persisted_mention = cursor.fetchone()
                    assert str(persisted_mention[1]) == mention["normalized_iso"]
                    assert persisted_mention[0] == mention["original_text"]
                    assert persisted_mention[2] == mention["date_role"]
                    assert persisted_mention[3] == mention["evidence_id"]

                raise _RollbackTest
        except _RollbackTest:
            pass

        with pytest.raises(psycopg.Error):
            persist_dataset(
                {
                    **dataset,
                    "records": [
                        {
                            "record_id": "rollback-invalid",
                            "record_type": "invalid",
                            "attributes": {},
                            "evidence_refs": [],
                        }
                    ],
                },
                connection,
            )
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM record WHERE record_id = %s",
                ("rollback-invalid",),
            )
            assert cursor.fetchone() == (0,)
    finally:
        connection.close()
