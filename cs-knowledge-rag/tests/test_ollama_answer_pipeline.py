import json
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from cs_ingest.answer_pipeline import AnswerPipeline
from cs_ingest.evidence_response import build_evidence_response
from cs_ingest.ollama_answer_generator import (
    OllamaAnswerGenerator,
    OllamaHTTPError,
    OllamaResponseError,
)
from cs_ingest.pipeline import QueryRetrievalPipeline


ROOT = Path(__file__).parents[1]


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        del exc_type, exc_value, traceback
        return False

    def read(self):
        return self.payload


class OllamaAnswerPipelineIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.query_pipeline = QueryRetrievalPipeline.from_json(
            ROOT / "output" / "sample_normalized.json"
        )

    @staticmethod
    def _model_payload(answer):
        return json.dumps({"response": json.dumps(answer)}).encode("utf-8")

    @staticmethod
    def _citation(evidence):
        return {
            "evidence_id": evidence["evidence_id"],
            "source_id": evidence["source_id"],
            "filename": evidence["filename"],
            "location": {
                field: evidence[field]
                for field in ("page", "sheet", "row", "cell", "cell_range")
                if field in evidence
            },
        }

    def _answerable_answer(self, evidence_response):
        return {
            "status": "answered",
            "claims": [{"text": "The retrieved evidence identifies the coordinator.", "citation_refs": ["E1"]}],
        }

    def test_answerable_question_uses_real_pipeline_and_validates(self):
        generator = OllamaAnswerGenerator(model="integration-test-model")
        pipeline = AnswerPipeline(self.query_pipeline, generator)
        captured = {}
        expected_evidence = pipeline.query_pipeline.run("Who coordinated C-START?")

        def mocked_urlopen(http_request, timeout):
            captured["request"] = http_request
            captured["timeout"] = timeout
            payload = json.loads(http_request.data)
            captured["prompt"] = payload["prompt"]
            return FakeHTTPResponse(
                self._model_payload({"status": "answered", "claims": [
                    {"text": "The retrieved evidence identifies the coordinator.", "citation_refs": ["E1"]}
                ]})
            )

        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            side_effect=mocked_urlopen,
        ) as urlopen:
            result = pipeline.run("Who coordinated C-START?")

        self.assertEqual(result["question"], "Who coordinated C-START?")
        self.assertEqual(result["evidence_response"]["status"], "answerable")
        self.assertTrue(result["evidence_response"]["answer_context"]["records"])
        self.assertTrue(result["validation"]["valid"])
        self.assertEqual(result["answer"]["status"], "answered")
        self.assertEqual(captured["timeout"], 30.0)
        self.assertEqual(urlopen.call_count, 1)
        self.assertIn("Who coordinated C-START?", captured["prompt"])
        self.assertIn('"answer_plan"', captured["prompt"])
        self.assertIn('"model_context"', captured["prompt"])
        self.assertNotIn('"supporting_evidence"', captured["prompt"])
        self.assertNotIn("retriever", captured["prompt"].lower())
        self.assertNotIn("sample_normalized.json", captured["prompt"])
        self.assertNotEqual(expected_evidence, result["evidence_response"])
        self.assertEqual(
            result["evidence_response"]["query_understanding"],
            expected_evidence["query_understanding"],
        )

    def test_invalid_citation_is_preserved_and_rejected(self):
        invalid_answer = {
            "status": "answered",
            "claims": [{"text": "Unsupported citation.", "citation_refs": ["E99"]}],
        }
        pipeline = AnswerPipeline(
            self.query_pipeline,
            OllamaAnswerGenerator(),
        )
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=FakeHTTPResponse(self._model_payload(invalid_answer)),
        ):
            with self.assertRaises(ValueError):
                pipeline.run("Who coordinated C-START?")

    def test_malformed_model_json_raises_provider_error(self):
        pipeline = AnswerPipeline(self.query_pipeline, OllamaAnswerGenerator())
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=FakeHTTPResponse(b"{malformed"),
        ):
            with self.assertRaises(OllamaResponseError):
                pipeline.run("Who coordinated C-START?")

    def test_http_500_raises_provider_error(self):
        pipeline = AnswerPipeline(self.query_pipeline, OllamaAnswerGenerator())
        http_error = HTTPError("http://localhost", 500, "server error", {}, None)
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            side_effect=http_error,
        ):
            with self.assertRaises(OllamaHTTPError):
                pipeline.run("Who coordinated C-START?")

    def test_insufficient_evidence_never_calls_ollama(self):
        pipeline = AnswerPipeline(self.query_pipeline, OllamaAnswerGenerator())
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen"
        ) as urlopen:
            result = pipeline.run("What happened on 10 January 2099?")
        self.assertEqual(result["evidence_response"]["status"], "insufficient_evidence")
        self.assertEqual(result["answer"]["status"], "insufficient_evidence")
        self.assertTrue(result["validation"]["valid"])
        urlopen.assert_not_called()

    def test_clarification_required_never_calls_ollama(self):
        pipeline = AnswerPipeline(self.query_pipeline, OllamaAnswerGenerator())
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen"
        ) as urlopen:
            result = pipeline.run("What happened on 18 July?")
        self.assertEqual(result["evidence_response"]["status"], "clarification_required")
        self.assertEqual(result["answer"]["status"], "clarification_required")
        self.assertTrue(result["validation"]["valid"])
        urlopen.assert_not_called()

    def test_evidence_context_is_unchanged_and_plan_is_additive(self):
        question = "Who coordinated C-START?"
        expected = build_evidence_response(self.query_pipeline.run(question))
        answer = self._answerable_answer(expected)
        pipeline = AnswerPipeline(self.query_pipeline, OllamaAnswerGenerator())
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=FakeHTTPResponse(self._model_payload(answer)),
        ):
            result = pipeline.run(question)
        self.assertEqual(
            result["evidence_response"]["answer_context"],
            expected["answer_context"],
        )
        self.assertIn("answer_plan", result["evidence_response"])


if __name__ == "__main__":
    unittest.main()
