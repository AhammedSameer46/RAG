import unittest
from copy import deepcopy
from pathlib import Path

from cs_ingest.answer_pipeline import AnswerPipeline
from cs_ingest.evidence_response import build_evidence_response
from cs_ingest.mock_answer_generator import MockAnswerGenerator
from cs_ingest.pipeline import QueryRetrievalPipeline


ROOT = Path(__file__).parents[1]


class InvalidGenerator:
    def generate(self, _evidence_response):
        del _evidence_response
        return {
            "status": "answered",
            "answer": "Invalid claim.",
            "citations": [
                {
                    "evidence_id": "outside-package",
                    "source_id": "unknown",
                    "filename": "unknown.pdf",
                    "location": {"page": 1},
                }
            ],
        }


class MockAnswerGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.query_pipeline = QueryRetrievalPipeline.from_json(
            ROOT / "output" / "sample_normalized.json"
        )
        cls.pipeline = AnswerPipeline(cls.query_pipeline)

    def test_date_query_generates_valid_cited_answer(self):
        result = self.pipeline.run("What happened on 18 July 2026?")
        self.assertEqual(result["answer"]["status"], "answered")
        self.assertTrue(result["answer"]["answer"])
        self.assertTrue(result["answer"]["citations"])
        self.assertTrue(result["validation"]["valid"])

    def test_cstart_has_valid_provenance_citation(self):
        result = self.pipeline.run("Who coordinated C-START?")
        self.assertTrue(result["validation"]["valid"])
        self.assertTrue(
            any(
                citation["location"].get("page") is not None
                for citation in result["answer"]["citations"]
            )
        )

    def test_lab_procurement_can_cite_independent_evidence(self):
        result = self.pipeline.run("What was discussed about lab procurement?")
        evidence_response = result["evidence_response"]
        supporting_ids = {
            item["evidence_id"]
            for item in evidence_response["answer_context"]["supporting_evidence"]
        }
        independent_ids = {
            item["evidence_id"]
            for item in evidence_response["answer_context"]["independent_evidence"]
        }
        cited_ids = {item["evidence_id"] for item in result["answer"]["citations"]}
        self.assertTrue(independent_ids - supporting_ids)
        self.assertTrue((independent_ids - supporting_ids) & cited_ids)
        self.assertTrue(result["validation"]["valid"])

    def test_insufficient_evidence_stays_empty_and_valid(self):
        result = self.pipeline.run("What happened on 10 January 2099?")
        self.assertEqual(result["answer"], {
            "status": "insufficient_evidence",
            "answer": "",
            "citations": [],
        })
        self.assertTrue(result["validation"]["valid"])

    def test_clarification_never_generates_factual_answer(self):
        result = self.pipeline.run("What happened on 18 July?")
        self.assertEqual(result["answer"]["status"], "clarification_required")
        self.assertEqual(result["answer"]["answer"], "")
        self.assertEqual(result["answer"]["citations"], [])
        self.assertTrue(result["validation"]["valid"])

    def test_invalid_generator_result_is_preserved_and_rejected(self):
        pipeline = AnswerPipeline(self.query_pipeline, InvalidGenerator())
        result = pipeline.run("What happened on 18 July 2026?")
        self.assertEqual(result["answer"]["answer"], "Invalid claim.")
        self.assertFalse(result["validation"]["valid"])
        self.assertTrue(
            any(
                error["code"] == "UNKNOWN_EVIDENCE_ID"
                for error in result["validation"]["errors"]
            )
        )

    def test_evidence_response_is_unchanged(self):
        evidence_response = build_evidence_response(
            self.query_pipeline.run("Who coordinated C-START?")
        )
        original = deepcopy(evidence_response)
        MockAnswerGenerator().generate(evidence_response)
        self.assertEqual(evidence_response, original)


if __name__ == "__main__":
    unittest.main()
