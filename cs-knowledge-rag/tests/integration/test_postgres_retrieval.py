from __future__ import annotations

from pathlib import Path

import psycopg
import pytest

from cs_ingest.database import DatabaseConfigurationError, get_connection
from cs_ingest.postgres_retrieval import PostgresRetriever
from cs_ingest.retrieval import Retriever


ROOT = Path(__file__).parents[2]


def _connection():
    try:
        return get_connection()
    except DatabaseConfigurationError as exc:
        pytest.skip(str(exc))
    except (OSError, psycopg.Error) as exc:
        pytest.skip(f"PostgreSQL is unavailable: {type(exc).__name__}")


def _canonical(result):
    def records(items):
        normalized = []

        for item in items:
            copy = dict(item)
            copy["evidence_refs"] = sorted(
                copy.get("evidence_refs", []),
                key=lambda ref: ref["evidence_id"],
            )
            normalized.append(copy)

        return sorted(normalized, key=lambda item: item["record_id"])

    def evidence(items):
        return [
            {
                **item,
                "matched_fields": sorted(item.get("matched_fields", [])),
            }
            for item in sorted(items, key=lambda item: item["evidence_id"])
        ]

    return {
        "filters": result["filters"],
        "records": records(result["records"]),
        "evidence_units": evidence(result["evidence_units"]),
        "supporting_evidence_units": evidence(result["supporting_evidence_units"]),
        "matched_evidence_units": evidence(result["matched_evidence_units"]),
        "has_evidence": result["has_evidence"],
    }

@pytest.mark.parametrize(
    "filters",
    [
        {"date": "2026-07-18"},
        {
            "date": "2026-07-18",
            "record_type": "attendance",
            "person": "Dr. Reena Nair",
        },
        {"event_name": "C-START Industry Interaction"},
        {"date_role": "rescheduled_date"},
        {"keyword": "lab procurement"},
        {"date": "2026-07-18", "keyword": "something-that-does-not-exist"},
        {"date": "2099-01-10"},
    ],
)
def test_postgres_matches_in_memory_retriever(filters):
    normalized = ROOT / "output" / "sample_normalized.json"
    expected = Retriever.from_json(normalized).query(**filters)
    connection = _connection()
    try:
        actual = PostgresRetriever(connection).query(**filters)
    finally:
        connection.close()
    assert _canonical(actual) == _canonical(expected)


def test_postgres_retriever_rejects_unsupported_record_type():
    with pytest.raises(ValueError, match="record_type must be"):
        PostgresRetriever().query(record_type="unsupported")
