"""Explicit development cleanup for the confirmed repository integration rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from psycopg import Connection

from .database import get_connection


_TARGET_SOURCES = {
    "sha256:e7ab7c42d6d24536831ff10e343ee73adc93d690e67442fda10ccca320ead70f": (
        "repository-4a79ecc5670a40318d6e747fd8d887ce.pdf"
    ),
    "sha256:cb01276a468f445bbb4c23c563875ae62808c1f5098e4fe8a28d64dfe4e748f9": (
        "repository-b8601dea996140358c371e6c0b48ac78.pdf"
    ),
    "sha256:05000fa0a2dc49e9be5ce0058d54e0e74ea88677b69e404fa2b2a511f6da38bf": (
        "repository-4a79ecc5670a40318d6e747fd8d887ce.xlsx"
    ),
    "sha256:738d3c8e21b8475ebcf7de75c1047f467fa67c86a7bd41109c833fbc375fb46a": (
        "repository-b8601dea996140358c371e6c0b48ac78.xlsx"
    ),
}
_TARGET_RECORDS = {
    "event:repository-test-4a79ecc5670a40318d6e747fd8d887ce",
    "meeting:repository-test-4a79ecc5670a40318d6e747fd8d887ce",
    "event:repository-test-b8601dea996140358c371e6c0b48ac78",
    "meeting:repository-test-b8601dea996140358c371e6c0b48ac78",
}
_TARGET_SHA256 = {
    "e7ab7c42d6d24536831ff10e343ee73adc93d690e67442fda10ccca320ead70f",
    "cb01276a468f445bbb4c23c563875ae62808c1f5098e4fe8a28d64dfe4e748f9",
    "05000fa0a2dc49e9be5ce0058d54e0e74ea88677b69e404fa2b2a511f6da38bf",
    "738d3c8e21b8475ebcf7de75c1047f467fa67c86a7bd41109c833fbc375fb46a",
}
_TARGET_EVIDENCE_IDS = {
    "sha256:e7ab7c42d6d24536831ff10e343ee73adc93d690e67442fda10ccca320ead70f:pdf-page:1",
    "sha256:cb01276a468f445bbb4c23c563875ae62808c1f5098e4fe8a28d64dfe4e748f9:pdf-page:1",
    "sha256:05000fa0a2dc49e9be5ce0058d54e0e74ea88677b69e404fa2b2a511f6da38bf:sheet:Attendance:row:2",
    "sha256:738d3c8e21b8475ebcf7de75c1047f467fa67c86a7bd41109c833fbc375fb46a:sheet:Attendance:row:2",
}


def _counts(connection: Connection[Any]) -> dict[str, int]:
    with connection.cursor() as cursor:
        result = {}
        for table in ("source", "evidence", "record", "record_evidence", "date_mention"):
            cursor.execute(f"SELECT count(*) FROM {table}")
            result[table] = cursor.fetchone()[0]
    return result


def _fixture_source_ids(path: str | Path) -> set[str]:
    dataset = json.loads(Path(path).read_text(encoding="utf-8"))
    source_ids = {source["source_id"] for source in dataset["sources"]}
    if len(source_ids) != 5:
        raise RuntimeError(
            f"Expected five protected sample sources, found {len(source_ids)}."
        )
    return source_ids


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
        if {sha256 for _, _, sha256 in sources} != _TARGET_SHA256:
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
            SELECT evidence_id, source_id
            FROM evidence
            WHERE evidence_id = ANY(%s)
            """,
            (list(_TARGET_EVIDENCE_IDS),),
        )
        evidence_rows = cursor.fetchall()
        evidence_ids = {row[0] for row in evidence_rows}
        if evidence_ids != _TARGET_EVIDENCE_IDS:
            raise RuntimeError(
                "Cleanup targets have unexpected evidence: "
                + repr(sorted(evidence_ids))
            )
        if any(
            source_id not in target_source_ids
            or not evidence_id.startswith(source_id + ":")
            for evidence_id, source_id in evidence_rows
        ):
            raise RuntimeError("Cleanup evidence does not belong to its target source.")

        expected_relationships = {
            (
                "event:repository-test-4a79ecc5670a40318d6e747fd8d887ce",
                "sha256:e7ab7c42d6d24536831ff10e343ee73adc93d690e67442fda10ccca320ead70f:pdf-page:1",
            ),
            (
                "event:repository-test-4a79ecc5670a40318d6e747fd8d887ce",
                "sha256:05000fa0a2dc49e9be5ce0058d54e0e74ea88677b69e404fa2b2a511f6da38bf:sheet:Attendance:row:2",
            ),
            (
                "meeting:repository-test-4a79ecc5670a40318d6e747fd8d887ce",
                "sha256:e7ab7c42d6d24536831ff10e343ee73adc93d690e67442fda10ccca320ead70f:pdf-page:1",
            ),
            (
                "event:repository-test-b8601dea996140358c371e6c0b48ac78",
                "sha256:cb01276a468f445bbb4c23c563875ae62808c1f5098e4fe8a28d64dfe4e748f9:pdf-page:1",
            ),
            (
                "event:repository-test-b8601dea996140358c371e6c0b48ac78",
                "sha256:738d3c8e21b8475ebcf7de75c1047f467fa67c86a7bd41109c833fbc375fb46a:sheet:Attendance:row:2",
            ),
            (
                "meeting:repository-test-b8601dea996140358c371e6c0b48ac78",
                "sha256:cb01276a468f445bbb4c23c563875ae62808c1f5098e4fe8a28d64dfe4e748f9:pdf-page:1",
            ),
        }
        cursor.execute(
            """
            SELECT record_id, evidence_id
            FROM record_evidence
            WHERE record_id = ANY(%s)
            """,
            (list(_TARGET_RECORDS),),
        )
        actual_relationships = set(cursor.fetchall())
        if actual_relationships != expected_relationships:
            raise RuntimeError(
                "Cleanup targets have unexpected record-evidence relationships: "
                + repr(sorted(actual_relationships))
            )
    return target_source_ids, evidence_ids


def cleanup(connection: Connection[Any], fixture_path: str | Path) -> tuple[
    dict[str, int], dict[str, int]
]:
    """Delete only confirmed repository-test rows in one transaction."""
    protected_source_ids = _fixture_source_ids(fixture_path)
    before = _counts(connection)
    connection.commit()

    with connection.transaction():
        target_source_ids, evidence_ids = _verify_targets(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT source_id FROM source WHERE source_id = ANY(%s)",
                (list(protected_source_ids),),
            )
            if {row[0] for row in cursor.fetchall()} != protected_source_ids:
                raise RuntimeError("Protected sample sources are incomplete.")

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
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM source WHERE source_id = ANY(%s)",
                (list(target_source_ids),),
            )
            if cursor.fetchone()[0] != 0:
                raise RuntimeError("Cleanup target sources still exist.")
            cursor.execute(
                "SELECT count(*) FROM evidence WHERE evidence_id = ANY(%s)",
                (list(evidence_ids),),
            )
            if cursor.fetchone()[0] != 0:
                raise RuntimeError("Cleanup target evidence still exists.")
            cursor.execute(
                "SELECT count(*) FROM record WHERE record_id = ANY(%s)",
                (list(_TARGET_RECORDS),),
            )
            if cursor.fetchone()[0] != 0:
                raise RuntimeError("Cleanup target records still exist.")
            cursor.execute(
                "SELECT source_id FROM source WHERE source_id = ANY(%s)",
                (list(protected_source_ids),),
            )
            if {row[0] for row in cursor.fetchall()} != protected_source_ids:
                raise RuntimeError("Protected sample sources were not preserved.")

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
