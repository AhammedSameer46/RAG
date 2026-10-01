import json
import socket
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from cs_ingest.answer_contract import validate_answer
from cs_ingest.answer_plan import build_answer_plan
from cs_ingest.citation_builder import CitationBuilder
from cs_ingest.evidence_response import build_evidence_response
from cs_ingest.ollama_answer_generator import (
    OllamaAnswerGenerator,
    OllamaConnectionError,
    OllamaHTTPError,
    OllamaResponseError,
    OllamaTimeoutError,
    _SYSTEM_PROMPT,
    _user_prompt,
)
from cs_ingest.pipeline import QueryRetrievalPipeline
from cs_ingest.model_facing_context import build_model_facing_context


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
        cls.evidence_response["answer_plan"] = build_answer_plan(cls.evidence_response)
        cls.model_context = build_model_facing_context(cls.evidence_response)
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
        answer = {"status": "answered", "claims": [{"text": "Evidence.", "citation_refs": ["E1"]}]}
        response = FakeHTTPResponse(self._model_payload(answer))
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=response,
        ) as urlopen:
            result = OllamaAnswerGenerator(
                base_url="http://127.0.0.1:11434/", model="test-model"
            ).generate("Who coordinated C-START?", self.model_context)

        self.assertEqual(result, answer)
        http_request = urlopen.call_args.args[0]
        payload = json.loads(http_request.data)
        self.assertEqual(payload["model"], "test-model")
        self.assertEqual(payload["format"], "json")
        self.assertFalse(payload["stream"])
        self.assertIn("Who coordinated C-START?", payload["prompt"])
        self.assertIn("Model context (JSON):", payload["prompt"])
        self.assertIn('"question": "Who coordinated C-START?"', payload["prompt"])
        self.assertIn('"answer_plan"', payload["prompt"])
        self.assertIn('"model_context"', payload["prompt"])
        self.assertNotIn('"answer_context"', payload["prompt"])
        self.assertNotIn('"supporting_evidence"', payload["prompt"])
        self.assertIn('"id": "E1"', payload["prompt"])
        self.assertIn('"evidence"', payload["prompt"])
        self.assertNotIn("selection", payload["prompt"])
        self.assertNotIn("query_understanding", payload["prompt"])
        self.assertNotIn('"sources"', payload["prompt"])
        self.assertIn('"coverage"', payload["prompt"])
        self.assertNotIn("sample_normalized.json", payload["prompt"])
        self.assertNotIn("retriever", payload["prompt"].lower())

    def test_system_prompt_describes_explicit_answer_contract(self):
        for field in (
            "status",
            "answer",
            "claims",
        ):
            self.assertIn(field, _SYSTEM_PROMPT)
        self.assertIn("Never output source IDs, evidence IDs, filenames, or locations.", _SYSTEM_PROMPT)
        self.assertIn('"answered | insufficient_evidence | clarification_required"', _SYSTEM_PROMPT)
        self.assertIn("EXACTLY these three top-level fields", _SYSTEM_PROMPT)

    def test_user_prompt_contains_question_plan_and_answer_context(self):
        prompt = _user_prompt("Question", self.model_context)
        expected_context = json.dumps({
            "question": "Question",
            "model_context": self.model_context,
        }, sort_keys=True)
        self.assertEqual(
            prompt,
            "Model context (JSON):\n" + expected_context,
        )
        self.assertNotIn("source_id", prompt)
        self.assertNotIn("query_understanding", prompt)
        self.assertNotIn('"sources"', prompt)

    def test_system_prompt_describes_generic_answer_plan_rules(self):
        for text in (
            "The Answer Plan is deterministic metadata",
            "Preserve every observation marked for separate preservation.",
            "Preserve every lifecycle distinction marked as required.",
            "Cite the underlying evidence handles, never the Answer Plan.",
            "If model-context coverage is incomplete, do not invent missing information.",
        ):
            self.assertIn(text, _SYSTEM_PROMPT)
        for term in ("E001", "E014", "E016", "E017", "C-START"):
            self.assertNotIn(term, _SYSTEM_PROMPT)

    def test_non_answerable_statuses_do_not_call_ollama(self):
        generator = OllamaAnswerGenerator()
        with patch("cs_ingest.ollama_answer_generator.request.urlopen") as urlopen:
            with self.assertRaises(OllamaResponseError):
                generator.generate("Question", {"answer_plan": {}, "evidence": []})
        urlopen.assert_not_called()

    def test_valid_json_response_is_parsed(self):
        answer = {"status": "answered", "claims": [{"text": "Evidence.", "citation_refs": ["E1"]}]}
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=FakeHTTPResponse(self._model_payload(answer)),
        ):
            self.assertEqual(
                OllamaAnswerGenerator().generate("Question", self.model_context),
                answer,
            )

    def test_valid_provider_result_passes_answer_contract(self):
        answer = {
            "status": "answered",
            "claims": [{"text": "The retrieved record contains the coordination detail.", "citation_refs": ["E1"]}],
        }
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=FakeHTTPResponse(self._model_payload(answer)),
        ):
            result = OllamaAnswerGenerator().generate(
                "Question", self.model_context
            )
        self.assertEqual(
            validate_answer(
                CitationBuilder().build(result, self.evidence_response),
                self.evidence_response,
            ),
            {"valid": True, "errors": []},
        )

    def test_malformed_json_raises_response_error(self):
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=FakeHTTPResponse(b"{not-json"),
        ):
            with self.assertRaises(OllamaResponseError):
                OllamaAnswerGenerator().generate("Question", self.model_context)

    def test_missing_fields_raises_response_error(self):
        payload = self._model_payload({"status": "answered", "answer": "Missing citations"})
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=FakeHTTPResponse(payload),
        ):
            with self.assertRaises(OllamaResponseError):
                OllamaAnswerGenerator().generate("Question", self.model_context)

    def test_unsupported_status_raises_response_error(self):
        payload = self._model_payload(
            {"status": "unknown", "claims": []}
        )
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=FakeHTTPResponse(payload),
        ):
            with self.assertRaises(OllamaResponseError):
                OllamaAnswerGenerator().generate("Question", self.model_context)

    def test_http_error_is_explicit(self):
        http_error = HTTPError("http://localhost", 503, "unavailable", {}, None)
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            side_effect=http_error,
        ):
            with self.assertRaises(OllamaHTTPError):
                OllamaAnswerGenerator().generate("Question", self.model_context)

    def test_timeout_is_explicit(self):
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            side_effect=socket.timeout(),
        ):
            with self.assertRaises(OllamaTimeoutError):
                OllamaAnswerGenerator().generate("Question", self.model_context)

    def test_connection_failure_is_explicit(self):
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            side_effect=URLError("connection refused"),
        ):
            with self.assertRaises(OllamaConnectionError):
                OllamaAnswerGenerator().generate("Question", self.model_context)

    def test_evidence_response_is_not_mutated(self):
        snapshot = deepcopy(self.evidence_response)
        answer = {"status": "answered", "claims": [{"text": "Evidence.", "citation_refs": ["E1"]}]}
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=FakeHTTPResponse(self._model_payload(answer)),
        ):
            OllamaAnswerGenerator().generate("Question", self.model_context)
        self.assertEqual(self.evidence_response, snapshot)

    def test_invalid_citations_pass_through_for_contract_validation(self):
        answer = {
            "status": "answered",
            "claims": [{"text": "Unsupported citation.", "citation_refs": ["sha256:not-retrieved"]}],
        }
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=FakeHTTPResponse(self._model_payload(answer)),
        ):
            result = OllamaAnswerGenerator().generate(
                "Question", self.model_context
            )
        validation = validate_answer(result, self.evidence_response)
        self.assertFalse(validation["valid"])
        self.assertEqual(result["claims"][0]["citation_refs"], ["sha256:not-retrieved"])

    def test_unknown_evidence_status_fails_before_http(self):
        with patch("cs_ingest.ollama_answer_generator.request.urlopen") as urlopen:
            with self.assertRaises(OllamaResponseError):
                OllamaAnswerGenerator().generate(
                    "Question", {"status": "unknown", "answer_context": {}}
                )
        urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
