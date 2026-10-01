# STEP 12F Prompt Isolation

## Objective

Isolate the D4 → D5 production-prompt failure boundary using the same E014 Answer Plan reconstruction. These are diagnostic requests, not evaluation attempts.

## STEP 12E baseline

- D1: VALID
- D2: VALID
- D3: VALID
- D4: VALID
- D5: INVALID

## Actual production instruction groups

The variants use these groups extracted from the current production prompt: contract/schema, evidence-grounding, atomic claims, citations, conflict/lifecycle, and other production formatting/Answer Plan rules. F7 uses the exact production prompt.

## F1–F7 results

| Variant | Prompt chars | HTTP | Latency | Contract valid | Error |
|---|---:|---:|---:|---|---|
| F1_D4_BASELINE | 5073 | 200 | 6.386s | True | None |
| F2_CONTRACT_SCHEMA | 5073 | 200 | 7.595s | True | None |
| F3_GROUNDING | 5073 | 200 | 7.334s | True | None |
| F4_ATOMIC_CLAIMS | 5073 | 200 | 4.961s | True | None |
| F5_CITATIONS | 5073 | 200 | 8.128s | True | None |
| F6_CONFLICT_LIFECYCLE | 5073 | 200 | 6.140s | True | None |
| F7_FULL_PRODUCTION_PROMPT | 10532 | 200 | 6.523s | False | {'type': 'OllamaResponseError', 'message': 'Ollama answer is missing required fields.'} |

## First observed valid → invalid transition

- `F6_CONFLICT_LIFECYCLE → F7_FULL_PRODUCTION_PROMPT`

## Raw failure modes

- **F7_FULL_PRODUCTION_PROMPT**: `{'type': 'OllamaResponseError', 'message': 'Ollama answer is missing required fields.'}`. The raw response was retained in the JSON artifact.

## Evidence-supported interpretation

- Contract instructions as the cause: not established unless F2 is the first invalid variant.
- Grounding instructions as the cause: not established unless F3 is the first invalid variant.
- Atomic-claim instructions as the cause: not established unless F4 is the first invalid variant.
- Citation instructions as the cause: not established unless F5 is the first invalid variant.
- Conflict/lifecycle instructions as the cause: not established unless F6 is the first invalid variant.
- Full prompt interaction: supported only if F1–F6 are valid and F7 is invalid.
- No isolated cause: supported if the sequence does not isolate one accumulated group.

## Next smallest controlled experiment

Use only the earliest observed transition, if any, and vary one production instruction group or formatting block at that boundary. Preserve the model, context, timeout, and single-attempt rule.
