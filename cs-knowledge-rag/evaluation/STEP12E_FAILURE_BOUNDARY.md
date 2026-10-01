# STEP 12E Failure Boundary

## Diagnostic scope

D1–D5 are isolated diagnostic requests, not evaluation attempts. No E001/E006/E014/E016/E017 question was rerun.

| ID | Prompt chars | HTTP | Latency | Contract | Parser/contract error |
|---|---:|---:|---:|---|---|
| D1 | 35 | 200 | 9.541s | True | None |
| D2 | 92 | 200 | 2.743s | True | None |
| D3 | 5497 | 200 | 3.745s | True | None |
| D4 | 5073 | 200 | 3.843s | True | None |
| D5 | 10532 | 200 | 9.379s | False | {'type': 'OllamaResponseError', 'message': 'Ollama answer is missing required fields.'} |

## Observed boundary

- Result: **D4 → D5: first observed valid-to-invalid transition**
- Contract-valid sequence: `[True, True, True, True, False]`
- This conclusion uses only the recorded diagnostic responses.

## Interpretation

- Answer Plan implicated: **not established**. D4, which included the Answer
  Plan without the full production instructions, returned a valid claim-level
  response.
- Parser implicated: **no parser defect observed**. D5 returned a valid Ollama
  JSON envelope, but its inner `response` was a JSON object with only a
  `response` field containing Markdown-like prose and record/evidence IDs. It
  did not contain the required top-level `status` and `claims` fields. The
  parser correctly rejected that structurally invalid model output.
- Full production prompt/context implicated: **yes, as the first observed
  boundary**. D5 is the only invalid diagnostic; it combines the production
  system instructions with the Step 12C context.

The D5 inner response began as a prose/list response identifying records and
raw evidence IDs. It was not a structurally valid claim-level answer, so this
was a model-format failure rather than a parser rejection of a valid claim
response.

## Next smallest controlled experiment

Use the earliest observed transition only, with one narrowly varied payload at that boundary; preserve the same model, timeout, and single-attempt rule. Do not change production code until that experiment identifies a reproducible cause.
