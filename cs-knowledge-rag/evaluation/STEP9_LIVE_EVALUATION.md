# STEP 9 Live Evaluation ? Conflict-Aware Evidence Selection

All 17 questions were run exactly once with the current production pipeline. No production code, evaluation input, or STEP 8 artifact was modified.

## Aggregate comparison

| Metric | STEP 8 | STEP 9 |
|---|---:|---:|
| total_questions | n/a | 17 |
| expected_status_matches | 17/17 | 16/17 |
| final_validator_pass_rate | 17/17 | 16/17 |
| valid_citation_handle_rate | 12/12 | 11/12 |
| claims_with_directly_supporting_citations | 12 | 11 |
| wrong_citation_count | 0 | 1 |
| conflict_preservation_count | 0/3 | 0 |
| temporal_status_interpretation_errors | 1 | 1 |
| incomplete_answer_count | 4/12 | 6 |
| unsupported_claim_count | 0 | 1 |
| average_latency_seconds | 3.516 | 3.8330785646993557 |
| median_latency_seconds | 4.261 | 4.50396310002543 |
| maximum_latency_seconds | 9.953 | 14.954348500003107 |
| truncated_selections | 6 | 6 |
| incomplete_coverage | n/a | 1 |
| api_or_model_failures | n/a | 1 |

## All 12 answerable cases

### E001 ? What happened on 18 July 2026?

- Status: `answered`; validator: `True`; classification: **PARTIALLY_GROUNDED**
- Direct support: `True`; incomplete: `True`
- Selected evidence: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2', 'sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Excluded evidence: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:2', 'sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:B2', 'sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:B3', 'sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:B4', 'sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:B5', 'sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:B6']`
- Handles: `['E1', 'E2', 'E3']`; refs exact: `True`
- Truncated: `True`; coverage complete: `False`; latency: `14.954s`
- Notes: ['Participant-category conflict was not fully preserved.']

Claims:
- `On 18 July 2026, the C-START Industry Interaction Programme was held at the department seminar hall.` ? refs `['E2', 'E3']`; evidence `['sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2']`; directly supported: `True`
- `The C-START Industry Interaction Programme on 18 July 2026 involved 45 third-year students.` ? refs `['E2', 'E3']`; evidence `['sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2']`; directly supported: `True`
- `Mr. Rajesh Pillai, Chief Technology Officer of Nimbus Technologies, delivered the keynote address on 18 July 2026.` ? refs `['E2']`; evidence `['sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`; directly supported: `True`

### E002 ? What meetings happened on 18 July 2026?

- Status: `answered`; validator: `True`; classification: **GROUNDED**
- Direct support: `True`; incomplete: `False`
- Selected evidence: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:2', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Excluded evidence: `[]`
- Handles: `['E1', 'E2']`; refs exact: `True`
- Truncated: `False`; coverage complete: `True`; latency: `4.477s`
- Notes: None

Claims:
- `A department meeting took place on 18 July 2026` ? refs `['E1', 'E2']`; evidence `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:2', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`; directly supported: `True`

### E003 ? Was Dr. Reena Nair present at the meeting on 18 July 2026?

- Status: `None`; validator: `None`; classification: **UNSUPPORTED**
- Direct support: `False`; incomplete: `True`
- Selected evidence: `[]`
- Excluded evidence: `[]`
- Handles: `[]`; refs exact: `True`
- Truncated: `None`; coverage complete: `None`; latency: `3.190s`
- Notes: None

Claims:

### E004 ? When was the faculty meeting rescheduled?

- Status: `answered`; validator: `True`; classification: **GROUNDED**
- Direct support: `True`; incomplete: `False`
- Selected evidence: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:3', 'sha256:d30e1dca7e0cc5b51844c40ef462a33fe1cceb66bfd29acb899f7150f11b0456:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Excluded evidence: `[]`
- Handles: `['E1', 'E2', 'E3']`; refs exact: `True`
- Truncated: `False`; coverage complete: `True`; latency: `4.591s`
- Notes: None

Claims:
- `The faculty meeting was rescheduled to 25 July 2026` ? refs `['E1', 'E2', 'E3']`; evidence `['sha256:d30e1dca7e0cc5b51844c40ef462a33fe1cceb66bfd29acb899f7150f11b0456:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:3']`; directly supported: `True`

### E005 ? What was discussed about lab procurement?

- Status: `answered`; validator: `True`; classification: **GROUNDED**
- Direct support: `True`; incomplete: `False`
- Selected evidence: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:4', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Excluded evidence: `[]`
- Handles: `['E1', 'E2']`; refs exact: `True`
- Truncated: `False`; coverage complete: `True`; latency: `4.655s`
- Notes: None

Claims:
- `The department discussed pending final budget approval for 12 new workstations as part of lab equipment procurement` ? refs `['E2']`; evidence `['sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`; directly supported: `True`

### E006 ? Who coordinated C-START?

- Status: `answered`; validator: `True`; classification: **PARTIALLY_GROUNDED**
- Direct support: `True`; incomplete: `True`
- Selected evidence: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2', 'sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Excluded evidence: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:1', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:4', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:5', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:2']`
- Handles: `['E1', 'E2', 'E3']`; refs exact: `True`
- Truncated: `True`; coverage complete: `True`; latency: `4.314s`
- Notes: ['Coordinator claim did not cite the event report.']

Claims:
- `Prof. Sarah Thomas coordinated C-START` ? refs `['E2', 'E3']`; evidence `['sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2']`; directly supported: `True`

### E007 ? What happened on 10 August 2026 regarding the FDP?

- Status: `answered`; validator: `True`; classification: **GROUNDED**
- Direct support: `True`; incomplete: `False`
- Selected evidence: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:3', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Excluded evidence: `[]`
- Handles: `['E1', 'E2', 'E3']`; refs exact: `True`
- Truncated: `False`; coverage complete: `True`; latency: `5.180s`
- Notes: None

Claims:
- `The Faculty Development Programme (FDP) was planned for the week of 10 August 2026.` ? refs `['E1', 'E3']`; evidence `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:3']`; directly supported: `True`

### E013 ? What decisions were made regarding the FDP?

- Status: `answered`; validator: `True`; classification: **GROUNDED**
- Direct support: `True`; incomplete: `False`
- Selected evidence: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:3', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Excluded evidence: `[]`
- Handles: `['E1', 'E2', 'E3']`; refs exact: `True`
- Truncated: `False`; coverage complete: `True`; latency: `4.810s`
- Notes: None

Claims:
- `The committee agreed to finalize the schedule for the Faculty Development Programme (FDP) at the next meeting on 25 July 2026.` ? refs `['E3']`; evidence `['sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`; directly supported: `True`

### E014 ? What was reported about C-START participation?

- Status: `answered`; validator: `True`; classification: **PARTIALLY_GROUNDED**
- Direct support: `True`; incomplete: `True`
- Selected evidence: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2', 'sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Excluded evidence: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:1', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:4', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:5', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:2']`
- Handles: `['E1', 'E2', 'E3']`; refs exact: `True`
- Truncated: `True`; coverage complete: `True`; latency: `4.504s`
- Notes: ['Participant-category conflict was not fully preserved.']

Claims:
- `Forty-five third-year students attended the C-START Industry Interaction Programme on 2026-07-18.` ? refs `['E2', 'E3']`; evidence `['sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2']`; directly supported: `True`

### E015 ? What happened on 25 July 2026?

- Status: `answered`; validator: `True`; classification: **GROUNDED**
- Direct support: `True`; incomplete: `False`
- Selected evidence: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:3', 'sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:C2', 'sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:C5']`
- Excluded evidence: `['sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:C3', 'sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:C4', 'sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:C6', 'sha256:d30e1dca7e0cc5b51844c40ef462a33fe1cceb66bfd29acb899f7150f11b0456:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Handles: `['E1', 'E2', 'E3']`; refs exact: `True`
- Truncated: `True`; coverage complete: `True`; latency: `4.828s`
- Notes: None

Claims:
- `On 25 July 2026, a Faculty Meeting was held.` ? refs `['E1', 'E2', 'E3']`; evidence `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:3', 'sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:C2', 'sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:C5']`; directly supported: `True`

### E016 ? What happened on 10 August 2026?

- Status: `answered`; validator: `True`; classification: **PARTIALLY_GROUNDED**
- Direct support: `True`; incomplete: `True`
- Selected evidence: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5', 'sha256:d30e1dca7e0cc5b51844c40ef462a33fe1cceb66bfd29acb899f7150f11b0456:pdf-page:1']`
- Excluded evidence: `['sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Handles: `['E1', 'E2', 'E3']`; refs exact: `True`
- Truncated: `True`; coverage complete: `True`; latency: `5.071s`
- Notes: ['Planning and completed lifecycle observations were not both distinguished.']

Claims:
- `The Faculty Development Programme was planned for 10 August 2026` ? refs `['E3', 'E1', 'E2']`; evidence `['sha256:d30e1dca7e0cc5b51844c40ef462a33fe1cceb66bfd29acb899f7150f11b0456:pdf-page:1', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5']`; directly supported: `True`

### E017 ? How many participants were reported for C-START?

- Status: `answered`; validator: `True`; classification: **PARTIALLY_GROUNDED**
- Direct support: `True`; incomplete: `True`
- Selected evidence: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2', 'sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Excluded evidence: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:1', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:4', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:5', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:2']`
- Handles: `['E1', 'E2', 'E3']`; refs exact: `True`
- Truncated: `True`; coverage complete: `True`; latency: `4.588s`
- Notes: ['Participant-category conflict was not fully preserved.']

Claims:
- `45 participants were reported for C-START` ? refs `['E2', 'E3']`; evidence `['sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2']`; directly supported: `True`

## Focused analyses

### E001
- Selector coverage: `{"record_coverage_complete": true, "supporting_coverage_complete": false, "independent_coverage_complete": true, "conflict_coverage_complete": true, "conflict_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}], "coverage_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}, {"coverage_group_id": "coverage:9f8609e436e165eb", "kind": "primary_record_types", "evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:2", "sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:B2"], "selected_evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2"], "excluded_evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:2", "sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:B2"], "reason": "distinct directly relevant record types.", "complete": false}], "coverage_complete": false}`
- Conflict groups: `[{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}]`
- Conflict coverage complete: `True`
- Lifecycle/coverage groups: `[{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}, {"coverage_group_id": "coverage:9f8609e436e165eb", "kind": "primary_record_types", "evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:2", "sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:B2"], "selected_evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2"], "excluded_evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:2", "sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:B2"], "reason": "distinct directly relevant record types.", "complete": false}]`
- Coverage complete: `False`
- Claim analysis: `{"claims": [{"text": "On 18 July 2026, the C-START Industry Interaction Programme was held at the department seminar hall.", "citation_refs": ["E2", "E3"], "cited_evidence_ids": ["sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2"], "directly_supported": true, "overlap_scores": [0.875, 0.375]}, {"text": "The C-START Industry Interaction Programme on 18 July 2026 involved 45 third-year students.", "citation_refs": ["E2", "E3"], "cited_evidence_ids": ["sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2"], "directly_supported": true, "overlap_scores": [0.9333333333333333, 0.4666666666666667]}, {"text": "Mr. Rajesh Pillai, Chief Technology Officer of Nimbus Technologies, delivered the keynote address on 18 July 2026.", "citation_refs": ["E2"], "cited_evidence_ids": ["sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "directly_supported": true, "overlap_scores": [0.8235294117647058]}], "all_claims_directly_supported": true, "classification": "PARTIALLY_GROUNDED", "incomplete": true, "notes": ["Participant-category conflict was not fully preserved."], "conflict_review": {"required": true, "preserved": false, "event_observation_present": false, "meeting_observation_present": true}, "temporal_review": null, "wrong_citation_review": null}`

### E006
- Selector coverage: `{"record_coverage_complete": true, "supporting_coverage_complete": true, "independent_coverage_complete": false, "conflict_coverage_complete": true, "conflict_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}], "coverage_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}], "coverage_complete": true}`
- Conflict groups: `[{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}]`
- Conflict coverage complete: `True`
- Lifecycle/coverage groups: `[{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}]`
- Coverage complete: `True`
- Claim analysis: `{"claims": [{"text": "Prof. Sarah Thomas coordinated C-START", "citation_refs": ["E2", "E3"], "cited_evidence_ids": ["sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2"], "directly_supported": true, "overlap_scores": [0.8333333333333334, 0.8333333333333334]}], "all_claims_directly_supported": true, "classification": "PARTIALLY_GROUNDED", "incomplete": true, "notes": ["Coordinator claim did not cite the event report."], "conflict_review": null, "temporal_review": null, "wrong_citation_review": {"coordinator_claim_present": true, "event_report_cited": false, "wrong_citation": true}}`

### E014
- Selector coverage: `{"record_coverage_complete": true, "supporting_coverage_complete": true, "independent_coverage_complete": false, "conflict_coverage_complete": true, "conflict_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}], "coverage_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}], "coverage_complete": true}`
- Conflict groups: `[{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}]`
- Conflict coverage complete: `True`
- Lifecycle/coverage groups: `[{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}]`
- Coverage complete: `True`
- Claim analysis: `{"claims": [{"text": "Forty-five third-year students attended the C-START Industry Interaction Programme on 2026-07-18.", "citation_refs": ["E2", "E3"], "cited_evidence_ids": ["sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2"], "directly_supported": true, "overlap_scores": [0.875, 0.375]}], "all_claims_directly_supported": true, "classification": "PARTIALLY_GROUNDED", "incomplete": true, "notes": ["Participant-category conflict was not fully preserved."], "conflict_review": {"required": true, "preserved": false, "event_observation_present": false, "meeting_observation_present": true}, "temporal_review": null, "wrong_citation_review": null}`

### E016
- Selector coverage: `{"record_coverage_complete": true, "supporting_coverage_complete": true, "independent_coverage_complete": false, "conflict_coverage_complete": true, "conflict_groups": [], "coverage_groups": [{"coverage_group_id": "coverage:561436382443de26", "kind": "lifecycle", "evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5"], "selected_evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5"], "excluded_evidence_ids": [], "reason": "records describe related lifecycle stages.", "complete": true}, {"coverage_group_id": "coverage:95e01d67bf44d5e4", "kind": "primary_record_types", "evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5"], "selected_evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5"], "excluded_evidence_ids": [], "reason": "distinct directly relevant record types.", "complete": true}], "coverage_complete": true}`
- Conflict groups: `[]`
- Conflict coverage complete: `True`
- Lifecycle/coverage groups: `[{"coverage_group_id": "coverage:561436382443de26", "kind": "lifecycle", "evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5"], "selected_evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5"], "excluded_evidence_ids": [], "reason": "records describe related lifecycle stages.", "complete": true}, {"coverage_group_id": "coverage:95e01d67bf44d5e4", "kind": "primary_record_types", "evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5"], "selected_evidence_ids": ["sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5"], "excluded_evidence_ids": [], "reason": "distinct directly relevant record types.", "complete": true}]`
- Coverage complete: `True`
- Claim analysis: `{"claims": [{"text": "The Faculty Development Programme was planned for 10 August 2026", "citation_refs": ["E3", "E1", "E2"], "cited_evidence_ids": ["sha256:d30e1dca7e0cc5b51844c40ef462a33fe1cceb66bfd29acb899f7150f11b0456:pdf-page:1", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5"], "directly_supported": true, "overlap_scores": [0.9, 0.5, 0.2]}], "all_claims_directly_supported": true, "classification": "PARTIALLY_GROUNDED", "incomplete": true, "notes": ["Planning and completed lifecycle observations were not both distinguished."], "conflict_review": null, "temporal_review": {"required": true, "planning_distinguished": false, "completed_distinguished": false, "preserved": false}, "wrong_citation_review": null}`

### E017
- Selector coverage: `{"record_coverage_complete": true, "supporting_coverage_complete": true, "independent_coverage_complete": false, "conflict_coverage_complete": true, "conflict_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}], "coverage_groups": [{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}], "coverage_complete": true}`
- Conflict groups: `[{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}]`
- Conflict coverage complete: `True`
- Lifecycle/coverage groups: `[{"coverage_group_id": "conflict:024a5a9b0dfb0198", "kind": "conflict", "evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "selected_evidence_ids": ["sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1"], "excluded_evidence_ids": [], "reason": "participant observations differ across selected evidence.", "complete": true}]`
- Coverage complete: `True`
- Claim analysis: `{"claims": [{"text": "45 participants were reported for C-START", "citation_refs": ["E2", "E3"], "cited_evidence_ids": ["sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1", "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2"], "directly_supported": true, "overlap_scores": [0.7142857142857143, 0.5714285714285714]}], "all_claims_directly_supported": true, "classification": "PARTIALLY_GROUNDED", "incomplete": true, "notes": ["Participant-category conflict was not fully preserved."], "conflict_review": {"required": true, "preserved": false, "event_observation_present": false, "meeting_observation_present": false}, "temporal_review": null, "wrong_citation_review": null}`

## Execution validation

- No retries were performed.
- STEP 8 artifacts were preserved.
- The raw JSON includes final contracts, internal claims, handles, selected/excluded evidence, selector metadata, raw Ollama responses, telemetry, and exceptions.
