# STEP 11B Controlled Live Smoke Test

## Configuration

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
  "question_ids": [
    "E001",
    "E006",
    "E014",
    "E016",
    "E017"
  ],
  "question_count": 5,
  "attempts_per_question": 1,
  "retry_policy": "none"
}
```

## Per-question results

| ID | Expected | Actual | Validator | Obligation | Missing obligations | Wrong citations | API failure |
|---|---|---|---|---|---|---|---|
| E001 | answerable | answered | True | PARTIAL | ['cstart_participant_category', 'department_meeting'] | [] | None |

### E001 details

- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2', 'sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Claim-level output: `{"status": "answered", "claims": [{"text": "On 18 July 2026, the C-START Industry Interaction programme was held.", "citation_refs": ["E2", "E3"]}, {"text": "The C-START Industry Interaction programme on 18 July 2026 involved 45 third-year students.", "citation_refs": ["E2", "E3"]}, {"text": "Prof. Sarah Thomas was the event coordinator for the C-START Industry Interaction programme on 18 July 2026.", "citation_refs": ["E2", "E3"]}]}`
- Citation mapping: `{"E1": "sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "E2": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1", "E3": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2"}`
- Obligation evaluation: `{"status": "PARTIAL", "required_obligations": ["event_activity", "department_meeting", "participant_conflict"], "satisfied_obligations": ["event_activity", "participant_conflict"], "missing_obligations": ["cstart_participant_category", "department_meeting"], "wrong_citation_obligations": [], "invalid_evidence_handles": [], "conflict_preservation": [{"id": "cstart_participant_category", "satisfied": false, "complete": false, "observations": [{"id": "event_report_participants", "satisfied": false, "wrong_citation": false}, {"id": "meeting_minutes_participants", "satisfied": true, "wrong_citation": false}]}], "lifecycle_distinction": [], "direct_citation_requirements": [], "acceptable_scope": ["Attendance rows need not be listed individually unless attendance is claimed or the answer asserts complete same-day coverage."], "incomplete_conditions": ["Missing the meeting or event for a broad date answer.", "Mentioning participation without preserving both participant-category observations."]}`

| E006 | answerable | answered | True | PASS | [] | [] | None |

### E006 details

- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2', 'sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Claim-level output: `{"status": "answered", "claims": [{"text": "Prof. Sarah Thomas coordinated C-START", "citation_refs": ["E1", "E2", "E3"]}]}`
- Citation mapping: `{"E1": "sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "E2": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1", "E3": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2"}`
- Obligation evaluation: `{"status": "PASS", "required_obligations": ["coordinator"], "satisfied_obligations": ["coordinator"], "missing_obligations": [], "wrong_citation_obligations": [], "invalid_evidence_handles": [], "conflict_preservation": [], "lifecycle_distinction": [], "direct_citation_requirements": [{"id": "coordinator", "satisfied": true, "wrong_citation": false}], "acceptable_scope": ["Only the coordinator needs to be answered."], "incomplete_conditions": ["Sarah Thomas is absent.", "Sarah Thomas is cited only to meeting minutes that do not identify her as coordinator."]}`

| E014 | answerable | answered | True | FAIL | ['cstart_participant_category', 'participant_count'] | [] | None |

### E014 details

- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2', 'sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Claim-level output: `{"status": "answered", "claims": [{"text": "Forty-five third-year students participated in the C-START Industry Interaction programme.", "citation_refs": ["E2"]}, {"text": "Forty-five students from the third and fourth year batches participated in the C-START Industry Interaction programme.", "citation_refs": ["E1"]}, {"text": "The C-START Industry Interaction programme was completed on 2026-07-18.", "citation_refs": ["E2"]}]}`
- Citation mapping: `{"E1": "sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "E2": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1", "E3": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2"}`
- Obligation evaluation: `{"status": "FAIL", "required_obligations": ["participant_count"], "satisfied_obligations": [], "missing_obligations": ["cstart_participant_category", "participant_count"], "wrong_citation_obligations": [], "invalid_evidence_handles": [], "conflict_preservation": [{"id": "cstart_participant_category", "satisfied": false, "complete": false, "observations": [{"id": "event_report_participants", "satisfied": false, "wrong_citation": false}, {"id": "meeting_minutes_participants", "satisfied": false, "wrong_citation": false}]}], "lifecycle_distinction": [], "direct_citation_requirements": [], "acceptable_scope": ["The answer may omit unrelated event details, but not the category discrepancy."], "incomplete_conditions": ["Only one participant observation is stated.", "The count is stated without the differing categories."]}`

| E016 | answerable | answered | True | PARTIAL | ['completed_event', 'fdp_planning_vs_completed'] | [] | None |

### E016 details

- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5', 'sha256:d30e1dca7e0cc5b51844c40ef462a33fe1cceb66bfd29acb899f7150f11b0456:pdf-page:1']`
- Claim-level output: `{"status": "answered", "claims": [{"text": "The Faculty Development Programme was planned for 10 August 2026", "citation_refs": ["E3", "E1"]}, {"text": "The Faculty Development Programme started on 10 August 2026", "citation_refs": ["E1"]}, {"text": "The Faculty Development Programme ended on 14 August 2026", "citation_refs": ["E1"]}, {"text": "A meeting was held on 10 August 2026 for FDP Planning", "citation_refs": ["E2"]}, {"text": "Prof. Arun Kumar was the chair of the FDP Planning meeting on 10 August 2026", "citation_refs": ["E2"]}, {"text": "Six attendees were present at the FDP Planning meeting on 10 August 2026", "citation_refs": ["E2"]}]}`
- Citation mapping: `{"E1": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3", "E2": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5", "E3": "sha256:d30e1dca7e0cc5b51844c40ef462a33fe1cceb66bfd29acb899f7150f11b0456:pdf-page:1"}`
- Obligation evaluation: `{"status": "PARTIAL", "required_obligations": ["planning_meeting", "completed_event"], "satisfied_obligations": ["planning_meeting"], "missing_obligations": ["completed_event", "fdp_planning_vs_completed"], "wrong_citation_obligations": [], "invalid_evidence_handles": [], "conflict_preservation": [], "lifecycle_distinction": [{"id": "fdp_planning_vs_completed", "satisfied": false, "complete": false, "observations": [{"id": "planning", "satisfied": true, "wrong_citation": false}, {"id": "completed", "satisfied": false, "wrong_citation": false}]}], "direct_citation_requirements": [], "acceptable_scope": ["A narrowly scoped answer must identify that it is discussing only the planning meeting or only the completed event."], "incomplete_conditions": ["Planning is presented as completion or completion is presented as planning.", "One lifecycle observation is silently omitted."]}`

| E017 | answerable | answered | True | FAIL | ['participant_category_discrepancy'] | ['reported_count'] | None |

### E017 details

- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2', 'sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Claim-level output: `{"status": "answered", "claims": [{"text": "The number of participants reported for C-START was 45", "citation_refs": ["E2", "E3"]}]}`
- Citation mapping: `{"E1": "sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1", "E2": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1", "E3": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2"}`
- Obligation evaluation: `{"status": "FAIL", "required_obligations": ["reported_count"], "satisfied_obligations": [], "missing_obligations": ["participant_category_discrepancy"], "wrong_citation_obligations": ["reported_count"], "invalid_evidence_handles": [], "conflict_preservation": [{"id": "participant_category_discrepancy", "satisfied": false, "complete": false, "observations": [{"id": "event_report_category", "satisfied": false, "wrong_citation": false}, {"id": "meeting_minutes_category", "satisfied": false, "wrong_citation": false}]}], "lifecycle_distinction": [], "direct_citation_requirements": [], "acceptable_scope": ["The numeric answer may be concise, but a fully grounded answer must preserve the category discrepancy."], "incomplete_conditions": ["Only the number 45 is returned without the two category observations."]}`

## Step 10B vs Step 11B comparison

| ID | Step 10B obligation | Step 11B obligation | Step 10B conflict | Step 11B conflict | Step 10B lifecycle | Step 11B lifecycle |
|---|---|---|---|---|---|---|
| E001 | PARTIAL | PARTIAL | False | False | None | None |
| E006 | PASS | PASS | None | None | None | None |
| E014 | FAIL | FAIL | False | False | None | None |
| E016 | FAIL | PARTIAL | None | None | False | False |
| E017 | FAIL | FAIL | False | False | None | None |

## Aggregate comparison

- Step 11B summary: `{"obligation_pass": 1, "obligation_partial": 2, "obligation_fail": 2, "model_api_failures": 0, "conflict_complete_count": 0, "lifecycle_complete_count": 0, "average_latency_seconds": 7.638550340034999, "improved_obligation_cases": []}`
- Observable improvement is credited only where the deterministic obligation status improves or a required conflict/lifecycle group becomes complete.
- No improvement is claimed from prompt wording, validator success, or citation-handle validity alone.

## Citation correctness and latency

- E001: wrong citations Step 10B `[]` -> Step 11B `[]`; latency 13.766s -> 13.992s.
- E006: wrong citations Step 10B `[]` -> Step 11B `[]`; latency 3.959s -> 4.657s.
- E014: wrong citations Step 10B `[]` -> Step 11B `[]`; latency 4.185s -> 6.141s.
- E016: wrong citations Step 10B `[]` -> Step 11B `[]`; latency 4.406s -> 8.878s.
- E017: wrong citations Step 10B `[]` -> Step 11B `['reported_count']`; latency 4.735s -> 4.525s.
