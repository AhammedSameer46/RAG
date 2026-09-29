import json
import socket
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from cs_ingest.answer_contract import validate_answer
from cs_ingest.evidence_response import build_evidence_response
from cs_ingest.ollama_answer_generator import (
    OllamaAnswerGenerator,
    OllamaConnectionError,
    OllamaHTTPError,
    OllamaResponseError,
    OllamaTimeoutError,
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


class OllamaAnswerGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pipeline = QueryRetrievalPipeline.from_json(
            ROOT / "output" / "sample_normalized.json"
        )
        cls.evidence_response = build_evidence_response(
            pipeline.run("Who coordinated C-START?")
        )
        cls.clarification_response = build_evidence_response(
            pipeline.run("What happened on 18 July?")
        )
        cls.insufficient_response = build_evidence_response(
            pipeline.run("What happened on 10 January 2099?")
        )

    @staticmethod
    def _model_payload(answer):
        return json.dumps({"response": json.dumps(answer)}).encode("utf-8")

    def test_answerable_request_sends_question_and_structured_evidence(self):
        answer = {"status": "answered", "answer": "Evidence.", "citations": []}
        response = FakeHTTPResponse(self._model_payload(answer))
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=response,
        ) as urlopen:
            result = OllamaAnswerGenerator(
                base_url="http://127.0.0.1:11434/", model="test-model"
            ).generate("Who coordinated C-START?", self.evidence_response)

        self.assertEqual(result, answer)
        http_request = urlopen.call_args.args[0]
        payload = json.loads(http_request.data)
        self.assertEqual(payload["model"], "test-model")
        self.assertEqual(payload["format"], "json")
        self.assertFalse(payload["stream"])
        self.assertIn("Who coordinated C-START?", payload["prompt"])
        self.assertIn("answer_context", payload["prompt"])
        self.assertNotIn("sample_normalized.json", payload["prompt"])
        self.assertNotIn("retriever", payload["prompt"].lower())

    def test_non_answerable_statuses_do_not_call_ollama(self):
        generator = OllamaAnswerGenerator()
        with patch("cs_ingest.ollama_answer_generator.request.urlopen") as urlopen:
            clarification = generator.generate("Question", self.clarification_response)
            insufficient = generator.generate("Question", self.insufficient_response)
        self.assertEqual(
            clarification,
            {"status": "clarification_required", "answer": "", "citations": []},
        )
        self.assertEqual(
            insufficient,
            {"status": "insufficient_evidence", "answer": "", "citations": []},
        )
        urlopen.assert_not_called()

    def test_valid_json_response_is_parsed(self):
        answer = {"status": "answered", "answer": "Evidence.", "citations": []}
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=FakeHTTPResponse(self._model_payload(answer)),
        ):
            self.assertEqual(
                OllamaAnswerGenerator().generate("Question", self.evidence_response),
                answer,
            )

    def test_valid_provider_result_passes_answer_contract(self):
        evidence = self.evidence_response["answer_context"]["supporting_evidence"][0]
        answer = {
            "status": "answered",
            "answer": "The retrieved record contains the coordination detail.",
            "citations": [
                {
                    "evidence_id": evidence["evidence_id"],
                    "source_id": evidence["source_id"],
                    "filename": evidence["filename"],
                    "location": {
                        field: evidence[field]
                        for field in ("page", "sheet", "row", "cell", "cell_range")
                        if field in evidence
                    },
                }
            ],
        }
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=FakeHTTPResponse(self._model_payload(answer)),
        ):
            result = OllamaAnswerGenerator().generate(
                "Question", self.evidence_response
            )
        self.assertEqual(
            validate_answer(result, self.evidence_response),
            {"valid": True, "errors": []},
        )

    def test_malformed_json_raises_response_error(self):
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=FakeHTTPResponse(b"{not-json"),
        ):
            with self.assertRaises(OllamaResponseError):
                OllamaAnswerGenerator().generate("Question", self.evidence_response)

    def test_missing_fields_raises_response_error(self):
        payload = self._model_payload({"status": "answered", "answer": "Missing citations"})
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=FakeHTTPResponse(payload),
        ):
            with self.assertRaises(OllamaResponseError):
                OllamaAnswerGenerator().generate("Question", self.evidence_response)

    def test_unsupported_status_raises_response_error(self):
        payload = self._model_payload(
            {"status": "unknown", "answer": "No", "citations": []}
        )
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=FakeHTTPResponse(payload),
        ):
            with self.assertRaises(OllamaResponseError):
                OllamaAnswerGenerator().generate("Question", self.evidence_response)

    def test_http_error_is_explicit(self):
        http_error = HTTPError("http://localhost", 503, "unavailable", {}, None)
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            side_effect=http_error,
        ):
            with self.assertRaises(OllamaHTTPError):
                OllamaAnswerGenerator().generate("Question", self.evidence_response)

    def test_timeout_is_explicit(self):
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            side_effect=socket.timeout(),
        ):
            with self.assertRaises(OllamaTimeoutError):
                OllamaAnswerGenerator().generate("Question", self.evidence_response)

    def test_connection_failure_is_explicit(self):
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            side_effect=URLError("connection refused"),
        ):
            with self.assertRaises(OllamaConnectionError):
                OllamaAnswerGenerator().generate("Question", self.evidence_response)

    def test_evidence_response_is_not_mutated(self):
        snapshot = deepcopy(self.evidence_response)
        answer = {"status": "answered", "answer": "Evidence.", "citations": []}
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=FakeHTTPResponse(self._model_payload(answer)),
        ):
            OllamaAnswerGenerator().generate("Question", self.evidence_response)
        self.assertEqual(self.evidence_response, snapshot)

    def test_invalid_citations_pass_through_for_contract_validation(self):
        answer = {
            "status": "answered",
            "answer": "Unsupported citation.",
            "citations": [
                {
                    "evidence_id": "not-retrieved",
                    "source_id": "unknown",
                    "filename": "unknown.pdf",
                    "location": {"page": 1},
                }
            ],
        }
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=FakeHTTPResponse(self._model_payload(answer)),
        ):
            result = OllamaAnswerGenerator().generate(
                "Question", self.evidence_response
            )
        validation = validate_answer(result, self.evidence_response)
        self.assertFalse(validation["valid"])
        self.assertEqual(result["citations"][0]["evidence_id"], "not-retrieved")

    def test_unknown_evidence_status_fails_before_http(self):
        with patch("cs_ingest.ollama_answer_generator.request.urlopen") as urlopen:
            with self.assertRaises(OllamaResponseError):
                OllamaAnswerGenerator().generate(
                    "Question", {"status": "unknown", "answer_context": {}}
                )
        urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
