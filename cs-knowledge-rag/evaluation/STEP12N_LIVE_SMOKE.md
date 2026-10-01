# STEP 12N Live Compact-Context Ollama Smoke Test

## 1. Objective

Verify the real production pipeline sends compact Model-Facing Context to Ollama and record Gemma3:4b output without retries.

## 2. Exact Configuration

```json
{
  "model": "gemma3:4b",
  "base_url": "http://localhost:11434",
  "timeout_seconds": 120.0,
  "attempts_per_case": 1,
  "retries": 0,
  "selector_configuration": {
    "max_evidence_units": 3,
    "max_characters": 12000,
    "max_records": 8
  }
}
```

## 3. Production Path Tested

Question ? QueryUnderstanding ? Retrieval ? EvidenceSelector ? AnswerPlan ? Model-Facing Context ? Ollama ? Claim Contract ? CitationBuilder ? Final Validation

## 4. Per-Case Results

### E003

- Question: Was Dr. Reena Nair present at the meeting on 18 July 2026?
- Latency: 9972.736 ms
- HTTP/API: 200 (success=True)
- Parser success: True
- Claim contract: valid
- Final validation: {'valid': True, 'errors': []}
- Compact context characters: 543
- Model-context evidence handles: ['E1']
- Conflict groups: []
- Lifecycle groups: []
- Obligation: PASS
- Model/API failure: None

### E006

- Question: Who coordinated C-START?
- Latency: 3916.841 ms
- HTTP/API: 200 (success=True)
- Parser success: True
- Claim contract: valid
- Final validation: {'valid': True, 'errors': []}
- Compact context characters: 3833
- Model-context evidence handles: ['E1', 'E2', 'E3']
- Conflict groups: [{'must_preserve_separately': True, 'observation_indexes': [1, 2]}]
- Lifecycle groups: []
- Obligation: PASS
- Model/API failure: None

### E014

- Question: What was reported about C-START participation?
- Latency: 3616.365 ms
- HTTP/API: 200 (success=True)
- Parser success: True
- Claim contract: valid
- Final validation: {'valid': True, 'errors': []}
- Compact context characters: 3833
- Model-context evidence handles: ['E1', 'E2', 'E3']
- Conflict groups: [{'must_preserve_separately': True, 'observation_indexes': [1, 2]}]
- Lifecycle groups: []
- Obligation: PARTIAL
- Model/API failure: None

### E016

- Question: What happened on 10 August 2026?
- Latency: 3738.711 ms
- HTTP/API: 200 (success=True)
- Parser success: True
- Claim contract: valid
- Final validation: {'valid': True, 'errors': []}
- Compact context characters: 2154
- Model-context evidence handles: ['E1', 'E2', 'E3']
- Conflict groups: []
- Lifecycle groups: [{'must_distinguish': True, 'observation_indexes': [1, 2]}]
- Obligation: FAIL
- Model/API failure: None

### E017

- Question: How many participants were reported for C-START?
- Latency: 3625.089 ms
- HTTP/API: 200 (success=True)
- Parser success: True
- Claim contract: valid
- Final validation: {'valid': True, 'errors': []}
- Compact context characters: 3833
- Model-context evidence handles: ['E1', 'E2', 'E3']
- Conflict groups: [{'must_preserve_separately': True, 'observation_indexes': [1, 2]}]
- Lifecycle groups: []
- Obligation: PARTIAL
- Model/API failure: None

## 5. Compact Context Verification

The request body was captured at the production `OllamaAnswerGenerator` HTTP boundary for every case. The serialized user `model_context` JSON was checked for compact `answer_plan` and compact `evidence`, and for absence of old `answer_context`, raw EvidenceResponse wrappers, internal hashes, evaluator metadata, and authentication/secrets. The initial detector searched the full payload and overmatched system-prompt wording; that telemetry classification was corrected offline without rerunning any case.

## 6. Model Output Results

See the per-case JSON records for raw Ollama envelopes, claim outputs, citation refs, resolved citations, invalid handles, obligation results, conflict/lifecycle results, and failures.

## 7. Latency

{
  "average_ms": 4973.948,
  "median_ms": 3738.711,
  "maximum_ms": 9972.736,
  "per_case_ms": {
    "E003": 9972.736,
    "E006": 3916.841,
    "E014": 3616.365,
    "E016": 3738.711,
    "E017": 3625.089
  }
}

## 8. Comparison With Step 12L

Step 12L reconstructed/recorded compact context offline while the then-current provider path sent rich context. Step 12N captures the actual HTTP request from the now-wired production pipeline and therefore tests a distinct boundary.

## 9. Interpretation

A. Pipeline/wiring result: compact context reached the real Ollama request boundary for all five cases; the corrected request-verification fields are true.

B. Model-quality result: determined independently from parser, claim-contract, citation, and obligation fields.

C. Evaluator result: determined only by the existing deterministic obligation evaluator.

## 10. Final Verdict

PARTIAL

## Final Summary

Compact context reached Ollama: True. Valid claim-level outputs: 5/5. Model-quality obligations: 2 PASS, 2 PARTIAL, 1 FAIL.

12N COMPLETE ? NEXT ACTION: review the baseline model-quality failures before any prompt or production change
