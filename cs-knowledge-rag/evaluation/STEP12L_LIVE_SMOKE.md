# STEP 12L ? Live Smoke Test

## Configuration

```json
{
  "model": "gemma3:4b",
  "base_url": "http://localhost:11434",
  "timeout_seconds": 120,
  "attempts_per_case": 1,
  "retries": 0
}
```

## Cases

### E006

- Status: `None` (expected `answerable`)
- Latency: `22796.524 ms`
- HTTP/API success: `True` (HTTP `200`)
- Parser success: `False`; exception: `{'type': 'OllamaResponseError', 'message': 'Ollama answer is missing required fields.'}`
- Claim Answer Contract valid: `False`
- Public Answer Contract valid: `False`
- Citation handles returned: `[]`
- Exact provenance restored: `False`
- Obligation result: `N/A`
- Interpretation: The HTTP call succeeded, but the model returned internal evidence metadata rather than the required claim contract.

### E014

- Status: `None` (expected `answerable`)
- Latency: `7030.695 ms`
- HTTP/API success: `True` (HTTP `200`)
- Parser success: `False`; exception: `{'type': 'OllamaResponseError', 'message': 'Ollama answer is missing required fields.'}`
- Claim Answer Contract valid: `False`
- Public Answer Contract valid: `False`
- Citation handles returned: `[]`
- Exact provenance restored: `False`
- Obligation result: `N/A`
- Conflict context available: `True`
- Both conflicting observations selected: `True`
- Both conflicting evidence handles available: `True`
- Both conflicting claims represented: `False`
- Conflict citations correct: `False`
- Interpretation: The selected context preserved the conflict metadata, but the model response failed parsing before claims could be evaluated.

### E016

- Status: `None` (expected `answerable`)
- Latency: `3686.705 ms`
- HTTP/API success: `True` (HTTP `200`)
- Parser success: `False`; exception: `{'type': 'OllamaResponseError', 'message': 'Ollama answer is missing required fields.'}`
- Claim Answer Contract valid: `False`
- Public Answer Contract valid: `False`
- Citation handles returned: `[]`
- Exact provenance restored: `False`
- Obligation result: `N/A`
- Lifecycle context available: `True`
- Both lifecycle observations available: `True`
- Both lifecycle claims represented: `False`
- Lifecycle claims distinguished: `False`
- Lifecycle citations correct: `False`
- Interpretation: The selected context preserved the lifecycle metadata, but the model response failed parsing before claims could be evaluated.

## Aggregate Result

```json
{
  "cases_executed": 3,
  "successful_model_api_calls": 3,
  "parser_failures": 3,
  "validator_failures": 3,
  "citation_failures": 3,
  "obligation_counts": {
    "PASS": 0,
    "PARTIAL": 0,
    "FAIL": 0,
    "N/A": 3
  },
  "average_latency_ms": 11171.308,
  "median_latency_ms": 7030.695,
  "maximum_latency_ms": 22796.524
}
```

## Interpretation

1. **Model/API behavior:** All three HTTP calls returned 200 exactly once. All three parser attempts failed because the response lacked the required `status` and `claims` top-level fields.
2. **Contract/provenance behavior:** No Claim Answer Contract or final public answer was produced, so citation restoration and obligation evaluation were N/A. The deterministic citation mapping remained available in the captured selected context.
3. **Conflict behavior:** E014 retained both selected observations and its conflict group in the reconstructed compact context. No model claims were available to test preservation.
4. **Lifecycle behavior:** E016 retained its lifecycle group and both observations in the reconstructed compact context. No model claims were available to test distinction.

The current Ollama generator supplied the existing rich `answer_context` payload; the compact Model-Facing Context was not directly passed to the provider in this run. This was recorded without changing production code.
