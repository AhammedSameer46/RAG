import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from cs_ingest.answer_pipeline import AnswerPipeline
from cs_ingest.answer_plan import build_answer_plan
from cs_ingest.citation_builder import CitationBuilder
from cs_ingest.evidence_response import build_evidence_response
from cs_ingest.evidence_selector import EvidenceSelectionConfig, EvidenceSelector
from cs_ingest.model_facing_context import build_model_facing_context
from cs_ingest.ollama_answer_generator import OllamaAnswerGenerator, _user_prompt
from cs_ingest.pipeline import QueryRetrievalPipeline


ROOT = Path(__file__).parents[1]


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload
        self.status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class CapturingGenerator:
    def __init__(self):
        self.context = None

    def generate(self, question, model_context):
        del question
        self.context = copy.deepcopy(model_context)
        return {
            "status": "answered",
            "claims": [{"text": "A test claim.", "citation_refs": ["E1"]}],
        }


class ModelFacingOllamaIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.query_pipeline = QueryRetrievalPipeline.from_json(
            ROOT / "output" / "sample_normalized.json"
        )

    def test_compact_context_reaches_pipeline_generator(self):
        generator = CapturingGenerator()
        result = AnswerPipeline(
            self.query_pipeline,
            generator,
            EvidenceSelector(),
            EvidenceSelectionConfig(),
        ).run("Who coordinated C-START?")
        self.assertTrue(result["validation"]["valid"])
        self.assertIn("answer_plan", generator.context)
        self.assertIn("evidence", generator.context)
        self.assertNotIn("records", generator.context)
        self.assertNotIn("supporting_evidence", generator.context)
        self.assertNotIn("independent_evidence", generator.context)

    def test_ollama_serializes_model_context_without_reconstruction(self):
        context = {
            "answer_plan": {
                "observations": [
                    {"evidence_ids": ["E1"], "preserve_separately": False}
                ],
                "conflict_groups": [],
                "lifecycle_groups": [],
                "coverage": {"complete": True},
            },
            "evidence": [
                {
                    "id": "E1",
                    "source": "meeting.pdf",
                    "location": {"page": 1},
                    "text": "A test claim.",
                }
            ],
        }
        answer = {
            "status": "answered",
            "claims": [{"text": "A test claim.", "citation_refs": ["E1"]}],
        }
        with patch(
            "cs_ingest.ollama_answer_generator.request.urlopen",
            return_value=FakeHTTPResponse(
                json.dumps({"response": json.dumps(answer)}).encode()
            ),
        ) as urlopen:
            result = OllamaAnswerGenerator().generate("Question", context)
        payload = json.loads(urlopen.call_args.args[0].data)
        model_payload = json.loads(
            payload["prompt"].split("Model context (JSON):\n", 1)[1]
        )
        self.assertEqual(model_payload, {"question": "Question", "model_context": context})
        self.assertEqual(result, answer)

    def test_plan_conflict_lifecycle_and_coverage_are_preserved(self):
        response = {
            "status": "answerable",
            "answer_context": {
                "records": [],
                "supporting_evidence": [
                    {"evidence_id": "a", "source_id": "s", "filename": "a.pdf",
                     "extracted_text": "A", "page": 1},
                    {"evidence_id": "b", "source_id": "s", "filename": "b.pdf",
                     "extracted_text": "B", "page": 2},
                ],
                "independent_evidence": [],
            },
            "selection": {
                "coverage": {
                    "coverage_complete": False,
                    "truncated": True,
                    "excluded_evidence_ids": ["c"],
                    "conflict_groups": [{
                        "coverage_group_id": "conflict:1",
                        "evidence_ids": ["a", "b"],
                        "complete": True,
                    }],
                    "lifecycle_groups": [{
                        "coverage_group_id": "lifecycle:1",
                        "evidence_ids": ["a", "b"],
                        "complete": True,
                    }],
                }
            },
        }
        response["answer_plan"] = build_answer_plan(response)
        context = build_model_facing_context(response)
        self.assertEqual(context["answer_plan"]["coverage"], {
            "complete": False,
            "reason": "selection_budget",
        })
        self.assertEqual(context["answer_plan"]["conflict_groups"][0]["observation_indexes"], [0, 1])
        self.assertEqual(context["answer_plan"]["lifecycle_groups"][0]["observation_indexes"], [0, 1])
        self.assertEqual([item["id"] for item in context["evidence"]], ["E1", "E2"])

    def test_original_response_remains_for_citation_builder(self):
        response = build_evidence_response(
            self.query_pipeline.run("Who coordinated C-START?")
        )
        response["answer_plan"] = build_answer_plan(response)
        context = build_model_facing_context(response)
        self.assertNotIn("source_id", json.dumps(context))
        answer = {
            "status": "answered",
            "claims": [{"text": "A test claim.", "citation_refs": ["E1"]}],
        }
        citation = CitationBuilder().build(answer, response)["citations"][0]
        self.assertEqual(citation["evidence_id"], response["answer_context"]["supporting_evidence"][0]["evidence_id"])
        self.assertIn("source_id", citation)

    def test_input_immutability(self):
        response = build_evidence_response(
            self.query_pipeline.run("Who coordinated C-START?")
        )
        response["answer_plan"] = build_answer_plan(response)
        before = copy.deepcopy(response)
        build_model_facing_context(response)
        _user_prompt("Question", build_model_facing_context(response))
        self.assertEqual(response, before)
