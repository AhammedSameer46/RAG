"""Persist an existing normalized JSON dataset to PostgreSQL."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from psycopg import Connection

from .database import get_connection
from .repository import Repository


_REQUIRED_KEYS = {"schema_version", "sources", "evidence_units", "records", "date_mentions"}


def load_normalized_dataset(path: str | Path) -> dict[str, Any]:
    """Load and minimally validate a normalized dataset."""
    input_path = Path(path)
    try:
        dataset = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid normalized JSON in {input_path}: {exc.msg}.") from exc
    except OSError as exc:
        raise OSError(f"Unable to read normalized dataset {input_path}: {exc}") from exc

    if not isinstance(dataset, dict):
        raise ValueError("Normalized dataset must be a JSON object.")
    missing = _REQUIRED_KEYS - dataset.keys()
    if missing:
        raise ValueError(
            f"Normalized dataset is missing required keys: {', '.join(sorted(missing))}."
        )
    for key in _REQUIRED_KEYS - {"schema_version"}:
        if not isinstance(dataset[key], list):
            raise ValueError(f"Normalized dataset field '{key}' must be a list.")
    for index, record in enumerate(dataset["records"]):
        if not isinstance(record, Mapping):
            raise ValueError(f"Normalized record at index {index} must be an object.")
        if "evidence_refs" not in record or not isinstance(
            record["evidence_refs"], list
        ):
            raise ValueError(
                f"Normalized record at index {index} must contain evidence_refs."
            )
    return dataset


def persist_dataset(dataset: Mapping[str, Any], connection: Connection[Any]) -> None:
    """Persist a normalized dataset atomically using the supplied connection."""
    with connection.transaction():
        Repository(connection).save_normalized_dataset(dataset)


def persist_file(path: str | Path) -> dict[str, int]:
    """Load and persist a normalized dataset, closing the connection afterward."""
    dataset = load_normalized_dataset(path)
    connection = get_connection()
    try:
        persist_dataset(dataset, connection)
    finally:
        connection.close()
    return {
        "sources": len(dataset["sources"]),
        "evidence_units": len(dataset["evidence_units"]),
        "records": len(dataset["records"]),
        "record_evidence": sum(
            len(record["evidence_refs"]) for record in dataset["records"]
        ),
        "date_mentions": len(dataset["date_mentions"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Persist a normalized JSON dataset to PostgreSQL."
    )
    parser.add_argument("input", type=Path)
    args = parser.parse_args()

    print("Loading normalized dataset...")
    dataset = load_normalized_dataset(args.input)
    print(f"Sources: {len(dataset['sources'])}")
    print(f"Evidence units: {len(dataset['evidence_units'])}")
    print(f"Records: {len(dataset['records'])}")
    print(f"Date mentions: {len(dataset['date_mentions'])}")
    print("Persisting...")
    connection = get_connection()
    try:
        persist_dataset(dataset, connection)
    finally:
        connection.close()
    print("Persistence successful.")


if __name__ == "__main__":
    main()
