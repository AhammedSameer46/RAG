# Local Ollama LLM Provider Design

## Scope

This document defines the first real answer-generation provider boundary. It
does not implement the provider, add Ollama dependencies, or select a
production model.

The provider is a local Ollama deployment accessed through its HTTP/API
boundary. It receives a question and an already-built evidence response. It
does not access the filesystem, Google Drive, the Retriever, source documents,
or any other application service directly.

The provider is an answer generator only. Query understanding, retrieval,
evidence packaging, and answer validation remain separate components.

## Provider boundary

```text
AnswerPipeline
  -> evidence response
  -> local Ollama HTTP API
  -> answer-contract object
  -> Answer Contract validator
```

The provider must:

- Send requests only to the configured local Ollama HTTP endpoint.
- Receive only `question` and `evidence_response`.
- Never read source files or application databases directly.
- Never call the Retriever.
- Never access Google Drive.
- Never send institutional content to an external model provider.
- Return the answer-contract object, not a framework-specific response.

The HTTP client, endpoint configuration, timeout, and model name are
implementation concerns for a later provider module. They are not defined as
application-wide settings by this design document.

## Implemented initial Ollama adapter

The initial adapter is implemented in
`cs_ingest/ollama_answer_generator.py`. It is a small
`AnswerGenerator` implementation that calls Ollama's local `POST
/api/generate` endpoint over HTTP. It sends the configured model, grounding
system instruction, original question, and structured evidence response.
Ollama JSON output is requested with `format: "json"` and `stream: false`.

`OllamaAnswerGenerator` accepts `base_url`, `model`, and `timeout` constructor
parameters. Its default model is the explicit placeholder
`SET_OLLAMA_MODEL`; no production model has been selected.

Clarification-required and insufficient-evidence responses return their empty
answer contracts without making an HTTP call. Only answerable responses reach
Ollama. Connection failures, timeouts, HTTP errors, malformed responses,
missing fields, and unsupported statuses raise explicit provider errors.
Returned citations are not repaired or semantically checked; the existing
Answer Contract validator remains the final provenance gate.

The adapter uses Python's standard-library HTTP client, so no additional HTTP
package is required. Ollama is not required for unit tests, which mock the
HTTP boundary. This adapter is an initial integration, not a production-ready
model or deployment configuration.

## Input contract

The provider receives one structured request:

```json
{
  "question": "What happened on 18 July 2026?",
  "evidence_response": {
    "status": "answerable",
    "query_understanding": {
      "intent": "date_activity",
      "retrieval_mode": "exact",
      "filters": {
        "date": "2026-07-18"
      },
      "keywords": [],
      "ambiguities": [],
      "unresolved": [],
      "confidence": "high"
    },
    "answer_context": {
      "records": [],
      "supporting_evidence": [],
      "independent_evidence": []
    },
    "sources": [],
    "coverage": {
      "has_records": true,
      "has_supporting_evidence": true,
      "has_independent_evidence": false
    }
  }
}
```

The evidence response is the provider's complete factual context. The
provider must not assume that omitted information exists elsewhere.

## Output contract

The provider must return only this answer-contract shape:

```json
{
  "status": "answered",
  "answer": "…",
  "citations": [
    {
      "evidence_id": "sha256:…:pdf-page:1",
      "source_id": "sha256:…",
      "filename": "document.pdf",
      "location": {
        "page": 1
      }
    }
  ]
}
```

Allowed statuses are:

- `answered`
- `insufficient_evidence`
- `clarification_required`

Citation location fields must preserve the supplied provenance. PDFs use
`page`; spreadsheets may use `sheet`, `row`, `cell`, or `cell_range`, along
with any other provenance fields already present in the evidence response.

No additional provider-specific output fields should be treated as part of the
contract. The Answer Contract validator remains the final structural and
provenance gate.

## Grounding instructions

The model instructions must explicitly require that the model:

- Uses only the supplied evidence.
- Does not use outside knowledge.
- Does not invent missing facts.
- Does not infer unsupported facts.
- Says that evidence is insufficient when it cannot support an answer.
- Preserves conflicting observations instead of silently selecting a winner.
- Cites every factual claim with supplied evidence.
- Never invents evidence IDs or source IDs.
- Never invents page, sheet, row, cell, or cell-range locations.
- Does not cite evidence that was not supplied.

These instructions reduce risk but do not replace deterministic validation.
The returned object must always pass the Answer Contract validator before it is
presented to a caller.

## Clarification and insufficient evidence

The provider must not generate a factual answer when the evidence response
status is:

- `clarification_required`
- `insufficient_evidence`

For either status, the expected output is:

```json
{
  "status": "clarification_required",
  "answer": "",
  "citations": []
}
```

or:

```json
{
  "status": "insufficient_evidence",
  "answer": "",
  "citations": []
}
```

The status must match the evidence response status. Clarification details
remain available in `query_understanding`; they must not be converted into
guessed facts.

## Conflict handling

Evidence from different sources may contain different observations. The model
must report both observations, each with its respective citation, when both
are relevant. It must not reconcile, average, deduplicate, or silently choose
a preferred source.

The distinction between `supporting_evidence` and `independent_evidence` must
remain available in the structured evidence payload. Independent evidence may
be cited when relevant, but it must not be relabeled as supporting evidence.

## Prompt structure

The provider request should be constructed from three explicit sections:

### System instruction

Contains the grounding rules, output schema, status behavior, citation rules,
and conflict policy. It should state that the model is producing a
source-grounded answer object, not performing retrieval.

### User question

Contains the original question exactly as received by the pipeline.

### Structured evidence payload

Contains the bounded `evidence_response` JSON, including:

- Query-understanding information
- Normalized records
- Supporting evidence
- Independent evidence
- Source index
- Coverage flags

Raw source files must not be inserted into the prompt. Evidence text and raw
values may be included only through the structured evidence response.

## Context-size protection

Before a provider request is sent, a future bounded-context step may select
the relevant records and evidence units. That step must be deterministic and
must not use arbitrary character truncation that can split provenance or
change evidence meaning.

The selection policy is not finalized here. Any future bound must preserve, for
every retained evidence unit:

- `evidence_id`
- `source_id`
- `filename`
- All available provenance location fields
- Relevant extracted text
- Relevant raw values

If the complete relevant evidence cannot fit within the configured context,
the provider should fail safely or return an explicit insufficient-context
outcome rather than silently dropping citations or provenance. The exact
limit, prioritization policy, and handling of large records require evaluation
against the project's dataset.

## Privacy

This provider is local-only by design. Institutional source content,
questions, normalized records, evidence text, raw spreadsheet values, and
provenance must not be sent to an external provider by this implementation.

Network access must be limited to the local Ollama endpoint. Deployment and
network-policy controls will be required to enforce this boundary in a
production environment.

## Failure handling

The future adapter must expose failures explicitly and must not return a
success-shaped answer when the provider has failed:

| Failure | Required behavior |
| --- | --- |
| Ollama unavailable | Return an explicit provider-unavailable error; do not fabricate an answer. |
| Request timeout | Return an explicit timeout error; do not retry indefinitely or fabricate an answer. |
| Malformed model JSON | Return an explicit malformed-output error; preserve raw output only for diagnostics subject to privacy policy. |
| Missing required output fields | Return an explicit contract error. |
| Invalid citations | Pass the generated object to the Answer Contract validator; reject it when validation fails. |
| Unsupported model status | Return an explicit unsupported-status/contract error. |

Validation errors must remain observable to callers. The adapter must not
silently repair missing fields, unknown evidence IDs, or invalid locations.

## Model choice

No final production model is selected by this design. Model selection will be
evaluated later using the project's institutional evaluation dataset, with
attention to grounding accuracy, citation accuracy, conflict preservation,
latency, context capacity, and local resource requirements.

## Testing strategy

The provider adapter should be tested without requiring a live Ollama
deployment:

- Mock a successful HTTP response containing valid answer JSON.
- Mock malformed JSON.
- Mock an answer with an invalid citation.
- Mock an unsupported status.
- Mock a timeout.
- Mock an unavailable provider/connection failure.
- Verify the exact request contains only the question and structured evidence
  response.
- Verify no filesystem, Google Drive, Retriever, or external-provider access
  is introduced.
- Run every generated answer through the Answer Contract validator.

These tests validate the HTTP and contract boundary. Live-model evaluation,
prompt quality, model selection, and production performance are separate
future work.

## Unresolved decisions

The following decisions intentionally remain open:

- Ollama endpoint URL and deployment configuration
- Request timeout and retry policy
- Final Ollama model
- JSON-mode or structured-output mechanism supported by the selected model
- Exact context-budget and evidence-prioritization policy
- Provider-specific error type and serialization
- Whether provider diagnostics may retain raw malformed output
- Evaluation thresholds for grounding and citation accuracy
