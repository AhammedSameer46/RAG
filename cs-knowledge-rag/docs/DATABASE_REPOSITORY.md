# Database Repository

## Responsibility

`cs_ingest/repository.py` persists the existing normalized model to the
already-created PostgreSQL schema. It supports only:

- Source;
- Evidence;
- Record;
- Record-to-Evidence relationships;
- DateMention.

The repository does not perform extraction, normalization, retrieval, answer
generation, or citation building.

## API and transaction ownership

`Repository` receives an existing psycopg 3 connection:

```python
repository = Repository(connection)
with connection.transaction():
    repository.save_normalized_dataset(normalized)
```

The lower-level `save_source`, `save_evidence`, `save_record`,
`save_record_evidence`, and `save_date_mention` operations are also available.
No repository method commits or closes the connection. The caller owns the
transaction boundary and can roll back the entire dataset.

## Idempotency

Sources, evidence, records, and record/evidence links use their existing
logical identifiers and PostgreSQL conflict handling. Re-saving the same
logical objects updates the source, evidence, or record row and leaves one
relationship.

The migration intentionally gives DateMention an internal identity only. Since
the normalized model has no DateMention ID or database uniqueness constraint,
the repository uses `(evidence_id, original_text, normalized_iso,
date_role)` as the base identity. If the same exact identity occurs multiple
times in one normalized dataset, its occurrence number is retained as an
implicit ordinal. Before inserting, the repository counts existing rows for
the base identity and inserts only until the dataset's required occurrence
count is present. This preserves repeated normalized objects while keeping a
second persistence run idempotent, without inventing a new public identifier.

## Provenance and JSONB

PDF page, worksheet row, and worksheet cell provenance is stored in the
structured Evidence columns. Spreadsheet values and headers use JSONB.
Record attributes are written through psycopg's JSONB adapter, preserving
nested dictionaries and lists.

## Testing

The repository integration test uses a synthetic dataset containing PDF and
spreadsheet provenance, nested JSONB, shared evidence, DateMention data,
repeat persistence, and transaction rollback. It is separate from the normal
unit-test suite and skips when PostgreSQL credentials or the server are
unavailable.

## Persisting normalized JSON

The explicit persistence command loads an existing normalized artifact and
persists it atomically through the repository:

```text
python -m cs_ingest.persist output/sample_normalized.json
```

It uses the environment variables documented in
`docs/DATABASE_MIGRATIONS.md`, prints counts derived from the input artifact,
and closes the connection after the transaction completes. It does not run
extraction or normalization and does not modify the source files.

## Development-only repository-test cleanup

The confirmed stale repository integration rows can be removed explicitly with:

```text
python -m cs_ingest.cleanup_repository_test_data output/sample_normalized.json
```

This command is not part of normal persistence. It validates the two confirmed
source IDs, filenames, evidence IDs, and repository-test record relationships,
then deletes only those rows in foreign-key order within one transaction:
DateMention, record/evidence links, records, evidence, and sources. It verifies
that the resulting counts exactly match the normalized fixture before closing
the connection.
