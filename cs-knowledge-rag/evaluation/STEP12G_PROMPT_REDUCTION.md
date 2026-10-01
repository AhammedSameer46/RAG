# STEP 12G Prompt Reduction

## Objective

Isolate the remaining full-production-prompt failure observed in STEP 12F. This is a diagnostic experiment only.

## STEP 12F findings

F1-F6 were valid and F7 was invalid. The observed boundary was F6 → F7.

## Actual remaining production-prompt blocks

- Answer Plan/metadata instructions are explicit in the production prompt.
- Additional output-format restrictions are explicit in the production prompt.
- Model-knowledge and insufficient-evidence rules are already represented in the previously isolated grounding/contract groups; G4 and G5 are therefore not applicable.

## G1-G6 configuration and results

| Variant | Removed | System chars | HTTP | Contract valid | Error |
|---|---|---:|---:|---|---|
| G1_FULL_PRODUCTION_BASELINE | none | 3092 | 200 | False | {'type': 'OllamaResponseError', 'message': 'Ollama answer is missing required fields.'} |
| G2_WITHOUT_ANSWER_PLAN_METADATA | Answer Plan/metadata | 2710 | 200 | False | {'type': 'OllamaResponseError', 'message': 'Ollama answer is missing required fields.'} |
| G3_WITHOUT_EXTRA_FORMATTING | extra formatting | 2982 | 200 | False | {'type': 'OllamaResponseError', 'message': 'Ollama answer is missing required fields.'} |
| G4_WITHOUT_META_RESTRICTIONS | none | 0 | None | None | None |
| G5_WITHOUT_UNSUPPORTED_HANDLING | none | 0 | None | None | None |
| G6_MINIMAL_REMAINING_PROMPT | none | 2404 | 200 | False | {'type': 'OllamaResponseError', 'message': 'Ollama answer is missing required fields.'} |

## First INVALID → VALID transition

- `none`

## Evidence-supported interpretation

- No validity restoration was observed.
- A specific prompt block is implicated only if removing that block restores validity while the exact G1 baseline is invalid.
- If G2-G5 remain invalid and G6 is valid, no individual remaining block is isolated; the evidence supports an interaction or prompt-length/context-shape effect.

## Smallest next controlled experiment

Use the first observed restoration, if any, and split only that remaining block into smaller exact sub-blocks. If no individual removal restores validity, vary one prompt-length or context-shape factor while preserving the production instructions.
