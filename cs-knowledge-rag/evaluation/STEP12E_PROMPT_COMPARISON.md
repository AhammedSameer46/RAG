# STEP 12E Prompt Comparison

This is a descriptive offline comparison. No Ollama request is made by this section.

| Metric | Step 11B-style | Step 12C |
|---|---:|---:|
| Context characters | 5497 | 10510 |
| Evidence objects | 3 | 3 |
| Answer Plan observations | 0 | 3 |
| Conflict groups | 0 | 1 |
| Lifecycle groups | 0 | 0 |
| Citation handles | 3 | 3 |
| Maximum nesting depth | 7 | 7 |

## Prompt instructions

- Production system prompt characters: 3092
- Production system prompt bullet instructions: 35

## Duplication and structure

- Evidence objects are the same selected wrapped evidence in both contexts.
- Step 12C adds deterministic plan metadata; it does not replace evidence.
- Provenance remains inside each evidence object and is not copied into claims.
- The plan contains evidence IDs and provenance references, so some identifiers are repeated between plan metadata and evidence objects.
- Conflict and lifecycle group membership is represented in the plan in addition to the underlying evidence text.
- No causal conclusion is drawn from these structural differences.
