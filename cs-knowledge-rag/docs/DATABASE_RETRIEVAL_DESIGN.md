# PostgreSQL Retrieval Design

## 1. Purpose

This document designs a PostgreSQL-backed replacement for the current
deterministic in-memory `Retriever`. It is design only. No PostgreSQL retriever
is implemented in this phase, and the normalized JSON retriever remains the
behavioral reference.

The design preserves the existing evidence-first contract and works with
`migrations/001_initial_schema.sql` without schema changes.

## 2. Current and target architecture

Current:

```text
Question
  -> QueryUnderstanding
  -> Retriever(normalized JSON)
  -> EvidenceResponse
  -> EvidenceSelector
  -> AnswerPlan
  -> Model-Facing Context
  -> AnswerGenerator
```

Target:

```text
Question
  -> QueryUnderstanding
  -> PostgreSQL Retriever
  -> EvidenceResponse
  -> EvidenceSelector
  -> AnswerPlan
  -> Model-Facing Context
  -> AnswerGenerator
```

The downstream stages receive the same retrieval shape regardless of storage
provider. Vector retrieval is not part of this design.

## 3. Existing Retriever contract

`Retriever.query()` accepts these optional filters:

```text
date, record_type, person, event_name, date_role, keyword
```

All supplied filters are ANDed.

### Record matching

- `record_type` accepts only `meeting`, `event`, or `attendance`; another
  value raises `ValueError`.
- `date` matches only record-type-specific date attributes:
  - meeting: `attributes.meeting_date`;
  - event: `attributes.start_date` or `attributes.end_date`;
  - attendance: `attributes.meeting_date`.
- `date_role` matches record attributes only for:
  - `meeting_date` on meeting and attendance records;
  - `event_date` on event `start_date` or `end_date`;
  - `start_date` on event `start_date`;
  - `end_date` on event `end_date`.
  Other roles do not admit a record through record matching.
- `person` matches only attendance records and exact
  `attributes.person` equality.
- `event_name` matches only event records and exact `attributes.name` equality.
- `keyword` requires every token from the query to occur as a case-folded
  substring of the flattened record value.
- A record with no structured filter match gets `matched_fields = ["record"]`.
  Other values can include `date`, `date_role`, `person`, `event_name`, and
  `record_keyword`.

The record output is a deep copy of the normalized record with
`matched_fields` added.

### Evidence expansion

1. Every evidence reference of a matching record becomes supporting evidence.
2. If `keyword` is present, every evidence unit whose flattened values contain
   all keyword tokens becomes independently matched evidence.
3. If `date_role` is present, every DateMention matching the requested date
   and role contributes independently matched evidence. With no `date`,
   DateMention filtering is by role alone.
4. If `date` is present without `record_type`, `person`, `event_name`, or
   `keyword`, every DateMention for that date contributes independently
   matched evidence, regardless of role.

`evidence_units` is the sorted union of all expanded evidence IDs. Each unit
contains its normalized evidence fields, source filename, and
`matched_fields`, whose current values are:

```text
record_reference
keyword
date_mention
date_role
```

`supporting_evidence_units` contains only evidence referenced by matching
records. `matched_evidence_units` contains only independently matched
keyword/date-mention evidence. They must not be collapsed.

Empty results contain no records, no evidence units, and `has_evidence =
false`. The pipeline maps this to `insufficient_evidence`.

## 4. PostgreSQL schema mapping

The retriever must use only columns in the current migration:

| Retrieval value | PostgreSQL source |
|---|---|
| Source identity and filename | `source.source_id`, `source.filename` |
| File metadata | `source.file_type`, `source.sha256`, `source.size_bytes` |
| Record identity/type | `record.record_id`, `record.record_type` |
| Heterogeneous fields | `record.attributes` JSONB |
| Record support | `record_evidence.record_id`, `record_evidence.evidence_id` |
| Evidence identity/source | `evidence.evidence_id`, `evidence.source_id` |
| PDF text/page | `evidence.extracted_text`, `evidence.page` |
| Spreadsheet provenance | `evidence.sheet`, `evidence.row_number`, `evidence.cell`, `evidence.cell_range` |
| Spreadsheet values | `evidence.raw_values`, `evidence.header_context` |
| Date mentions | `date_mention.evidence_id`, `normalized_iso`, `date_role`, `original_text` |

Supporting evidence is reconstructed with:

```text
record
  JOIN record_evidence ON record.record_id = record_evidence.record_id
  JOIN evidence ON evidence.evidence_id = record_evidence.evidence_id
  JOIN source ON source.source_id = evidence.source_id
```

Independent evidence is obtained by querying `evidence` and, for date
operations, joining `date_mention` to `evidence` and `source`.

## 5. Record-type query mapping

The sample contains 5 meeting, 4 event, and 15 attendance records.

Observed meeting attributes:

```text
meeting_date, meeting_type, chair, attendees_count, key_decision
```

Observed event attributes:

```text
name, start_date, end_date, coordinator, participants, status,
participant_observations
```

Observed attendance attributes:

```text
person, meeting_date, meeting_label, status, remarks
```

Currently executable structured filters are only `meeting_date`,
`start_date`/`end_date`, `person`, `name`, `record_type`, and the supported
date roles described below. Other stored fields remain retrievable as record
attributes or keyword content but are not independently queryable filters.

The future implementation should use JSONB extraction expressions such as:

```sql
record.attributes ->> 'meeting_date'
record.attributes ->> 'start_date'
record.attributes ->> 'end_date'
record.attributes ->> 'person'
record.attributes ->> 'name'
```

Values must be compared as normalized text exactly as the current JSON
retriever compares them. Date strings should be validated by query
understanding before execution; no implicit date-role inference is allowed.

## 6. Date semantics

Record date filtering must not use arbitrary DateMention rows. It must use
the same record-type-specific JSONB fields as the current retriever:

| Record type | Date fields for `date` |
|---|---|
| meeting | `attributes.meeting_date` |
| event | `attributes.start_date`, `attributes.end_date` |
| attendance | `attributes.meeting_date` |

`date_mention` is an evidence-expansion table, not a canonical record-date
table. It is used to return the context in which a date was mentioned.

For `date_role`, record admission uses only the current supported mapping:

| Role | Record fields |
|---|---|
| `meeting_date` | meeting/attendance `meeting_date` |
| `event_date` | event `start_date` or `end_date` |
| `start_date` | event `start_date` |
| `end_date` | event `end_date` |

Roles such as `rescheduled_date`, `original_date`, `document_issue_date`,
`next_meeting_date`, and `report_submission_date` match DateMention evidence
but do not admit a record. Thus a query for a rescheduled date can return
evidence with no records, preserving lifecycle distinctions.

Example: “What happened on 18 July 2026?” first matches meeting, event, and
attendance record date attributes. It may also expand all DateMentions for
that date because it is a date-only query. A report submission or rescheduled
mention must not itself turn an unrelated record into a date match.

## 7. Keyword semantics

The current matcher:

1. extracts `\w+` tokens from the keyword query after case-folding;
2. flattens nested dictionaries, lists, tuples, sets, and scalar values by
   joining their string representations;
3. requires every token to occur as a case-folded substring;
4. rejects an empty-token query.

This applies separately to flattened `record` values and flattened `evidence`
values. It is not token-boundary search, ranking, fuzzy search, PostgreSQL
full-text search, or semantic search.

The first PostgreSQL implementation should preserve exact behavior by loading
the candidate scalar/JSONB/text values and applying the same deterministic
matcher in Python, or by explicitly proving equivalent SQL behavior. It must
not silently substitute `tsquery`, trigram, stemming, or fuzzy matching.
Full-text/trigram search is a future optimization decision.

## 8. Evidence expansion and matched fields

The future retriever should build three distinct collections:

```text
supporting_evidence_units  record-reference evidence
matched_evidence_units     independently matched keyword/date evidence
evidence_units             sorted union
```

If one evidence unit belongs to both paths, it remains one unit in the union
but carries both applicable matched-field values. Record evidence receives
`record_reference`; keyword matches receive `keyword`; date-only mention
matches receive `date_mention`; role-filtered mentions receive `date_role`.

The existing `record_evidence` join table is many-to-many and must be queried
without assuming one record or one evidence unit has only one relationship.

## 9. Provenance

Every returned evidence unit must reconstruct:

```text
source_id
filename
evidence_id
kind
page / sheet / row_number / cell / cell_range
extracted_text
raw_values
header_context
```

The public normalized shape currently calls the row field `row`; the SQL
column is `row_number`. The PostgreSQL adapter must map the column back to
`row` at the retrieval boundary so downstream citation code sees the existing
shape.

Records retain `record_id`, `record_type`, `attributes`, and
`evidence_refs`. No provenance is reconstructed from filenames or record IDs
when a structured Evidence row is available.

## 10. Query examples

### “What happened on 18 July 2026?”

Query understanding produces `date=2026-07-18`. PostgreSQL matches the
record-type-specific JSONB date fields, expands their `record_evidence`
references, and independently expands DateMention rows for the date.
Expected record types are meeting, event, and attendance. Matched fields are
primarily `date`, `record_reference`, and `date_mention`.

### “Was Dr. Reena Nair present on 18 July 2026?”

Filters are `record_type=attendance`, `person=Dr. Reena Nair`,
`date=2026-07-18`. Match `attributes.person` and
`attributes.meeting_date`; join the matching record to its attendance cell
evidence. Expected evidence includes the exact spreadsheet cell provenance.

### “Which event was coordinated by Prof. Sarah Thomas?”

The current query-understanding implementation supports event-name extraction
and keyword-oriented event lookup, but coordinator is not a supported
structured filter. Unless the query is safely represented as a keyword query,
the pipeline must retain its existing unresolved/clarification behavior rather
than silently adding a coordinator filter.

### “When was the faculty meeting rescheduled?”

Query understanding produces `date_role=rescheduled_date`. No record is
admitted by that role; DateMention rows with that role are independently
matched and returned with `date_role`.

### “What was discussed about lab procurement?”

This is narrative keyword retrieval. Candidate records and evidence are
filtered using the all-token substring rule for `lab` and `procurement`.
Record-linked worksheet evidence is supporting evidence; the meeting PDF page
may be independently matched evidence.

### “What decisions were made during the FDP Planning meeting?”

The known sample stores `key_decision` on meeting records, but it is not a
dedicated supported filter. Query understanding should either form a safe
keyword request or leave the request unresolved. If executable, the future
retriever returns the meeting record and its linked evidence without inventing
a new decision entity.

## 11. Unsupported filters and empty behavior

The pipeline currently allows only:

```text
date, record_type, person, event_name, date_role, keyword
```

Unsupported filters, low confidence, ambiguity, or unresolved query
understanding produce `clarification_required`; PostgreSQL retrieval must not
ignore an unsupported field.

Empty and partial cases remain distinct:

- no matching records and no independently matched evidence:
  `insufficient_evidence`;
- matching DateMention evidence but no matching records:
  `answerable` at retrieval level because evidence exists, with an empty
  records list;
- matching evidence without a supporting record: preserve it in
  `matched_evidence_units`;
- no keyword matches: return empty evidence and `insufficient_evidence`;
- unsupported constraints: return `clarification_required`, not an empty
  answer that looks authoritative.

## 12. Connection and transaction model

The future retriever should use `database.get_connection()` or receive an
existing connection according to the calling boundary. No global connection,
pool, retry loop, migration execution, or write transaction is appropriate.
Queries are read-only `SELECT` statements. A short-lived connection per
request is the simplest initial lifecycle; a caller-owned connection is
preferable when the surrounding pipeline already manages one.

## 13. Parameterized SQL requirement

All user-derived values must be parameters:

- dates;
- date roles;
- record types;
- people;
- event names;
- keyword values;
- filenames and source IDs.

SQL identifiers and fixed JSON keys may be hard-coded. No user question,
keyword, name, date, or filename may be interpolated into SQL text.

## 14. Existing index usage

The migration already provides:

- `record(record_type)`;
- expression indexes for meeting, event start, and event end dates;
- `(record_type, attributes->>'person')`;
- `(record_type, attributes->>'name')`;
- evidence source/kind and spreadsheet location indexes;
- DateMention date, role/date, and evidence indexes.

These support the exact structured predicates and provenance joins. The
current migration has no full-text or JSONB GIN index, and no such index
should be added merely for this design. The first implementation may need to
load candidate text for exact Python keyword semantics.

## 15. Known limitations

1. The current schema has no DateMention logical identity or uniqueness
   constraint; duplicate normalized mentions are an application-level
   occurrence concern.
2. Keyword semantics are substring-based and may require application-side
   filtering for exact compatibility.
3. JSONB fields not listed in the current supported filters are stored but not
   independently queryable.
4. The existing query-understanding layer can reject or clarify some natural
   language requests before retrieval.
5. No database-backed retriever has yet been implemented or benchmarked.
6. Permissions, tenant boundaries, versioning, and synchronization are out of
   scope.

## 16. Future vector-search boundary

Vector search is deferred. This phase adds no embeddings, vector columns,
pgvector dependency, vector indexes, or changes to the retrieval contract.
Semantic retrieval can be evaluated later as an additional evidence source
that still emits the same supporting/matched evidence and provenance shape.

## 17. Open questions

1. Can exact keyword behavior be retained at acceptable scale with
   application-side filtering, or should a deliberately versioned search
   semantic be introduced?
2. Should DateMention occurrence identity eventually become an explicit schema
   column or remain application-managed?
3. Which additional JSONB fields, if any, should become supported structured
   filters after real college data is available?
4. Should the pipeline own one connection per request or pass a caller-owned
   read-only connection?
5. What evaluation threshold would justify adding semantic/vector retrieval?
