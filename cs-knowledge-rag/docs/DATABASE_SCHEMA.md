# Database Schema

## 1. Purpose

This document defines the minimal PostgreSQL persistence model for the current
normalized representation. It replaces JSON persistence only; it does not
change normalization, retrieval, Answer Plan, Model-Facing Context, claim
validation, or citation behavior.

The design is based on:

- `output/sample_normalized.json`;
- `cs_ingest/normalize.py`;
- `cs_ingest/retrieval.py`;
- the normalization and retrieval tests.

The current canonical entities are exactly:

1. Source
2. Evidence
3. Record
4. DateMention

No Person, Event, Meeting, Topic, Conflict, or other additional canonical
tables are introduced.

## 2. Current Source Model

The normalized source object currently contains:

```json
{
  "source_id": "sha256:<digest>",
  "filename": "...",
  "file_type": "...",
  "sha256": "...",
  "size_bytes": 1234
}
```

`source_id` is deterministically derived from `sha256`. The current
implementation also uses the source ID in every evidence ID, so source
identity must remain stable across persistence and retrieval.

The normalized evidence object references a source by `source_id`. Filenames
are currently added to retrieved evidence by joining evidence to its source;
they do not need to be duplicated in Evidence.

## 3. Relational Schema

The SQL below is design notation, not an implementation or migration.

### 3.1 `source`

| Column | PostgreSQL type | Nullable | Constraints | Purpose |
|---|---|---:|---|---|
| `source_id` | `text` | No | Primary key | Existing logical source ID, including the `sha256:` prefix |
| `filename` | `text` | No |  | Original normalized filename |
| `file_type` | `text` | No |  | Current source type, such as PDF or XLSX |
| `sha256` | `char(64)` | No | `UNIQUE`, optionally a hex-format check | Content identity used by normalization |
| `size_bytes` | `bigint` | No | `CHECK (size_bytes >= 0)` | Source size from extraction metadata |

Recommendations:

- Keep `source_id` as the primary key because existing IDs are exposed in
  normalized data and used to construct evidence IDs.
- Keep `sha256` separately and uniquely constrained. This prevents two source
  rows from claiming the same content hash while preserving the current
  `source_id` value.
- Do not add a second generated UUID or bigint key in the minimal schema.
  PostgreSQL internal surrogate keys are not needed for the current logical-ID
  relationships and would add translation complexity.

Useful index: the unique constraint on `sha256` supplies the required lookup
index. No filename index is required by current retrieval.

### 3.2 `evidence`

| Column | PostgreSQL type | Nullable | Constraints | Purpose |
|---|---|---:|---|---|
| `evidence_id` | `text` | No | Primary key | Existing deterministic evidence ID |
| `source_id` | `text` | No | Foreign key to `source(source_id)` | Owning source |
| `kind` | `text` | No | Check for current kinds or controlled application validation | `pdf_page`, `worksheet_row`, or `worksheet_cell` |
| `page` | `integer` | Yes | `CHECK (page IS NULL OR page > 0)` | PDF page number |
| `sheet` | `text` | Yes |  | Spreadsheet worksheet name |
| `row_number` | `integer` | Yes | `CHECK (row_number IS NULL OR row_number > 0)` | Spreadsheet row number; named `row_number` to avoid SQL ambiguity |
| `cell` | `text` | Yes |  | Spreadsheet cell such as `B2` |
| `cell_range` | `text` | Yes |  | Spreadsheet range such as `A2:F2` |
| `extracted_text` | `text` | Yes |  | Extracted PDF text when present |
| `raw_values` | `jsonb` | Yes |  | Structured spreadsheet values |
| `header_context` | `jsonb` | Yes |  | Spreadsheet header mapping |

`evidence_id` remains the primary key. The current ID already encodes source
and location, but the structured columns remain necessary for typed filtering,
validation, and exact citation restoration.

Provenance is not flattened:

- PDF evidence stores `kind = 'pdf_page'` and `page`.
- Worksheet-row evidence stores `kind = 'worksheet_row'`, `sheet`,
  `row_number`, `cell_range`, `raw_values`, and `header_context`.
- Worksheet-cell evidence stores `kind = 'worksheet_cell'`, `sheet`,
  `row_number`, `cell`, `raw_values`, and `header_context`.

`raw_values` and `header_context` are JSONB because their keys and value types
come from spreadsheet columns and can vary by worksheet. `page`, `sheet`,
`row_number`, `cell`, and `cell_range` remain structured columns because they
are stable provenance fields used by exact citation and filtering. A future
constraint or application validator may require the appropriate fields for
each `kind`; the initial design should not reject future source-specific
evidence merely because it is not one of the current three kinds.

Recommended indexes:

- `evidence(source_id)` for source expansion and source cleanup;
- `evidence(kind, sheet, row_number)` for worksheet provenance lookup;
- `evidence(sheet, cell)` for exact attendance-cell lookup if that access
  pattern is retained.

No index on `raw_values` is justified by current retrieval. Current keyword
retrieval flattens values in application code rather than querying individual
JSON keys.

### 3.3 `record`

| Column | PostgreSQL type | Nullable | Constraints | Purpose |
|---|---|---:|---|---|
| `record_id` | `text` | No | Primary key | Existing deterministic logical record ID |
| `record_type` | `text` | No | Check for current `meeting`, `event`, `attendance` values, or application validation | Current record category |
| `attributes` | `jsonb` | No | Default `{}`; object validation at application boundary | Heterogeneous normalized record fields |

`attributes` is JSONB because the current record types have different fields:

- meetings: `meeting_date`, `meeting_type`, `chair`,
  `attendees_count`, `key_decision`;
- events: `name`, `start_date`, `end_date`, `coordinator`, `participants`,
  `status`, and optional `participant_observations`;
- attendance: `person`, `meeting_date`, `meeting_label`, `status`,
  `remarks`.

The event record also demonstrates why a fixed set of nullable columns would
be premature: `participant_observations` is a list of source statements with
its own evidence IDs. JSONB preserves that current shape without inventing a
new canonical observation entity.

The JSONB field is not a replacement for Evidence. Record attributes are
normalized interpretations and searchable record fields; Evidence remains the
authoritative source-linked material.

Recommended indexes:

- `record(record_type)` for the current record-type filter;
- expression indexes for date and exact scalar fields used by retrieval:
  `((attributes->>'meeting_date'))`,
  `((attributes->>'start_date'))`,
  `((attributes->>'end_date'))`,
  `((attributes->>'person'))`, and
  `((attributes->>'name'))`.

These should be implemented as separate targeted indexes only if the SQL
replacement preserves the corresponding retrieval paths. A broad GIN index on
all `attributes` is not required for the current exact scalar filters.

### 3.4 `record_evidence`

| Column | PostgreSQL type | Nullable | Constraints | Purpose |
|---|---|---:|---|---|
| `record_id` | `text` | No | Foreign key to `record(record_id)` | Referenced record |
| `evidence_id` | `text` | No | Foreign key to `evidence(evidence_id)` | Supporting or associated evidence |

Primary key: `(record_id, evidence_id)`.

This is the relational form of the current `record.evidence_refs` array.
There is no role column in the current normalized model, so none is added.
Supporting versus independently matched retrieval collections are derived
at query time, not persisted as a new canonical relationship attribute.

### 3.5 `date_mention`

| Column | PostgreSQL type | Nullable | Constraints | Purpose |
|---|---|---:|---|---|
| `date_mention_id` | `bigint generated always as identity` | No | Primary key | Relational row identity; no current logical ID exists |
| `evidence_id` | `text` | No | Foreign key to `evidence(evidence_id)` | Evidence containing the mention |
| `original_text` | `text` | No |  | Exact source wording |
| `normalized_iso` | `date` | No |  | Normalized calendar date |
| `date_role` | `text` | Yes |  | Semantic role, including `meeting_date`, `event_date`, `rescheduled_date`, and null |

`normalized_iso` should be PostgreSQL `date`, not text. `original_text` must be
retained because the source representation matters. `date_role` remains
nullable because the current normalization explicitly produces null roles for
some spreadsheet date mentions.

Recommended indexes:

- `date_mention(normalized_iso)`;
- `date_mention(normalized_iso, date_role)`;
- `date_mention(date_role, normalized_iso)`;
- `date_mention(evidence_id)`.

The role indexes support exact date and date-role retrieval without collapsing
different semantic date meanings into one document date.

## 4. Relationships

```text
Source
  │
  └──< Evidence
          │
          └──< DateMention
          │
          └──< RecordEvidence >── Record
```

More precisely:

- one Source has many Evidence rows;
- one Evidence row belongs to one Source;
- one Evidence row may contain many DateMention rows;
- one Record may reference many Evidence rows;
- one Evidence row may support many Records.

The Record-to-Evidence relationship is therefore many-to-many. This is
required by the current data: a meeting can reference a worksheet row and a
PDF page, and the same PDF evidence may be referenced by more than one
normalized record.

## 5. Evidence / Provenance Model

Evidence is the authoritative citation layer. A record attribute such as
`coordinator`, `status`, or `meeting_date` is not sufficient to reconstruct a
citation by itself.

The exact citation path is:

```text
record_evidence
  → evidence
  → source
```

Examples:

```text
PDF:
  evidence.kind = pdf_page
  evidence.page = 1
  source.filename = CS_Dept_Meeting_Minutes_18Jul2026.pdf

Spreadsheet:
  evidence.kind = worksheet_cell
  evidence.sheet = Faculty Attendance
  evidence.row_number = 2
  evidence.cell = B2
  source.filename = CS_Faculty_Attendance_GoogleSheet.xlsx
```

The database must preserve the existing logical `evidence_id` exactly. It
must not replace a row/cell or PDF page with only a source filename or a
record ID.

## 6. Record Attribute Strategy

Use `attributes jsonb` for the current stage. It preserves the existing
heterogeneous normalized representation and avoids creating speculative
Person, Event, Meeting, Decision, or Topic tables.

The retrieval replacement should extract only the currently required scalar
fields from JSONB for exact filters. It should not infer a new canonical
schema from names appearing inside attributes.

`participant_observations` remains nested JSONB. Its source statements and
evidence IDs are part of the current normalized event representation and must
not be collapsed into the event's single `participants` value.

## 7. Date Model

There are two distinct date representations:

1. Record attributes contain dates used by current record matching, such as
   meeting `meeting_date` and event `start_date`/`end_date`.
2. DateMention stores every extracted mention with its original wording,
   normalized date, role, and evidence reference.

DateMention is not a single document-date table. Current roles include:

- `meeting_date`;
- `event_date`;
- `start_date`;
- `end_date`;
- `document_issue_date`;
- `original_date`;
- `rescheduled_date`;
- `next_meeting_date`;
- `report_submission_date`;
- null for currently unclassified spreadsheet date mentions.

The `date` and `date_role` retrieval behavior must remain role-aware. A
rescheduled date mention must not become the meeting's canonical date merely
because both are dates in the same document.

## 8. Identifier Strategy

Keep the current logical identifiers:

- `source_id`: `sha256:<digest>`;
- `evidence_id`: deterministic source/location ID;
- `record_id`: deterministic type/date/name ID.

Use `source_id`, `evidence_id`, and `record_id` as unique primary keys in the
minimal schema. They are already used in normalized JSON, retrieval results,
selection metadata, and provenance restoration.

DateMention has no current application ID, so an internal identity
`date_mention_id` is appropriate. It is not exposed as a replacement for the
logical evidence relationship.

If a later implementation needs opaque internal keys for ORM or partitioning,
they may be added as non-authoritative surrogate columns while retaining
unique constraints on all three logical IDs. That is a future implementation
choice, not part of this minimal design.

## 9. Retrieval-to-Index Mapping

| Current retrieval need | Database field(s) | Proposed index | Reason |
|---|---|---|---|
| Source lookup for evidence filename | `source.source_id` | Primary key | Evidence expansion joins to its source |
| Source deduplication | `source.sha256` | Unique constraint/index | Preserves SHA-256 identity |
| Record type filter | `record.record_type` | B-tree on `record_type` | Exact filter for meeting, event, attendance |
| Meeting date filter | `record.attributes->>'meeting_date'` | B-tree expression index | Exact normalized date comparison |
| Event start/end date filter | `record.attributes->>'start_date'`, `record.attributes->>'end_date'` | Separate B-tree expression indexes | Current event date matching checks both fields |
| Person attendance lookup | `record.record_type`, `record.attributes->>'person'` | B-tree on `(record_type, (attributes->>'person'))` | Exact attendance-person filter |
| Event name lookup | `record.record_type`, `record.attributes->>'name'` | B-tree on `(record_type, (attributes->>'name'))` | Exact event-name filter |
| Exact date-role retrieval | `date_mention.normalized_iso`, `date_mention.date_role` | B-tree on `(normalized_iso, date_role)` | Preserves semantic date roles |
| Date-only evidence expansion | `date_mention.normalized_iso` | B-tree on `normalized_iso` | Finds all evidence mentions for a date |
| Evidence provenance lookup | `evidence.source_id`, `evidence.kind`, structured location fields | B-tree on `(source_id, kind)` and targeted sheet/location index | Exact source and spreadsheet provenance access |
| Attendance citation lookup | `evidence.sheet`, `evidence.cell` | B-tree on `(sheet, cell)` | Exact cell provenance such as `Faculty Attendance`, `B2` |
| Keyword search over current evidence/attributes | `evidence.extracted_text`, `evidence.raw_values`, `record.attributes` | No mandatory new index in minimal schema | Current implementation performs token containment after loading; a future full-text design would change semantics |

The current keyword matcher requires every query token to occur in a
case-folded flattened string. PostgreSQL full-text search or trigram indexes
would not be semantic equivalents without an explicit retrieval change.
Therefore neither is part of this design-only step.

## 10. Transaction Boundary

A future ingestion run should persist one normalized source snapshot in a
single database transaction:

```text
BEGIN
  upsert Source rows by sha256/source_id
  insert or replace Evidence rows for the normalized source version
  insert Record rows
  insert RecordEvidence rows
  insert DateMention rows
COMMIT
```

The transaction must not expose a source whose evidence, records, or date
mentions are only partially written. If any validation or constraint fails,
the transaction rolls back as a unit.

Idempotency should be based on the existing logical IDs and unique
constraints, not on insertion order. The exact replace/upsert policy for
changed source content requires a versioning decision and is intentionally not
implemented here.

## 11. Current Schema vs Future Extensions

### Current schema

The initial schema contains only:

- `source`;
- `evidence`;
- `record`;
- `record_evidence`;
- `date_mention`.

It contains no pgvector, credentials, authentication fields, Drive fields,
permissions, OCR fields, or synchronization state.

### Future extensions

The following may eventually be required, but are not justified by the
current normalized model:

- Google Drive file ID, Drive revision ID, provider URL, and sync cursor;
- Google Sheets spreadsheet ID, worksheet ID, and provider row metadata;
- source version/snapshot tables and supersession relationships;
- deletion or tombstone state for removed remote documents;
- ingestion run ID, parser version, and normalization version;
- permission/access-control metadata;
- OCR status, page image references, and extracted layout;
- semantic chunks, embeddings, and pgvector indexes.

These should be introduced only when real source integration and operational
requirements are confirmed.

## 12. Open Questions

1. Should future ingestion retain multiple source versions simultaneously, or
   replace the current active version?
2. Does the real college data require provenance kinds beyond PDF pages,
   worksheet rows, and worksheet cells?
3. Should `date_role` become a controlled database enum/check constraint, or
   remain application-controlled as new roles appear?
4. Should keyword retrieval retain the current token-substring semantics or
   move to PostgreSQL full-text/trigram search?
5. Will permissions be source-level, record-level, or evidence-level once
   authorized access is implemented?
6. Should future source synchronization distinguish the content hash from a
   provider version/revision?
7. Are record attributes sufficiently stable for targeted expression indexes
   after real college data is available?

## 13. Decision Summary

Recommended minimal PostgreSQL schema:

```text
source(
  source_id PK,
  filename,
  file_type,
  sha256 UNIQUE,
  size_bytes
)

evidence(
  evidence_id PK,
  source_id FK,
  kind,
  page,
  sheet,
  row_number,
  cell,
  cell_range,
  extracted_text,
  raw_values JSONB,
  header_context JSONB
)

record(
  record_id PK,
  record_type,
  attributes JSONB
)

record_evidence(
  record_id FK,
  evidence_id FK,
  PK(record_id, evidence_id)
)

date_mention(
  date_mention_id identity PK,
  evidence_id FK,
  original_text,
  normalized_iso DATE,
  date_role
)
```

This preserves the current normalized semantics, keeps Evidence as the
authoritative provenance layer, supports the existing exact retrieval
operations, permits many-to-many Record/Evidence relationships, and avoids
premature domain tables or vector infrastructure.

**DESIGN READY**
