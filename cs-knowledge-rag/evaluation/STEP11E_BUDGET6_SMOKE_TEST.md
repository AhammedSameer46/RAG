# STEP 11E Evidence-Budget Experiment

## Configuration

This is an evaluation-only run using the Step 11A prompt and the Step 11B configuration, with only `max_evidence_units` changed from 3 to 6.

```json
{
  "model": "gemma3:4b",
  "base_url": "http://localhost:11434",
  "timeout": 120.0,
  "selector": {
    "max_evidence_units": 6,
    "max_characters": 12000,
    "max_records": 8,
    "max_characters_per_unit": null
  },
  "question_ids": [
    "E001",
    "E006",
    "E014",
    "E016",
    "E017"
  ],
  "executed_question_ids": [
    "E006",
    "E014",
    "E016",
    "E017"
  ],
  "not_recorded_question_ids": [
    "E001"
  ],
  "question_count": 5,
  "attempts_per_question": 1,
  "retry_policy": "none"
}
```

## Per-question results

| ID | Expected | Actual | Selected units | Truncated | Validator | Obligation | Missing obligations | Wrong citations | Latency |
|---|---|---|---:|---|---|---|---|---|---:|
| E001 | not recorded | not recorded | — | — | — | — | — | — | — |
| E006 | answerable | answered | 6 | True | True | PARTIAL | [] | ['coordinator'] | 5.157s |
| E014 | answerable | answered | 6 | True | True | FAIL | ['cstart_participant_category'] | ['participant_count'] | 5.345s |
| E016 | answerable | answered | 4 | False | True | FAIL | ['completed_event', 'fdp_planning_vs_completed', 'planning_meeting'] | [] | 6.625s |
| E017 | answerable | answered | 6 | True | True | FAIL | ['participant_category_discrepancy'] | ['reported_count'] | 4.892s |

## Step 11B versus Step 11E

E001 has no valid Step 11B-versus-Step 11E comparison because its single Step 11E attempt was not persisted and was not rerun.

| ID | 11B units | 11E units | 11B truncation | 11E truncation | 11B obligation | 11E obligation | 11B conflict | 11E conflict | 11B lifecycle | 11E lifecycle | 11B citation errors | 11E citation errors | 11B validator | 11E validator | 11B latency | 11E latency |
|---|---:|---:|---|---|---|---|---|---|---|---|---|---|---|---|---:|---:|
| E006 | 3 | 6 | True | True | PASS | PARTIAL | None | None | None | None | [] | ['coordinator'] | True | True | 4.657s | 5.157s |
| E014 | 3 | 6 | True | True | FAIL | FAIL | False | False | None | None | [] | ['participant_count'] | True | True | 6.141s | 5.345s |
| E016 | 3 | 4 | True | False | PARTIAL | FAIL | None | None | False | False | [] | [] | True | True | 8.878s | 6.625s |
| E017 | 3 | 6 | True | True | FAIL | FAIL | False | False | None | None | ['reported_count'] | ['reported_count'] | True | True | 4.525s | 4.892s |

## Interpretation

- Aggregate Step 11E summary: `{"executed_question_count": 4, "not_recorded_question_ids": ["E001"], "obligation_pass": 0, "obligation_partial": 1, "obligation_fail": 3, "model_api_failures": 0, "truncated_count": 3, "average_latency_seconds": 5.5046053750265855}`
- More selected evidence is not treated as improvement by itself.
- The experiment succeeds only where deterministic obligation outcomes improve without citation or grounding regressions.
- Model outputs were generated once per question and are preserved in the JSON artifact.

### E006 evidence and obligation details

- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:1', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:4', 'sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Selector coverage: `{"record_coverage_complete": true, "supporting_coverage_complete": true, "independent_coverage_complete": false, "conflict_coverage_complete": true, "conflict_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}], "coverage_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}], "coverage_complete": true}`
- Claim-level output: `{"status": "answered", "claims": [{"text": "Prof. Sarah Thomas coordinated C-START, an Industry Interaction Programme on 18-Jul-2026.", "citation_refs": ["E4", "E2", "E3"]}]}`
- Citation mapping: `{"E1": "sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "E2": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1", "E3": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2", "E4": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:1", "E5": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "E6": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:4"}`
- Conflict preservation: `[]`
- Lifecycle preservation: `[]`
- Obligation evaluation: `{"status": "PARTIAL", "required_obligations": ["coordinator"], "satisfied_obligations": [], "missing_obligations": [], "wrong_citation_obligations": ["coordinator"], "invalid_evidence_handles": [], "conflict_preservation": [], "lifecycle_distinction": [], "direct_citation_requirements": [{"id": "coordinator", "satisfied": false, "wrong_citation": true}], "acceptable_scope": ["Only the coordinator needs to be answered."], "incomplete_conditions": ["Sarah Thomas is absent.", "Sarah Thomas is cited only to meeting minutes that do not identify her as coordinator."]}`

### E014 evidence and obligation details

- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:1', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:4', 'sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Selector coverage: `{"record_coverage_complete": true, "supporting_coverage_complete": true, "independent_coverage_complete": false, "conflict_coverage_complete": true, "conflict_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}], "coverage_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}], "coverage_complete": true}`
- Claim-level output: `{"status": "answered", "claims": [{"text": "The C-START Industry Interaction programme took place on July 18, 2026, and was coordinated by Prof. Sarah Thomas. Forty-five third-year students participated.", "citation_refs": ["E4", "E5", "E6"]}]}`
- Citation mapping: `{"E1": "sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "E2": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1", "E3": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2", "E4": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:1", "E5": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "E6": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:4"}`
- Conflict preservation: `[{"id": "cstart_participant_category", "satisfied": false, "complete": false, "observations": [{"id": "event_report_participants", "satisfied": false, "wrong_citation": false}, {"id": "meeting_minutes_participants", "satisfied": false, "wrong_citation": true}]}]`
- Lifecycle preservation: `[]`
- Obligation evaluation: `{"status": "FAIL", "required_obligations": ["participant_count"], "satisfied_obligations": [], "missing_obligations": ["cstart_participant_category"], "wrong_citation_obligations": ["participant_count"], "invalid_evidence_handles": [], "conflict_preservation": [{"id": "cstart_participant_category", "satisfied": false, "complete": false, "observations": [{"id": "event_report_participants", "satisfied": false, "wrong_citation": false}, {"id": "meeting_minutes_participants", "satisfied": false, "wrong_citation": true}]}], "lifecycle_distinction": [], "direct_citation_requirements": [], "acceptable_scope": ["The answer may omit unrelated event details, but not the category discrepancy."], "incomplete_conditions": ["Only one participant observation is stated.", "The count is stated without the differing categories."]}`

### E016 evidence and obligation details

- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5', 'sha256:d30e1dca7e0cc5b51844c40ef462a33fe1cceb66bfd29acb899f7150f11b0456:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Selector coverage: `{"record_coverage_complete": true, "supporting_coverage_complete": true, "independent_coverage_complete": true, "conflict_coverage_complete": true, "conflict_groups": [], "coverage_groups": [{"coverage_group_id": "coverage:561436382443de26", "kind": "lifecycle", "evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5"], "selected_evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5"], "excluded_evidence_ids": [], "reason": "records describe related lifecycle stages.", "complete": true}, {"coverage_group_id": "coverage:95e01d67bf44d5e4", "kind": "primary_record_types", "evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5"], "selected_evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5"], "excluded_evidence_ids": [], "reason": "distinct directly relevant record types.", "complete": true}], "coverage_complete": true}`
- Claim-level output: `{"status": "answered", "claims": [{"text": "The Faculty Development Programme was planned for 10 August 2026.", "citation_refs": ["E1", "E2"]}, {"text": "Prof. Arun Kumar was the coordinator for the Faculty Development Programme scheduled for 10 August 2026.", "citation_refs": ["E1", "E2"]}, {"text": "The Faculty Development Programme involved 12 participants and was marked as Completed.", "citation_refs": ["E1"]}]}`
- Citation mapping: `{"E1": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "E2": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5", "E3": "sha256:d30e1dca7e0cc5b51844c40ef462a33fe1cceb66bfd29acb899f7150f11b0456:pdf-page:1", "E4": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"}`
- Conflict preservation: `[]`
- Lifecycle preservation: `[{"id": "fdp_planning_vs_completed", "satisfied": false, "complete": false, "observations": [{"id": "planning", "satisfied": false, "wrong_citation": false}, {"id": "completed", "satisfied": true, "wrong_citation": false}]}]`
- Obligation evaluation: `{"status": "FAIL", "required_obligations": ["planning_meeting", "completed_event"], "satisfied_obligations": [], "missing_obligations": ["completed_event", "fdp_planning_vs_completed", "planning_meeting"], "wrong_citation_obligations": [], "invalid_evidence_handles": [], "conflict_preservation": [], "lifecycle_distinction": [{"id": "fdp_planning_vs_completed", "satisfied": false, "complete": false, "observations": [{"id": "planning", "satisfied": false, "wrong_citation": false}, {"id": "completed", "satisfied": true, "wrong_citation": false}]}], "direct_citation_requirements": [], "acceptable_scope": ["A narrowly scoped answer must identify that it is discussing only the planning meeting or only the completed event."], "incomplete_conditions": ["Planning is presented as completion or completion is presented as planning.", "One lifecycle observation is silently omitted."]}`

### E017 evidence and obligation details

- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:1', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:4', 'sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Selector coverage: `{"record_coverage_complete": true, "supporting_coverage_complete": true, "independent_coverage_complete": false, "conflict_coverage_complete": true, "conflict_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}], "coverage_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}], "coverage_complete": true}`
- Claim-level output: `{"status": "answered", "claims": [{"text": "The number of participants reported for C-START Industry Interaction was 45", "citation_refs": ["E4", "E2", "E3"]}]}`
- Citation mapping: `{"E1": "sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "E2": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1", "E3": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2", "E4": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:1", "E5": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "E6": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:4"}`
- Conflict preservation: `[{"id": "participant_category_discrepancy", "satisfied": false, "complete": false, "observations": [{"id": "event_report_category", "satisfied": false, "wrong_citation": false}, {"id": "meeting_minutes_category", "satisfied": false, "wrong_citation": false}]}]`
- Lifecycle preservation: `[]`
- Obligation evaluation: `{"status": "FAIL", "required_obligations": ["reported_count"], "satisfied_obligations": [], "missing_obligations": ["participant_category_discrepancy"], "wrong_citation_obligations": ["reported_count"], "invalid_evidence_handles": [], "conflict_preservation": [{"id": "participant_category_discrepancy", "satisfied": false, "complete": false, "observations": [{"id": "event_report_category", "satisfied": false, "wrong_citation": false}, {"id": "meeting_minutes_category", "satisfied": false, "wrong_citation": false}]}], "lifecycle_distinction": [], "direct_citation_requirements": [], "acceptable_scope": ["The numeric answer may be concise, but a fully grounded answer must preserve the category discrepancy."], "incomplete_conditions": ["Only the number 45 is returned without the two category observations."]}`
