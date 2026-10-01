# STEP 11C Offline Re-evaluation

This report applies the corrected deterministic phrase normalizer to the preserved Step 11B model outputs. No model calls were made and no model output was regenerated.

## Results

| ID | Old Step 11B | Corrected | Changed | Reason |
|---|---|---|---|---|
| E001 | PARTIAL | PARTIAL | False | no classification change |
| E006 | PASS | PASS | False | no classification change |
| E014 | FAIL | PARTIAL | True | number-word normalization changed phrase matching |
| E016 | PARTIAL | PARTIAL | False | no classification change |
| E017 | FAIL | FAIL | False | no classification change |

## Changed cases

### E014

- Old missing obligations: `['cstart_participant_category', 'participant_count']`
- Corrected missing obligations: `[]`
- Old wrong citations: `[]`
- Corrected wrong citations: `['participant_count']`
- Cause: evaluator-only lexical normalization; model behavior and citations were unchanged.

## Interpretation

- Numeric forms such as `45`, `Forty-five`, and `forty five` are treated as the same explicit number.
- Case, repeated whitespace, and surrounding punctuation are normalized.
- Different numbers, participant categories, lifecycle states, date ranges, evidence sources, and citation correctness remain distinct.
- Step 11B artifacts were not overwritten.
