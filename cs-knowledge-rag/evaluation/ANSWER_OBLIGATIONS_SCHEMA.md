# Answer Obligations Schema

`ANSWER_OBLIGATIONS.json` defines deterministic review obligations for each
answerable evaluation question. It is an evaluation artifact only; it does
not change retrieval, selection, generation, or validation.

## Record shape

Each record contains:

- `id`, `question`
- `required_observations`: material facts that must be represented
- `required_evidence_relationships`: evidence selectors that must support a
  matching claim
- `conflict_requirements`: observations that must remain separate
- `lifecycle_requirements`: distinct planning, scheduling, or completion
  observations
- `direct_citation_requirements`: claims whose cited evidence must include
  specified evidence selectors
- `acceptable_scope`: omissions that are acceptable when the answer narrows
  its scope or when selection metadata reports truncation
- `incomplete_conditions`: deterministic conditions that make an answer
  incomplete

## Evidence selectors

Evidence selectors use exact structured provenance rather than token overlap:

```json
{
  "filename": "CSTART_2026_Event_Report.pdf",
  "location": {"page": 1}
}
```

Supported fields are `evidence_id`, `filename`, `source_id`, `page`, `sheet`,
`row`, `cell`, and `cell_range`. A selector matches only when every supplied
field matches the selected evidence object.

## Claim matching

An observation can specify:

- `all_phrases`: case-insensitive phrases that must occur in one claim
- `any_phrases`: at least one phrase must occur in one claim
- `required_evidence`: evidence selectors that must be cited by that claim

This is explicit obligation matching, not token-overlap grounding. The
evaluator never invents facts, performs fuzzy matching, or calls an LLM.

## Results

The evaluator returns:

- `PASS`, `PARTIAL`, or `FAIL`
- satisfied and missing obligations
- wrong-citation obligations
- invalid handle details
- conflict-preservation details
- lifecycle-distinction details

`PARTIAL` means the answer contains a supported central observation but misses
one or more required observations or relationships. `FAIL` means required
claims are absent, unsupported, or cite invalid evidence.
