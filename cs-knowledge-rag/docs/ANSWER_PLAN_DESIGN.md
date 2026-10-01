# Generic Deterministic Answer Plan Design

## Status

This document is a design proposal only. It does not implement an Answer Plan,
change production behavior, run Ollama, or change retrieval, evidence
selection, prompting, validation, or evaluation.

## 1. Purpose and position in the pipeline

The proposed Answer Plan is a deterministic, provenance-preserving
intermediate representation between evidence selection and answer generation:

```text
Question
→ Query Understanding
→ Retrieval
→ EvidenceSelector
→ Answer Plan
→ Answer Generator
→ Claim-level output
→ CitationBuilder
→ Validator
```

The plan is **not an answer**, summary, ranking replacement, or LLM-generated
interpretation. It tells the generator which selected evidence-backed
observations are present, which groups must remain distinct, and where the
selected context is incomplete or ambiguous.

The primary objective is to make structure already discovered deterministically
by selection explicit to the generator. It must not manufacture factual
observations that are absent from selected records or evidence.

## 2. Design principles

1. **Evidence IDs remain the source references.** The plan refers to selected
   `evidence_id` values, not copied or paraphrased provenance.
2. **No question-specific rules.** The plan has no question IDs, filenames,
   event names, dates, people, or evaluation obligation definitions.
3. **No semantic guessing.** A plan may expose a selector-derived grouping, but
   it must not infer that two records are the same event merely because they
   share a date, name, or number.
4. **Selection remains authoritative for bounds.** The plan cannot re-add
   excluded evidence or silently exceed selector budgets.
5. **Distinct evidence stays distinct.** Conflict and lifecycle groups point to
   separate observations and their source evidence.
6. **Citation references are handles, not provenance.** The generator may emit
   short handles such as `E1`; the plan must not require raw source metadata in
   claims.
7. **Incompleteness is explicit.** Truncation, excluded group members, and
   unresolved query status must be represented rather than hidden.
8. **Stable output.** Equivalent selector output should produce equivalent plan
   structure and deterministic identifiers.

## 3. What is already available from current output

### 3.1 From `EvidenceSelector`

The current selector returns enough information to construct a useful first
version without modifying the selector:

- selected records and their `record_id` values;
- selected supporting evidence;
- selected independent evidence;
- evidence IDs and full provenance-bearing evidence objects;
- deterministic evidence roles (`supporting` or `independent`);
- selected and excluded evidence IDs;
- selector budgets and character usage;
- truncation and exclusion reasons;
- conflict flags and conflict coverage groups;
- lifecycle coverage groups;
- primary record-type coverage groups;
- `coverage_complete`;
- `record_coverage_complete`;
- `supporting_coverage_complete`;
- `independent_coverage_complete`;
- `conflict_coverage_complete`;
- warnings such as conflict evidence excluded by budget;
- `evidence_needed_to_answer`;
- `evidence_included_for_conflict`.

The selector's conflict groups currently identify evidence IDs, a group kind,
and a generic reason. Lifecycle groups similarly identify records indirectly
through their evidence IDs and state that the records describe related
lifecycle stages. This is sufficient to tell the generator to preserve the
members separately, even though it is not a complete natural-language
description of every fact.

### 3.2 From `EvidenceResponse`

The response also contains:

- the question;
- answerability status;
- query-understanding output;
- selected records;
- supporting and independent evidence collections;
- source grouping;
- basic context availability flags.

The plan should retain references to this context rather than duplicate full
record or evidence payloads. The generator can continue receiving the existing
evidence context alongside the plan.

### 3.3 From the existing citation flow

`CitationBuilder` deterministically maps `E1`, `E2`, and similar handles to
selected evidence. Its behavior does not need to change. The plan must
therefore use the same selected evidence set and the same handle assignment
order as the current generator context.

## 4. What is missing from current output

The current output does not expose a single model-facing object that answers
these structural questions:

- Which selected evidence units should be represented as separate
  observations?
- Which evidence units form one selector-derived conflict group?
- Which evidence units form one selector-derived lifecycle group?
- Which groups are incomplete because members were excluded?
- Which evidence references may support a claim, and which are independent
  corroboration?
- Whether the generator should qualify the answer because selection was
  truncated or coverage was incomplete?

The current selector also does **not** provide a general semantic fact
extraction layer. It cannot, without new logic, guarantee that every
attribute-level fact relevant to an arbitrary question has been identified as
an individual observation. The first Answer Plan must not pretend otherwise.
It can represent selected record/evidence observations and selector-derived
relationships; it cannot replace future query-aware fact planning.

## 5. Proposed minimal structure

The recommended first schema is intentionally smaller than a full semantic
answer specification:

```json
{
  "schema_version": "1.0",
  "answerability": "answerable",
  "observations": [
    {
      "observation_id": "obs-001",
      "record_ids": ["record-001"],
      "evidence_ids": ["evidence-001"],
      "roles": {
        "supporting": ["evidence-001"],
        "independent": []
      },
      "preserve_separately": true,
      "reason": "distinct selected record"
    }
  ],
  "conflict_groups": [
    {
      "group_id": "conflict:...",
      "observation_ids": ["obs-001", "obs-002"],
      "evidence_ids": ["evidence-001", "evidence-002"],
      "must_preserve": true,
      "complete": true,
      "reason": "selector reported differing observations"
    }
  ],
  "lifecycle_groups": [
    {
      "group_id": "coverage:...",
      "observation_ids": ["obs-003", "obs-004"],
      "evidence_ids": ["evidence-003", "evidence-004"],
      "must_distinguish": true,
      "complete": true,
      "reason": "selector reported related lifecycle stages"
    }
  ],
  "citation_requirements": {
    "claim_must_reference_selected_evidence": true,
    "allowed_evidence_ids": ["evidence-001", "evidence-002"],
    "supporting_evidence_ids": ["evidence-001"],
    "independent_evidence_ids": ["evidence-002"]
  },
  "coverage": {
    "complete": true,
    "truncated": false,
    "missing_groups": [],
    "excluded_evidence_ids": [],
    "warnings": []
  },
  "unsupported_or_ambiguous": []
}
```

### 5.1 Why this is the minimum useful shape

- `answerability` preserves the upstream status without inventing an answer.
- `observations` gives the generator an explicit unit of representation.
- `conflict_groups` and `lifecycle_groups` express the two relationships
  already detected by selection.
- `citation_requirements` prevents claims from citing evidence outside the
  selected context and preserves the supporting/independent distinction.
- `coverage` exposes incompleteness without converting it into an
  evaluation-only pass/fail judgment.
- `unsupported_or_ambiguous` gives the generator a deterministic place to
  qualify the answer when the pipeline knows that context is unresolved.

The plan should not include a generated observation sentence. The observation
label is an internal stable identifier; its factual wording must still come
from the evidence context.

### 5.2 Observation construction

The first implementation should construct observations conservatively:

1. Create an observation for each selected record that has selected evidence.
2. Create an evidence-backed observation for selected evidence not attached to
   a selected record.
3. Preserve the record/evidence relationship through `record_ids` and
   `evidence_ids`.
4. Mark observations referenced by a conflict or lifecycle group as
   `preserve_separately` / `must_distinguish`.
5. Do not merge observations merely because their text, date, person, or
   numeric value looks similar.
6. Use deterministic IDs derived from stable record/evidence IDs, not list
   position alone.

An observation may reference multiple evidence IDs when those units support the
same selected record. This does not mean the evidence should be merged in the
answer; conflict and lifecycle membership overrides any generic grouping.

### 5.3 “Required” observations

In this design, “required factual observations” means observations required by
the selected context's deterministic structure, not facts copied from
`ANSWER_OBLIGATIONS.json`.

An observation is structurally required when it is:

- attached to a selected record relevant to the query;
- in `evidence_needed_to_answer`;
- a member of a selected conflict group;
- a member of a selected lifecycle group; or
- the only selected evidence for a directly supporting result.

The plan must not claim that it has semantic completeness for every possible
attribute. If the selector does not identify a fact or group, the plan should
not invent one.

## 6. Conflict and lifecycle semantics

### 6.1 Conflict groups

Conflict groups are copied from selector-derived metadata by reference, with
plan-local observation IDs added. A conflict group means:

> These selected observations contain materially different source-reported
> values for a selector-detected dimension. Represent both separately and
> attribute each claim to its direct evidence.

It does **not** mean that one source is incorrect, that the values should be
reconciled, or that the generator should choose a winner.

If a conflict group is incomplete because one or more members were excluded,
`complete` must be `false`, the missing evidence IDs must appear in
`coverage.missing_groups`, and the generator must not present the selected
member as the complete conflict picture.

### 6.2 Lifecycle groups

Lifecycle groups mean that selected records describe related stages or states
that must remain distinct. The plan should instruct the generator to report
each supported stage separately when relevant.

It does not assert that the records are the same underlying record. The
generic reason should remain the selector's relationship description, such as
“related lifecycle stages,” without adding domain-specific stage names.

If lifecycle coverage is incomplete, the plan should expose the missing
evidence IDs and require qualification rather than silently collapsing the
available stage into a complete lifecycle.

## 7. Citation mapping and `CitationBuilder`

No `CitationBuilder` change is proposed.

The plan should use stable long `evidence_id` references internally. Before
serialization to the generator, the pipeline can derive the existing short
handle map from the same selected response using the existing citation-handle
ordering:

1. selected supporting evidence;
2. selected independent evidence;
3. deduplicate repeated evidence IDs.

The model-facing plan may include a compact `citation_ref` beside each
evidence ID, for example:

```json
{
  "evidence_id": "sha256:...:pdf-page:1",
  "citation_ref": "E1",
  "role": "supporting"
}
```

This is a serialization aid, not a new public citation contract. The generator
still emits only:

```json
{
  "status": "answered",
  "claims": [
    {
      "text": "one atomic evidence-backed claim",
      "citation_refs": ["E1"]
    }
  ]
}
```

The existing claim validator continues to reject unknown handles and raw
provenance. `CitationBuilder` continues to restore exact source, file, page,
sheet, row, cell, or range information from the selected evidence.

For a claim supported by two source observations, the model may cite both
handles. For a conflict, separate claims should cite the direct evidence for
each observation rather than citing an unrelated corroborating record.

## 8. Coverage, incompleteness, and unsupported areas

The plan should distinguish these conditions:

| Condition | Plan representation | Generator behavior |
|---|---|---|
| Complete selected context | `coverage.complete=true` | Answer from selected evidence |
| Selector truncation | `truncated=true`, exclusions and warnings | Avoid claiming exhaustive coverage |
| Incomplete conflict group | missing group with excluded IDs | Preserve selected observation and disclose limitation |
| Incomplete lifecycle group | missing group with excluded IDs | Do not collapse stages |
| No supporting evidence | empty supporting list | Use insufficient-evidence behavior upstream |
| Clarification required | `answerability=clarification_required` | Do not generate factual claims |
| Unsupported filter or unresolved ambiguity | `unsupported_or_ambiguous` entry | Ask for clarification or qualify |
| Independent evidence only | supporting list empty, independent list non-empty | Do not treat independent matches as direct support |

The plan does not change the current status behavior. It gives the generator
more structure only for `answerable` contexts. For
`insufficient_evidence` and `clarification_required`, the plan should contain
empty observations and no citation requirements, and the pipeline should
continue bypassing answer generation as it does today.

## 9. Where the component should live

### Recommendation: separate deterministic production component, invoked by `AnswerPipeline`

The Answer Plan should eventually be implemented as a small production
component, for example a pure `cs_ingest/answer_plan.py` module, with a
function or class that accepts the selected evidence response and returns a
plan.

It should not be embedded as ad hoc dictionary construction inside
`AnswerPipeline` because:

- plan construction has its own invariants and tests;
- it should be reusable by different answer generators;
- it should be inspectable independently of Ollama;
- it should remain deterministic and easy to compare in evaluation;
- it separates selection from model serialization.

`AnswerPipeline` should orchestrate it after `_selected_evidence_response`
creation and before `_generate`. The pipeline should pass the plan together
with the existing evidence context to the generator through the existing
provider-neutral boundary only after a future interface decision and focused
tests. This design task does not authorize that interface change.

An evaluation-only copy should not be created. The plan is intended to be
production metadata, while evaluation may inspect and score it later.

## 10. How this addresses the observed failures

The Step 11D audit found that selected conflict and lifecycle evidence was
present, but its group metadata was not exposed to the generator. The plan
would expose:

- the separate observation units;
- the conflict/lifecycle group membership;
- the requirement to preserve or distinguish members;
- the exact evidence references allowed for citations;
- incomplete coverage and excluded members.

This directly addresses a presentation and provenance-structure gap. It does
not prove that a small model will comply, and it does not justify increasing
the evidence budget. Step 11E showed that selecting more evidence alone did
not improve deterministic obligations and introduced citation regressions.

The plan also does not replace prompt instructions, claim validation, or
deterministic post-generation obligation evaluation. Those remain separate
controls.

## 11. Small JSON examples

The examples use generic identifiers deliberately. They are illustrative plan
objects, not production records or evaluation obligations.

### 11.1 Normal factual answer

```json
{
  "schema_version": "1.0",
  "answerability": "answerable",
  "observations": [
    {
      "observation_id": "obs-record-a",
      "record_ids": ["record-a"],
      "evidence_ids": ["evidence-a1"],
      "roles": {"supporting": ["evidence-a1"], "independent": []},
      "preserve_separately": true,
      "reason": "distinct selected record"
    }
  ],
  "conflict_groups": [],
  "lifecycle_groups": [],
  "citation_requirements": {
    "claim_must_reference_selected_evidence": true,
    "allowed_evidence_ids": ["evidence-a1"],
    "supporting_evidence_ids": ["evidence-a1"],
    "independent_evidence_ids": []
  },
  "coverage": {
    "complete": true,
    "truncated": false,
    "missing_groups": [],
    "excluded_evidence_ids": [],
    "warnings": []
  },
  "unsupported_or_ambiguous": []
}
```

### 11.2 Conflict

```json
{
  "schema_version": "1.0",
  "answerability": "answerable",
  "observations": [
    {
      "observation_id": "obs-source-a",
      "record_ids": ["record-a"],
      "evidence_ids": ["evidence-a1"],
      "roles": {"supporting": ["evidence-a1"], "independent": []},
      "preserve_separately": true,
      "reason": "member of selector conflict group"
    },
    {
      "observation_id": "obs-source-b",
      "record_ids": ["record-a"],
      "evidence_ids": ["evidence-b1"],
      "roles": {"supporting": ["evidence-b1"], "independent": []},
      "preserve_separately": true,
      "reason": "member of selector conflict group"
    }
  ],
  "conflict_groups": [
    {
      "group_id": "conflict:group-a",
      "observation_ids": ["obs-source-a", "obs-source-b"],
      "evidence_ids": ["evidence-a1", "evidence-b1"],
      "must_preserve": true,
      "complete": true,
      "reason": "selector reported differing source observations"
    }
  ],
  "lifecycle_groups": [],
  "citation_requirements": {
    "claim_must_reference_selected_evidence": true,
    "allowed_evidence_ids": ["evidence-a1", "evidence-b1"],
    "supporting_evidence_ids": ["evidence-a1", "evidence-b1"],
    "independent_evidence_ids": []
  },
  "coverage": {
    "complete": true,
    "truncated": false,
    "missing_groups": [],
    "excluded_evidence_ids": [],
    "warnings": []
  },
  "unsupported_or_ambiguous": []
}
```

### 11.3 Lifecycle distinction

```json
{
  "schema_version": "1.0",
  "answerability": "answerable",
  "observations": [
    {
      "observation_id": "obs-stage-a",
      "record_ids": ["record-a"],
      "evidence_ids": ["evidence-a1"],
      "roles": {"supporting": ["evidence-a1"], "independent": []},
      "preserve_separately": true,
      "reason": "member of selector lifecycle group"
    },
    {
      "observation_id": "obs-stage-b",
      "record_ids": ["record-b"],
      "evidence_ids": ["evidence-b1"],
      "roles": {"supporting": ["evidence-b1"], "independent": []},
      "preserve_separately": true,
      "reason": "member of selector lifecycle group"
    }
  ],
  "conflict_groups": [],
  "lifecycle_groups": [
    {
      "group_id": "coverage:lifecycle-a",
      "observation_ids": ["obs-stage-a", "obs-stage-b"],
      "evidence_ids": ["evidence-a1", "evidence-b1"],
      "must_distinguish": true,
      "complete": true,
      "reason": "records describe related lifecycle stages"
    }
  ],
  "citation_requirements": {
    "claim_must_reference_selected_evidence": true,
    "allowed_evidence_ids": ["evidence-a1", "evidence-b1"],
    "supporting_evidence_ids": ["evidence-a1", "evidence-b1"],
    "independent_evidence_ids": []
  },
  "coverage": {
    "complete": true,
    "truncated": false,
    "missing_groups": [],
    "excluded_evidence_ids": [],
    "warnings": []
  },
  "unsupported_or_ambiguous": []
}
```

### 11.4 Incomplete coverage

```json
{
  "schema_version": "1.0",
  "answerability": "answerable",
  "observations": [
    {
      "observation_id": "obs-selected-member",
      "record_ids": ["record-a"],
      "evidence_ids": ["evidence-a1"],
      "roles": {"supporting": ["evidence-a1"], "independent": []},
      "preserve_separately": true,
      "reason": "selected member of an incomplete group"
    }
  ],
  "conflict_groups": [
    {
      "group_id": "conflict:group-incomplete",
      "observation_ids": ["obs-selected-member"],
      "evidence_ids": ["evidence-a1", "evidence-b1"],
      "must_preserve": true,
      "complete": false,
      "reason": "one conflict member was excluded by selection budget"
    }
  ],
  "lifecycle_groups": [],
  "citation_requirements": {
    "claim_must_reference_selected_evidence": true,
    "allowed_evidence_ids": ["evidence-a1"],
    "supporting_evidence_ids": ["evidence-a1"],
    "independent_evidence_ids": []
  },
  "coverage": {
    "complete": false,
    "truncated": true,
    "missing_groups": [
      {
        "group_id": "conflict:group-incomplete",
        "missing_evidence_ids": ["evidence-b1"]
      }
    ],
    "excluded_evidence_ids": ["evidence-b1"],
    "warnings": ["A selected group is incomplete."]
  },
  "unsupported_or_ambiguous": [
    "The selected evidence does not establish the complete set of observations."
  ]
}
```

## 12. Recommended implementation sequence after approval

This design should be implemented incrementally:

1. Add a pure plan builder that consumes the existing selected response.
2. Add unit tests for deterministic IDs, role preservation, conflict groups,
   lifecycle groups, truncation, and non-answerable statuses.
3. Add a non-live serialization test showing the plan and existing evidence
   context together.
4. Integrate the plan into the provider-neutral generator boundary without
   changing the public Answer Contract or `CitationBuilder`.
5. Run focused tests before any controlled Ollama experiment.
6. Only then evaluate whether the plan changes deterministic obligation
   outcomes; do not infer improvement from plan shape alone.
