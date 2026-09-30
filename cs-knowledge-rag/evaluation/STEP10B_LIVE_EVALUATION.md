# STEP 10B Live Evaluation

## Run configuration

```json
{
  "model": "gemma3:4b",
  "base_url": "http://localhost:11434",
  "timeout": 120.0,
  "selector": {
    "max_evidence_units": 3,
    "max_characters": 12000,
    "max_records": 8,
    "max_characters_per_unit": null
  },
  "question_count": 17,
  "attempts_per_question": 1,
  "retry_policy": "none"
}
```

## Aggregate results

| Metric | Result |
|---|---:|
| total_questions | 17 |
| expected_status_matches | 17 |
| validator_passes | 17 |
| valid_citation_handles | 12 |
| model_api_failures | 0 |
| obligation_pass | 5 |
| obligation_partial | 3 |
| obligation_fail | 4 |
| obligation_na | 5 |
| wrong_citation_obligations | 1 |
| conflict_preservation | 9 |
| lifecycle_distinction | 10 |
| incomplete_answerable | 7 |
| average_latency_seconds | 3.8056430705918878 |
| median_latency_seconds | 4.331023399950936 |
| maximum_latency_seconds | 13.766401800094172 |
| truncated_selections | 6 |

## Comparison with STEP 9

| Metric | STEP 9 | STEP 10B |
|---|---:|---:|
| expected_status_matches | 16 | 17 |
| validator_passes | not recorded | 17 |
| valid_citation_handles | not recorded | 12 |
| model_api_failures | not recorded | 0 |
| incomplete_answerable | not recorded | 7 |
| average_latency_seconds | 3.8330785646993557 | 3.8056430705918878 |
| median_latency_seconds | 4.50396310002543 | 4.331023399950936 |
| maximum_latency_seconds | 14.954348500003107 | 13.766401800094172 |
| truncated_selections | 6 | 6 |

## Per-question results

| ID | Expected Status | Actual Status | Validator | Obligation | Key Failure |
|---|---|---|---|---|---|
| E001 | answerable | answered | True | PARTIAL | ['cstart_participant_category', 'department_meeting'] |
| E002 | answerable | answered | True | PASS |  |
| E003 | answerable | answered | True | PASS |  |
| E004 | answerable | answered | True | PASS |  |
| E005 | answerable | answered | True | PARTIAL | ['budget_pending', 'workstations'] |
| E006 | answerable | answered | True | PASS |  |
| E007 | answerable | answered | True | FAIL | ['completed_fdp', 'fdp_lifecycle', 'planning_meeting'] |
| E008 | clarification_required | clarification_required | True | N/A |  |
| E009 | clarification_required | clarification_required | True | N/A |  |
| E010 | clarification_required | clarification_required | True | N/A |  |
| E011 | clarification_required | clarification_required | True | N/A |  |
| E012 | insufficient_evidence | insufficient_evidence | True | N/A |  |
| E013 | answerable | answered | True | PARTIAL | ['schedule_decision'] |
| E014 | answerable | answered | True | FAIL | ['cstart_participant_category', 'participant_count'] |
| E015 | answerable | answered | True | PASS |  |
| E016 | answerable | answered | True | FAIL | ['completed_event', 'fdp_planning_vs_completed', 'planning_meeting'] |
| E017 | answerable | answered | True | FAIL | ['participant_category_discrepancy', 'reported_count'] |

## Focused analysis

### E001

- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2', 'sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Selector coverage: `{"record_coverage_complete": true, "supporting_coverage_complete": false, "independent_coverage_complete": true, "conflict_coverage_complete": true, "conflict_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}], "coverage_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}, {"coverage_group_id": "coverage:9f8609e436e165eb", "kind": "primary_record_types", "evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:2", "sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:B2"], "selected_evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2"], "excluded_evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:2", "sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:B2"], "reason": "distinct directly relevant record types.", "complete": false}], "coverage_complete": false}`
- Claim output: `{"status": "answered", "claims": [{"text": "On 18 July 2026, the C-START Industry Interaction Programme was held at the department seminar hall.", "citation_refs": ["E2", "E3"]}, {"text": "The C-START Industry Interaction Programme on 18 July 2026 involved 45 third-year students.", "citation_refs": ["E2", "E3"]}, {"text": "Mr. Rajesh Pillai, Chief Technology Officer of Nimbus Technologies, delivered the keynote address at the C-START Industry Interaction Programme on 18 July 2026.", "citation_refs": ["E2"]}]}`
- Obligation result: `{"status": "PARTIAL", "required_obligations": ["event_activity", "department_meeting", "participant_conflict"], "satisfied_obligations": ["event_activity", "participant_conflict"], "missing_obligations": ["cstart_participant_category", "department_meeting"], "wrong_citation_obligations": [], "invalid_evidence_handles": [], "conflict_preservation": [{"id": "cstart_participant_category", "satisfied": false, "complete": false, "observations": [{"id": "event_report_participants", "satisfied": false, "wrong_citation": false}, {"id": "meeting_minutes_participants", "satisfied": true, "wrong_citation": false}]}], "lifecycle_distinction": [], "direct_citation_requirements": [], "acceptable_scope": ["Attendance rows need not be listed individually unless attendance is claimed or the answer asserts complete same-day coverage."], "incomplete_conditions": ["Missing the meeting or event for a broad date answer.", "Mentioning participation without preserving both participant-category observations."]}`

### E006

- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2', 'sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Selector coverage: `{"record_coverage_complete": true, "supporting_coverage_complete": true, "independent_coverage_complete": false, "conflict_coverage_complete": true, "conflict_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}], "coverage_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}], "coverage_complete": true}`
- Claim output: `{"status": "answered", "claims": [{"text": "Prof. Sarah Thomas coordinated C-START.", "citation_refs": ["E1", "E2", "E3"]}]}`
- Obligation result: `{"status": "PASS", "required_obligations": ["coordinator"], "satisfied_obligations": ["coordinator"], "missing_obligations": [], "wrong_citation_obligations": [], "invalid_evidence_handles": [], "conflict_preservation": [], "lifecycle_distinction": [], "direct_citation_requirements": [{"id": "coordinator", "satisfied": true, "wrong_citation": false}], "acceptable_scope": ["Only the coordinator needs to be answered."], "incomplete_conditions": ["Sarah Thomas is absent.", "Sarah Thomas is cited only to meeting minutes that do not identify her as coordinator."]}`

### E014

- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2', 'sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Selector coverage: `{"record_coverage_complete": true, "supporting_coverage_complete": true, "independent_coverage_complete": false, "conflict_coverage_complete": true, "conflict_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}], "coverage_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}], "coverage_complete": true}`
- Claim output: `{"status": "answered", "claims": [{"text": "The C-START Industry Interaction programme took place on 18-Jul-2026.", "citation_refs": ["E2", "E3"]}]}`
- Obligation result: `{"status": "FAIL", "required_obligations": ["participant_count"], "satisfied_obligations": [], "missing_obligations": ["cstart_participant_category", "participant_count"], "wrong_citation_obligations": [], "invalid_evidence_handles": [], "conflict_preservation": [{"id": "cstart_participant_category", "satisfied": false, "complete": false, "observations": [{"id": "event_report_participants", "satisfied": false, "wrong_citation": false}, {"id": "meeting_minutes_participants", "satisfied": false, "wrong_citation": false}]}], "lifecycle_distinction": [], "direct_citation_requirements": [], "acceptable_scope": ["The answer may omit unrelated event details, but not the category discrepancy."], "incomplete_conditions": ["Only one participant observation is stated.", "The count is stated without the differing categories."]}`

### E016

- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5', 'sha256:d30e1dca7e0cc5b51844c40ef462a33fe1cceb66bfd29acb899f7150f11b0456:pdf-page:1']`
- Selector coverage: `{"record_coverage_complete": true, "supporting_coverage_complete": true, "independent_coverage_complete": false, "conflict_coverage_complete": true, "conflict_groups": [], "coverage_groups": [{"coverage_group_id": "coverage:561436382443de26", "kind": "lifecycle", "evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5"], "selected_evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5"], "excluded_evidence_ids": [], "reason": "records describe related lifecycle stages.", "complete": true}, {"coverage_group_id": "coverage:95e01d67bf44d5e4", "kind": "primary_record_types", "evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5"], "selected_evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5"], "excluded_evidence_ids": [], "reason": "distinct directly relevant record types.", "complete": true}], "coverage_complete": true}`
- Claim output: `{"status": "answered", "claims": [{"text": "The Faculty Development Programme was planned for 10 August 2026", "citation_refs": ["E3", "E2"]}]}`
- Obligation result: `{"status": "FAIL", "required_obligations": ["planning_meeting", "completed_event"], "satisfied_obligations": [], "missing_obligations": ["completed_event", "fdp_planning_vs_completed", "planning_meeting"], "wrong_citation_obligations": [], "invalid_evidence_handles": [], "conflict_preservation": [], "lifecycle_distinction": [{"id": "fdp_planning_vs_completed", "satisfied": false, "complete": false, "observations": [{"id": "planning", "satisfied": false, "wrong_citation": false}, {"id": "completed", "satisfied": false, "wrong_citation": false}]}], "direct_citation_requirements": [], "acceptable_scope": ["A narrowly scoped answer must identify that it is discussing only the planning meeting or only the completed event."], "incomplete_conditions": ["Planning is presented as completion or completion is presented as planning.", "One lifecycle observation is silently omitted."]}`

### E017

- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2', 'sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Selector coverage: `{"record_coverage_complete": true, "supporting_coverage_complete": true, "independent_coverage_complete": false, "conflict_coverage_complete": true, "conflict_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}], "coverage_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}], "coverage_complete": true}`
- Claim output: `{"status": "answered", "claims": [{"text": "Forty-five third-year students and fourth-year students participated in C-START.", "citation_refs": ["E2", "E3"]}]}`
- Obligation result: `{"status": "FAIL", "required_obligations": ["reported_count"], "satisfied_obligations": [], "missing_obligations": ["participant_category_discrepancy", "reported_count"], "wrong_citation_obligations": [], "invalid_evidence_handles": [], "conflict_preservation": [{"id": "participant_category_discrepancy", "satisfied": false, "complete": false, "observations": [{"id": "event_report_category", "satisfied": false, "wrong_citation": false}, {"id": "meeting_minutes_category", "satisfied": false, "wrong_citation": false}]}], "lifecycle_distinction": [], "direct_citation_requirements": [], "acceptable_scope": ["The numeric answer may be concise, but a fully grounded answer must preserve the category discrepancy."], "incomplete_conditions": ["Only the number 45 is returned without the two category observations."]}`

