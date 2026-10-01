import json
import unittest
from pathlib import Path
from unittest.mock import patch

from cs_ingest.claim_answer_contract import validate_claim_answer
from cs_ingest.ollama_answer_generator import (
    OllamaAnswerGenerator,
    _SYSTEM_PROMPT,
)
from cs_ingest.answer_plan import build_answer_plan
from cs_ingest.model_facing_context import build_model_facing_context


ROOT = Path(__file__).parents[1]


class FakeResponse:
    def __init__(self, answer):
        self.payload = json.dumps({"response": json.dumps(answer)}).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


def evidence_response(status="answerable"):
    return {
        "status": status,
        "answer_context": {
            "supporting_evidence": [
                {
                    "evidence_id": "participant-report",
                    "source_id": "source-1",
                    "filename": "report.pdf",
                    "page": 1,
                    "extracted_text": "45 third and fourth year students participated.",
                },
                {
                    "evidence_id": "participant-minutes",
                    "source_id": "source-2",
                    "filename": "minutes.pdf",
                    "page": 1,
                    "extracted_text": "45 third-year students attended.",
                },
                {
                    "evidence_id": "planning",
                    "source_id": "source-3",
                    "filename": "log.xlsx",
                    "sheet": "Meeting Log",
                    "row": 5,
                    "extracted_text": "FDP Planning meeting on 10 August 2026.",
                },
                {
                    "evidence_id": "completed",
                    "source_id": "source-4",
                    "filename": "log.xlsx",
                    "sheet": "Events",
                    "row": 3,
                    "extracted_text": "FDP event, 10-14 August 2026, Completed.",
                },
            ],
            "independent_evidence": [],
        },
    }


class AnswerGenerationObligationTests(unittest.TestCase):
    def generate(self, answer, response=None):
        response = response or evidence_response()
        response["answer_plan"] = build_answer_plan(response)
        model_context = build_model_facing_context(response)
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=FakeResponse(answer),
        ):
            return OllamaAnswerGenerator().generate(
                "What was reported?", model_context
            )

    def validate(self, answer, response=None):
        return validate_claim_answer(answer, response or evidence_response())

    def test_conflicting_observations_can_be_separate_claims(self):
        answer = self.generate(
            {
                "status": "answered",
                "claims": [
                    {"text": "45 third and fourth year students participated.", "citation_refs": ["E1"]},
                    {"text": "45 third-year students attended.", "citation_refs": ["E2"]},
                ],
            }
        )
        self.validate(answer)
        self.assertEqual(len(answer["claims"]), 2)
        self.assertEqual({*answer["claims"][0]["citation_refs"], *answer["claims"][1]["citation_refs"]}, {"E1", "E2"})

    def test_lifecycle_observations_can_be_separate_claims(self):
        answer = self.generate(
            {
                "status": "answered",
                "claims": [
                    {"text": "An FDP Planning meeting occurred on 10 August 2026.", "citation_refs": ["E3"]},
                    {"text": "The FDP event was recorded as Completed for 10-14 August 2026.", "citation_refs": ["E4"]},
                ],
            }
        )
        self.validate(answer)
        self.assertEqual(len(answer["claims"]), 2)
        self.assertEqual(
            {ref for claim in answer["claims"] for ref in claim["citation_refs"]},
            {"E3", "E4"},
        )

    def test_primary_and_secondary_facts_remain_multiple_claims(self):
        answer = self.generate(
            {
                "status": "answered",
                "claims": [
                    {"text": "The event was held in the seminar hall.", "citation_refs": ["E1"]},
                    {"text": "The keynote was delivered by the invited speaker.", "citation_refs": ["E1"]},
                ],
            }
        )
        self.validate(answer)
        self.assertGreaterEqual(len(answer["claims"]), 2)

    def test_one_fact_may_have_two_direct_sources(self):
        answer = self.generate(
            {
                "status": "answered",
                "claims": [
                    {"text": "The reported participant count was 45.", "citation_refs": ["E1", "E2"]},
                ],
            }
        )
        self.validate(answer)
        self.assertEqual(answer["claims"][0]["citation_refs"], ["E1", "E2"])

    def test_non_answerable_statuses_keep_empty_claims(self):
        for status in ("insufficient_evidence", "clarification_required"):
            with self.subTest(status=status):
                response = evidence_response(status)
                response["answer_context"] = {
                    "supporting_evidence": [],
                    "independent_evidence": [],
                    "records": [],
                }
                response["answer_plan"] = build_answer_plan(response)
                self.assertEqual(
                    build_model_facing_context(response)["evidence"], []
                )

    def test_claim_shape_rejects_raw_provenance(self):
        answer = {
            "status": "answered",
            "claims": [
                {
                    "text": "The fact is supported.",
                    "citation_refs": ["E1"],
                    "filename": "report.pdf",
                }
            ],
        }
        with self.assertRaises(ValueError):
            self.validate(answer)

    def test_prompt_states_generic_observation_preservation_rules(self):
        required_phrases = (
            "Every materially distinct supported observation",
            "different values, categories, or statuses",
            "Planning, meeting, status, and event lifecycle stages",
            "Do not infer a relationship",
            "If evidence is insufficient",
        )
        for phrase in required_phrases:
            self.assertIn(phrase, _SYSTEM_PROMPT)
        for forbidden in ("E001", "E014", "E016", "E017", "C-START"):
            self.assertNotIn(forbidden, _SYSTEM_PROMPT)
