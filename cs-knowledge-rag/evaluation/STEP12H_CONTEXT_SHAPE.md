# STEP 12H Context Shape

## Objective

Determine whether a structural feature of the E014 model-facing context changes Gemma3:4b claim-level contract validity. This is diagnostic only.

## Baseline findings

- STEP 12E: D1-D4 valid, D5 invalid.
- STEP 12F: F1-F6 valid, F7 invalid.
- STEP 12G: G1, G2, G3, and G6 invalid.

## Representation and equivalence

All variants use the same E014 question and the same selected evidence values. Compact forms retain observation/evidence IDs, citation handles, source identity, locations, and evidence values. Only serialization and nesting change.

## Results

| Variant | Representation | Context chars | Depth | Evidence objects | Plan observations | HTTP | Contract | Error |
|---|---|---:|---:|---:|---:|---:|---|---|
| H1_D4_BASELINE | question_plus_full_answer_plan | 5073 | 6 | 0 | 3 | 200 | True | None |
| H2_EVIDENCE_ONLY | question_plus_evidence | 4361 | 5 | 3 | 0 | 200 | True | None |
| H3_COMPACT_ANSWER_PLAN | question_plus_compact_plan_plus_evidence | 6285 | 5 | 3 | 3 | 200 | True | None |
| H4_COMPACT_EVIDENCE_WRAPPER | question_plus_full_plan_plus_compact_evidence | 9495 | 6 | 3 | 3 | 200 | False | {'type': 'OllamaResponseError', 'message': 'Ollama answer is missing required fields.'} |
| H5_COMPACT_CONTEXT | question_plus_compact_plan_plus_compact_evidence | 6402 | 5 | 3 | 3 | 200 | True | None |
| H6_FLAT_CONTEXT | question_plus_compact_plan_plus_flat_evidence | 6240 | 5 | 3 | 3 | 200 | True | None |
| H7_PLAIN_TEXT_CONTEXT | plain_text | 5260 | 5 | 3 | 3 | 200 | True | None |

## First transition

- The first transition is recorded from the observed sequence only; no causal conclusion is made from a single run.

## Interpretation

Interpretation is limited to contract validity. If compact representations remain invalid or results vary across equivalent representations, no deterministic context-shape boundary is established and model/output instability remains a hypothesis.
