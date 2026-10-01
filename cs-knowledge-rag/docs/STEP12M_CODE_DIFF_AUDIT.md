# STEP 12M Code-Diff Audit

## 1. Audit Scope

Audited the five requested production files:

- `cs_ingest/answer_pipeline.py`
- `cs_ingest/ollama_answer_generator.py`
- `cs_ingest/answer_generator.py`
- `cs_ingest/mock_answer_generator.py`
- `cs_ingest/model_facing_context.py`

Also inspected the directly relevant modified tests covering the pipeline/provider
boundary, compact-context serialization, Answer Plan preservation, citation
restoration, immutability, handle mapping, and provider error handling.

No Ollama request was made. No protected historical evaluation artifact was
modified.

## 2. EvidenceResponse → Model-Facing Context Flow

The production flow is:

1. `AnswerPipeline.run()` builds the full `EvidenceResponse`
   (`answer_pipeline.py:58-62`).
2. When selection is enabled, `_selected_evidence_response()` creates a deep
   selected response containing only selected records and selected supporting
   and independent evidence (`answer_pipeline.py:68-76`, `105-132`).
3. The selected response is deep-copied and enriched with the deterministic
   Answer Plan (`answer_pipeline.py:73-75`).
4. `build_model_facing_context()` converts that enriched response into the
   compact `{answer_plan, evidence}` view (`answer_pipeline.py:77`,
   `model_facing_context.py:29-73`).
5. Only the compact context is passed to the generator
   (`answer_pipeline.py:87-90`).
6. The selected rich response remains available for claim validation,
   CitationBuilder, final public-contract validation, and the returned audit
   result (`answer_pipeline.py:91-96`).

**Result: PASS.** The authoritative internal evidence response is not replaced
by the compact view.

Non-answerable states still bypass generation and return the existing public
`insufficient_evidence` or `clarification_required` contract
(`answer_pipeline.py:78-86`).

## 3. Provider Boundary

`OllamaAnswerGenerator.generate()` accepts a compact `model_context` and
rejects unsupported shapes before making an HTTP request
(`ollama_answer_generator.py:48-68`). The HTTP payload contains the question
and the supplied compact context under `model_context`
(`ollama_answer_generator.py:70-74`, `98-105`).

The provider does not call the Retriever, access the filesystem, access a
database or Drive, reconstruct `answer_context`, or regenerate citation
handles. The system prompt explicitly tells the model that evidence objects
are the factual material and that handles are the only citation identifiers
(`ollama_answer_generator.py:151-158`, `184-198`).

The modified integration test captures the outgoing request and verifies that
`answer_context`, supporting/independent wrappers, selection metadata, query
understanding, source IDs, and retriever references are absent.

**Result: PASS.**

## 4. File-by-File Audit

### `answer_pipeline.py`

- **PASS** — Selected evidence is separated from the model-facing view; the
  selected rich response remains the validation/provenance source
  (`answer_pipeline.py:62-77`, `91-96`).
- **PASS** — The generator receives `model_context`, not the rich response
  (`answer_pipeline.py:87-90`).
- **PASS** — Claim validation and CitationBuilder consume the selected rich
  response (`answer_pipeline.py:91-92`).
- **PASS** — Non-answerable states do not invoke the provider
  (`answer_pipeline.py:78-86`).
- **PASS** — Selection remains upstream and is not recomputed by the compact
  serializer.
- **WARNING** — `_generate()` retains compatibility for one-positional-argument
  test doubles (`answer_pipeline.py:134-146`). This is narrow and does not
  restore rich-response access for the Ollama provider, but the protocol
  parameter name is still `evidence_response` in `answer_generator.py`.

### `ollama_answer_generator.py`

- **PASS** — Validates the compact shape before HTTP (`ollama_answer_generator.py:52-68`).
- **PASS** — Sends the supplied compact object directly; no rich context or
  handle reconstruction occurs (`ollama_answer_generator.py:70-74`,
  `98-105`).
- **PASS** — Preserves the claim-level output contract and rejects extra or
  missing top-level fields (`ollama_answer_generator.py:109-126`).
- **PASS** — Existing connection, timeout, HTTP, malformed JSON, unsupported
  status, and missing-field failures remain explicit
  (`ollama_answer_generator.py:80-95`, `109-126`).
- **PASS** — Provider-side parsing does not weaken downstream claim or public
  contract validation.

### `answer_generator.py`

- **PASS** — The protocol documents generation from compact model-facing
  context (`answer_generator.py:9-16`).
- **PASS** — No Retriever, provenance, or provider-specific dependency is
  exposed.
- **WARNING** — The second parameter is still named `evidence_response`
  (`answer_generator.py:12-14`). Its annotation is only `dict[str, Any]`, so
  the runtime boundary is correct but the name is semantically stale and
  leaves more room for accidental misuse by future implementations.

### `mock_answer_generator.py`

- **PASS** — Normal two-argument operation consumes compact evidence and emits
  deterministic E# claim references (`mock_answer_generator.py:12-35`).
- **PASS** — It remains provider-neutral and does not access external data.
- **WARNING** — A narrow one-argument legacy path still accepts a rich
  `EvidenceResponse` (`mock_answer_generator.py:17-18`, `45-73`). This is
  limited to direct compatibility calls and is not used by the production
  pipeline. It does independently derive E# strings, so it should not be
  treated as the authoritative provider path; production callers use the
  compact builder and CitationBuilder mapping.
- **PASS** — The normal compact path rejects a missing/non-list evidence field
  rather than silently fabricating context (`mock_answer_generator.py:19-23`).

### `model_facing_context.py`

- **PASS** — Handle assignment reuses `citation_handles()` rather than creating
  a second mapping (`model_facing_context.py:42-49`).
- **PASS** — Evidence is emitted in stable handle order with structured
  location fields (`model_facing_context.py:100-129`).
- **PASS** — Observations preserve order and convert evidence IDs to E# handles
  (`model_facing_context.py:156-188`).
- **PASS** — Conflict and lifecycle groups convert observation IDs to validated
  array indexes (`model_facing_context.py:196-228`).
- **PASS** — Coverage is copied from the Answer Plan; the builder only maps
  deterministic incomplete states to the schema reason
  (`model_facing_context.py:230-243`).
- **PASS** — Forbidden internal metadata is recursively rejected
  (`model_facing_context.py:253-289`).
- **PASS** — Deep copies are used for location and raw values, and no input
  mutation was observed in the focused tests.
- **PASS** — Identical evidence present in supporting and independent
  collections is deduplicated according to the existing handle mapping, with
  supporting role taking precedence (`model_facing_context.py:75-98`).
  Distinct evidence IDs remain distinct handles; the compatibility fix does
  not merge genuinely different evidence.

## 5. Provenance and Citation Audit

The deterministic chain is:

`selected EvidenceResponse` → `citation_handles()` → `E1/E2/...` in compact
context → model claim `citation_refs` → `validate_claim_answer()` →
`CitationBuilder.build()` → exact evidence/source/location citation.

`CitationBuilder` reconstructs handles from the original selected response and
rejects unknown handles before producing citations
(`citation_builder.py:31-61`, `77-104`). The model-facing context contains no
raw source IDs, while the original response remains available for restoration.

**Result: PASS.** No model-facing shortcut bypasses CitationBuilder.

## 6. Conflict and Lifecycle Audit

The Answer Plan is built from the selected response and compacted without
recomputing evidence relevance. Observation order is preserved, conflict groups
remain explicit with `must_preserve_separately`, and lifecycle groups remain
explicit with `must_distinguish`.

The focused integration tests verify both group types, incomplete coverage,
and the availability of both E1/E2 evidence handles. No information was lost
at the provider boundary.

**Result: PASS.**

## 7. Security / Leakage Audit

The serialized model input is restricted to:

- the user question;
- compact Answer Plan observations, group metadata, and coverage;
- selected evidence source filename, structured location, text, optional role,
  and required raw structured values.

The compact builder rejects or omits internal source IDs, evidence IDs,
record IDs, provenance references, selector/evaluator metadata, expected
answers, and authentication/secrets (`model_facing_context.py:10-27`,
`253-289`). The provider has no imports or handles for Retriever, filesystem,
database, Drive, or raw source access.

**Result: PASS.**

## 8. Compatibility Audit

The 12M compatibility fix addresses the case where the same evidence ID is
present in both supporting and independent collections. `citation_handles()`
deduplicates by evidence ID in supporting-first order; `_roles()` mirrors that
policy by allowing the duplicate and retaining supporting precedence. This
keeps the compact E# mapping compatible with CitationBuilder.

Distinct evidence IDs are never merged merely because their text, date, or
source resembles another item. They receive separate handles and remain
available for conflict/lifecycle preservation.

**Result: PASS.**

## 9. Regression Findings

**NO REGRESSIONS FOUND**

The audit found no weakening of provenance validation, citation validation,
selection, conflict/lifecycle preservation, insufficient-evidence handling,
clarification handling, immutability, determinism, or provider isolation.

The two warnings are maintainability observations only:

1. the protocol parameter name still says `evidence_response`;
2. MockAnswerGenerator retains a narrow legacy direct-call compatibility path.

Neither warning changes the production Ollama boundary.

## 10. Required Fixes

**NO FIXES REQUIRED**

Renaming the protocol parameter could improve clarity, but is not required for
correctness and was intentionally not changed during this audit.

## 11. Test Evidence

Executed without Ollama:

```text
python -m pytest -q
230 passed, 4 subtests passed
```

`git diff --check` also passed.

Pylance workspace diagnostics were inspected. No diagnostics were reported in
the five audited production files. Existing unrelated warnings remain in
other files and in a few test files; they do not affect this audit.

The directly relevant 12M integration and provider tests cover:

- compact context reaching the pipeline generator;
- direct Ollama serialization of `model_context`;
- absence of rich answer-context wrappers;
- conflict/lifecycle/coverage preservation;
- citation restoration from the original response;
- immutable and deterministic context building;
- sensitive metadata leakage prevention;
- provider error handling.

## 12. Final Verdict

**PASS WITH WARNING**

STEP 12M is safe to proceed to **one fresh live compact-context Ollama smoke
test**. The live test should be treated as a model-behavior test only; the
code audit establishes that the model will receive the compact context and
that deterministic claim validation and provenance restoration remain after
generation.
