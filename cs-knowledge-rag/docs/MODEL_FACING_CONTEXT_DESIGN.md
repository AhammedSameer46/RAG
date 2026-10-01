# Model-Facing Context Design

## 1. Problem statement

The internal Answer Plan is intentionally rich deterministic metadata. It
contains selector and provenance details that are useful to the application
but are not all necessary for an answer model. Exposing the complete internal
structure can duplicate metadata, increase context complexity, and make the
provider-facing contract harder to reason about.

The model-facing context needs a smaller, provider-neutral representation that
still lets a model:

- make claims only from supplied evidence;
- cite stable evidence handles;
- preserve conflicting observations;
- distinguish lifecycle stages;
- recognize incomplete evidence coverage; and
- avoid treating Answer Plan metadata as source evidence.

The model must not reconstruct provenance, resolve conflicts, or infer missing
evidence. Those responsibilities remain deterministic application behavior.

## 2. Findings from Steps 12D–12H

### STEP 12D

After Answer Plan integration, all five controlled live attempts returned HTTP
200 but failed claim-level parsing. No deterministic obligation result was
available from those malformed outputs.

### STEP 12E

The minimal schema/context progression was valid through D4. The full
production prompt and model-facing context was invalid at D5. The first
observed boundary was D4 to D5.

### STEP 12F

F1 through F6 were valid. F7, using the exact full production prompt and
Step 12C context, was invalid. No staged contract, grounding, atomic-claim,
citation, or conflict/lifecycle group was individually isolated.

### STEP 12G

Removing the remaining Answer Plan/metadata material, additional formatting
rules, or all remaining non-F6 material did not restore validity. No
individual remaining production prompt block was isolated.

### STEP 12H

The observed sequence was:

```text
H1 VALID
H2 VALID
H3 VALID
H4 INVALID
H5 VALID
H6 VALID
H7 VALID
```

H4 used a compact evidence wrapper and had the largest context. H5 used both
compact Answer Plan and compact evidence and was valid. These were one-shot
diagnostic requests, so H4 does not prove a deterministic production defect or
establish causality. It does support designing a compact representation that
avoids unnecessary nesting and duplicated metadata.

## 3. Internal Answer Plan vs model-facing context

### A. Internal Answer Plan

The internal plan remains the authoritative deterministic application
structure. It may include:

- schema version;
- generated observation and group identifiers;
- record identifiers;
- evidence identifiers;
- supporting and independent roles;
- preservation reasons;
- matched fields;
- provenance references;
- conflict and lifecycle groups;
- selector coverage;
- exclusions and warnings; and
- unsupported or ambiguous conditions.

This structure supports deterministic selection, evaluation, diagnostics, and
future application behavior. It is not a model output contract.

### B. Model-facing context

The model-facing context is a deliberately reduced view. It communicates only
the evidence organization rules and source material needed to produce atomic
claims. It must not expose internal selector telemetry merely because that
telemetry exists.

### C. Public Answer Contract

The public contract remains unchanged:

```json
{
  "status": "answered | insufficient_evidence | clarification_required",
  "answer": "string",
  "citations": []
}
```

The internal model response remains the validated claim-level contract:

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

These three structures must not be merged.

## 4. Proposed model-facing schema

The following is the proposed provider-neutral shape. The user question is
provided separately and is not repeated inside each object.

```json
{
  "answer_plan": {
    "observations": [
      {
        "id": "O1",
        "evidence_ids": ["E1"],
        "preserve_separately": false
      }
    ],
    "conflict_groups": [
      {
        "id": "C1",
        "observation_ids": ["O1", "O2"],
        "must_preserve_separately": true
      }
    ],
    "lifecycle_groups": [
      {
        "id": "L1",
        "observation_ids": ["O3", "O4"],
        "must_distinguish": true
      }
    ],
    "coverage_complete": true,
    "coverage_warning": null
  },
  "evidence": [
    {
      "id": "E1",
      "role": "supporting",
      "source": "meeting.pdf",
      "location": "page 1",
      "text": "Exact extracted evidence text."
    }
  ]
}
```

The original question remains a separate input:

```text
Question: What happened on [date]?
```

The schema is a model-facing view only. It does not replace the internal
Answer Plan or selected evidence response.

## 5. Field-by-field analysis

| Field | Keep/Remove | Reason |
|---|---|---|
| `answer_plan` | Keep | Separates deterministic organization metadata from source evidence. |
| `answer_plan.observations` | Keep | Links preservation units to evidence handles without copying facts into the plan. |
| `observations[].id` | Keep | Gives conflict/lifecycle groups a compact deterministic reference. It is not a citation handle. |
| `observations[].evidence_ids` | Keep | Tells the model which evidence supports an observation. |
| `observations[].preserve_separately` | Keep | Communicates a required separation without asking the model to infer it. |
| `conflict_groups` | Keep when non-empty | Explicitly links observations that must remain separate. |
| `conflict_groups[].id` | Keep | Stable internal reference for the model-facing plan only. |
| `conflict_groups[].observation_ids` | Keep | Avoids repeating evidence text and identifies the observations in conflict. |
| `must_preserve_separately` | Keep | Makes conflict preservation explicit. |
| `lifecycle_groups` | Keep when non-empty | Prevents planning, meeting, status, and completion records from being merged. |
| `lifecycle_groups[].observation_ids` | Keep | Identifies related but distinct observations. |
| `must_distinguish` | Keep | Makes lifecycle separation explicit. |
| `coverage_complete` | Keep | Tells the model whether selected evidence is known to be incomplete. |
| `coverage_warning` | Keep when incomplete | Gives a minimal actionable warning without exposing selector telemetry. |
| `evidence` | Keep | Source evidence remains the factual basis of every claim. |
| `evidence[].id` | Keep | Stable citation handle such as `E1`; this is the only identifier the model should cite. |
| `evidence[].role` | Keep | Preserves supporting versus independent context when that distinction affects interpretation. |
| `evidence[].source` | Keep | Helps the model attribute observations and distinguish sources. |
| `evidence[].location` | Keep | Provides human-readable source location while CitationBuilder retains exact provenance. |
| `evidence[].text` | Keep | Preserves exact extracted text or a deterministic textual representation of raw values. |
| `evidence[].raw_values` | Keep only when text alone loses meaning | Needed for table values or structured facts that cannot be faithfully represented as text. |
| `schema_version` | Remove | The model does not need internal version negotiation. |
| `record_ids` | Remove | Usually derivable from evidence and not needed for citation construction. Preserve only if a future model behavior demonstrably requires record distinction not expressible through observations. |
| `matched_fields` | Remove | Retrieval diagnostics, not model-facing evidence organization. |
| `provenance_refs` | Remove | Duplicates evidence source/location and risks encouraging raw provenance generation. |
| `reason` | Remove | Selector explanation is internal telemetry and can increase prompt complexity. |
| `excluded_evidence` | Remove | Replace with the single coverage signal and minimal warning. |
| `warnings` | Remove except for one coverage warning | Avoids exposing unrelated selector diagnostics. |
| `unsupported_or_ambiguous` | Keep only when answerability is not answerable | A compact answerability condition may be needed to prevent unsupported answering; do not include it for ordinary answerable contexts. |

Removing a field must not remove factual evidence, citation handles, source
locations, conflict membership, lifecycle membership, or material coverage
limitations.

## 6. Conflict representation

Conflicting source observations remain separate evidence-backed observations.
The plan links them without reconciling them.

```json
{
  "answer_plan": {
    "observations": [
      {
        "id": "O1",
        "evidence_ids": ["E1"],
        "preserve_separately": true
      },
      {
        "id": "O2",
        "evidence_ids": ["E2"],
        "preserve_separately": true
      }
    ],
    "conflict_groups": [
      {
        "id": "C1",
        "observation_ids": ["O1", "O2"],
        "must_preserve_separately": true
      }
    ],
    "coverage_complete": true
  },
  "evidence": [
    {
      "id": "E1",
      "role": "supporting",
      "source": "source-a.pdf",
      "location": "page 2",
      "text": "Source A observation."
    },
    {
      "id": "E2",
      "role": "independent",
      "source": "source-b.pdf",
      "location": "page 4",
      "text": "Source B observation."
    }
  ]
}
```

The model may produce two separate claims, each citing the evidence that
supports it. It must not produce a reconciled value unless the evidence
explicitly supports reconciliation.

## 7. Lifecycle representation

Related records across time remain distinct even when they share a topic,
person, event name, or date.

```json
{
  "answer_plan": {
    "observations": [
      {
        "id": "O1",
        "evidence_ids": ["E1"],
        "preserve_separately": true
      },
      {
        "id": "O2",
        "evidence_ids": ["E2"],
        "preserve_separately": true
      }
    ],
    "lifecycle_groups": [
      {
        "id": "L1",
        "observation_ids": ["O1", "O2"],
        "must_distinguish": true
      }
    ],
    "coverage_complete": true
  },
  "evidence": [
    {
      "id": "E1",
      "role": "supporting",
      "source": "planning-record.pdf",
      "location": "page 1",
      "text": "A planned activity was discussed."
    },
    {
      "id": "E2",
      "role": "supporting",
      "source": "completion-record.pdf",
      "location": "page 3",
      "text": "A completed activity was recorded."
    }
  ]
}
```

The lifecycle group is a distinction instruction, not a factual assertion.
Claims must cite the underlying evidence handles.

## 8. Coverage and incompleteness representation

The model-facing contract should expose only whether material selected
coverage is complete and, when it is not, one concise warning.

Complete coverage:

```json
{
  "coverage_complete": true,
  "coverage_warning": null
}
```

Incomplete coverage:

```json
{
  "coverage_complete": false,
  "coverage_warning": "Some relevant evidence was excluded by the selection budget."
}
```

The warning must not contain the entire selector result, ranking scores,
excluded-unit diagnostics, or internal reasons. If coverage is incomplete, the
model must not fill the gap with outside knowledge.

## 9. Evidence and provenance representation

Each evidence item must contain:

- a stable model citation handle;
- the evidence ID used internally;
- supporting or independent role where relevant;
- source identity;
- a human-readable location; and
- exact evidence text or a faithful representation of raw structured values.

Example:

```json
{
  "id": "E1",
  "role": "supporting",
  "source": "meeting.pdf",
  "location": "page 1",
  "text": "Exact extracted evidence text."
}
```

The model outputs only:

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

CitationBuilder continues to map `E1` to the exact evidence ID, source ID,
filename, page/sheet/row/cell location, and other stored provenance. The model
does not generate or modify those objects.

For structured spreadsheet evidence, `text` should be a deterministic
rendering of the relevant values. A separate raw-values field is justified
only when rendering as text would lose a material value or distinction.

## 10. Example normal case

Question:

```text
What happened on [date]?
```

Model context:

```json
{
  "answer_plan": {
    "observations": [
      {
        "id": "O1",
        "evidence_ids": ["E1"],
        "preserve_separately": false
      }
    ],
    "conflict_groups": [],
    "lifecycle_groups": [],
    "coverage_complete": true,
    "coverage_warning": null
  },
  "evidence": [
    {
      "id": "E1",
      "role": "supporting",
      "source": "meeting.pdf",
      "location": "page 1",
      "text": "An institutional activity was recorded on the requested date."
    }
  ]
}
```

## 11. Example conflict case

```json
{
  "answer_plan": {
    "observations": [
      {
        "id": "O1",
        "evidence_ids": ["E1"],
        "preserve_separately": true
      },
      {
        "id": "O2",
        "evidence_ids": ["E2"],
        "preserve_separately": true
      }
    ],
    "conflict_groups": [
      {
        "id": "C1",
        "observation_ids": ["O1", "O2"],
        "must_preserve_separately": true
      }
    ],
    "lifecycle_groups": [],
    "coverage_complete": true,
    "coverage_warning": null
  },
  "evidence": [
    {
      "id": "E1",
      "role": "supporting",
      "source": "record-a.pdf",
      "location": "page 1",
      "text": "Source A reports one observation."
    },
    {
      "id": "E2",
      "role": "independent",
      "source": "record-b.pdf",
      "location": "page 2",
      "text": "Source B reports a different observation."
    }
  ]
}
```

The expected model behavior is two attributed claims rather than one
reconciled claim.

## 12. Example lifecycle case

```json
{
  "answer_plan": {
    "observations": [
      {
        "id": "O1",
        "evidence_ids": ["E1"],
        "preserve_separately": true
      },
      {
        "id": "O2",
        "evidence_ids": ["E2"],
        "preserve_separately": true
      }
    ],
    "conflict_groups": [],
    "lifecycle_groups": [
      {
        "id": "L1",
        "observation_ids": ["O1", "O2"],
        "must_distinguish": true
      }
    ],
    "coverage_complete": true,
    "coverage_warning": null
  },
  "evidence": [
    {
      "id": "E1",
      "role": "supporting",
      "source": "planning.pdf",
      "location": "page 1",
      "text": "A planned activity was discussed."
    },
    {
      "id": "E2",
      "role": "supporting",
      "source": "event-report.pdf",
      "location": "page 2",
      "text": "A completed activity was recorded."
    }
  ]
}
```

The expected model behavior is to keep the planning and completion claims
distinct.

## 13. Example incomplete-coverage case

```json
{
  "answer_plan": {
    "observations": [
      {
        "id": "O1",
        "evidence_ids": ["E1"],
        "preserve_separately": false
      }
    ],
    "conflict_groups": [],
    "lifecycle_groups": [],
    "coverage_complete": false,
    "coverage_warning": "Some relevant evidence was excluded by the selection budget."
  },
  "evidence": [
    {
      "id": "E1",
      "role": "supporting",
      "source": "record.pdf",
      "location": "page 1",
      "text": "The selected evidence supports a partial observation."
    }
  ]
}
```

The model may answer only from `E1` and must not invent the excluded
information.

## 14. Serialization guidelines

1. Serialize one provider-neutral object with `answer_plan` and `evidence`.
2. Supply the original question separately and exactly once.
3. Use deterministic key ordering where the provider adapter serializes JSON.
4. Use compact identifiers (`O1`, `E1`, `C1`, `L1`) only as model-facing
   references; preserve the full internal identifiers in application state.
5. Keep evidence text exact; do not summarize it while constructing the
   model-facing view.
6. Do not duplicate evidence text inside observations or conflict groups.
7. Include conflict and lifecycle groups only when they are non-empty.
8. Include `coverage_warning` only when `coverage_complete` is false.
9. Keep source and location fields human-readable, but let CitationBuilder
   remain authoritative for exact provenance.
10. Do not serialize excluded evidence or selector ranking telemetry.
11. Bound the final serialized context using the existing selection policy.
12. If a provider requires a textual prompt, wrap the same serialized object
   without changing its fields or meanings.
13. Provider adapters may format transport envelopes differently, but the
   semantic model-facing contract must remain unchanged.

## 15. What is intentionally not exposed to the LLM

The following remain application-internal unless a later experiment proves a
specific need:

- internal Answer Plan schema version;
- full record identifiers;
- matched retrieval fields;
- selector scores and ranking reasons;
- excluded evidence lists;
- provenance reference arrays;
- raw selection telemetry;
- internal warnings unrelated to coverage;
- evaluator obligations;
- expected answers;
- obligation statuses;
- citation-builder implementation details;
- authentication or authorization metadata;
- filesystem paths or secrets;
- provider-specific transport settings.

The model must never be asked to generate raw provenance, reconcile source
conflicts, or reconstruct omitted evidence.

## 16. Provider-neutral interface

The application should conceptually provide a value such as:

```python
ModelFacingContext = {
    "answer_plan": {
        "observations": [...],
        "conflict_groups": [...],
        "lifecycle_groups": [...],
        "coverage_complete": True,
        "coverage_warning": None,
    },
    "evidence": [...],
}
```

The interface is a data contract, not an Ollama-specific prompt. A provider
adapter receives:

```text
question: str
model_context: ModelFacingContext
```

It is responsible only for serialization and transport. It must not add
provider-specific factual fields or alter evidence semantics.

## 17. Compatibility with existing CitationBuilder

Compatibility is preserved because citation handles remain the model-facing
identifiers and continue to map to the selected evidence response. The model
outputs `citation_refs` such as `E1`; the application passes the validated
claim response and the unchanged selected evidence response to CitationBuilder.

CitationBuilder remains responsible for:

- validating referenced handles;
- restoring exact evidence IDs;
- restoring source IDs and filenames;
- restoring page, sheet, row, cell, and other locations; and
- producing the public citation objects.

The compact context must not replace or mutate the evidence response used by
CitationBuilder.

## 18. Compatibility with existing Claim Answer Contract

The claim-level output remains exactly:

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

The model-facing plan is input metadata. It does not add fields to claims,
status values, citation objects, or the public Answer Contract. The existing
validator continues to reject:

- missing `status` or `claims`;
- extra top-level fields;
- raw provenance in claims;
- unknown citation handles;
- empty citations for answered claims; and
- duplicate citation references within one claim.

Clarification and insufficient-evidence behavior remains deterministic and
does not require factual observations in the model-facing plan.

## 19. Security and privacy considerations

- Send only selected evidence needed for the question.
- Do not expose credentials, access tokens, filesystem paths, or internal
  authorization metadata.
- Treat source names and locations as potentially sensitive institutional
  metadata and include only what is needed for grounded attribution.
- Preserve exact evidence for correctness, but apply the existing context
  bounds to reduce unnecessary disclosure.
- Do not expose evaluator obligations or expected answers to the model.
- Do not trust model-generated provenance; restore provenance from application
  state.
- Keep the compact context provider-neutral so changing providers does not
  require changing evidence semantics.
- Log diagnostic payloads only under the project’s controlled evaluation
  process and avoid storing secrets.

## 20. Open questions

1. Should `role` remain mandatory for every evidence item, or only when
   supporting and independent evidence coexist?
2. Should source and location be one display string or a small structured
   object for provider-neutral consistency?
3. What exact deterministic rendering should represent spreadsheet raw values?
4. Should unsupported or ambiguous conditions be represented in the compact
   plan, or handled entirely before generation?
5. Should `coverage_warning` be a fixed controlled vocabulary rather than
   generated text?
6. What maximum serialized model-facing context should be approved for each
   provider?
7. Should a compact context builder preserve a mapping from compact handles to
   full selected evidence explicitly, or rely only on the unchanged response
   passed to CitationBuilder?
8. What repeated-run protocol is required before treating a context-shape
   effect as deterministic?

Implementation decision pending review.

Minimum decisions that must be approved before STEP 12J:

- final model-facing schema;
- required fields;
- conflict representation;
- lifecycle representation;
- coverage representation;
- evidence/provenance representation;
- serialization format;
- maximum context policy.
