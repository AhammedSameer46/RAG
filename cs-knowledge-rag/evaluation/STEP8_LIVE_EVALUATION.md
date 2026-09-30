# STEP 8 Live Evaluation ? Claim-Level Contract

Each of the 17 evaluation questions was executed exactly once using the current production pipeline, `gemma3:4b`, and the existing selector configuration. No production or dataset files were modified during the live run.

## Aggregate results

| Metric | Result |
|---|---:|
| total_questions | 17 |
| expected_status_matches | 17 |
| status_accuracy | 1.0 |
| validator_passes | 17 |
| validator_pass_rate | 1.0 |
| valid_citation_handle_cases | 12 |
| valid_citation_handle_rate | 1.0 |
| claims_with_directly_supporting_citations | 12 |
| wrong_citation_count | 0 |
| conflict_preservation_count | 0 |
| temporal_status_interpretation_errors | 1 |
| incomplete_answers | 4 |
| unsupported_claim_cases | 0 |
| api_or_model_failures | 0 |
| average_latency_seconds | 3.5164192000006818 |
| median_latency_seconds | 4.260833299951628 |
| maximum_latency_seconds | 9.953251300030388 |
| truncated_selections | 6 |
| incomplete_supporting_coverage | 0 |
| incomplete_conflict_coverage | 0 |

## Per-question results

### E001 ? What happened on 18 July 2026?

- Expected/final status: `answerable` / `answered`
- Validator valid: `True`
- Selected evidence IDs: `['sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1', 'sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:B5', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Excluded evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:2', 'sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:B2', 'sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:B3', 'sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:B4', 'sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:B6']`
- Supplied handles: `['E1', 'E2', 'E3']`
- Returned refs: `['E1', 'E2']`; all exact: `True`
- Truncated: `True`; latency: `9.953s`; eval_count: `48`; done_reason: `stop`; HTTP: `200`; exception: `None`

Internal model output:
```json
{
  "status": "answered",
  "claims": [
    {
      "text": "The C-START Industry Interaction programme took place on 18 July 2026.",
      "citation_refs": [
        "E1",
        "E2"
      ]
    }
  ]
}
```

Final Answer Contract:
```json
{
  "status": "answered",
  "answer": "The C-START Industry Interaction programme took place on 18 July 2026.",
  "citations": [
    {
      "evidence_id": "sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1",
      "source_id": "sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604",
      "filename": "CSTART_2026_Event_Report.pdf",
      "location": {
        "page": 1
      }
    },
    {
      "evidence_id": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1",
      "source_id": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a",
      "filename": "CS_Dept_Meeting_Minutes_18Jul2026.pdf",
      "location": {
        "page": 1
      }
    }
  ]
}
```

Claim-level classification: **PARTIALLY_GROUNDED**
Direct support for every claim: `True`
Analysis notes: ['Participant-category conflict was not explicitly preserved.']

### E002 ? What meetings happened on 18 July 2026?

- Expected/final status: `answerable` / `answered`
- Validator valid: `True`
- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:2', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Excluded evidence IDs: `[]`
- Supplied handles: `['E1', 'E2']`
- Returned refs: `['E1', 'E2']`; all exact: `True`
- Truncated: `False`; latency: `4.413s`; eval_count: `75`; done_reason: `stop`; HTTP: `200`; exception: `None`

Internal model output:
```json
{
  "status": "answered",
  "claims": [
    {
      "text": "A department meeting happened on 18 July 2026 with Dr. Reena Nair as chair and 5 attendees",
      "citation_refs": [
        "E1",
        "E2"
      ]
    }
  ]
}
```

Final Answer Contract:
```json
{
  "status": "answered",
  "answer": "A department meeting happened on 18 July 2026 with Dr. Reena Nair as chair and 5 attendees",
  "citations": [
    {
      "evidence_id": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:2",
      "source_id": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50",
      "filename": "CS_Meetings_Events_Log.xlsx",
      "location": {
        "sheet": "Meeting Log",
        "row": 2,
        "cell_range": "A:E"
      }
    },
    {
      "evidence_id": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1",
      "source_id": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a",
      "filename": "CS_Dept_Meeting_Minutes_18Jul2026.pdf",
      "location": {
        "page": 1
      }
    }
  ]
}
```

Claim-level classification: **GROUNDED**
Direct support for every claim: `True`
Analysis notes: None

### E003 ? Was Dr. Reena Nair present at the meeting on 18 July 2026?

- Expected/final status: `answerable` / `answered`
- Validator valid: `True`
- Selected evidence IDs: `['sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:B2']`
- Excluded evidence IDs: `[]`
- Supplied handles: `['E1']`
- Returned refs: `['E1']`; all exact: `True`
- Truncated: `False`; latency: `3.964s`; eval_count: `65`; done_reason: `stop`; HTTP: `200`; exception: `None`

Internal model output:
```json
{
  "status": "answered",
  "claims": [
    {
      "text": "Dr. Reena Nair was present at the meeting on 18 July 2026",
      "citation_refs": [
        "E1"
      ]
    }
  ]
}
```

Final Answer Contract:
```json
{
  "status": "answered",
  "answer": "Dr. Reena Nair was present at the meeting on 18 July 2026",
  "citations": [
    {
      "evidence_id": "sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:B2",
      "source_id": "sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35",
      "filename": "CS_Faculty_Attendance_GoogleSheet.xlsx",
      "location": {
        "sheet": "Faculty Attendance",
        "row": 2,
        "cell": "B2"
      }
    }
  ]
}
```

Claim-level classification: **GROUNDED**
Direct support for every claim: `True`
Analysis notes: None

### E004 ? When was the faculty meeting rescheduled?

- Expected/final status: `answerable` / `answered`
- Validator valid: `True`
- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:3', 'sha256:d30e1dca7e0cc5b51844c40ef462a33fe1cceb66bfd29acb899f7150f11b0456:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Excluded evidence IDs: `[]`
- Supplied handles: `['E1', 'E2', 'E3']`
- Returned refs: `['E1', 'E2', 'E3']`; all exact: `True`
- Truncated: `False`; latency: `4.261s`; eval_count: `68`; done_reason: `stop`; HTTP: `200`; exception: `None`

Internal model output:
```json
{
  "status": "answered",
  "claims": [
    {
      "text": "The faculty meeting was rescheduled to 25 July 2026",
      "citation_refs": [
        "E1",
        "E2",
        "E3"
      ]
    }
  ]
}
```

Final Answer Contract:
```json
{
  "status": "answered",
  "answer": "The faculty meeting was rescheduled to 25 July 2026",
  "citations": [
    {
      "evidence_id": "sha256:d30e1dca7e0cc5b51844c40ef462a33fe1cceb66bfd29acb899f7150f11b0456:pdf-page:1",
      "source_id": "sha256:d30e1dca7e0cc5b51844c40ef462a33fe1cceb66bfd29acb899f7150f11b0456",
      "filename": "CS_Notice_FacultyMeeting.pdf",
      "location": {
        "page": 1
      }
    },
    {
      "evidence_id": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1",
      "source_id": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a",
      "filename": "CS_Dept_Meeting_Minutes_18Jul2026.pdf",
      "location": {
        "page": 1
      }
    },
    {
      "evidence_id": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:3",
      "source_id": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50",
      "filename": "CS_Meetings_Events_Log.xlsx",
      "location": {
        "sheet": "Meeting Log",
        "row": 3,
        "cell_range": "A:E"
      }
    }
  ]
}
```

Claim-level classification: **GROUNDED**
Direct support for every claim: `True`
Analysis notes: None

### E005 ? What was discussed about lab procurement?

- Expected/final status: `answerable` / `answered`
- Validator valid: `True`
- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:4', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Excluded evidence IDs: `[]`
- Supplied handles: `['E1', 'E2']`
- Returned refs: `['E2']`; all exact: `True`
- Truncated: `False`; latency: `4.303s`; eval_count: `74`; done_reason: `stop`; HTTP: `200`; exception: `None`

Internal model output:
```json
{
  "status": "answered",
  "claims": [
    {
      "text": "The department discussed pending lab equipment procurement (12 new workstations) pending final budget approval from the college administration, expected by the end of the month.",
      "citation_refs": [
        "E2"
      ]
    }
  ]
}
```

Final Answer Contract:
```json
{
  "status": "answered",
  "answer": "The department discussed pending lab equipment procurement (12 new workstations) pending final budget approval from the college administration, expected by the end of the month.",
  "citations": [
    {
      "evidence_id": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1",
      "source_id": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a",
      "filename": "CS_Dept_Meeting_Minutes_18Jul2026.pdf",
      "location": {
        "page": 1
      }
    }
  ]
}
```

Claim-level classification: **GROUNDED**
Direct support for every claim: `True`
Analysis notes: None

### E006 ? Who coordinated C-START?

- Expected/final status: `answerable` / `answered`
- Validator valid: `True`
- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2', 'sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Excluded evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:1', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:4', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:5', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:2']`
- Supplied handles: `['E1', 'E2', 'E3']`
- Returned refs: `['E1', 'E2', 'E3']`; all exact: `True`
- Truncated: `True`; latency: `4.330s`; eval_count: `53`; done_reason: `stop`; HTTP: `200`; exception: `None`

Internal model output:
```json
{
  "status": "answered",
  "claims": [
    {
      "text": "Prof. Sarah Thomas coordinated C-START.",
      "citation_refs": [
        "E1",
        "E2",
        "E3"
      ]
    }
  ]
}
```

Final Answer Contract:
```json
{
  "status": "answered",
  "answer": "Prof. Sarah Thomas coordinated C-START.",
  "citations": [
    {
      "evidence_id": "sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1",
      "source_id": "sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604",
      "filename": "CSTART_2026_Event_Report.pdf",
      "location": {
        "page": 1
      }
    },
    {
      "evidence_id": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1",
      "source_id": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a",
      "filename": "CS_Dept_Meeting_Minutes_18Jul2026.pdf",
      "location": {
        "page": 1
      }
    },
    {
      "evidence_id": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2",
      "source_id": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50",
      "filename": "CS_Meetings_Events_Log.xlsx",
      "location": {
        "sheet": "Events",
        "row": 2,
        "cell_range": "A:F"
      }
    }
  ]
}
```

Claim-level classification: **GROUNDED**
Direct support for every claim: `True`
Analysis notes: None

### E007 ? What happened on 10 August 2026 regarding the FDP?

- Expected/final status: `answerable` / `answered`
- Validator valid: `True`
- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:3', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Excluded evidence IDs: `[]`
- Supplied handles: `['E1', 'E2', 'E3']`
- Returned refs: `['E1', 'E3']`; all exact: `True`
- Truncated: `False`; latency: `4.871s`; eval_count: `85`; done_reason: `stop`; HTTP: `200`; exception: `None`

Internal model output:
```json
{
  "status": "answered",
  "claims": [
    {
      "text": "The Faculty Development Programme (FDP) was planned for the week of 10 August 2026 at the meeting on 25 July 2026.",
      "citation_refs": [
        "E1",
        "E3"
      ]
    }
  ]
}
```

Final Answer Contract:
```json
{
  "status": "answered",
  "answer": "The Faculty Development Programme (FDP) was planned for the week of 10 August 2026 at the meeting on 25 July 2026.",
  "citations": [
    {
      "evidence_id": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5",
      "source_id": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50",
      "filename": "CS_Meetings_Events_Log.xlsx",
      "location": {
        "sheet": "Meeting Log",
        "row": 5,
        "cell_range": "A:E"
      }
    },
    {
      "evidence_id": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:3",
      "source_id": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50",
      "filename": "CS_Meetings_Events_Log.xlsx",
      "location": {
        "sheet": "Meeting Log",
        "row": 3,
        "cell_range": "A:E"
      }
    }
  ]
}
```

Claim-level classification: **GROUNDED**
Direct support for every claim: `True`
Analysis notes: None

### E008 ? Which meetings did Prof. Sarah Thomas attend?

- Expected/final status: `clarification_required` / `clarification_required`
- Validator valid: `True`
- Selected evidence IDs: `[]`
- Excluded evidence IDs: `[]`
- Supplied handles: `[]`
- Returned refs: `[]`; all exact: `True`
- Truncated: `False`; latency: `0.000s`; eval_count: `None`; done_reason: `None`; HTTP: `None`; exception: `None`

Final Answer Contract:
```json
{
  "status": "clarification_required",
  "answer": "",
  "citations": []
}
```

### E009 ? Who attended the C-START event?

- Expected/final status: `clarification_required` / `clarification_required`
- Validator valid: `True`
- Selected evidence IDs: `[]`
- Excluded evidence IDs: `[]`
- Supplied handles: `[]`
- Returned refs: `[]`; all exact: `True`
- Truncated: `False`; latency: `0.000s`; eval_count: `None`; done_reason: `None`; HTTP: `None`; exception: `None`

Final Answer Contract:
```json
{
  "status": "clarification_required",
  "answer": "",
  "citations": []
}
```

### E010 ? What happened on 18 July?

- Expected/final status: `clarification_required` / `clarification_required`
- Validator valid: `True`
- Selected evidence IDs: `[]`
- Excluded evidence IDs: `[]`
- Supplied handles: `[]`
- Returned refs: `[]`; all exact: `True`
- Truncated: `False`; latency: `0.000s`; eval_count: `None`; done_reason: `None`; HTTP: `None`; exception: `None`

Final Answer Contract:
```json
{
  "status": "clarification_required",
  "answer": "",
  "citations": []
}
```

### E011 ? Tell me something about the department.

- Expected/final status: `clarification_required` / `clarification_required`
- Validator valid: `True`
- Selected evidence IDs: `[]`
- Excluded evidence IDs: `[]`
- Supplied handles: `[]`
- Returned refs: `[]`; all exact: `True`
- Truncated: `False`; latency: `0.000s`; eval_count: `None`; done_reason: `None`; HTTP: `None`; exception: `None`

Final Answer Contract:
```json
{
  "status": "clarification_required",
  "answer": "",
  "citations": []
}
```

### E012 ? What happened on 10 January 2099?

- Expected/final status: `insufficient_evidence` / `insufficient_evidence`
- Validator valid: `True`
- Selected evidence IDs: `[]`
- Excluded evidence IDs: `[]`
- Supplied handles: `[]`
- Returned refs: `[]`; all exact: `True`
- Truncated: `False`; latency: `0.000s`; eval_count: `None`; done_reason: `None`; HTTP: `None`; exception: `None`

Final Answer Contract:
```json
{
  "status": "insufficient_evidence",
  "answer": "",
  "citations": []
}
```

### E013 ? What decisions were made regarding the FDP?

- Expected/final status: `answerable` / `answered`
- Validator valid: `True`
- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:3', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Excluded evidence IDs: `[]`
- Supplied handles: `['E1', 'E2', 'E3']`
- Returned refs: `['E3']`; all exact: `True`
- Truncated: `False`; latency: `4.460s`; eval_count: `75`; done_reason: `stop`; HTTP: `200`; exception: `None`

Internal model output:
```json
{
  "status": "answered",
  "claims": [
    {
      "text": "The committee agreed to finalize the schedule for the Faculty Development Programme (FDP) at the next meeting on 25 July 2026.",
      "citation_refs": [
        "E3"
      ]
    }
  ]
}
```

Final Answer Contract:
```json
{
  "status": "answered",
  "answer": "The committee agreed to finalize the schedule for the Faculty Development Programme (FDP) at the next meeting on 25 July 2026.",
  "citations": [
    {
      "evidence_id": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1",
      "source_id": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a",
      "filename": "CS_Dept_Meeting_Minutes_18Jul2026.pdf",
      "location": {
        "page": 1
      }
    }
  ]
}
```

Claim-level classification: **GROUNDED**
Direct support for every claim: `True`
Analysis notes: None

### E014 ? What was reported about C-START participation?

- Expected/final status: `answerable` / `answered`
- Validator valid: `True`
- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2', 'sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Excluded evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:1', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:4', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:5', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:2']`
- Supplied handles: `['E1', 'E2', 'E3']`
- Returned refs: `['E2', 'E3']`; all exact: `True`
- Truncated: `True`; latency: `4.229s`; eval_count: `54`; done_reason: `stop`; HTTP: `200`; exception: `None`

Internal model output:
```json
{
  "status": "answered",
  "claims": [
    {
      "text": "Forty-five third-year students attended the C-START Industry Interaction Programme on 18 July 2026.",
      "citation_refs": [
        "E2",
        "E3"
      ]
    }
  ]
}
```

Final Answer Contract:
```json
{
  "status": "answered",
  "answer": "Forty-five third-year students attended the C-START Industry Interaction Programme on 18 July 2026.",
  "citations": [
    {
      "evidence_id": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1",
      "source_id": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a",
      "filename": "CS_Dept_Meeting_Minutes_18Jul2026.pdf",
      "location": {
        "page": 1
      }
    },
    {
      "evidence_id": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2",
      "source_id": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50",
      "filename": "CS_Meetings_Events_Log.xlsx",
      "location": {
        "sheet": "Events",
        "row": 2,
        "cell_range": "A:F"
      }
    }
  ]
}
```

Claim-level classification: **PARTIALLY_GROUNDED**
Direct support for every claim: `True`
Analysis notes: ['Participant-category conflict was not explicitly preserved.']

### E015 ? What happened on 25 July 2026?

- Expected/final status: `answerable` / `answered`
- Validator valid: `True`
- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:3', 'sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:C2', 'sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:C5']`
- Excluded evidence IDs: `['sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:C3', 'sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:C4', 'sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:C6', 'sha256:d30e1dca7e0cc5b51844c40ef462a33fe1cceb66bfd29acb899f7150f11b0456:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Supplied handles: `['E1', 'E2', 'E3']`
- Returned refs: `['E1', 'E2', 'E3', 'E2', 'E2']`; all exact: `True`
- Truncated: `True`; latency: `6.643s`; eval_count: `188`; done_reason: `stop`; HTTP: `200`; exception: `None`

Internal model output:
```json
{
  "status": "answered",
  "claims": [
    {
      "text": "On 25 July 2026, Prof. Divya Menon was present at the 25-Jul-2026 (Faculty Mtg) meeting",
      "citation_refs": [
        "E1"
      ]
    },
    {
      "text": "On 25 July 2026, Dr. Reena Nair was present at the 25-Jul-2026 (Faculty Mtg) meeting",
      "citation_refs": [
        "E2",
        "E3"
      ]
    },
    {
      "text": "On 25 July 2026, the attendees count for the meeting was 5",
      "citation_refs": [
        "E2"
      ]
    },
    {
      "text": "On 25 July 2026, the final decision for the FDP schedule was finalized",
      "citation_refs": [
        "E2"
      ]
    }
  ]
}
```

Final Answer Contract:
```json
{
  "status": "answered",
  "answer": "On 25 July 2026, Prof. Divya Menon was present at the 25-Jul-2026 (Faculty Mtg) meeting\nOn 25 July 2026, Dr. Reena Nair was present at the 25-Jul-2026 (Faculty Mtg) meeting\nOn 25 July 2026, the attendees count for the meeting was 5\nOn 25 July 2026, the final decision for the FDP schedule was finalized",
  "citations": [
    {
      "evidence_id": "sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:C5",
      "source_id": "sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35",
      "filename": "CS_Faculty_Attendance_GoogleSheet.xlsx",
      "location": {
        "sheet": "Faculty Attendance",
        "row": 5,
        "cell": "C5"
      }
    },
    {
      "evidence_id": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:3",
      "source_id": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50",
      "filename": "CS_Meetings_Events_Log.xlsx",
      "location": {
        "sheet": "Meeting Log",
        "row": 3,
        "cell_range": "A:E"
      }
    },
    {
      "evidence_id": "sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35:sheet:Faculty Attendance:cell:C2",
      "source_id": "sha256:baa9d6f5734fae547201f0d524282640b752d33d89f237ff13a6e8f77f0fed35",
      "filename": "CS_Faculty_Attendance_GoogleSheet.xlsx",
      "location": {
        "sheet": "Faculty Attendance",
        "row": 2,
        "cell": "C2"
      }
    }
  ]
}
```

Claim-level classification: **GROUNDED**
Direct support for every claim: `True`
Analysis notes: None

### E016 ? What happened on 10 August 2026?

- Expected/final status: `answerable` / `answered`
- Validator valid: `True`
- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5', 'sha256:d30e1dca7e0cc5b51844c40ef462a33fe1cceb66bfd29acb899f7150f11b0456:pdf-page:1']`
- Excluded evidence IDs: `['sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Supplied handles: `['E1', 'E2', 'E3']`
- Returned refs: `['E1', 'E2', 'E3']`; all exact: `True`
- Truncated: `True`; latency: `4.324s`; eval_count: `69`; done_reason: `stop`; HTTP: `200`; exception: `None`

Internal model output:
```json
{
  "status": "answered",
  "claims": [
    {
      "text": "The Faculty Development Programme was scheduled for 10 August 2026",
      "citation_refs": [
        "E1",
        "E2",
        "E3"
      ]
    }
  ]
}
```

Final Answer Contract:
```json
{
  "status": "answered",
  "answer": "The Faculty Development Programme was scheduled for 10 August 2026",
  "citations": [
    {
      "evidence_id": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3",
      "source_id": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50",
      "filename": "CS_Meetings_Events_Log.xlsx",
      "location": {
        "sheet": "Events",
        "row": 3,
        "cell_range": "A:F"
      }
    },
    {
      "evidence_id": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:5",
      "source_id": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50",
      "filename": "CS_Meetings_Events_Log.xlsx",
      "location": {
        "sheet": "Meeting Log",
        "row": 5,
        "cell_range": "A:E"
      }
    },
    {
      "evidence_id": "sha256:d30e1dca7e0cc5b51844c40ef462a33fe1cceb66bfd29acb899f7150f11b0456:pdf-page:1",
      "source_id": "sha256:d30e1dca7e0cc5b51844c40ef462a33fe1cceb66bfd29acb899f7150f11b0456",
      "filename": "CS_Notice_FacultyMeeting.pdf",
      "location": {
        "page": 1
      }
    }
  ]
}
```

Claim-level classification: **PARTIALLY_GROUNDED**
Direct support for every claim: `True`
Analysis notes: ['Planning and completed FDP observations were not both distinguished.']

### E017 ? How many participants were reported for C-START?

- Expected/final status: `answerable` / `answered`
- Validator valid: `True`
- Selected evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2', 'sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1', 'sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1']`
- Excluded evidence IDs: `['sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:1', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:3', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:4', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:5', 'sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Meeting Log:row:2']`
- Supplied handles: `['E1', 'E2', 'E3']`
- Returned refs: `['E1', 'E2', 'E3']`; all exact: `True`
- Truncated: `True`; latency: `4.028s`; eval_count: `42`; done_reason: `stop`; HTTP: `200`; exception: `None`

Internal model output:
```json
{
  "status": "answered",
  "claims": [
    {
      "text": "45 participants were reported for C-START",
      "citation_refs": [
        "E1",
        "E2",
        "E3"
      ]
    }
  ]
}
```

Final Answer Contract:
```json
{
  "status": "answered",
  "answer": "45 participants were reported for C-START",
  "citations": [
    {
      "evidence_id": "sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604:pdf-page:1",
      "source_id": "sha256:ac8417244848ef99ee602bc6acb233dd7eb5303d186870467f2e796cb4907604",
      "filename": "CSTART_2026_Event_Report.pdf",
      "location": {
        "page": 1
      }
    },
    {
      "evidence_id": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a:pdf-page:1",
      "source_id": "sha256:f91a35b72d48ba190bf53134fe758ec83f4daf55846e7b1dd1ea86ad32e07b8a",
      "filename": "CS_Dept_Meeting_Minutes_18Jul2026.pdf",
      "location": {
        "page": 1
      }
    },
    {
      "evidence_id": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50:sheet:Events:row:2",
      "source_id": "sha256:a5940c52f86718b17baded15e84f10cd2388a4b7026c95570f32a3c642703c50",
      "filename": "CS_Meetings_Events_Log.xlsx",
      "location": {
        "sheet": "Events",
        "row": 2,
        "cell_range": "A:F"
      }
    }
  ]
}
```

Claim-level classification: **PARTIALLY_GROUNDED**
Direct support for every claim: `True`
Analysis notes: ['Participant-category conflict was not explicitly preserved.']

## Claim-level analysis for answerable cases

The JSON artifact contains per-claim text, exact refs, cited evidence IDs, and support checks for all 12 answerable cases. A structurally valid citation was not treated as proof of factual support.

## Focused cases

### E001
- Classification: **PARTIALLY_GROUNDED**
- Conflict review: `{'required': True, 'preserved': False, 'reason': 'Both participant observations must remain separately attributed.'}`
- Temporal review: `None`
- Wrong-citation review: `None`
- Notes: ['Participant-category conflict was not explicitly preserved.']

### E006
- Classification: **GROUNDED**
- Conflict review: `None`
- Temporal review: `None`
- Wrong-citation review: `{'claim_mentions_coordinator': True, 'event_report_cited': True, 'wrong_citation': False}`
- Notes: None

### E014
- Classification: **PARTIALLY_GROUNDED**
- Conflict review: `{'required': True, 'preserved': False, 'reason': 'Both participant observations must remain separately attributed.'}`
- Temporal review: `None`
- Wrong-citation review: `None`
- Notes: ['Participant-category conflict was not explicitly preserved.']

### E016
- Classification: **PARTIALLY_GROUNDED**
- Conflict review: `None`
- Temporal review: `{'required': True, 'planning_distinguished': False, 'completed_distinguished': False, 'preserved': False}`
- Wrong-citation review: `None`
- Notes: ['Planning and completed FDP observations were not both distinguished.']

### E017
- Classification: **PARTIALLY_GROUNDED**
- Conflict review: `{'required': True, 'preserved': False, 'reason': 'Both participant observations must remain separately attributed.'}`
- Temporal review: `None`
- Wrong-citation review: `None`
- Notes: ['Participant-category conflict was not explicitly preserved.']

## Comparison with previous evaluation

Previous evaluation baseline: 17/17 expected-status matches, 17/17 validator passes, 12/12 answerable cases with valid citation refs, and 0 API/model failures. The current run preserves the same status, validator, citation-handle, and failure baseline while adding claim-level measurements above.
