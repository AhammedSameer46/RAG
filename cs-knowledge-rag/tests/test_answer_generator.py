import unittest
from copy import deepcopy
from pathlib import Path

from cs_ingest.answer_generator import AnswerGenerator
from cs_ingest.answer_pipeline import AnswerPipeline
from cs_ingest.claim_answer_contract import ClaimAnswerContractError
from cs_ingest.mock_answer_generator import MockAnswerGenerator
from cs_ingest.pipeline import QueryRetrievalPipeline


ROOT = Path(__file__).parents[1]


class RecordingGenerator:
    def __init__(self):
        self.question = None
        self.model_context = None

    def generate(self, question, model_context):
        self.question = question
        self.model_context = model_context
        evidence = model_context["evidence"][0]
        return {
            "status": "answered",
            "claims": [{"text": "Recorded evidence.", "citation_refs": ["E1"]}],
        }


class InvalidGenerator:
    def generate(self, question, evidence_response):
        del question, evidence_response
        return {"status": "answered", "claims": [{"text": "Uncited claim.", "citation_refs": []}]}


class AnswerGeneratorInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.query_pipeline = QueryRetrievalPipeline.from_json(
            ROOT / "output" / "sample_normalized.json"
        )

    def test_mock_generator_can_be_injected(self):
        generator = MockAnswerGenerator()
        pipeline = AnswerPipeline(self.query_pipeline, generator)
        result = pipeline.run("What happened on 18 July 2026?")
        self.assertTrue(result["validation"]["valid"])

    def test_custom_generator_receives_question_and_evidence_response(self):
        generator = RecordingGenerator()
        self.assertIsInstance(generator, AnswerGenerator)
        pipeline = AnswerPipeline(self.query_pipeline, generator)
        question = "Who coordinated C-START?"
        result = pipeline.run(question)
        self.assertEqual(generator.question, question)
        self.assertIsNotNone(generator.model_context)
        self.assertIn("answer_plan", generator.model_context)
        self.assertIn("evidence", generator.model_context)
        self.assertNotIn("answer_context", generator.model_context)
        self.assertNotIn("sample_normalized.json", str(generator.model_context))
        self.assertTrue(result["validation"]["valid"])

    def test_custom_generator_output_is_validated(self):
        pipeline = AnswerPipeline(self.query_pipeline, RecordingGenerator())
        result = pipeline.run("What happened on 18 July 2026?")
        self.assertEqual(result["answer"]["answer"], "Recorded evidence.")
        self.assertEqual(result["validation"], {"valid": True, "errors": []})

    def test_invalid_custom_generator_output_is_rejected_before_final_validation(self):
        pipeline = AnswerPipeline(self.query_pipeline, InvalidGenerator())
        with self.assertRaises(ClaimAnswerContractError):
            pipeline.run("What happened on 18 July 2026?")

    def test_clarification_does_not_call_custom_generator(self):
        generator = RecordingGenerator()
        pipeline = AnswerPipeline(self.query_pipeline, generator)
        result = pipeline.run("What happened on 18 July?")
        self.assertEqual(result["answer"]["status"], "clarification_required")
        self.assertIsNone(generator.question)
        self.assertTrue(result["validation"]["valid"])

    def test_insufficient_evidence_does_not_call_custom_generator(self):
        generator = RecordingGenerator()
        pipeline = AnswerPipeline(self.query_pipeline, generator)
        result = pipeline.run("What happened on 10 January 2099?")
        self.assertEqual(result["answer"]["status"], "insufficient_evidence")
        self.assertIsNone(generator.question)
        self.assertTrue(result["validation"]["valid"])

    def test_custom_generator_does_not_mutate_evidence_response(self):
        generator = RecordingGenerator()
        pipeline = AnswerPipeline(self.query_pipeline, generator)
        result = pipeline.run("Who coordinated C-START?")
        snapshot = deepcopy(result["evidence_response"])
        generator.generate("again", generator.model_context)
        self.assertEqual(result["evidence_response"], snapshot)


if __name__ == "__main__":
    unittest.main()
