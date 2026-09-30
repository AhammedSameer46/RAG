import unittest
from pathlib import Path

from cs_ingest.answer_pipeline import AnswerPipeline
from cs_ingest.evidence_selector import EvidenceSelectionConfig, EvidenceSelector
from cs_ingest.pipeline import QueryRetrievalPipeline


ROOT = Path(__file__).parents[1]


class ClaimGenerator:
    def __init__(self, claims):
        self.claims = claims

    def generate(self, question, evidence_response):
        del question, evidence_response
        return {"status": "answered", "claims": self.claims}


class ClaimAnswerPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.query_pipeline = QueryRetrievalPipeline.from_json(
            ROOT / "output" / "sample_normalized.json"
        )
        cls.config = EvidenceSelectionConfig(
            max_evidence_units=3,
            max_characters=12000,
            max_records=8,
            max_characters_per_unit=None,
        )

    def run_claims(self, question, claims):
        return AnswerPipeline(
            self.query_pipeline,
            ClaimGenerator(claims),
            EvidenceSelector(),
            self.config,
        ).run(question)

    def test_e003_attendance_claim_keeps_external_contract(self):
        result = self.run_claims(
            "Was Dr. Reena Nair present at the meeting on 18 July 2026?",
            [{"text": "Dr. Reena Nair was present.", "citation_refs": ["E1"]}],
        )
        self.assertTrue(result["validation"]["valid"])
        self.assertEqual(set(result["answer"]), {"status", "answer", "citations"})
        self.assertEqual(result["answer"]["citations"][0]["location"]["cell"], "B2")

    def test_e006_coordinator_claim_uses_explicit_handle(self):
        result = self.run_claims(
            "Who coordinated C-START?",
            [{"text": "Prof. Sarah Thomas coordinated C-START.", "citation_refs": ["E1"]}],
        )
        self.assertTrue(result["validation"]["valid"])
        self.assertEqual(len(result["answer"]["citations"]), 1)

    def test_e014_conflicting_participant_claims_remain_separate(self):
        result = self.run_claims(
            "What was reported about C-START participation?",
            [
                {
                    "text": "The event report states that 45 third- and fourth-year students participated.",
                    "citation_refs": ["E1"],
                },
                {
                    "text": "The meeting minutes separately report 45 third-year students attended.",
                    "citation_refs": ["E2"],
                },
            ],
        )
        self.assertTrue(result["validation"]["valid"])
        self.assertIn("event report", result["answer"]["answer"])
        self.assertIn("meeting minutes", result["answer"]["answer"])
        self.assertEqual(len(result["answer"]["citations"]), 2)

    def test_e016_planning_and_completion_claims_remain_separate(self):
        result = self.run_claims(
            "What happened on 10 August 2026?",
            [
                {
                    "text": "An FDP Planning meeting was held on 10 August 2026.",
                    "citation_refs": ["E1"],
                },
                {
                    "text": "The event record lists the FDP as Completed for 10–14 August 2026.",
                    "citation_refs": ["E2"],
                },
            ],
        )
        self.assertTrue(result["validation"]["valid"])
        self.assertEqual(len(result["answer"]["citations"]), 2)

    def test_e017_count_claim_can_cite_both_conflicting_observations(self):
        result = self.run_claims(
            "How many participants were reported for C-START?",
            [
                {
                    "text": "Both selected sources report 45 participants.",
                    "citation_refs": ["E1", "E2"],
                }
            ],
        )
        self.assertTrue(result["validation"]["valid"])
        self.assertEqual(len(result["answer"]["citations"]), 2)
