# STEP 11D Evidence Context Audit

This audit uses the preserved `evaluation/step11b_smoke_test.json` outputs.
No Ollama request was made and no model output was regenerated.

## Scope and reconstruction limits

The current generator serializes:

```text
Question:
<question>

Evidence context (JSON):
<answer_context after citation_ref wrapping>
```

`_model_answer_context` copies `answer_context` and replaces each evidence
unit with:

```json
{
  "citation_ref": "E1",
  "evidence": { "...original evidence unit..." }
}
```

The Step 11B artifact does not persist:

- selected record objects;
- the `supporting_evidence` versus `independent_evidence` role for each
  selected evidence unit;
- the captured request payload or exact serialized prompt.

It does persist selected evidence units, selected evidence IDs, selector
coverage metadata, and the handle-to-evidence mapping. Therefore this audit
documents the exact recoverable evidence serialization and identifies where
the original full context cannot be proven from the artifact.

## Per-case recoverable context

All five cases selected three evidence units and used handles in deterministic
evidence order. The evidence units were wrapped with the handle immediately
adjacent to the evidence object in the model context.

| ID | Selected evidence count | Reconstructed evidence JSON characters* | Records persisted? | Roles persisted? | Truncated |
|---|---:|---:|---|---|---|
| E001 | 3 | 4,377 | No | No | Yes |
| E006 | 3 | 4,378 | No | No | Yes |
| E014 | 3 | 4,378 | No | No | Yes |
| E016 | 3 | 2,606 | No | No | Yes |
| E017 | 3 | 4,378 | No | No | Yes |

`*` This is the recoverable wrapped-evidence JSON size with records and role
split marked as unavailable; it is not claimed to be the exact original
prompt length.

### E001

- Selected evidence IDs:
  - `...:sheet:Events:row:2`
  - `...:pdf-page:1` — C-START event report
  - `...:pdf-page:1` — department meeting minutes
- Handles:
  - `E1` → event report
  - `E2` → department meeting minutes
  - `E3` → Events worksheet row 2
- Evidence ordering: event report, meeting minutes, Events row in the persisted
  selected-evidence list; handle ordering follows the persisted mapping.
- Selected-record objects: not persisted.
- Supporting/independent split: not persisted.
- Conflict metadata: participant conflict group complete; primary record-type
  coverage incomplete.
- Lifecycle metadata: none.

The two conflicting participant observations were selected together. The
coverage metadata was not sent to the model because `_model_answer_context`
serializes only `answer_context`, not `selection` or `coverage`.

### E006

- Selected evidence IDs:
  - event report PDF page 1
  - department meeting minutes PDF page 1
  - Events worksheet row 2
- Handles:
  - `E1` → event report
  - `E2` → meeting minutes
  - `E3` → Events worksheet row 2
- Evidence count: 3.
- Selected-record objects and supporting/independent role split: not persisted.
- Conflict metadata: participant conflict group complete.
- Lifecycle metadata: none.

The handle is adjacent to each evidence object in the serialized collection.
The model is not shown explicit semantic labels such as “coordinator source”
or “direct support”; it must read the evidence text and provenance fields.

### E014

- Selected evidence IDs:
  - event report PDF page 1
  - meeting minutes PDF page 1
  - Events worksheet row 2
- Handles:
  - `E1` → event report
  - `E2` → meeting minutes
  - `E3` → Events worksheet row 2
- Evidence count: 3.
- Selected-record objects and supporting/independent role split: not persisted.
- Conflict metadata: participant conflict group complete.
- Lifecycle metadata: none.

Both participant observations are present in the selected evidence and are
not separated into different requests. They are separated only as distinct
evidence objects within the collection.

### E016

- Selected evidence IDs:
  - Events worksheet row 3
  - Meeting Log row 5
  - an additional PDF page evidence unit
- Handles:
  - `E1` → Events worksheet row 3
  - `E2` → Meeting Log row 5
  - `E3` → PDF page evidence
- Evidence count: 3.
- Selected-record objects and supporting/independent role split: not persisted.
- Conflict metadata: none.
- Lifecycle metadata: lifecycle group complete; primary record-type coverage
  complete.

The planning and completed observations are present together in the selected
evidence collection. Lifecycle metadata is not exposed to the model.

### E017

- Selected evidence IDs:
  - event report PDF page 1
  - meeting minutes PDF page 1
  - Events worksheet row 2
- Handles:
  - `E1` → event report
  - `E2` → meeting minutes
  - `E3` → Events worksheet row 2
- Evidence count: 3.
- Selected-record objects and supporting/independent role split: not persisted.
- Conflict metadata: participant conflict group complete.
- Lifecycle metadata: none.

The count and both category observations are available in the selected
evidence text, but no model-visible coverage annotation identifies them as a
required conflict group.

## Serialization audit

### A. Can the model identify evidence supporting each record?

Partially. Each evidence object contains provenance fields such as
`evidence_id`, `filename`, `page`, `sheet`, `row`, and extracted/raw values.
However, the exact selected record objects were not persisted in Step 11B, and
the model context does not add an explicit evidence-to-record label beyond the
evidence object's own fields.

### B. Are conflicting observations presented together?

Yes, when selected. E001, E006, E014, and E017 contain both participant
source observations in the same evidence context. They are separate evidence
objects, not merged. The context does not explicitly label them as a conflict.

### C. Are lifecycle observations presented together?

Yes for E016. The planning meeting and completed event evidence are selected
together. The lifecycle group metadata is not included in the model-facing
context.

### D. Are citation handles adjacent to evidence?

Yes. The serializer wraps every evidence unit as an object containing
`citation_ref` immediately followed by its `evidence` object. This is a clear
local mapping and does not require a separate lookup table.

### E. Is conflict/lifecycle metadata exposed?

No. Selector metadata is stored in `selection` and `coverage`, but the user
prompt is built only from `answer_context`. The model receives evidence units
and their provenance, not `conflict_groups`, `coverage_groups`, or completeness
flags.

### F. Is irrelevant evidence consuming the budget?

The persisted selector metadata shows bounded selections of three units and
truncation for all five cases. E001 has incomplete primary record-type
coverage despite selecting three units. E006, E014, and E017 include the
Events worksheet row in addition to the two PDF observations. Whether that
row is irrelevant cannot be asserted: it is directly related to the same
C-START activity and is valid evidence. The concrete budget issue is that
the three-unit cap leaves no room for additional same-day records in E001.

### G. Are records/evidence duplicated or unnecessarily nested?

The production evidence context contains both `records` and evidence
collections, so the conceptual model can contain record-level and evidence-
level representations of related material. The exact record duplication cannot
be measured from Step 11B because selected records were not persisted.
Evidence itself is nested once under `{citation_ref, evidence}`; no duplicate
evidence object is created by the handle wrapper.

### H. Is there ambiguity between evidence roles and identifiers?

There are three distinct concepts:

1. evidence objects contain long `evidence_id` provenance identifiers;
2. `citation_ref` handles (`E1`, `E2`, `E3`) are short model output tokens;
3. `supporting_evidence` and `independent_evidence` are collection roles.

The handle mapping is deterministic and adjacent to each evidence object.
However, role semantics and selector coverage semantics are not included in
the model context. The Step 11B artifact also cannot prove which persisted
selected evidence belonged to which role.

## Concrete conclusion

- `CONTEXT_CLEAR`: citation handles are adjacent to evidence, provenance is
  present, and selected conflicts/lifecycle observations are co-located.
- `CONTEXT_HAS_PRESENTATION_PROBLEMS`: conflict and lifecycle groups are not
  explicitly labeled, coverage metadata is hidden, and Step 11B did not retain
  enough telemetry to reconstruct the full exact prompt.
- `CONTEXT_HAS_RELEVANCE/BUDGET_PROBLEMS`: E001 reports incomplete primary
  record-type coverage under the three-unit budget; all five contexts are
  truncated.
- `CONTEXT_HAS_PROVENANCE_MAPPING_PROBLEMS`: no production handle mapping
  defect was found, but the Step 11B evaluation artifact does not persist
  selected records or evidence roles, preventing complete auditability.

These conclusions are based on the serialized-context implementation and
persisted Step 11B fields, not on subjective assumptions about model ability.
