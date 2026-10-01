# Model-Facing Context Schema

## 1. Status

**SCHEMA FINALIZED FOR IMPLEMENTATION REVIEW**

This document finalizes the compact, provider-neutral model-facing context
candidate for implementation review. It does not implement the builder or
change the current production context.

## 2. Relationship to Internal Answer Plan

The internal Answer Plan remains rich, deterministic application state. It
continues to contain fields such as internal observation IDs, record IDs,
matched fields, provenance references, selector coverage telemetry, excluded
evidence, and diagnostic reasons.

The model-facing context is a separate deterministic view:

```text
Internal Answer Plan
        |
        v
compact deterministic transformation
        |
        v
ModelFacingContext
```

The transformation must be:

- deterministic;
- side-effect-free;
- provider-neutral;
- lossless for material factual evidence;
- lossless for citation handles;
- lossless for conflict and lifecycle requirements; and
- explicit about material coverage limitations.

It must never mutate the internal Answer Plan. CitationBuilder must continue
to receive the original selected evidence response, not the compact view.

The public Answer Contract and internal Claim Answer Contract remain unchanged.

## 3. Final Schema

The final candidate is:

```json
{
  "answer_plan": {
    "observations": [
      {
        "evidence_ids": ["E1"],
        "preserve_separately": false
      }
    ],
    "conflict_groups": [],
    "lifecycle_groups": [],
    "coverage": {
      "complete": true
    }
  },
  "evidence": [
    {
      "id": "E1",
      "source": "meeting.pdf",
      "location": "page 1",
      "text": "Exact extracted evidence text."
    }
  ]
}
```

The question is supplied separately:

```text
question: str
model_context: ModelFacingContext
```

Observation IDs such as `O1` are intentionally omitted. Groups refer to
observations by zero-based array indexes. This is deterministic because the
observation array is produced in a stable order and is serialized as one
immutable context.

`E1`, `E2`, and similar values are citation handles, not internal evidence
IDs. They are the only identifiers the model may put in `citation_refs`.

## 4. Field Definitions

### `answer_plan`

- **Type:** object
- **Required:** yes
- **Purpose:** deterministic organization metadata for the supplied evidence;
  not factual evidence.
- **Deterministic source:** compact transformation of the internal Answer
  Plan.
- **Constraints:** contains only observations, non-empty conflict/lifecycle
  groups, and compact coverage information.

### `answer_plan.observations`

- **Type:** array of objects
- **Required:** yes; empty when no factual evidence is selected
- **Purpose:** links each preservation unit to one or more evidence handles.
- **Deterministic source:** internal Answer Plan observations.
- **Constraints:** preserve stable order; every evidence handle must exist in
  the `evidence` array; do not copy evidence text into observations.

### `observations[].evidence_ids`

- **Type:** non-empty array of strings for factual observations
- **Required:** yes
- **Purpose:** identifies the evidence supporting that observation.
- **Deterministic source:** internal observation evidence IDs converted to
  model handles.
- **Constraints:** every value must refer to exactly one evidence item.

### `observations[].preserve_separately`

- **Type:** boolean
- **Required:** yes
- **Purpose:** tells the model not to collapse the observation with another
  observation.
- **Deterministic source:** internal preservation and group membership flags.
- **Constraints:** must not be inferred from model output.

### `answer_plan.conflict_groups`

- **Type:** array of objects
- **Required:** yes as a field; empty when there are no conflict groups
- **Purpose:** identifies observations whose differing source observations must
  remain separate.
- **Deterministic source:** internal conflict groups.
- **Constraints:** omit no group that is materially required; do not include
  internal group IDs, reasons, scores, or duplicated evidence.

### `conflict_groups[].observation_indexes`

- **Type:** non-empty array of non-negative integers
- **Required:** yes
- **Purpose:** references observations in the plan array.
- **Deterministic source:** mapping from internal observation IDs to their
  stable array positions.
- **Constraints:** every index must be valid and unique within the group.

### `conflict_groups[].must_preserve_separately`

- **Type:** boolean
- **Required:** yes
- **Purpose:** explicit conflict-preservation instruction.
- **Deterministic source:** internal conflict-group requirement.
- **Constraints:** currently `true` for emitted conflict groups.

### `answer_plan.lifecycle_groups`

- **Type:** array of objects
- **Required:** yes as a field; empty when there are no lifecycle groups
- **Purpose:** identifies related observations that must remain distinct across
  planning, meeting, status, event, or completion stages.
- **Deterministic source:** internal lifecycle groups.
- **Constraints:** omit internal lifecycle IDs and selector telemetry.

### `lifecycle_groups[].observation_indexes`

- **Type:** non-empty array of non-negative integers
- **Required:** yes
- **Purpose:** references related observations in the plan array.
- **Deterministic source:** internal observation-ID mapping.
- **Constraints:** every index must be valid and unique within the group.

### `lifecycle_groups[].must_distinguish`

- **Type:** boolean
- **Required:** yes
- **Purpose:** explicit lifecycle-separation instruction.
- **Deterministic source:** internal lifecycle-group requirement.
- **Constraints:** currently `true` for emitted lifecycle groups.

### `answer_plan.coverage`

- **Type:** object
- **Required:** yes
- **Purpose:** exposes whether selected context is materially complete.
- **Deterministic source:** selector coverage.
- **Constraints:** contains only `complete` and, when incomplete, controlled
  `reason`.

### `coverage.complete`

- **Type:** boolean
- **Required:** yes
- **Purpose:** prevents the model from filling known evidence gaps.
- **Deterministic source:** false when the selector reports truncation,
  excluded material relevant to the response, or incomplete required groups;
  otherwise true.
- **Constraints:** no excluded evidence IDs or selector rankings.

### `coverage.reason`

- **Type:** controlled string
- **Required:** only when `complete` is false
- **Purpose:** minimal explanation of incompleteness.
- **Deterministic source:** selector state.
- **Allowed initial values:** `selection_budget` when truncation or budget
  exclusion is established; `incomplete` for a generic established
  incomplete state.
- **Constraints:** no free-form model-generated text and no large taxonomy.

### `evidence`

- **Type:** array of objects
- **Required:** yes
- **Purpose:** factual source material for grounded claims.
- **Deterministic source:** selected supporting and independent evidence.
- **Constraints:** preserve exact evidence meaning and stable handle order.

### `evidence[].id`

- **Type:** non-empty string
- **Required:** yes
- **Purpose:** model citation handle, such as `E1`.
- **Deterministic source:** CitationBuilder handle ordering over the selected
  evidence response.
- **Constraints:** unique within the evidence array; never use an internal
  SHA-256 evidence ID as the model citation handle.

### `evidence[].role`

- **Type:** `"supporting"` or `"independent"`
- **Required:** conditional
- **Purpose:** preserves role distinctions when they materially affect
  interpretation.
- **Deterministic source:** selected evidence collection.
- **Rule:** omit `role` when all selected evidence has the same role and role
  does not affect a conflict or lifecycle distinction. Include it for every
  relevant evidence item when both supporting and independent evidence are
  present or when role is needed to interpret the answer context.
- **Constraints:** never infer or change role.

### `evidence[].source`

- **Type:** non-empty human-readable string
- **Required:** yes
- **Purpose:** source attribution for model understanding.
- **Deterministic source:** source filename or equivalent display name.
- **Constraints:** no source hashes, filesystem paths, database IDs, or
  credentials.

### `evidence[].location`

- **Type:** human-readable string or small structured location object
- **Required:** yes when a source location exists
- **Purpose:** identifies the page, sheet/row, cell, or equivalent display
  location.
- **Deterministic source:** selected evidence provenance fields.
- **Constraints:** no raw internal provenance arrays; CitationBuilder remains
  authoritative for exact restoration.

### `evidence[].text`

- **Type:** non-empty string for factual evidence
- **Required:** yes
- **Purpose:** exact extracted text or deterministic textual rendering of raw
  structured values.
- **Deterministic source:** extracted evidence text or a stable rendering of
  raw values.
- **Constraints:** no summarization, invented facts, or empty text for
  factual evidence.

### `evidence[].raw_values`

- **Type:** optional array or object
- **Required:** only when text rendering would lose material structured
  information
- **Purpose:** preserves structured values that cannot be faithfully
  represented in `text`.
- **Deterministic source:** selected evidence raw values.
- **Constraints:** omit when `text` already faithfully represents the values;
  never duplicate raw values unnecessarily.

## 5. Conflict Representation

Conflicts are represented by separate observations and a group linking their
array positions:

```json
{
  "observations": [
    {
      "evidence_ids": ["E1"],
      "preserve_separately": true
    },
    {
      "evidence_ids": ["E2"],
      "preserve_separately": true
    }
  ],
  "conflict_groups": [
    {
      "observation_indexes": [0, 1],
      "must_preserve_separately": true
    }
  ]
}
```

The group contains no conflict reason, internal ID, evidence text, or
provenance. The model must produce separate attributed claims when both
observations answer the question. It must not reconcile them merely because
they concern the same subject.

## 6. Lifecycle Representation

Lifecycle groups use the same index strategy:

```json
{
  "observations": [
    {
      "evidence_ids": ["E1"],
      "preserve_separately": true
    },
    {
      "evidence_ids": ["E2"],
      "preserve_separately": true
    }
  ],
  "lifecycle_groups": [
    {
      "observation_indexes": [0, 1],
      "must_distinguish": true
    }
  ]
}
```

The model must keep related planning, meeting, status, and completion records
distinct unless the evidence explicitly states that they are the same record.

## 7. Coverage Representation

Complete coverage:

```json
{
  "coverage": {
    "complete": true
  }
}
```

Incomplete coverage caused by the selector budget:

```json
{
  "coverage": {
    "complete": false,
    "reason": "selection_budget"
  }
}
```

Generic established incompleteness:

```json
{
  "coverage": {
    "complete": false,
    "reason": "incomplete"
  }
}
```

The compact context does not expose excluded evidence IDs, ranking scores,
selection reasons, or the full internal coverage telemetry.

## 8. Evidence Representation

The model-facing evidence item is:

```json
{
  "id": "E1",
  "source": "meeting.pdf",
  "location": "page 1",
  "text": "Exact extracted evidence text."
}
```

When roles materially matter:

```json
{
  "id": "E2",
  "role": "independent",
  "source": "report.pdf",
  "location": "page 2",
  "text": "Exact extracted evidence text."
}
```

The model sees enough display provenance to understand what `E1` means, but it
does not generate raw provenance. The application retains the original
selected evidence response for exact citation restoration.

## 9. Raw Structured Values

Raw values are optional. If deterministic text rendering faithfully preserves
the material values, do not add `raw_values`:

```json
{
  "id": "E1",
  "source": "attendance.xlsx",
  "location": "Faculty Attendance / B2",
  "text": "Person: [name] | Date: [date] | Status: Present"
}
```

If text alone would lose material structure, retain the values:

```json
{
  "id": "E7",
  "source": "attendance.xlsx",
  "location": "Faculty Attendance / B2",
  "text": "Person: [name] | Date: [date] | Status: Present",
  "raw_values": ["[name]", "[date]", "Present"]
}
```

The rendering rule must be deterministic, preserve column meaning, and never
create facts that were absent from the source.

## 10. Schema Invariants

The implementation must enforce or guarantee:

1. Every observation evidence handle refers to an evidence item.
2. Every conflict-group observation index is valid.
3. Every lifecycle-group observation index is valid.
4. Every evidence handle is unique within the evidence list.
5. Evidence text is non-empty for factual evidence.
6. The compact context contains no raw internal provenance arrays.
7. The compact context contains no evaluator obligations.
8. The compact context contains no expected answers.
9. The compact context contains no authentication or authorization data.
10. The compact context contains no secrets.
11. The internal Answer Plan is unchanged after transformation.
12. CitationBuilder continues using the original selected evidence response.
13. Model-facing observation indexes are never confused with citation handles.
14. No factual information is created during compaction.
15. Conflict and lifecycle group members remain represented by their
    evidence-backed observations.
16. Incomplete material coverage is represented as `complete: false`.
17. Unsupported or ambiguous internal diagnostics are not included in normal
    answerable contexts.

## 11. Internal → Model-Facing Transformation

The deterministic transformation should:

1. Read, but never mutate, the internal Answer Plan and selected evidence.
2. Assign stable `E1`, `E2`, ... handles using the existing selected-evidence
   ordering.
3. Create observations in deterministic internal-plan order.
4. Convert each observation's internal evidence IDs to handles.
5. Convert internal group observation IDs to array indexes.
6. Emit only non-empty conflict and lifecycle groups.
7. Set `coverage.complete` from material selector completeness and emit only
   an allowed controlled reason when incomplete.
8. Render source/location display values deterministically.
9. Render evidence text exactly, or render raw structured values without loss.
10. Include roles only under the defined conditional rule.
11. Return a new provider-neutral object.

No provider-specific formatting, prompt wording, or factual summarization
belongs in this transformation.

## 12. CitationBuilder Compatibility

The model outputs only handles:

```json
{
  "status": "answered",
  "claims": [
    {
      "text": "Grounded atomic claim.",
      "citation_refs": ["E1"]
    }
  ]
}
```

The application validates the model response and passes it, together with the
unchanged selected evidence response, to CitationBuilder. CitationBuilder
continues to restore:

- exact evidence IDs;
- source IDs;
- filenames;
- page, sheet, row, cell, and cell-range locations; and
- public citation objects.

The compact context is never passed as a replacement for the provenance
source used by CitationBuilder.

## 13. Claim Answer Contract Compatibility

The Claim Answer Contract remains exactly:

```json
{
  "status": "answered",
  "claims": [
    {
      "text": "atomic claim",
      "citation_refs": ["E1"]
    }
  ]
}
```

The compact context is input metadata only. It does not add claim fields,
status values, provenance objects, or public citation fields. Existing
validation continues to reject missing fields, extra fields, raw provenance,
unknown handles, empty answered claims, and duplicate citation references.

Clarification and insufficient-evidence handling remains deterministic before
generation where possible. If a provider receives one of those statuses, it
must not be given fabricated factual observations.

## 14. Security / Privacy

- Send only selected evidence required for the question.
- Do not expose source hashes, filesystem paths, database IDs, secrets,
  credentials, tokens, or authorization metadata.
- Include human-readable source and location only as needed for grounded
  attribution.
- Do not expose evaluator obligations, expected answers, or internal ranking
  telemetry.
- Do not trust model-generated provenance.
- Keep exact provenance in application state and restore it deterministically.
- Apply the existing evidence and context bounds before serialization.
- Keep the schema provider-neutral so changing providers does not change
  evidence semantics.

## 15. Representative Size Analysis

The persisted STEP 12H E014 context was transformed offline into the final
candidate schema. For the spreadsheet row whose extracted text was empty, the
candidate used a deterministic header/value rendering rather than an empty
factual text field.

Representative candidate metrics:

| Metric | Candidate |
|---|---:|
| Serialized character count | 3,715 |
| Maximum nesting depth | 5 |
| Evidence objects | 3 |
| Observations | 3 |
| Conflict groups | 1 |
| Lifecycle groups | 0 |
| Coverage fields | 2 |
| Citation handles | 3 |

Conceptual comparison with STEP 12H:

| Representation | Characters | Depth | Contract result |
|---|---:|---:|---|
| H1 full Answer Plan only | 5,073 | 6 | VALID |
| H3 compact plan plus nested evidence | 6,285 | 5 | VALID |
| H4 full plan plus compact evidence | 9,495 | 6 | INVALID |
| H5 compact plan plus compact evidence | 6,402 | 5 | VALID |
| H6 compact plan plus flat evidence | 6,240 | 5 | VALID |
| Final candidate, offline | 3,715 | 5 | Not tested; design only |

The smaller size is a complexity observation, not a correctness or model
quality guarantee. No Ollama request was made for the final candidate.

## 16. Generic Examples

### 16.1 Normal evidence

```json
{
  "answer_plan": {
    "observations": [
      {
        "evidence_ids": ["E1"],
        "preserve_separately": false
      }
    ],
    "conflict_groups": [],
    "lifecycle_groups": [],
    "coverage": {
      "complete": true
    }
  },
  "evidence": [
    {
      "id": "E1",
      "source": "meeting.pdf",
      "location": "page 1",
      "text": "An institutional activity was recorded."
    }
  ]
}
```

### 16.2 Conflict

```json
{
  "answer_plan": {
    "observations": [
      {
        "evidence_ids": ["E1"],
        "preserve_separately": true
      },
      {
        "evidence_ids": ["E2"],
        "preserve_separately": true
      }
    ],
    "conflict_groups": [
      {
        "observation_indexes": [0, 1],
        "must_preserve_separately": true
      }
    ],
    "lifecycle_groups": [],
    "coverage": {
      "complete": true
    }
  },
  "evidence": [
    {
      "id": "E1",
      "source": "record-a.pdf",
      "location": "page 1",
      "text": "Source A reports one observation."
    },
    {
      "id": "E2",
      "source": "record-b.pdf",
      "location": "page 2",
      "text": "Source B reports a different observation."
    }
  ]
}
```

### 16.3 Lifecycle

```json
{
  "answer_plan": {
    "observations": [
      {
        "evidence_ids": ["E1"],
        "preserve_separately": true
      },
      {
        "evidence_ids": ["E2"],
        "preserve_separately": true
      }
    ],
    "conflict_groups": [],
    "lifecycle_groups": [
      {
        "observation_indexes": [0, 1],
        "must_distinguish": true
      }
    ],
    "coverage": {
      "complete": true
    }
  },
  "evidence": [
    {
      "id": "E1",
      "source": "planning-record.pdf",
      "location": "page 1",
      "text": "A planned activity was discussed."
    },
    {
      "id": "E2",
      "source": "completion-record.pdf",
      "location": "page 3",
      "text": "A completed activity was recorded."
    }
  ]
}
```

### 16.4 Incomplete coverage

```json
{
  "answer_plan": {
    "observations": [
      {
        "evidence_ids": ["E1"],
        "preserve_separately": false
      }
    ],
    "conflict_groups": [],
    "lifecycle_groups": [],
    "coverage": {
      "complete": false,
      "reason": "selection_budget"
    }
  },
  "evidence": [
    {
      "id": "E1",
      "source": "record.pdf",
      "location": "page 1",
      "text": "The selected evidence supports a partial observation."
    }
  ]
}
```

## 17. Implementation Checklist for STEP 12J

The STEP 12J implementation scope is limited to the deterministic
compact-context builder:

- Add a provider-neutral transformation from the internal Answer Plan and
  selected evidence response to this schema.
- Keep the transformation side-effect-free and verify input immutability.
- Preserve existing `E1`, `E2`, ... handle mapping compatibility.
- Convert internal observation references to deterministic array indexes.
- Emit only non-empty conflict and lifecycle groups.
- Map material coverage incompleteness to the controlled coverage shape.
- Render human-readable source/location values without leaking internal hashes
  or paths.
- Render exact evidence text and structured values without factual loss.
- Apply the conditional evidence-role rule.
- Validate schema invariants deterministically.
- Keep CitationBuilder on the original selected evidence response.
- Add focused unit tests for normal, conflict, lifecycle, incomplete, raw
  structured-value, immutability, and provenance-preservation cases.
- Do not change the public Answer Contract or Claim Answer Contract.
- Do not change provider-specific prompting as part of the builder work.

No Ollama run or evaluation run is part of schema finalization.
