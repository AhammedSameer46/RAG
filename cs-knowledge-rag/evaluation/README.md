# Initial Deterministic Evaluation Dataset

This directory contains the first regression/evaluation set for the local
institutional RAG prototype:

- `sample_questions.json` contains questions and expected deterministic
  retrieval outcomes.
- The cases are based only on the current sample institutional records in
  `output/sample_normalized.json` and the behavior implemented by the
  deterministic query-understanding, retrieval, evidence-response, and answer
  contract layers.

This is an initial regression set, not a production benchmark. The sample
files are mock institutional data and do not represent the final college
dataset.

## Expected fields

Each case contains:

- `id`: stable evaluation-case identifier
- `question`: natural-language question sent to the current pipeline
- `expected_status`:
  - `answerable`: deterministic retrieval is executable and evidence exists
  - `insufficient_evidence`: retrieval is executable but no evidence matches
  - `clarification_required`: the request is ambiguous, unsupported, or
    insufficiently precise to execute safely
- `expected_record_types`: normalized record types expected from retrieval
- `expected_source_ids`: source identities expected in the evidence package
- `expected_evidence_ids`: all evidence IDs expected to be relevant to the
  case
- `expected_supporting_evidence_ids`: evidence referenced by matching
  normalized records
- `expected_independent_evidence_ids`: evidence matched independently, such as
  keyword or date-mention evidence, rather than serving as record support
- `notes`: deterministic scope or provenance notes

Empty expected arrays are intentional for clarification-required and
insufficient-evidence cases.

## What can be evaluated now

Retrieval correctness can be evaluated deterministically, including:

- status classification
- record-type filtering
- exact date and date-role behavior
- source IDs and evidence IDs
- supporting versus independently matched evidence
- provenance locations such as PDF pages and spreadsheet cells
- preservation of conflicting source observations

Natural-language answer quality cannot yet be fully evaluated because no real
answer generator is connected. A future evaluation set can add
human-reviewed expected answers, citation-quality judgments, grounding
judgments, larger datasets, and provider-specific model comparisons.

## Conflict case

The C-START participation case intentionally preserves two source statements:

- one source reports 45 third-year students attended
- another source reports 45 students from the third and fourth year batches
  participated

The dataset does not resolve this difference. A future answer generator must
preserve both observations and cite their respective evidence.
