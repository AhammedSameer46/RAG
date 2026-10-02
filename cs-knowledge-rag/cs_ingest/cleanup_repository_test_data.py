"""Explicit development cleanup for the confirmed repository integration rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from psycopg import Connection

from .database import get_connection


_TARGET_SOURCES = {
    "sha256:" + "1" * 64: "repository-aa34d0c960e94a9d8f9844367c93e40b.pdf",
    "sha256:" + "2" * 64: "repository-aa34d0c960e94a9d8f9844367c93e40b.xlsx",
}
_TARGET_RECORDS = {
    "meeting:repository-test-aa34d0c960e94a9d8f9844367c93e40b",
    "event:repository-test-aa34d0c960e94a9d8f9844367c93e40b",
}


def _counts(connection: Connection[Any]) -> dict[str, int]:
    with connection.cursor() as cursor:
        result = {}
        for table in ("source", "evidence", "record", "record_evidence", "date_mention"):
            cursor.execute(f"SELECT count(*) FROM {table}")
            result[table] = cursor.fetchone()[0]
    return result


def _fixture_counts(path: str | Path) -> dict[str, int]:
    dataset = json.loads(Path(path).read_text(encoding="utf-8"))
    return {
        "source": len(dataset["sources"]),
        "evidence": len(dataset["evidence_units"]),
        "record": len(dataset["records"]),
        "record_evidence": sum(
            len(record["evidence_refs"]) for record in dataset["records"]
        ),
        "date_mention": len(dataset["date_mentions"]),
    }


def _verify_targets(connection: Connection[Any]) -> tuple[set[str], set[str]]:
    target_source_ids = set(_TARGET_SOURCES)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT source_id, filename, sha256
            FROM source
            WHERE source_id = ANY(%s)
            """,
            (list(target_source_ids),),
        )
        sources = cursor.fetchall()
        if {
            source_id: filename for source_id, filename, _ in sources
        } != _TARGET_SOURCES:
            raise RuntimeError("Cleanup targets do not match the confirmed source rows.")
        if {sha256 for _, _, sha256 in sources} != {"1" * 64, "2" * 64}:
            raise RuntimeError("Cleanup target SHA-256 values do not match confirmation.")

        cursor.execute(
            """
            SELECT record_id
            FROM record_evidence
            WHERE evidence_id IN (
                SELECT evidence_id FROM evidence WHERE source_id = ANY(%s)
            )
            """,
            (list(target_source_ids),),
        )
        related_record_ids = {row[0] for row in cursor.fetchall()}
        if related_record_ids != _TARGET_RECORDS:
            raise RuntimeError(
                "Cleanup targets have unexpected record relationships: "
                + repr(sorted(related_record_ids))
            )

        cursor.execute(
            """
            SELECT record_id
            FROM record
            WHERE record_id = ANY(%s)
            """,
            (list(_TARGET_RECORDS),),
        )
        if {row[0] for row in cursor.fetchall()} != _TARGET_RECORDS:
            raise RuntimeError("Confirmed repository-test records are incomplete.")

        cursor.execute(
            """
            SELECT evidence_id
            FROM evidence
            WHERE source_id = ANY(%s)
            """,
            (list(target_source_ids),),
        )
        evidence_ids = {row[0] for row in cursor.fetchall()}
        expected_evidence_ids = {
            "sha256:" + "1" * 64 + ":pdf-page:1",
            "sha256:" + "2" * 64 + ":sheet:Attendance:row:2",
        }
        if evidence_ids != expected_evidence_ids:
            raise RuntimeError(
                "Cleanup targets have unexpected evidence: "
                + repr(sorted(evidence_ids))
            )
    return target_source_ids, evidence_ids


def cleanup(connection: Connection[Any], fixture_path: str | Path) -> tuple[
    dict[str, int], dict[str, int]
]:
    """Delete only confirmed repository-test rows in one transaction."""
    expected = _fixture_counts(fixture_path)
    before = _counts(connection)
    target_source_ids, evidence_ids = _verify_targets(connection)
    if any(before[key] < expected[key] for key in expected):
        raise RuntimeError(f"Database counts are below fixture counts: {before}")

    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM date_mention WHERE evidence_id = ANY(%s)",
                (list(evidence_ids),),
            )
            cursor.execute(
                "DELETE FROM record_evidence WHERE record_id = ANY(%s)",
                (list(_TARGET_RECORDS),),
            )
            cursor.execute(
                "DELETE FROM record WHERE record_id = ANY(%s)",
                (list(_TARGET_RECORDS),),
            )
            cursor.execute(
                "DELETE FROM evidence WHERE source_id = ANY(%s)",
                (list(target_source_ids),),
            )
            cursor.execute(
                "DELETE FROM source WHERE source_id = ANY(%s)",
                (list(target_source_ids),),
            )
        after = _counts(connection)
        if after != expected:
            raise RuntimeError(
                f"Cleanup would produce incorrect counts; transaction rolled back: "
                f"{after}"
            )
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM source WHERE source_id = ANY(%s)",
                (list(target_source_ids),),
            )
            if cursor.fetchone()[0] != 0:
                raise RuntimeError("Cleanup target sources still exist.")
            cursor.execute(
                "SELECT count(*) FROM evidence WHERE source_id = ANY(%s)",
                (list(target_source_ids),),
            )
            if cursor.fetchone()[0] != 0:
                raise RuntimeError("Cleanup target evidence still exists.")
            cursor.execute(
                "SELECT count(*) FROM record WHERE record_id = ANY(%s)",
                (list(_TARGET_RECORDS),),
            )
            if cursor.fetchone()[0] != 0:
                raise RuntimeError("Cleanup target records still exist.")

    after = _counts(connection)
    return before, after


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove only confirmed repository integration-test rows."
    )
    parser.add_argument(
        "fixture",
        type=Path,
        help="Normalized fixture used to verify production counts.",
    )
    args = parser.parse_args()
    connection = get_connection()
    try:
        before, after = cleanup(connection, args.fixture)
    finally:
        connection.close()
    print(f"Counts before cleanup: {before}")
    print(f"Counts after cleanup:  {after}")
    print("Repository-test cleanup completed.")


if __name__ == "__main__":
    main()
