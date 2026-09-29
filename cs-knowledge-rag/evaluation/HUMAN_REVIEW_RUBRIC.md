# Human-Review Evaluation Rubric

This rubric is for manual review of the 12 answerable questions in
[`sample_questions.json`](./sample_questions.json). It evaluates factual
grounding and completeness separately from the Answer Contract validator.

The authoritative review boundary is
[`output/sample_normalized.json`](../output/sample_normalized.json). Reviewers
must inspect the exact evidence object, including PDF page, spreadsheet sheet,
row, cell, header context, and raw value where present.

## Review procedure

For each answer:

1. Break the answer into atomic factual claims.
2. Locate direct support for each claim in the selected evidence.
3. Verify every citation against the exact cited evidence, not merely the
   source file.
4. Check whether relevant evidence was excluded by selector truncation.
5. Check conflict requirements before assigning a label.

Do not treat validator success as proof of factual correctness. A validator
pass proves structural and provenance consistency only.

## Labels

- **GROUNDED**: Every material claim is directly supported by selected
  evidence; citations support the nearby claims; required conflicts are
  preserved; and the answer is complete enough for the question.
- **PARTIALLY_GROUNDED**: The central answer is supported, but one or more
  material claims are omitted, overgeneralized, weakly supported, or a
  relevant conflict is incompletely represented.
- **UNSUPPORTED**: A material claim has no support in the selected evidence,
  or the answer relies on outside knowledge or an inference not warranted by
  the evidence.
- **INCOMPLETE**: The answer omits a material fact required by the question or
  omits a required source observation. Use this in addition to, or as the
  reason for, a partial-grounding decision where appropriate.
- **WRONG_CITATION**: The citation is structurally valid but does not support
  the nearby claim, even if another selected evidence unit would support it.
- **NEEDS_HUMAN_REVIEW**: Use when the reviewer cannot safely decide from the
  available evidence, particularly where truncation removed relevant records,
  the answer combines claims across sources, or the claim boundary is
  ambiguous. Do not force a stronger label.

## Definitions

### Unsupported claim

A claim is unsupported when no selected evidence states it, records it in a
raw value/header, or provides an unavoidable direct statement. Do not treat a
shared date, filename, record type, or plausible inference as support for a
specific fact.

### Structurally valid but non-supporting citation

A citation is wrong when its evidence ID, source ID, filename, and location
are exact, but the cited page/row/cell does not contain the fact asserted
nearby. A source that discusses the same topic is not sufficient.

### Conflict preservation

When two selected authoritative observations disagree in a material
dimension, the answer must report both observations or explicitly state that
the sources differ. It must not silently merge, reconcile, or select one
observation. The known C-START conflict is:

- Meeting minutes PDF, page 1: **45 third-year students attended**.
- C-START event report PDF, page 1: **45 students from the third and fourth
  year batches participated**.

The count agrees, but the participant category differs.

### Selector truncation

If `selection.truncated` is true, reviewers must distinguish:

- **Answer omission**: a relevant fact was excluded and the answer claims
  completeness without acknowledging the missing coverage.
- **Acceptable scope**: the answer is explicitly limited to the selected
  evidence and does not imply that excluded records were considered.

An excluded evidence unit must not be used to credit a claim unless the same
claim is independently supported by selected evidence.

## Case-specific criteria

Evidence IDs below are the expected source boundary from the existing
evaluation dataset. They identify evidence that may be required, not facts
that a model must mention verbatim in every response.

### E001 — What happened on 18 July 2026?

**Expected scope:** broad date activity. A complete answer should reasonably
cover the C-START event, the department meeting, and relevant attendance
observations represented by the date query.

**Material claims to review:**

- C-START occurred on 18 July 2026.
- Event location/time and major activity details, if mentioned.
- Event participation and coordinator, if mentioned.
- A department meeting occurred on the same date.
- Meeting decisions or discussion details, if mentioned.
- Attendance facts, if mentioned, must use the correct meeting header and
  person/value.

**Required evidence boundary:** event row 2, meeting-log row 2, C-START PDF
page 1, meeting-minutes PDF page 1, and attendance cells B2:B6. The complete
IDs are in the JSON template.

**Conflict requirement:** if participation is reported, preserve both
participant-category observations. A single “45 participants” statement is
incomplete for a broad answer when it suppresses the category difference.

**Review outcome:** GROUNDED only when material date activities are covered and
the relevant conflict is preserved; otherwise PARTIALLY_GROUNDED or INCOMPLETE.

### E002 — What meetings happened on 18 July 2026?

**Material claims to review:**

- A Department Meeting occurred on 18 July 2026.
- Chair, attendee count, and approved C-START budget may be stated only if
  supported by Meeting Log row 2.
- Meeting minutes may corroborate the meeting but must not be used to claim
  spreadsheet-only fields without direct support.

**Required evidence:** Meeting Log row 2 and meeting-minutes PDF page 1.

**Scope rule:** Do not require the same-day C-START event or attendance rows;
the question is meeting-focused. Including them is unnecessary and may make
the answer less precise, but is not by itself unsupported if accurately
identified as separate records.

### E003 — Was Dr. Reena Nair present at the meeting on 18 July 2026?

**Material claim:** Dr. Reena Nair was present.

**Required evidence:** Faculty Attendance sheet, row 2, cell B2, whose header is
`18-Jul-2026 (Dept Mtg)` and value is `Present`.

**Citation rule:** A citation to another attendance cell, row, or date header
does not support this claim.

### E004 — When was the faculty meeting rescheduled?

**Material claim:** The faculty meeting was rescheduled to 25 July 2026; the
original date was 20 July 2026 if the answer mentions it.

**Required evidence:** Faculty notice PDF page 1 is the direct source. Meeting
Log row 3 and meeting-minutes PDF page 1 are corroborating/date-related
evidence, not a substitute for the notice's rescheduling statement.

**Scope rule:** Do not require a fabricated normalized “rescheduled meeting”
record.

### E005 — What was discussed about lab procurement?

**Material claims:**

- Procurement concerned 12 new workstations.
- Final budget approval from college administration was pending.
- Approval was expected by the end of the month.

**Required evidence:** Meeting Log row 4 and meeting-minutes PDF page 1.

**Role rule:** The spreadsheet row is supporting evidence for the meeting
record. A PDF keyword match may be independently matched; reviewers must not
attribute spreadsheet-only values to the PDF unless the PDF states them.

### E006 — Who coordinated C-START?

**Claim correctness:** The expected person is Prof. Sarah Thomas, directly
identified as event coordinator in the C-START event report PDF page 1 and in
the event-log row 2 coordinator field.

**Citation correctness:** A citation to the meeting-minutes PDF can be
structurally exact yet wrong for this claim if it only says Sarah Thomas
reported on the event and does not identify her as coordinator. The answer can
therefore be claim-correct but citation-incorrect.

**Required evidence:** Event Log row 2 and C-START event report PDF page 1.
Meeting-minutes PDF page 1 may corroborate Sarah Thomas's involvement but is
not sufficient alone for the coordinator claim.

### E007 — What happened on 10 August 2026 regarding the FDP?

**Material claims:**

- An FDP Planning meeting occurred on 10 August 2026.
- Prof. Arun Kumar chaired it.
- FDP resource persons were confirmed.
- The FDP event date/status may be mentioned only with the event-log
  evidence.

**Required evidence:** Meeting Log row 5 and Events row 3. Meeting Log row 3
and meeting-minutes PDF page 1 are related FDP evidence but refer to other
dates or planning context.

**Scope rule:** Keep the 10 August meeting and the FDP event as separate
records.

### E013 — What decisions were made regarding the FDP?

**Material claims:**

- The schedule was to be finalized at the next meeting on 25 July 2026.
- The 10 August FDP planning meeting confirmed resource persons.
- Prof. Arun Kumar may be named only where the cited row supports him.

**Required evidence:** Meeting Log rows 3 and 5; meeting-minutes PDF page 1
for the 25 July scheduling decision.

**Completeness rule:** An answer that reports only one of the two decisions is
incomplete unless it explicitly narrows its scope.

### E014 — What was reported about C-START participation?

**Material claims may include:**

- C-START occurred on 18 July 2026.
- 45 participants were reported.
- The participant category differs between sources.
- Coordinator, keynote, location, time, and feedback may be included only
  when directly supported by the cited event report or event row.

**Required evidence:** Events row 2, C-START event report PDF page 1, and
meeting-minutes PDF page 1.

**Conflict requirement:** Both observations must be stated or the discrepancy
must be explicit:

- Event report: 45 students from third and fourth year batches.
- Meeting minutes: 45 third-year students.

Saying only “45 third-year students” or only “45 students” without noting the
other observation is INCOMPLETE and generally PARTIALLY_GROUNDED.

### E015 — What happened on 25 July 2026?

**Material claims may include:**

- A Faculty Meeting occurred.
- Dr. Reena Nair chaired it and the meeting-log attendee count was 5.
- The FDP schedule for August was finalized.
- Faculty attendance facts must use the 25 July column/header.

**Required evidence:** Meeting Log row 3; Faculty Attendance cells C2:C6;
faculty notice PDF page 1 and meeting-minutes PDF page 1 only for claims they
actually state.

**Spreadsheet rule:** Verify sheet `Faculty Attendance`, the exact row and
cell, header `25-Jul-2026 (Faculty Mtg)`, faculty name, and value. A citation
to an 18 July or 2 August cell is wrong for this question.

### E016 — What happened on 10 August 2026?

**Material distinctions:**

- **Scheduled:** a date or meeting/event is placed on a calendar; the notice
  discusses the FDP planned for 10 August.
- **Planned:** preparation or intention, such as the proposed FDP week in the
  meeting minutes.
- **Completed:** the Events row 3 records the Faculty Development Programme
  as `Completed` for 10–14 August 2026.

An answer must not replace “Completed” with “planned” when relying on Events
row 3, nor treat a planning meeting as proof that the event itself was
completed unless the event record supports it.

**Required evidence:** Events row 3 and Meeting Log row 5. Notice PDF page 1
and meeting-minutes PDF page 1 provide planning/date context.

### E017 — How many participants were reported for C-START?

**Material claim:** The reported count is 45.

**Required evidence:** Events row 2, C-START event report PDF page 1, and
meeting-minutes PDF page 1.

**Conflict requirement:** The numeric count is the same, but the category
differs. A fully grounded answer should say that both sources report 45 while
describing different year-group coverage. Returning only `45` is numerically
correct but INCOMPLETE for conflict-aware review.

## Facts not safely collapsed by this rubric

- The rubric does not decide whether every broad date query must list every
  attendance row verbatim; it identifies attendance as relevant and requires
  exact headers/cells when attendance is claimed.
- It does not infer facts from excluded evidence after truncation.
- It does not assign factual conclusions to the current model outputs. Those
  conclusions belong in completed human-review records.
