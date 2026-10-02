# PostgreSQL Retriever Implementation

## Status

`cs_ingest/postgres_retrieval.py` provides a separate `PostgresRetriever` with
the same query parameters and result shape as the in-memory `Retriever`.
The in-memory implementation remains the behavioral reference until parity is
demonstrated.

It is not wired into `QueryRetrievalPipeline` yet.

## Connection lifecycle

`PostgresRetriever` may receive a caller-owned psycopg connection. If no
connection is supplied, it opens one with `get_connection()` for the query and
closes it afterward. It does not create a pool, global connection, retry loop,
migrations, or writes.

## Query strategy

Record type, normalized record dates, date roles, people, and event names use
parameterized SQL predicates against `record.record_type` and JSONB
expressions. Record evidence is expanded through `record_evidence`.
Evidence joins `source` to restore filenames and maps SQL `row_number` back to
the normalized `row` field.

DateMention rows are used only for independent date evidence. They never admit
canonical records. Supporting and independently matched evidence remain
separate, with a deterministic union.

## Keyword handling

The implementation reuses the existing `_flatten_text` and
`_contains_keyword` functions. It does not use full-text search, trigram
search, fuzzy matching, or semantic search. This preserves the current
case-folded all-token substring behavior.

## Parity tests

Integration tests compare deterministic canonical structures from both
retrievers for date, attendance, event, date-role, keyword, empty-result, and
unsupported-record-type cases. They require the already-populated PostgreSQL
database and skip when credentials or PostgreSQL are unavailable.

## Known limitations

- The retriever is not yet connected to the public query pipeline.
- Keyword matching currently loads candidate values and applies the reference
  Python matcher for exact semantic parity.
- No vector search, embeddings, permissions, or authorization are included.
